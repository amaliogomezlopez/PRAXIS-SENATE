"""
Worker Agent - Ejecuta tareas específicas con soporte LLM y Docker
"""
import asyncio
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from core.agent_base import AgentBase
from core.event_bus import EventBus, Event, EventType
from core.state_manager import StateManager, TaskStatus, FileChange
from core.json_utils import extract_json
from tools.file_operations import FileOperations
from tools.web_tools import WebTools
from docker import DockerAgentExecutor
from roles.loader import get_role_loader, AgentRole
from llm.manager import LLMManager
from llm.base import LLMMessage


class WorkerAgent(AgentBase):
    """Agente trabajador que ejecuta tareas específicas con soporte HITL"""

    # Circuit breaker: max consecutive errors before backing off
    MAX_CONSECUTIVE_ERRORS = 5
    BACKOFF_BASE_SECONDS = 2.0
    BACKOFF_MAX_SECONDS = 60.0

    def __init__(
        self,
        agent_id: str,
        event_bus: EventBus,
        state_manager: StateManager,
        file_ops: FileOperations,
        web_tools: WebTools,
        llm_manager: Optional[LLMManager] = None,
        execution_mode: str = "docker",
        workspace: str = None
    ):
        super().__init__(agent_id, event_bus, state_manager)
        self.file_ops = file_ops
        self.web_tools = web_tools
        self.current_task: Optional[str] = None
        self.llm = llm_manager

        # Load role prompt if LLM is available
        self._role_loader = get_role_loader()
        self._system_prompt = self._role_loader.get_system_prompt(
            AgentRole.WORKER,
            agent_id=agent_id,
            context={"mode": "worker_executor"}
        )

        # Docker executor for safe command execution
        self._docker_executor = DockerAgentExecutor(mode=execution_mode, workspace=workspace)

        # HITL: Pending human feedback per task
        self._pending_feedback: Dict[str, str] = {}

        # Circuit breaker state
        self._consecutive_errors = 0
        self._total_tasks_processed = 0

    async def _on_agent_message(self, event: Event):
        """Handle incoming agent messages (including human feedback)"""
        data = event.data or {}
        if data.get("type") == "human_feedback" and data.get("source") == "human":
            task_id = data.get("task_id")
            feedback = data.get("feedback", "")
            if task_id and feedback:
                # Store feedback for the task
                self._pending_feedback[task_id] = feedback
                await self._log(f"Received human feedback for task {task_id}")

                # If this is for current task, wake up the loop immediately
                if task_id == self.current_task:
                    await self._log(f"Waking up to process feedback for current task")

    async def _process_human_feedback(self, task_id: str, feedback: str):
        """Process human feedback for a specific task - inject into next LLM call"""
        # Mark that we've received feedback - the next LLM call will inject this
        await self._log(f"Will inject feedback into next LLM call: {feedback[:50]}...")

        # Also store in task metadata for visibility
        task = await self.state_manager.get_task(task_id)
        if task:
            if not task.metadata:
                task.metadata = {}
            # Prepend new feedback to existing
            existing = task.metadata.get("pending_human_feedback", "")
            task.metadata["pending_human_feedback"] = f"{feedback}\n{existing}" if existing else feedback
            await self.state_manager.update_task(task_id, metadata=task.metadata)

    async def run(self):
        """Loop principal del worker con soporte HITL y circuit breaker"""
        await self.start()

        # Subscribe to human feedback events
        self.event_bus.subscribe(EventType.AGENT_MESSAGE, self._on_agent_message)

        while self._running:
            try:
                # Check for pending feedback for current task first
                if self.current_task and self.current_task in self._pending_feedback:
                    feedback = self._pending_feedback.pop(self.current_task)
                    await self._log(f"Processing human feedback for {self.current_task}: {feedback[:50]}...")
                    await self._process_human_feedback(self.current_task, feedback)

                # Clean up stale pending feedback (tasks that finished or were never assigned)
                if len(self._pending_feedback) > 50:
                    stale_keys = list(self._pending_feedback.keys())[:25]
                    for k in stale_keys:
                        del self._pending_feedback[k]

                # Esperar tareas de la cola
                task_data = await asyncio.wait_for(
                    self._task_queue.get(),
                    timeout=1.0
                )
                await self._execute_task(task_data)
                self._total_tasks_processed += 1
                self._consecutive_errors = 0  # Reset on success

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self._consecutive_errors += 1
                await self._log(f"Error in worker loop: {e} (consecutive: {self._consecutive_errors})", "error")

                # Circuit breaker: exponential backoff on repeated errors
                if self._consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS:
                    backoff = min(
                        self.BACKOFF_BASE_SECONDS * (2 ** (self._consecutive_errors - self.MAX_CONSECUTIVE_ERRORS)),
                        self.BACKOFF_MAX_SECONDS
                    )
                    await self._log(
                        f"Circuit breaker: {self._consecutive_errors} consecutive errors, "
                        f"backing off {backoff:.1f}s",
                        "warning"
                    )
                    await asyncio.sleep(backoff)

    async def assign_task(self, task_data: Dict[str, Any]):
        """Asignar una tarea al worker"""
        await self._task_queue.put(task_data)

    async def _execute_task(self, task_data: Dict[str, Any]):
        """Ejecutar una tarea"""
        task_id = task_data.get("task_id")
        self.current_task = task_id

        try:
            await self._log(f"Starting task: {task_id}")
            await self.state_manager.update_task(
                task_id,
                status=TaskStatus.IN_PROGRESS,
                assigned_to=self.agent_id,
                started_at=datetime.now()
            )

            # Publicar evento de inicio
            event = Event(
                type=EventType.TASK_STARTED,
                data={"task_id": task_id, "agent_id": self.agent_id},
                timestamp=datetime.now(),
                source=self.agent_id
            )
            await self.event_bus.publish(event)

            # Procesar la tarea
            result = await self.process_task(task_data)

            # Actualizar estado
            await self.state_manager.update_task(
                task_id,
                status=TaskStatus.COMPLETED,
                completed_at=datetime.now(),
                result=result
            )

            # Publicar evento de completado
            event = Event(
                type=EventType.TASK_COMPLETED,
                data={
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "result": result
                },
                timestamp=datetime.now(),
                source=self.agent_id
            )
            await self.event_bus.publish(event)

            await self._log(f"Task completed: {task_id}")

        except Exception as e:
            await self._log(f"Task failed: {task_id} - {str(e)}", "error")
            await self.state_manager.update_task(
                task_id,
                status=TaskStatus.FAILED,
                error=str(e),
                completed_at=datetime.now()
            )

            event = Event(
                type=EventType.TASK_FAILED,
                data={
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "error": str(e)
                },
                timestamp=datetime.now(),
                source=self.agent_id
            )
            await self.event_bus.publish(event)

        finally:
            self.current_task = None

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Procesar una tarea específica con soporte HITL"""
        task_type = task_data.get("type", "unknown")
        task_params = task_data.get("params", {})
        task_description = task_data.get("description", "")
        task_id = task_data.get("task_id")

        # Check for pending human feedback first
        if task_id and task_id in self._pending_feedback:
            feedback = self._pending_feedback.pop(task_id)
            await self._log(f"Processing human feedback before LLM call: {feedback[:50]}...")
            # Prepend feedback context to the description
            task_description = f"[HUMAN FEEDBACK]: {feedback}\n\nOriginal task: {task_description}"

        # If task type is unknown but we have LLM, use it to decide
        if task_type == "unknown" and self.llm and task_description:
            await self._log("Task type unknown, using LLM to decide action...")
            decision = await self._decide_action_with_llm(task_description, task_id)
            task_type = decision.get("action", "unknown")
            task_params = decision.get("params", task_params)
            await self._log(f"LLM decided: {task_type}")

        await self._publish_progress(f"Processing {task_type}", 0.1)

        # Ejecutar según tipo de tarea
        if task_type == "create_file":
            result = await self._handle_create_file(task_params)
        elif task_type == "read_file":
            result = await self._handle_read_file(task_params)
        elif task_type == "update_file":
            result = await self._handle_update_file(task_params)
        elif task_type == "delete_file":
            result = await self._handle_delete_file(task_params)
        elif task_type == "web_request":
            result = await self._handle_web_request(task_params)
        elif task_type == "search_web":
            result = await self._handle_search_web(task_params)
        elif task_type == "code_analysis":
            result = await self._handle_code_analysis(task_params)
        elif task_type == "execute_command":
            result = await self._handle_execute_command(task_params)
        else:
            result = {"success": False, "error": f"Unknown task type: {task_type}"}

        await self._publish_progress(f"Completed {task_type}", 1.0)
        return result

    async def _handle_create_file(self, params: Dict) -> Dict:
        """Manejar creación de archivo"""
        path = params.get("path")
        content = params.get("content", "")

        result = await self.file_ops.create_file(path, content)

        if result["success"]:
            # Registrar cambio de archivo
            change = FileChange(
                path=path,
                action="created",
                timestamp=datetime.now(),
                agent=self.agent_id
            )
            await self.state_manager.add_file_change(change)

            # Publicar evento
            event = Event(
                type=EventType.FILE_MODIFIED,
                data={"path": path, "action": "created", "agent": self.agent_id},
                timestamp=datetime.now(),
                source=self.agent_id
            )
            await self.event_bus.publish(event)

        return result

    async def _handle_read_file(self, params: Dict) -> Dict:
        """Manejar lectura de archivo"""
        path = params.get("path")
        return await self.file_ops.read_file(path)

    async def _handle_update_file(self, params: Dict) -> Dict:
        """Manejar actualización de archivo"""
        path = params.get("path")
        content = params.get("content")

        result = await self.file_ops.update_file(path, content)

        if result["success"]:
            change = FileChange(
                path=path,
                action="modified",
                timestamp=datetime.now(),
                agent=self.agent_id
            )
            await self.state_manager.add_file_change(change)

            event = Event(
                type=EventType.FILE_MODIFIED,
                data={"path": path, "action": "modified", "agent": self.agent_id},
                timestamp=datetime.now(),
                source=self.agent_id
            )
            await self.event_bus.publish(event)

        return result

    async def _handle_delete_file(self, params: Dict) -> Dict:
        """Manejar eliminación de archivo"""
        path = params.get("path")
        result = await self.file_ops.delete_file(path)

        if result["success"]:
            change = FileChange(
                path=path,
                action="deleted",
                timestamp=datetime.now(),
                agent=self.agent_id
            )
            await self.state_manager.add_file_change(change)

        return result

    async def _handle_web_request(self, params: Dict) -> Dict:
        """Manejar petición web"""
        url = params.get("url")
        method = params.get("method", "GET")

        if method == "GET":
            return await self.web_tools.get_request(url)
        elif method == "POST":
            data = params.get("data")
            return await self.web_tools.post_request(url, json_data=data)
        else:
            return {"success": False, "error": f"Unsupported method: {method}"}

    async def _handle_search_web(self, params: Dict) -> Dict:
        """Manejar búsqueda web"""
        query = params.get("query")
        return await self.web_tools.search_web(query)

    async def _handle_code_analysis(self, params: Dict) -> Dict:
        """Manejar análisis de código"""
        # Simulación de análisis de código
        file_path = params.get("path")
        read_result = await self.file_ops.read_file(file_path)

        if not read_result["success"]:
            return read_result

        content = read_result["content"]
        lines = content.split("\n")

        analysis = {
            "success": True,
            "file": file_path,
            "lines_of_code": len(lines),
            "blank_lines": sum(1 for line in lines if not line.strip()),
            "has_imports": any("import " in line for line in lines),
            "has_functions": any("def " in line for line in lines),
            "has_classes": any("class " in line for line in lines),
        }

        return analysis

    async def _handle_execute_command(self, params: Dict) -> Dict:
        """
        Execute a terminal command inside an isolated Docker container.
        This is the safe way to execute dangerous or untrusted commands.
        """
        command = params.get("command")
        if not command:
            return {"success": False, "error": "No command provided"}

        workspace = params.get("workspace", "/workspace/agent_workspace")

        await self._log(f"Executing command in Docker: {command[:50]}...")

        try:
            # Execute in Docker container
            result = await self._docker_executor.execute(
                command=command,
                workspace=workspace,
                context={
                    "agent_id": self.agent_id,
                    "task_id": self.current_task
                }
            )

            if result.success:
                return {
                    "success": True,
                    "output": result.output,
                    "exit_code": result.exit_code,
                    "duration_seconds": result.duration_seconds,
                    "container_id": result.container_id
                }
            else:
                return {
                    "success": False,
                    "error": result.error,
                    "output": result.output,
                    "exit_code": result.exit_code
                }

        except Exception as e:
            await self._log(f"Docker execution failed: {e}", "error")
            return {
                "success": False,
                "error": f"Docker execution error: {str(e)}"
            }

    async def _decide_action_with_llm(self, task_description: str, task_id: str = None) -> Dict[str, Any]:
        """
        Use LLM to decide what action to take based on task description.
        Returns the action type and parameters.

        If human feedback is pending for this task, inject it into the prompt.
        """
        if not self.llm:
            return {"action": "unknown", "params": {}}

        # Check for pending human feedback
        feedback_to_inject = ""
        if task_id and task_id in self._pending_feedback:
            feedback_to_inject = self._pending_feedback.pop(task_id)
            await self._log(f"Injecting human feedback into LLM prompt: {feedback_to_inject[:50]}...")

        feedback_section = ""
        if feedback_to_inject:
            feedback_section = f"""
[URGENT HUMAN OVERRIDE/FEEDBACK]:
{feedback_to_inject}

IMPORTANT: You MUST acknowledge and strictly follow the human's feedback above.
Adjust your current plan and strictly follow this new instruction.
If the feedback suggests a different approach, change your planned action accordingly.
"""

        prompt = f"""Analyze this task and determine how to execute it:

TASK: {task_description}
{feedback_section}
Available actions:
- create_file: Create a new file with content
- read_file: Read contents of a file
- update_file: Update/modify an existing file
- delete_file: Delete a file
- execute_command: Run a terminal command (USE WITH CAUTION)
- web_request: Make an HTTP request
- search_web: Search the web
- code_analysis: Analyze code files

Respond in JSON format:
{{
  "action": "action_name",
  "params": {{
    // Parameters specific to the action
  }},
  "reasoning": "Why this action is appropriate"
}}
"""

        try:
            messages = [
                LLMMessage(role="system", content=self._system_prompt),
                LLMMessage(role="user", content=prompt)
            ]

            result = await self.llm.chat(messages, temperature=0.3, max_tokens=500)
            response_text = result["response"]

            # Extract JSON using robust parser
            decision = extract_json(response_text)
            if decision is not None:
                # Type guard: extract_json may return a str instead of dict
                if not isinstance(decision, dict):
                    logger.warning(f"LLM response parsed as {type(decision).__name__}, expected dict. Raw: {str(decision)[:100]}")
                    return {"action": "unknown", "params": {}}
                return decision

            logger.warning(f"Failed to extract JSON from LLM response: {response_text[:100]}")
            return {"action": "unknown", "params": {}}

        except Exception as e:
            logger.error(f"LLM decision failed: {e}")
            return {"action": "unknown", "params": {}}
