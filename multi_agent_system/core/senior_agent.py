"""
Senior Agent - Enhanced Manager with LLM integration and CriticAgent support
"""
import asyncio
import uuid
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from core.manager_agent import ManagerAgent
from core.event_bus import EventBus, Event, EventType
from core.state_manager import StateManager, Task, TaskStatus
from core.json_utils import extract_json, extract_and_validate_json
from core.experiment_tracker import ExperimentTracker
from llm.manager import LLMManager
from llm.base import LLMMessage
from roles.loader import get_role_loader, AgentRole


logger = logging.getLogger(__name__)


class SeniorAgent(ManagerAgent):
    """Enhanced manager agent with LLM-powered task decomposition and analysis"""

    def __init__(
        self,
        agent_id: str,
        event_bus: EventBus,
        state_manager: StateManager,
        llm_manager: LLMManager,
        critic_config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(agent_id, event_bus, state_manager)
        self.llm = llm_manager
        self.corrections: Dict[str, List[str]] = {}
        self.task_context: Dict[str, Dict] = {}

        # Load role prompt
        self._role_loader = get_role_loader()
        self._system_prompt = self._role_loader.get_system_prompt(
            AgentRole.SENIOR,
            agent_id=agent_id,
            context={"mode": "senior_manager"}
        )

        # CriticAgent configuration
        self.critic_config = critic_config or {}
        self.critic_enabled = self.critic_config.get("enabled", False)
        self.critic_blocking = self.critic_config.get("blocking", True)
        self._critique_results: Dict[str, Dict] = {}
        self._pending_critiques: Dict[str, asyncio.Event] = {}
        self._critique_subscribed = False

        # Memory management constants
        self._max_corrections_per_worker = 20
        self._max_critique_results = 50

        # Experiment tracker (autoresearch-inspired)
        self._experiment_tracker = ExperimentTracker()

    async def _publish_llm_event(self, event_type: EventType, data: Dict[str, Any]):
        """Publish an LLM transparency event"""
        event = Event(
            type=event_type,
            data=data,
            timestamp=datetime.now(),
            source=self.agent_id
        )
        await self.event_bus.publish(event)

    def _ensure_critique_subscription(self):
        """Subscribe to critique events exactly once"""
        if self.critic_enabled and not self._critique_subscribed:
            self.event_bus.subscribe(
                EventType.CRITIQUE_RECEIVED,
                self._on_critique_received
            )
            self._critique_subscribed = True

    async def receive_correction(self, worker_id: str, correction: str):
        """
        Receive correction from user for a specific worker

        Args:
            worker_id: Worker agent ID
            correction: Correction message from user
        """
        await self._log(f"Received correction for {worker_id}: {correction}")

        # Store correction (bounded)
        if worker_id not in self.corrections:
            self.corrections[worker_id] = []
        self.corrections[worker_id].append(correction)
        # Trim to prevent unbounded growth
        if len(self.corrections[worker_id]) > self._max_corrections_per_worker:
            self.corrections[worker_id] = self.corrections[worker_id][-self._max_corrections_per_worker:]

        # Analyze correction and decide action
        action = await self._analyze_correction(worker_id, correction)

        if action.get("type") == "reassign":
            # Reassign task to different worker
            task_id = action.get("task_id")
            await self._reassign_task(task_id)

        elif action.get("type") == "modify_task":
            # Modify task parameters
            task_id = action.get("task_id")
            new_params = action.get("params", {})
            await self._modify_task(task_id, new_params)

        elif action.get("type") == "pause":
            # Pause the worker
            await self._log(f"Pausing worker {worker_id}")

        await self._log(f"Correction processed: {action.get('type')}")

    async def _on_critique_received(self, event: Event):
        """Handle critique response from CriticAgent"""
        task_id = event.data.get("task_id")
        if task_id in self._pending_critiques:
            self._critique_results[task_id] = event.data
            self._pending_critiques[task_id].set()
            await self._log(f"Critique received for task {task_id}")

    async def _process_user_task(self, task_data: Dict[str, Any]):
        """Process user task with optional critic review before execution"""
        task_id = task_data["task_id"]
        task = await self.state_manager.get_task(task_id)

        if not task:
            await self._log(f"Task not found: {task_id}", "error")
            return

        await self._log(f"Processing user task: {task.description}")
        await self._publish_progress("Analyzing task", 0.1)

        # Ensure critique subscription is active (once)
        self._ensure_critique_subscription()

        # Descomponer en subtareas (LLM-powered in SeniorAgent)
        subtasks = await self._decompose_task(task)

        # Publish TASK_DECOMPOSED event for critic review
        if self.critic_enabled:
            await self._publish_decomposition_for_critique(task, subtasks)

            # Wait for critique if blocking mode
            if self.critic_blocking:
                await self._wait_for_critique(task_id)
                critique = self._critique_results.get(task_id)

                if critique and not critique.get("approved", True):
                    await self._log("Critic rejected decomposition, redecomposing...")
                    # Inject critique context into task metadata for worker visibility
                    critique_context = {
                        "critic_feedback": critique.get("reasoning", ""),
                        "critic_risks": critique.get("risks", []),
                        "critic_gaps": critique.get("gaps", []),
                        "critic_suggestions": critique.get("suggestions", []),
                        "redecomposed": True,
                    }
                    await self.state_manager.update_task(
                        task_id,
                        metadata={**(task.metadata or {}), **critique_context}
                    )
                    subtasks = await self._redecompose_with_critique(task, critique)

                # Clean up consumed critique result
                self._critique_results.pop(task_id, None)

                # Trim old critique results to prevent memory leak
                if len(self._critique_results) > self._max_critique_results:
                    oldest_keys = sorted(self._critique_results.keys())[:len(self._critique_results) - self._max_critique_results]
                    for k in oldest_keys:
                        del self._critique_results[k]

        await self._publish_progress("Creating subtasks", 0.3)

        # Crear y asignar subtareas
        for i, subtask_desc in enumerate(subtasks):
            subtask_id = f"{task_id}_sub_{i}"

            subtask = Task(
                id=subtask_id,
                description=subtask_desc["description"],
                status=TaskStatus.PENDING,
                parent_task_id=task_id
            )

            await self.state_manager.add_task(subtask)
            task.subtasks.append(subtask_id)

            # Asignar a worker
            await self._assign_to_worker(subtask_id, subtask_desc)

        await self._publish_progress("Subtasks assigned", 0.5)

        # Actualizar tarea principal con subtasks
        await self.state_manager.update_task(
            task_id,
            status=TaskStatus.IN_PROGRESS,
            started_at=datetime.now(),
            subtasks=task.subtasks  # Persist the subtasks list
        )

    async def _publish_decomposition_for_critique(self, task: Task, subtasks: List[Dict[str, Any]]):
        """Publish decomposition for critic review"""
        event = Event(
            type=EventType.TASK_DECOMPOSED,
            data={
                "task_id": task.id,
                "description": task.description,
                "subtasks": subtasks
            },
            timestamp=datetime.now(),
            source=self.agent_id
        )
        await self.event_bus.publish(event)
        await self._log(f"Published decomposition for critique: {task.id}")

        # Create event to wait on
        self._pending_critiques[task.id] = asyncio.Event()

    async def _wait_for_critique(self, task_id: str, timeout: Optional[float] = None):
        """Wait for critique to be published"""
        timeout = timeout or self.critic_config.get("timeout_seconds", 30)
        event = self._pending_critiques.get(task_id)

        if not event:
            return

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            await self._log(f"Critique timeout for task {task_id}, proceeding anyway", "warning")
        finally:
            self._pending_critiques.pop(task_id, None)

    async def _redecompose_with_critique(self, task: Task, critique: Dict) -> List[Dict[str, Any]]:
        """Redecompose task incorporating critique feedback"""
        suggestions = critique.get("suggestions", [])
        gaps = critique.get("gaps", [])
        risks = critique.get("risks", [])

        # Build context from critique
        critique_context = f"""
PREVIOUS DECOMPOSITION WAS REJECTED:
- Risks: {json.dumps(risks, indent=2)}
- Gaps: {json.dumps(gaps, indent=2)}
- Suggestions: {json.dumps(suggestions, indent=2)}

Please reconsider the decomposition addressing these issues.
"""

        prompt = f"""You are an expert project manager. Decompose this task into clear, actionable subtasks.

ORIGINAL TASK: {task.description}

CRITIQUE FEEDBACK TO INCORPORATE:
{critique_context}

Requirements:
- Break down into 2-5 concrete subtasks
- Address the gaps identified by the critic
- Mitigate the identified risks
- Each subtask should be specific and executable
- Consider the suggestions provided

Respond in JSON array format:
[
  {{
    "description": "...",
    "type": "create_file|search_web|web_request|code_analysis|update_file",
    "params": {{}},
    "priority": 1-5,
    "dependencies": []
  }}
]
"""

        try:
            messages = [
                LLMMessage(role="system", content=self._system_prompt),
                LLMMessage(role="user", content=prompt)
            ]

            result = await self.llm.chat(messages, temperature=0.5, max_tokens=2000)
            response_text = result["response"]

            # Extract JSON from response
            json_match = response_text.strip()
            if "```json" in json_match:
                json_match = json_match.split("```json")[1].split("```")[0]
            elif "```" in json_match:
                json_match = json_match.split("```")[1].split("```")[0]

            subtasks = extract_json(json_match)

            if subtasks is None:
                raise ValueError("Failed to extract valid JSON from LLM response")

            # Type guard: extract_json may return a str if the LLM returned a raw string
            if isinstance(subtasks, str):
                raise ValueError(f"LLM response parsed as str, expected list/dict. Raw: {subtasks[:100]}")

            # Validate subtasks
            if isinstance(subtasks, dict):
                subtasks = [subtasks]
            if not isinstance(subtasks, list):
                raise ValueError(f"Response is not a list, got {type(subtasks)}")

            # Ensure each subtask has required fields
            for subtask in subtasks:
                if not isinstance(subtask, dict):
                    continue
                if "description" not in subtask:
                    subtask["description"] = "Execute subtask"
                if "type" not in subtask:
                    subtask["type"] = "create_file"
                if "params" not in subtask:
                    subtask["params"] = {}

            await self._log(f"Redecomposed into {len(subtasks)} subtasks based on critique")
            return subtasks

        except Exception as e:
            logger.error(f"Failed to redecompose task with critique: {e}")
            # Emit failure event instead of crashing
            await self._emit_task_failed_event(task.id, f"Failed to redecompose: {str(e)}")
            # Fallback to simple decomposition
            return [{"description": task.description, "type": "create_file", "params": {}, "priority": 1, "dependencies": []}]

    async def _analyze_correction(self, worker_id: str, correction: str) -> Dict[str, Any]:
        """
        Use LLM to analyze user correction and determine action

        Args:
            worker_id: Worker agent ID
            correction: Correction message

        Returns:
            Dictionary with recommended action
        """
        prompt = f"""Analyze this user correction for a worker agent and recommend an action.

Worker ID: {worker_id}
Correction: {correction}

Recent corrections for this worker:
{json.dumps(self.corrections.get(worker_id, []), indent=2)}

Based on the correction, what should be done? Respond in JSON format:
{{
  "type": "reassign|modify_task|pause|continue",
  "reason": "explanation",
  "task_id": "if applicable",
  "params": {{}} // if modifying task
}}
"""

        try:
            messages = [
                LLMMessage(role="system", content="You are an expert project manager analyzing team feedback."),
                LLMMessage(role="user", content=prompt)
            ]

            result = await self.llm.chat(messages, temperature=0.3)
            response_text = result["response"]

            # Extract JSON from response
            json_match = response_text.strip()
            if "```json" in json_match:
                json_match = json_match.split("```json")[1].split("```")[0]
            elif "```" in json_match:
                json_match = json_match.split("```")[1].split("```")[0]

            action = extract_json(json_match)
            if action is None:
                raise ValueError("Failed to extract valid JSON from LLM response")
            if not isinstance(action, dict):
                raise ValueError(f"LLM response parsed as {type(action).__name__}, expected dict. Raw: {str(action)[:100]}")
            return action

        except Exception as e:
            logger.error(f"Failed to analyze correction: {e}")
            return {"type": "continue", "reason": f"Analysis failed: {str(e)}"}

    async def _decompose_task(self, task: Task) -> List[Dict[str, Any]]:
        """
        Use LLM to intelligently decompose task into subtasks

        Args:
            task: Task object to decompose

        Returns:
            List of subtask specifications
        """
        await self._log(f"Decomposing task with LLM: {task.description}")

        prompt = f"""You are an expert project manager. Decompose this task into clear, actionable subtasks.

TASK: {task.description}

Requirements:
- Break down into 2-5 concrete subtasks
- Each subtask should be specific and executable
- Identify the type of work (create_file, search_web, code_analysis, etc.)
- Include necessary parameters for each subtask

Respond in JSON array format:
[
  {{
    "description": "Clear description of the subtask",
    "type": "create_file|search_web|web_request|code_analysis|update_file",
    "params": {{
      // Relevant parameters for the task type
    }},
    "priority": 1-5,
    "dependencies": []
  }}
]

Be practical and specific. Focus on what needs to be done, not how to do it in detail.
"""

        try:
            messages = [
                LLMMessage(role="system", content=self._system_prompt),
                LLMMessage(role="user", content=prompt)
            ]

            # Emit thinking event first
            await self._publish_llm_event(EventType.AGENT_THINKING, {
                "task_id": task.id,
                "agent": self.agent_id,
                "message": "Decomposing task into subtasks..."
            })

            # Publish LLM prompt event for transparency
            await self._publish_llm_event(EventType.LLM_PROMPT, {
                "task_id": task.id,
                "agent": self.agent_id,
                "action": "decompose_task",
                "system_prompt": self._system_prompt[:500] + "..." if len(self._system_prompt) > 500 else self._system_prompt,
                "user_prompt": prompt[:1000] + "..." if len(prompt) > 1000 else prompt,
                "model": "unknown"
            })

            # Call LLM
            result = await self.llm.chat(messages, temperature=0.5, max_tokens=2000)
            response_text = result["response"]

            # Publish LLM response event
            await self._publish_llm_event(EventType.LLM_RESPONSE, {
                "task_id": task.id,
                "agent": self.agent_id,
                "action": "decompose_task",
                "response": response_text[:2000] + "..." if len(response_text) > 2000 else response_text,
                "model": result.get("provider", "unknown"),
                "tokens_used": result.get("tokens_used", 0)
            })

            # Extract JSON from response using robust parser
            subtasks = extract_json(response_text)

            if subtasks is None:
                logger.warning(f"JSON extraction failed for decomposition. Response: {response_text[:300]}")
                # Fallback: create single-step task
                subtasks = [{"description": task.description, "type": "create_file", "params": {}, "priority": 1, "dependencies": []}]

            # Type guard: extract_json may return a str if the LLM returned a raw string
            if isinstance(subtasks, str):
                raise ValueError(f"LLM response parsed as str, expected list/dict. Raw: {subtasks[:100]}")

            # Validate subtasks
            if isinstance(subtasks, dict):
                subtasks = [subtasks]
            if not isinstance(subtasks, list):
                raise ValueError(f"Decomposition response is not a list, got {type(subtasks)}")

            # Ensure each subtask has required fields
            for subtask in subtasks:
                if not isinstance(subtask, dict):
                    continue
                if "description" not in subtask:
                    subtask["description"] = "Execute subtask"
                if "type" not in subtask:
                    subtask["type"] = "create_file"
                if "params" not in subtask:
                    subtask["params"] = {}

            await self._log(f"Decomposed into {len(subtasks)} subtasks using {result.get('provider')}")
            return subtasks

        except Exception as e:
            logger.error(f"Failed to decompose task with LLM: {e}")
            # Emit failure event
            await self._emit_task_failed_event(task.id, f"Task decomposition failed: {str(e)}")
            # Fallback to simple single-step decomposition
            return [{"description": task.description, "type": "create_file", "params": {}, "priority": 1, "dependencies": []}]

    async def _analyze_results(self, task: Task):
        """
        Use LLM to analyze subtask results and detect gaps

        Args:
            task: Parent task with completed subtasks
        """
        await self._log(f"Analyzing results for task: {task.id}")

        # Collect subtask results
        results = []
        for subtask_id in task.subtasks:
            subtask = await self.state_manager.get_task(subtask_id)
            if subtask:
                results.append({
                    "id": subtask_id,
                    "description": subtask.description,
                    "status": subtask.status.value,
                    "result": subtask.result
                })

        # Use LLM to analyze
        prompt = f"""Analyze the results of these subtasks and identify any gaps or issues.

ORIGINAL TASK: {task.description}

SUBTASK RESULTS:
{json.dumps(results, indent=2, default=str)}

Provide analysis in JSON format:
{{
  "success": true/false,
  "summary": "Overall summary of results",
  "gaps": ["List of identified gaps or missing items"],
  "quality_score": 1-10,
  "recommendations": ["Specific recommendations for improvement"],
  "next_steps": ["Suggested next actions"]
}}
"""

        try:
            messages = [
                LLMMessage(role="system", content=self._system_prompt),
                LLMMessage(role="user", content=prompt)
            ]

            result = await self.llm.chat(messages, temperature=0.3, max_tokens=1500)
            response_text = result["response"]

            # Extract JSON using robust parser
            analysis = extract_json(response_text)

            # Fallback if JSON extraction fails
            if analysis is None:
                logger.warning(f"JSON extraction failed, creating default analysis. Response: {response_text[:300]}")
                analysis = {
                    "success": True,
                    "summary": response_text[:500] if response_text else "Analysis completed but JSON extraction failed",
                    "gaps": [],
                    "quality_score": 7,
                    "recommendations": [],
                    "next_steps": [],
                    "raw_response": response_text[:1000] if response_text else None
                }

            # Type guard: extract_json may return a str instead of dict
            if not isinstance(analysis, dict):
                logger.warning(f"Analysis parsed as {type(analysis).__name__}, wrapping. Raw: {str(analysis)[:100]}")
                analysis = {"success": True, "summary": str(analysis), "gaps": [], "quality_score": 7}

            # Store analysis
            analysis["subtask_count"] = len(results)
            analysis["analyzed_by"] = result.get("provider")

            await self.state_manager.update_task(task.id, result=analysis)

            # Log findings - handle gaps that might be strings or dicts
            gaps = analysis.get("gaps", [])
            if gaps:
                gap_strings = []
                for g in gaps[:3]:
                    if isinstance(g, dict):
                        gap_strings.append(g.get("description", str(g)))
                    else:
                        gap_strings.append(str(g))
                await self._log(f"Gaps detected: {', '.join(gap_strings)}")

            quality = analysis.get("quality_score", 7)
            try:
                quality = int(quality)
            except (ValueError, TypeError):
                quality = 7

            if quality < 7:
                await self._log(f"Quality score low: {quality}/10")

            await self._log(f"Analysis complete. Quality: {quality}/10")

            # Record experiment result (autoresearch-inspired tracking)
            duration_sec = None
            if task.started_at and task.completed_at:
                duration_sec = (task.completed_at - task.started_at).total_seconds()
            elif task.started_at:
                duration_sec = (datetime.now() - task.started_at).total_seconds()

            outcome = "keep" if analysis.get("success", True) and quality >= 5 else "discard"
            self._experiment_tracker.record(
                task_id=task.id,
                description=task.description,
                outcome=outcome,
                quality_score=quality,
                duration_sec=duration_sec,
                subtask_count=len(results),
                provider=analysis.get("analyzed_by", "unknown"),
                notes=analysis.get("summary", "")[:300],
            )

        except Exception as e:
            logger.error(f"Failed to analyze results with LLM: {e}")
            # Record as crash in experiment tracker
            self._experiment_tracker.record(
                task_id=task.id,
                description=task.description,
                outcome="crash",
                subtask_count=len(results),
                notes=f"Analysis failed: {str(e)}"[:300],
            )
            # Store error as result instead of crashing
            await self.state_manager.update_task(task.id, result={
                "error": f"Analysis failed: {str(e)}",
                "success": False,
                "subtask_count": len(results)
            })

    async def generate_task_report(self, task_id: str) -> str:
        """
        Generate a detailed report for a completed task

        Args:
            task_id: Task ID

        Returns:
            Formatted report text
        """
        task = await self.state_manager.get_task(task_id)
        if not task:
            return "Task not found"

        report_lines = [
            f"# Task Report: {task_id}",
            f"\n## Description",
            task.description,
            f"\n## Status",
            f"Status: {task.status.value}",
            f"Created: {task.created_at}",
            f"Completed: {task.completed_at or 'N/A'}",
        ]

        if task.result:
            report_lines.extend([
                f"\n## Analysis",
                f"Quality Score: {task.result.get('quality_score', 'N/A')}/10",
                f"Summary: {task.result.get('summary', 'N/A')}",
            ])

            if task.result.get('gaps'):
                report_lines.append(f"\n## Identified Gaps")
                for gap in task.result['gaps']:
                    report_lines.append(f"- {gap}")

            if task.result.get('recommendations'):
                report_lines.append(f"\n## Recommendations")
                for rec in task.result['recommendations']:
                    report_lines.append(f"- {rec}")

        # Subtasks
        if task.subtasks:
            report_lines.append(f"\n## Subtasks ({len(task.subtasks)})")
            for subtask_id in task.subtasks:
                subtask = await self.state_manager.get_task(subtask_id)
                if subtask:
                    report_lines.append(f"- [{subtask.status.value}] {subtask.description}")

        return "\n".join(report_lines)

    async def _reassign_task(self, task_id: str):
        """Reassign a task to a different worker"""
        task = await self.state_manager.get_task(task_id)
        if not task:
            return

        # Find a different worker
        current_worker = task.assigned_to
        available_workers = [w for w in self.workers if w.agent_id != current_worker]

        if not available_workers:
            await self._log("No alternative workers available for reassignment")
            return

        new_worker = available_workers[0]

        # Update task assignment
        await self.state_manager.update_task(
            task_id,
            assigned_to=new_worker.agent_id,
            status=TaskStatus.PENDING
        )

        # Assign to new worker
        task_data = {
            "task_id": task_id,
            "type": task.metadata.get("type") if task.metadata else "create_file",
            "params": task.metadata.get("params", {}) if task.metadata else {}
        }

        await new_worker.assign_task(task_data)
        await self._log(f"Reassigned {task_id} from {current_worker} to {new_worker.agent_id}")

    async def _modify_task(self, task_id: str, new_params: Dict):
        """Modify task parameters"""
        task = await self.state_manager.get_task(task_id)
        if not task:
            return

        if not task.metadata:
            task.metadata = {}

        task.metadata.update(new_params)

        await self.state_manager.update_task(task_id, metadata=task.metadata)
        await self._log(f"Modified task {task_id} with new parameters")

    async def _emit_task_failed_event(self, task_id: str, error: str):
        """Emit a TASK_FAILED event for a task"""
        await self.state_manager.update_task(
            task_id,
            status=TaskStatus.FAILED,
            error=error,
            completed_at=datetime.now()
        )
        event = Event(
            type=EventType.TASK_FAILED,
            data={
                "task_id": task_id,
                "agent_id": self.agent_id,
                "error": error
            },
            timestamp=datetime.now(),
            source=self.agent_id
        )
        await self.event_bus.publish(event)

