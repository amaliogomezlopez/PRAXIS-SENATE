"""
Manager Agent - Coordina y supervisa workers
"""
import asyncio
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from core.agent_base import AgentBase
from core.event_bus import EventBus, Event, EventType
from core.state_manager import StateManager, Task, TaskStatus, Problem
from core.worker_agent import WorkerAgent


class ManagerAgent(AgentBase):
    """Agente manager que coordina workers y descompone tareas"""

    def __init__(
        self,
        agent_id: str,
        event_bus: EventBus,
        state_manager: StateManager
    ):
        super().__init__(agent_id, event_bus, state_manager)
        self.workers: List[WorkerAgent] = []
        self.user_tasks: asyncio.Queue = asyncio.Queue()

        # Suscribirse a eventos de tareas completadas
        self.event_bus.subscribe(
            EventType.TASK_COMPLETED,
            self._on_task_completed
        )
        self.event_bus.subscribe(
            EventType.TASK_FAILED,
            self._on_task_failed
        )
        self.event_bus.subscribe(
            EventType.TASK_RESUMED,
            self._on_task_resumed
        )

    def add_worker(self, worker: WorkerAgent):
        """Agregar un worker al pool"""
        self.workers.append(worker)

    async def submit_user_task(self, description: str, context: Optional[Dict] = None):
        """Recibir tarea del usuario"""
        task_id = f"task_{uuid.uuid4().hex[:8]}"

        task = Task(
            id=task_id,
            description=description,
            status=TaskStatus.PENDING
        )

        await self.state_manager.add_task(task)
        await self.user_tasks.put({"task_id": task_id, "context": context or {}})

        await self._log(f"Received user task: {description}")

        event = Event(
            type=EventType.TASK_CREATED,
            data={"task_id": task_id, "description": description},
            timestamp=datetime.now(),
            source=self.agent_id
        )
        await self.event_bus.publish(event)

        return task_id

    async def run(self):
        """Loop principal del manager"""
        await self.start()

        while self._running:
            try:
                task_data = await asyncio.wait_for(
                    self.user_tasks.get(),
                    timeout=1.0
                )
                await self._process_user_task(task_data)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                await self._log(f"Error in manager loop: {e}", "error")

    async def _process_user_task(self, task_data: Dict[str, Any]):
        """Procesar tarea del usuario"""
        task_id = task_data["task_id"]
        task = await self.state_manager.get_task(task_id)

        if not task:
            await self._log(f"Task not found: {task_id}", "error")
            return

        await self._log(f"Processing user task: {task.description}")
        await self._publish_progress("Analyzing task", 0.1)

        # Descomponer en subtareas
        subtasks = await self._decompose_task(task)

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

        # Actualizar tarea principal
        await self.state_manager.update_task(
            task_id,
            status=TaskStatus.IN_PROGRESS,
            started_at=datetime.now()
        )

    async def _decompose_task(self, task: Task) -> List[Dict[str, Any]]:
        """Descomponer tarea en subtareas"""
        await self._log(f"Decomposing task: {task.description}")

        # Análisis simple de la descripción
        description_lower = task.description.lower()

        subtasks = []

        # Estrategia de descomposición basada en palabras clave
        if "create" in description_lower and "file" in description_lower:
            subtasks.append({
                "description": "Create initial file structure",
                "type": "create_file",
                "params": {
                    "path": "output/result.txt",
                    "content": f"Task: {task.description}\n\nGenerated content..."
                }
            })

        if "analyze" in description_lower:
            subtasks.append({
                "description": "Perform analysis",
                "type": "code_analysis",
                "params": {"path": "output/result.txt"}
            })

        if "search" in description_lower or "find" in description_lower:
            query = task.description.replace("search for", "").replace("find", "").strip()
            subtasks.append({
                "description": f"Search web for: {query}",
                "type": "search_web",
                "params": {"query": query}
            })

        if "download" in description_lower:
            subtasks.append({
                "description": "Download resource",
                "type": "web_request",
                "params": {
                    "url": "https://api.github.com/repos/python/cpython",
                    "method": "GET"
                }
            })

        # Si no se identificaron subtareas específicas, crear una genérica
        if not subtasks:
            subtasks.append({
                "description": f"Execute: {task.description}",
                "type": "create_file",
                "params": {
                    "path": "output/result.txt",
                    "content": f"Completed task: {task.description}\n"
                }
            })

        await self._log(f"Decomposed into {len(subtasks)} subtasks")
        return subtasks

    async def _assign_to_worker(self, task_id: str, task_spec: Dict[str, Any]):
        """Asignar tarea a un worker disponible"""
        # Estrategia simple: round-robin
        if not self.workers:
            await self._log("No workers available!", "error")
            return

        worker = self.workers[hash(task_id) % len(self.workers)]

        task_data = {
            "task_id": task_id,
            "type": task_spec.get("type"),
            "params": task_spec.get("params", {})
        }

        await worker.assign_task(task_data)
        await self.state_manager.update_task(task_id, assigned_to=worker.agent_id)

        event = Event(
            type=EventType.TASK_ASSIGNED,
            data={
                "task_id": task_id,
                "worker_id": worker.agent_id
            },
            timestamp=datetime.now(),
            source=self.agent_id
        )
        await self.event_bus.publish(event)

        await self._log(f"Assigned {task_id} to {worker.agent_id}")

    async def _on_task_completed(self, event: Event):
        """Manejar evento de tarea completada"""
        task_id = event.data.get("task_id")
        task = await self.state_manager.get_task(task_id)

        if not task or not task.parent_task_id:
            return

        # Verificar si todas las subtareas del padre están completadas
        parent_task = await self.state_manager.get_task(task.parent_task_id)
        if parent_task:
            await self._check_parent_completion(parent_task)

    async def _on_task_failed(self, event: Event):
        """Manejar evento de tarea fallida"""
        task_id = event.data.get("task_id")
        error = event.data.get("error")

        # Detectar problema
        problem = Problem(
            id=f"problem_{uuid.uuid4().hex[:8]}",
            description=f"Task {task_id} failed: {error}",
            severity="high",
            detected_at=datetime.now()
        )
        await self.state_manager.add_problem(problem)

        event = Event(
            type=EventType.PROBLEM_DETECTED,
            data={
                "problem_id": problem.id,
                "description": problem.description,
                "severity": problem.severity
            },
            timestamp=datetime.now(),
            source=self.agent_id
        )
        await self.event_bus.publish(event)

        await self._log(f"Problem detected: {problem.description}", "warning")

    async def _check_parent_completion(self, parent_task: Task):
        """Verificar si todas las subtareas están completadas"""
        all_completed = True
        any_failed = False

        for subtask_id in parent_task.subtasks:
            subtask = await self.state_manager.get_task(subtask_id)
            if subtask:
                if subtask.status != TaskStatus.COMPLETED:
                    all_completed = False
                if subtask.status == TaskStatus.FAILED:
                    any_failed = True

        if all_completed:
            # Analizar resultados
            await self._analyze_results(parent_task)

            # Marcar como completada
            await self.state_manager.update_task(
                parent_task.id,
                status=TaskStatus.COMPLETED,
                completed_at=datetime.now()
            )

            await self._log(f"Parent task completed: {parent_task.id}")
            await self._publish_progress(f"Completed: {parent_task.description}", 1.0)

        elif any_failed:
            await self.state_manager.update_task(
                parent_task.id,
                status=TaskStatus.FAILED,
                error="One or more subtasks failed"
            )

    async def _analyze_results(self, task: Task):
        """Analizar resultados de subtareas"""
        await self._log(f"Analyzing results for task: {task.id}")

        results = []
        for subtask_id in task.subtasks:
            subtask = await self.state_manager.get_task(subtask_id)
            if subtask and subtask.result:
                results.append({
                    "subtask_id": subtask_id,
                    "description": subtask.description,
                    "result": subtask.result
                })

        # Guardar análisis
        analysis = {
            "total_subtasks": len(task.subtasks),
            "results": results,
            "summary": f"Completed {len(results)} subtasks for: {task.description}"
        }

        await self.state_manager.update_task(task.id, result=analysis)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Implementación requerida por AgentBase"""
        return {"success": True, "message": "Manager processes tasks via run loop"}

    async def _on_task_resumed(self, event: Event):
        """Handle TASK_RESUMED event - re-queue the task for processing"""
        task_id = event.data.get("task_id")
        if not task_id:
            return

        task = await self.state_manager.get_task(task_id)
        if not task:
            return

        await self._log(f"Task resumed: {task_id}")

        # Re-assign to a worker
        # Find the task spec from the original task or use default
        task_spec = {
            "type": task.metadata.get("type", "create_file") if task.metadata else "create_file",
            "params": task.metadata.get("params", {}) if task.metadata else {}
        }

        # Re-assign to worker
        await self._assign_to_worker(task_id, task_spec)

        # Publish that task was resumed
        resume_event = Event(
            type=EventType.TASK_STARTED,
            data={"task_id": task_id, "agent_id": task.assigned_to},
            timestamp=datetime.now(),
            source=self.agent_id
        )
        await self.event_bus.publish(resume_event)
