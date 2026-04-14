"""
CriticAgent - Independent challenger that reviews SeniorAgent's decompositions
"""
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

from core.agent_base import AgentBase
from core.event_bus import EventBus, Event, EventType
from core.state_manager import StateManager
from core.json_utils import extract_json
from llm.manager import LLMManager
from llm.base import LLMMessage
from roles.loader import get_role_loader, AgentRole

logger = logging.getLogger(__name__)


@dataclass
class CritiqueResult:
    """Structured critique output"""
    critic_id: str
    task_id: str
    approved: bool
    risks: List[Dict]
    gaps: List[str]
    alternatives: List[Dict]
    suggestions: List[Dict]
    confidence: float
    reasoning: str
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "critic_id": self.critic_id,
            "task_id": self.task_id,
            "approved": self.approved,
            "risks": self.risks,
            "gaps": self.gaps,
            "alternatives": self.alternatives,
            "suggestions": self.suggestions,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat()
        }


class CriticAgent(AgentBase):
    """
    Independent critic agent that challenges SeniorAgent's task decompositions.

    Acts as a "devil's advocate" to improve workflow quality by:
    - Identifying risks and gaps in the decomposition
    - Suggesting alternative approaches
    - Recommending modifications before execution begins
    """

    def __init__(
        self,
        agent_id: str,
        event_bus: EventBus,
        state_manager: StateManager,
        llm_manager: LLMManager,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(agent_id, event_bus, state_manager)
        self.llm = llm_manager
        self.config = config or {}

        # Load role prompt
        self._role_loader = get_role_loader()
        self._system_prompt = self._role_loader.get_system_prompt(
            AgentRole.CRITIC,
            agent_id=agent_id,
            context={"mode": "critic_reviewer"}
        )

        # Configuration
        self.enabled = self.config.get("enabled", True)
        self.blocking = self.config.get("blocking", True)
        self.timeout = self.config.get("timeout_seconds", 30)

        # Pending critiques awaiting response
        self._pending_critiques: Dict[str, asyncio.Event] = {}
        self._critique_results: Dict[str, CritiqueResult] = {}

        # Subscribe to relevant events
        self.event_bus.subscribe(
            EventType.TASK_DECOMPOSED,
            self._on_task_decomposed
        )

        self.event_bus.subscribe(
            EventType.CRITIQUE_REQUEST,
            self._on_critique_request
        )

    async def _publish_llm_event(self, event_type: EventType, data: Dict[str, Any]):
        """Publish an LLM transparency event"""
        event = Event(
            type=event_type,
            data=data,
            timestamp=datetime.now(),
            source=self.agent_id
        )
        await self.event_bus.publish(event)

    async def _on_task_decomposed(self, event: Event):
        """Handle TASK_DECOMPOSED event from SeniorAgent"""
        if not self.enabled:
            return

        task_id = event.data.get("task_id")
        subtasks = event.data.get("subtasks", [])
        original_description = event.data.get("description", "")

        await self._log(f"Received decomposition for task: {task_id}")

        # Generate critique
        critique = await self._generate_critique(
            task_id=task_id,
            original_description=original_description,
            subtasks=subtasks
        )

        # Store result
        self._critique_results[task_id] = critique

        # Create event to signal critique is ready
        if task_id in self._pending_critiques:
            self._pending_critiques[task_id].set()

        # Publish critique result
        critique_event = Event(
            type=EventType.CRITIQUE_RECEIVED,
            data=critique.to_dict(),
            timestamp=datetime.now(),
            source=self.agent_id
        )
        await self.event_bus.publish(critique_event)

        await self._log(
            f"Critique complete for {task_id}: "
            f"approved={critique.approved}, "
            f"confidence={critique.confidence:.2f}, "
            f"risks={len(critique.risks)}, "
            f"gaps={len(critique.gaps)}"
        )

    async def _on_critique_request(self, event: Event):
        """Handle explicit critique request (for re-critique scenarios)"""
        if not self.enabled:
            return

        task_id = event.data.get("task_id")
        await self._log(f"Received explicit critique request for: {task_id}")

        # Re-trigger critique for the task
        subtasks = event.data.get("subtasks", [])
        original_description = event.data.get("description", "")

        critique = await self._generate_critique(
            task_id=task_id,
            original_description=original_description,
            subtasks=subtasks
        )

        self._critique_results[task_id] = critique

        critique_event = Event(
            type=EventType.CRITIQUE_RECEIVED,
            data=critique.to_dict(),
            timestamp=datetime.now(),
            source=self.agent_id
        )
        await self.event_bus.publish(critique_event)

    async def _generate_critique(
        self,
        task_id: str,
        original_description: str,
        subtasks: List[Dict[str, Any]]
    ) -> CritiqueResult:
        """
        Use LLM to generate independent critique of the decomposition

        Args:
            task_id: Parent task ID
            original_description: What the user asked for
            subtasks: LLM-generated subtasks

        Returns:
            CritiqueResult with structured feedback
        """
        prompt = f"""You are an expert project manager acting as a critical reviewer.
Your role is to challenge and improve task decompositions BEFORE execution begins.

ORIGINAL TASK: {original_description}

PROPOSED DECOMPOSITION:
{json.dumps(subtasks, indent=2)}

Analyze this decomposition critically and provide structured feedback:

1. RISKS: What could go wrong during execution? Consider:
   - Dependencies that could cause deadlocks
   - Tasks that might timeout
   - Resource conflicts
   - Unclear success criteria

2. GAPS: What's MISSING from this decomposition? Consider:
   - Error handling tasks
   - Validation/verification tasks
   - Edge cases not covered
   - Missing dependencies

3. ALTERNATIVES: What DIFFERENT approaches could work? Consider:
   - Parallel vs sequential execution
   - Different task ordering
   - Consolidation or splitting of tasks

4. SUGGESTIONS: What SPECIFIC changes do you recommend? Be actionable.

Respond in JSON format:
{{
  "approved": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "Overall assessment in 1-2 sentences",
  "risks": [
    {{"severity": "high|medium|low", "description": "...", "affected_subtask": "if applicable"}}
  ],
  "gaps": ["Gap description 1", "Gap description 2"],
  "alternatives": [
    {{"description": "...", "impact": "speedup|quality|reliability"}}
  ],
  "suggestions": [
    {{"action": "add|remove|reorder|modify", "target": "subtask id or index", "description": "..."}}
  ]
}}

IMPORTANT:
- Set approved=false only if there are HIGH severity risks or major gaps
- Be constructive, not destructive
- Focus on IMPROVING the plan, not rejecting it
"""

        try:
            messages = [
                LLMMessage(role="system", content=self._system_prompt),
                LLMMessage(role="user", content=prompt)
            ]

            # Publish LLM prompt event for transparency
            await self._publish_llm_event(EventType.LLM_PROMPT, {
                "task_id": task_id,
                "agent": self.agent_id,
                "action": "generate_critique",
                "system_prompt": self._system_prompt[:500] + "..." if len(self._system_prompt) > 500 else self._system_prompt,
                "user_prompt": prompt[:1000] + "..." if len(prompt) > 1000 else prompt,
                "model": "pending"
            })

            # Emit thinking event
            await self._publish_llm_event(EventType.AGENT_THINKING, {
                "task_id": task_id,
                "agent": self.agent_id,
                "message": "Analyzing task decomposition for risks and gaps..."
            })

            result = await self.llm.chat(messages, temperature=0.3, max_tokens=2000)
            response_text = result["response"]

            # Publish LLM response event
            await self._publish_llm_event(EventType.LLM_RESPONSE, {
                "task_id": task_id,
                "agent": self.agent_id,
                "action": "generate_critique",
                "response": response_text[:2000] + "..." if len(response_text) > 2000 else response_text,
                "model": result.get("provider", "unknown"),
                "tokens_used": result.get("tokens_used", 0)
            })

            # Extract JSON using robust parser
            critique_data = extract_json(response_text)

            if critique_data is None:
                raise ValueError("Failed to extract valid JSON critique from LLM response")

            # Type guard: extract_json may return a str instead of dict
            if not isinstance(critique_data, dict):
                raise ValueError(f"LLM response parsed as {type(critique_data).__name__}, expected dict. Raw: {str(critique_data)[:100]}")

            return CritiqueResult(
                critic_id=self.agent_id,
                task_id=task_id,
                approved=critique_data.get("approved", True),
                risks=critique_data.get("risks", []),
                gaps=critique_data.get("gaps", []),
                alternatives=critique_data.get("alternatives", []),
                suggestions=critique_data.get("suggestions", []),
                confidence=critique_data.get("confidence", 0.5),
                reasoning=critique_data.get("reasoning", "No reasoning provided")
            )

        except Exception as e:
            logger.error(f"Failed to generate critique: {e}")
            # Return approving critique on failure (fail open) but log the error
            return CritiqueResult(
                critic_id=self.agent_id,
                task_id=task_id,
                approved=True,
                risks=[{"severity": "high", "description": f"Critique generation error: {str(e)}", "affected_subtask": "all"}],
                gaps=[f"Critique generation failed: {str(e)}"],
                alternatives=[],
                suggestions=[],
                confidence=0.0,
                reasoning=f"Critique generation failed: {str(e)} - auto-approved to avoid blocking"
            )

    async def get_critique(self, task_id: str, timeout: Optional[float] = None) -> Optional[CritiqueResult]:
        """
        Wait for and retrieve critique result for a task

        Args:
            task_id: Task ID to get critique for
            timeout: Optional timeout in seconds

        Returns:
            CritiqueResult or None if not available
        """
        timeout = timeout or self.timeout

        if task_id in self._critique_results:
            return self._critique_results[task_id]

        # Wait for critique to be published
        event = asyncio.Event()
        self._pending_critiques[task_id] = event

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return self._critique_results.get(task_id)
        except asyncio.TimeoutError:
            await self._log(f"Critique timeout for task: {task_id}", "warning")
            return None
        finally:
            self._pending_critiques.pop(task_id, None)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Required by AgentBase - CriticAgent doesn't process typical tasks"""
        return {"success": True, "message": "CriticAgent processes critique requests via events"}
