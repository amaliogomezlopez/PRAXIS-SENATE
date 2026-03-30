"""
Senior Manager Agent
Responsible for task decomposition, orchestration, and gap analysis
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from models import (
    Task, TaskStatus, TaskPriority, AgentState, AgentType, AgentStatus,
    MessageEnvelope, MessageType, create_task_command, create_status_update
)
from message_bus import MessageBus, MessageRouter


logger = logging.getLogger(__name__)


class ManagerAgent:
    """
    Senior Manager Agent - Orchestrates all workers
    """

    def __init__(self, agent_id: str, message_bus: MessageBus, config: Dict[str, Any]):
        self.agent_id = agent_id
        self.message_bus = message_bus
        self.config = config

        # Agent state
        self.state = AgentState(
            agent_id=agent_id,
            agent_type=AgentType.MANAGER,
            specialization="orchestrator",
            status=AgentStatus.IDLE
        )

        # Task tracking
        self.tasks: Dict[str, Task] = {}  # task_id -> Task
        self.pending_tasks: List[str] = []
        self.active_tasks: List[str] = []
        self.completed_tasks: List[str] = []
        self.failed_tasks: List[str] = []

        # Worker tracking
        self.available_workers: Dict[str, AgentState] = {}  # worker_id -> AgentState

        # Task dependency graph
        self.dependency_graph: Dict[str, List[str]] = {}  # task_id -> [dependencies]

        # Running flag
        self._running = False

    async def start(self) -> None:
        """Start the manager agent"""
        logger.info(f"Starting Manager Agent: {self.agent_id}")

        self._running = True
        self.state.status = AgentStatus.IDLE

        # Subscribe to relevant topics
        self.message_bus.subscribe("task_results", self._handle_task_result)
        self.message_bus.subscribe("status_updates", self._handle_status_update)
        self.message_bus.subscribe("system_events", self._handle_system_event)

        # Start background tasks
        asyncio.create_task(self._monitor_tasks())
        asyncio.create_task(self._send_heartbeat())

        logger.info(f"Manager Agent {self.agent_id} is now active")

    async def stop(self) -> None:
        """Stop the manager agent"""
        logger.info(f"Stopping Manager Agent: {self.agent_id}")
        self._running = False
        self.state.status = AgentStatus.OFFLINE

    async def receive_user_request(self, request: str, context: Optional[Dict] = None) -> str:
        """
        Receive request from user and start processing

        Args:
            request: User's request description
            context: Additional context

        Returns:
            Initial response to user
        """
        logger.info(f"Received user request: {request}")

        self.state.status = AgentStatus.BUSY

        # Analyze complexity
        is_complex = await self._analyze_complexity(request)

        if is_complex:
            # Decompose into subtasks
            subtasks = await self._decompose_task(request, context)
            logger.info(f"Decomposed into {len(subtasks)} subtasks")

            # Create task objects
            task_ids = []
            for subtask in subtasks:
                task = Task(
                    objective=subtask["objective"],
                    task_type=subtask["type"],
                    priority=TaskPriority(subtask.get("priority", "medium")),
                    input_data=subtask.get("input_data", {}),
                    completion_criteria=subtask.get("completion_criteria", [])
                )
                self.tasks[task.task_id] = task
                task_ids.append(task.task_id)

            # Build dependency graph
            await self._build_dependency_graph(task_ids, subtasks)

            # Start execution
            await self._execute_tasks()

            return f"Task decomposed into {len(subtasks)} subtasks. Execution started."

        else:
            # Execute directly
            task = Task(
                objective=request,
                task_type="general",
                priority=TaskPriority.MEDIUM
            )
            self.tasks[task.task_id] = task
            await self._assign_and_execute_task(task.task_id)

            return f"Task started: {task.task_id}"

    async def _analyze_complexity(self, request: str) -> bool:
        """
        Analyze if task is complex and needs decomposition

        Args:
            request: User request

        Returns:
            True if complex, False if simple
        """
        # Simple heuristics (can be enhanced with LLM)
        complexity_indicators = [
            " and ",
            "then",
            "after",
            "multiple",
            "all",
            "several"
        ]

        request_lower = request.lower()
        return any(indicator in request_lower for indicator in complexity_indicators)

    async def _decompose_task(self, request: str, context: Optional[Dict] = None) -> List[Dict]:
        """
        Decompose complex task into subtasks

        Args:
            request: User request
            context: Additional context

        Returns:
            List of subtask specifications
        """
        # This is a simplified version - in production, use LLM for decomposition
        logger.info(f"Decomposing task: {request}")

        # Example decomposition logic
        subtasks = []

        # Simple keyword-based decomposition
        if "implement" in request.lower() and "authentication" in request.lower():
            subtasks = [
                {
                    "objective": "Design authentication schema",
                    "type": "design",
                    "priority": "high",
                    "completion_criteria": ["schema defined", "security reviewed"]
                },
                {
                    "objective": "Implement authentication models",
                    "type": "code_editor",
                    "priority": "high",
                    "completion_criteria": ["code complete", "tests pass"]
                },
                {
                    "objective": "Create authentication tests",
                    "type": "code_editor",
                    "priority": "medium",
                    "completion_criteria": ["coverage >= 80%"]
                },
                {
                    "objective": "Review security implementation",
                    "type": "code_reviewer",
                    "priority": "high",
                    "completion_criteria": ["no security issues found"]
                },
                {
                    "objective": "Update documentation",
                    "type": "researcher",
                    "priority": "low",
                    "completion_criteria": ["docs complete"]
                }
            ]
        else:
            # Default decomposition
            subtasks = [
                {
                    "objective": request,
                    "type": "general",
                    "priority": "medium"
                }
            ]

        return subtasks

    async def _build_dependency_graph(self, task_ids: List[str], subtasks: List[Dict]) -> None:
        """
        Build dependency graph for tasks

        Args:
            task_ids: List of task IDs
            subtasks: List of subtask specifications
        """
        # Simple sequential dependencies for now
        for i, task_id in enumerate(task_ids):
            if i > 0:
                # Depend on previous task
                self.dependency_graph[task_id] = [task_ids[i - 1]]
                self.tasks[task_id].dependencies = [task_ids[i - 1]]
            else:
                self.dependency_graph[task_id] = []

    async def _execute_tasks(self) -> None:
        """Execute all pending tasks respecting dependencies"""
        # Get tasks ready to execute (no dependencies or dependencies completed)
        ready_tasks = self._get_ready_tasks()

        for task_id in ready_tasks:
            await self._assign_and_execute_task(task_id)

    def _get_ready_tasks(self) -> List[str]:
        """Get tasks ready to execute"""
        ready = []
        for task_id, task in self.tasks.items():
            if task.status != TaskStatus.PENDING:
                continue

            # Check if dependencies are met
            dependencies_met = all(
                self.tasks.get(dep_id, Task()).status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
            )

            if dependencies_met:
                ready.append(task_id)

        return ready

    async def _assign_and_execute_task(self, task_id: str) -> None:
        """
        Assign task to appropriate worker and execute

        Args:
            task_id: Task ID to execute
        """
        task = self.tasks[task_id]

        # Select best worker
        worker_id = await self._select_worker(task)

        if not worker_id:
            logger.warning(f"No available worker for task {task_id}")
            self.pending_tasks.append(task_id)
            return

        # Assign task
        task.assigned_to = worker_id
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()
        self.active_tasks.append(task_id)

        # Create and publish task command
        message = create_task_command(
            objective=task.objective,
            task_type=task.task_type,
            sender_id=self.agent_id,
            recipient_id=worker_id,
            priority=task.priority,
            input_data=task.input_data,
            completion_criteria=task.completion_criteria
        )
        message.payload["task_id"] = task_id

        await self.message_bus.publish("task_commands", message)

        logger.info(f"Assigned task {task_id} to worker {worker_id}")

    async def _select_worker(self, task: Task) -> Optional[str]:
        """
        Select best worker for task based on specialization and availability

        Args:
            task: Task to assign

        Returns:
            Worker ID or None if no worker available
        """
        # Filter workers by specialization match
        matching_workers = [
            worker_id for worker_id, worker_state in self.available_workers.items()
            if worker_state.specialization == task.task_type and
            worker_state.status == AgentStatus.IDLE
        ]

        if not matching_workers:
            # No exact match, try any idle worker
            matching_workers = [
                worker_id for worker_id, worker_state in self.available_workers.items()
                if worker_state.status == AgentStatus.IDLE
            ]

        if not matching_workers:
            return None

        # Select worker with best performance
        best_worker = min(
            matching_workers,
            key=lambda wid: self.available_workers[wid].tasks_failed
        )

        return best_worker

    async def _handle_task_result(self, message: MessageEnvelope) -> None:
        """
        Handle task result from worker

        Args:
            message: Task result message
        """
        task_id = message.payload.get("task_id")
        status = TaskStatus(message.payload.get("status"))
        output_data = message.payload.get("output_data", {})

        if task_id not in self.tasks:
            logger.warning(f"Received result for unknown task: {task_id}")
            return

        task = self.tasks[task_id]
        task.status = status
        task.output_data = output_data
        task.completed_at = datetime.now()

        # Update tracking lists
        if task_id in self.active_tasks:
            self.active_tasks.remove(task_id)

        if status == TaskStatus.COMPLETED:
            self.completed_tasks.append(task_id)
            logger.info(f"Task {task_id} completed successfully")

            # Analyze output for gaps
            await self._analyze_gaps(task_id)

            # Execute dependent tasks
            await self._execute_tasks()

        elif status == TaskStatus.FAILED:
            self.failed_tasks.append(task_id)
            logger.error(f"Task {task_id} failed")

            # Retry if possible
            if task.retry_count < task.max_retries:
                logger.info(f"Retrying task {task_id} ({task.retry_count + 1}/{task.max_retries})")
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                await asyncio.sleep(5)  # Wait before retry
                await self._assign_and_execute_task(task_id)

        # Update agent state
        if task.assigned_to in self.available_workers:
            worker = self.available_workers[task.assigned_to]
            worker.status = AgentStatus.IDLE
            if status == TaskStatus.COMPLETED:
                worker.tasks_completed += 1
            else:
                worker.tasks_failed += 1

    async def _analyze_gaps(self, task_id: str) -> None:
        """
        Analyze task output for gaps or missing work

        Args:
            task_id: Completed task ID
        """
        task = self.tasks[task_id]
        output_data = task.output_data or {}

        # Simple gap detection (can be enhanced)
        issues_found = output_data.get("issues_found", [])
        if issues_found:
            logger.warning(f"Gaps detected in task {task_id}: {issues_found}")

            # Create follow-up tasks
            for issue in issues_found:
                follow_up = Task(
                    parent_task_id=task_id,
                    objective=f"Address issue: {issue}",
                    task_type=task.task_type,
                    priority=TaskPriority.HIGH
                )
                self.tasks[follow_up.task_id] = follow_up
                logger.info(f"Created follow-up task: {follow_up.task_id}")

    async def _handle_status_update(self, message: MessageEnvelope) -> None:
        """Handle status update from worker"""
        task_id = message.payload.get("task_id")
        progress = message.payload.get("progress_percent", 0)

        if task_id in self.tasks:
            self.tasks[task_id].progress_percent = progress

    async def _handle_system_event(self, message: MessageEnvelope) -> None:
        """Handle system events"""
        event_type = message.payload.get("event_type")

        if event_type == "worker_registered":
            worker_id = message.payload.get("agent_id")
            worker_state = AgentState(
                agent_id=worker_id,
                agent_type=AgentType.WORKER,
                specialization=message.payload.get("specialization", "general")
            )
            self.available_workers[worker_id] = worker_state
            logger.info(f"Worker registered: {worker_id}")

    async def _monitor_tasks(self) -> None:
        """Monitor tasks for timeouts and issues"""
        while self._running:
            await asyncio.sleep(10)

            # Check for timed out tasks
            current_time = datetime.now()
            for task_id in self.active_tasks[:]:
                task = self.tasks[task_id]
                if task.started_at:
                    elapsed = (current_time - task.started_at).total_seconds()
                    if elapsed > task.timeout_seconds:
                        logger.warning(f"Task {task_id} timed out")
                        task.status = TaskStatus.FAILED
                        # Handle as failed

    async def _send_heartbeat(self) -> None:
        """Send periodic heartbeat"""
        while self._running:
            self.state.last_heartbeat = datetime.now()
            await asyncio.sleep(30)

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics"""
        return {
            "total_tasks": len(self.tasks),
            "pending": len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING]),
            "in_progress": len(self.active_tasks),
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks),
            "available_workers": len([w for w in self.available_workers.values()
                                     if w.status == AgentStatus.IDLE])
        }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def example_usage():
    """Example usage of ManagerAgent"""
    from message_bus import MessageBus

    bus = MessageBus()
    config = {"max_concurrent_tasks": 10}

    manager = ManagerAgent("manager-001", bus, config)
    await manager.start()

    # Simulate user request
    response = await manager.receive_user_request(
        "Implement authentication system and create tests"
    )
    print(f"Manager response: {response}")

    # Wait a bit
    await asyncio.sleep(2)

    # Get stats
    print("\nManager Stats:")
    print(manager.get_stats())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_usage())
