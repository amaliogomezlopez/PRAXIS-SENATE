"""
Worker Agent
Specialized agent that executes tasks assigned by the manager
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import logging
from models import (
    Task, TaskStatus, AgentState, AgentType, AgentStatus,
    MessageEnvelope, MessageType, create_task_result, create_status_update
)
from message_bus import MessageBus


logger = logging.getLogger(__name__)


class WorkerAgent:
    """
    Base Worker Agent - Executes specialized tasks
    """

    def __init__(self,
                 agent_id: str,
                 specialization: str,
                 capabilities: list,
                 message_bus: MessageBus,
                 config: Dict[str, Any]):
        self.agent_id = agent_id
        self.specialization = specialization
        self.capabilities = capabilities
        self.message_bus = message_bus
        self.config = config

        # Agent state
        self.state = AgentState(
            agent_id=agent_id,
            agent_type=AgentType.WORKER,
            specialization=specialization,
            status=AgentStatus.IDLE
        )

        # Current task
        self.current_task: Optional[Task] = None

        # Running flag
        self._running = False

    async def start(self) -> None:
        """Start the worker agent"""
        logger.info(f"Starting Worker Agent: {self.agent_id} ({self.specialization})")

        self._running = True
        self.state.status = AgentStatus.IDLE

        # Subscribe to task commands
        self.message_bus.subscribe("task_commands", self._handle_task_command)

        # Register with manager
        await self._register_with_manager()

        # Start heartbeat
        asyncio.create_task(self._send_heartbeat())

        logger.info(f"Worker Agent {self.agent_id} is now active")

    async def stop(self) -> None:
        """Stop the worker agent"""
        logger.info(f"Stopping Worker Agent: {self.agent_id}")
        self._running = False
        self.state.status = AgentStatus.OFFLINE

    async def _register_with_manager(self) -> None:
        """Register this worker with the manager"""
        registration_msg = MessageEnvelope(
            message_type=MessageType.SYSTEM_EVENT,
            sender={"agent_id": self.agent_id},
            recipient={"agent_id": "manager"},
            payload={
                "event_type": "worker_registered",
                "agent_id": self.agent_id,
                "specialization": self.specialization,
                "capabilities": self.capabilities
            }
        )
        await self.message_bus.publish("system_events", registration_msg)

    async def _handle_task_command(self, message: MessageEnvelope) -> None:
        """
        Handle task command from manager

        Args:
            message: Task command message
        """
        # Check if this message is for us
        recipient_id = message.recipient.get("agent_id")
        if recipient_id != self.agent_id and recipient_id != "broadcast":
            return

        # Check if we can handle this task type
        task_data = message.payload.get("task", {})
        task_type = task_data.get("task_type")

        if task_type != self.specialization and task_type != "general":
            # Not our specialization
            return

        # Check if we're already busy
        if self.state.status == AgentStatus.BUSY:
            logger.warning(f"{self.agent_id} is busy, cannot accept task")
            return

        # Accept and execute task
        task = Task.from_dict(task_data)
        task.task_id = message.payload.get("task_id", task.task_id)

        logger.info(f"{self.agent_id} accepted task: {task.task_id}")

        await self._execute_task(task)

    async def _execute_task(self, task: Task) -> None:
        """
        Execute a task

        Args:
            task: Task to execute
        """
        self.current_task = task
        self.state.status = AgentStatus.BUSY
        self.state.current_task_id = task.task_id

        start_time = datetime.now()

        try:
            # Send initial status update
            await self._send_status_update(0, "Starting task...")

            # Execute based on specialization
            result = await self._perform_work(task)

            # Mark as completed
            task.status = TaskStatus.COMPLETED
            task.output_data = result

            # Update metrics
            execution_time = (datetime.now() - start_time).total_seconds()
            self.state.tasks_completed += 1
            self.state.total_execution_time += execution_time
            self.state.average_execution_time = (
                self.state.total_execution_time / self.state.tasks_completed
            )

            # Send completion status
            await self._send_status_update(100, "Task completed")

            # Send result to manager
            await self._send_result(task, TaskStatus.COMPLETED, result)

        except Exception as e:
            logger.error(f"Error executing task {task.task_id}: {e}")

            task.status = TaskStatus.FAILED
            task.output_data = {"error": str(e)}

            self.state.tasks_failed += 1

            await self._send_result(task, TaskStatus.FAILED, {"error": str(e)})

        finally:
            # Reset state
            self.current_task = None
            self.state.status = AgentStatus.IDLE
            self.state.current_task_id = None

    async def _perform_work(self, task: Task) -> Dict[str, Any]:
        """
        Perform the actual work based on specialization
        Override this method in specialized worker classes

        Args:
            task: Task to execute

        Returns:
            Task output data
        """
        logger.info(f"{self.agent_id} performing work: {task.objective}")

        # Simulate work with progress updates
        steps = 5
        for i in range(steps):
            await asyncio.sleep(1)  # Simulate work
            progress = int(((i + 1) / steps) * 100)
            await self._send_status_update(
                progress,
                f"Step {i + 1}/{steps}: Processing..."
            )

        # Return mock result
        return {
            "summary": f"Task completed by {self.specialization} specialist",
            "files_modified": [],
            "files_created": [],
            "issues_found": [],
            "recommendations": []
        }

    async def _send_status_update(self, progress: int, step: str) -> None:
        """Send status update to dashboard"""
        if not self.current_task:
            return

        status_msg = create_status_update(
            task_id=self.current_task.task_id,
            sender_id=self.agent_id,
            status=TaskStatus.IN_PROGRESS,
            progress_percent=progress,
            current_step=step
        )

        await self.message_bus.publish("status_updates", status_msg)

    async def _send_result(self, task: Task, status: TaskStatus, output: Dict) -> None:
        """Send task result to manager"""
        result_msg = create_task_result(
            task_id=task.task_id,
            sender_id=self.agent_id,
            status=status,
            output_data=output,
            execution_time=(datetime.now() - task.started_at).total_seconds() if task.started_at else 0
        )

        await self.message_bus.publish("task_results", result_msg)

    async def _send_heartbeat(self) -> None:
        """Send periodic heartbeat"""
        while self._running:
            self.state.last_heartbeat = datetime.now()

            heartbeat_msg = MessageEnvelope(
                message_type=MessageType.HEARTBEAT,
                sender={"agent_id": self.agent_id},
                recipient={"agent_id": "manager"},
                payload={
                    "status": self.state.status.value,
                    "current_task_id": self.state.current_task_id
                }
            )

            await self.message_bus.publish("system_events", heartbeat_msg)
            await asyncio.sleep(30)


# ============================================================================
# SPECIALIZED WORKERS
# ============================================================================

class CodeEditorWorker(WorkerAgent):
    """Worker specialized in editing code"""

    def __init__(self, agent_id: str, message_bus: MessageBus, config: Dict):
        super().__init__(
            agent_id=agent_id,
            specialization="code_editor",
            capabilities=["edit_file", "create_file", "refactor_code"],
            message_bus=message_bus,
            config=config
        )

    async def _perform_work(self, task: Task) -> Dict[str, Any]:
        """Perform code editing work"""
        logger.info(f"{self.agent_id} editing code for: {task.objective}")

        file_path = task.input_data.get("file_path", "unknown.py")

        # Simulate code editing
        await self._send_status_update(20, "Analyzing code structure...")
        await asyncio.sleep(1)

        await self._send_status_update(40, "Applying refactoring patterns...")
        await asyncio.sleep(1)

        await self._send_status_update(60, "Running syntax checks...")
        await asyncio.sleep(1)

        await self._send_status_update(80, "Running tests...")
        await asyncio.sleep(1)

        return {
            "summary": f"Successfully edited {file_path}",
            "files_modified": [file_path],
            "files_created": [],
            "lines_added": 25,
            "lines_deleted": 10,
            "issues_found": [],
            "test_results": {"passed": 15, "failed": 0}
        }


class ResearcherWorker(WorkerAgent):
    """Worker specialized in research"""

    def __init__(self, agent_id: str, message_bus: MessageBus, config: Dict):
        super().__init__(
            agent_id=agent_id,
            specialization="researcher",
            capabilities=["web_search", "documentation_lookup"],
            message_bus=message_bus,
            config=config
        )

    async def _perform_work(self, task: Task) -> Dict[str, Any]:
        """Perform research work"""
        logger.info(f"{self.agent_id} researching: {task.objective}")

        await self._send_status_update(30, "Searching documentation...")
        await asyncio.sleep(1)

        await self._send_status_update(60, "Analyzing results...")
        await asyncio.sleep(1)

        await self._send_status_update(90, "Compiling findings...")
        await asyncio.sleep(1)

        return {
            "summary": "Research completed",
            "findings": [
                "Best practice: Use dependency injection",
                "Security consideration: Hash passwords with bcrypt",
                "Performance: Use connection pooling"
            ],
            "sources": [
                "https://docs.example.com/auth",
                "https://security.example.com/best-practices"
            ]
        }


class CodeReviewerWorker(WorkerAgent):
    """Worker specialized in code review"""

    def __init__(self, agent_id: str, message_bus: MessageBus, config: Dict):
        super().__init__(
            agent_id=agent_id,
            specialization="code_reviewer",
            capabilities=["code_review", "security_audit"],
            message_bus=message_bus,
            config=config
        )

    async def _perform_work(self, task: Task) -> Dict[str, Any]:
        """Perform code review"""
        logger.info(f"{self.agent_id} reviewing code for: {task.objective}")

        await self._send_status_update(25, "Checking code quality...")
        await asyncio.sleep(1)

        await self._send_status_update(50, "Running security audit...")
        await asyncio.sleep(1)

        await self._send_status_update(75, "Analyzing test coverage...")
        await asyncio.sleep(1)

        return {
            "summary": "Code review completed",
            "issues_found": [
                "Missing error handling in auth/login.py line 45"
            ],
            "recommendations": [
                "Add input validation",
                "Increase test coverage to 85%"
            ],
            "security_issues": [],
            "code_quality_score": 8.5
        }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def example_usage():
    """Example usage of Worker Agents"""
    from message_bus import MessageBus

    bus = MessageBus()
    config = {}

    # Create workers
    code_editor = CodeEditorWorker("worker-001", bus, config)
    researcher = ResearcherWorker("worker-002", bus, config)
    reviewer = CodeReviewerWorker("worker-003", bus, config)

    # Start workers
    await code_editor.start()
    await researcher.start()
    await reviewer.start()

    # Simulate task assignment
    task = Task(
        task_id="task-001",
        objective="Refactor authentication module",
        task_type="code_editor",
        input_data={"file_path": "/workspace/auth.py"}
    )

    task_msg = MessageEnvelope(
        message_type=MessageType.TASK_COMMAND,
        sender={"agent_id": "manager"},
        recipient={"agent_id": "worker-001"},
        payload={"task": task.to_dict(), "task_id": task.task_id}
    )

    await bus.publish("task_commands", task_msg)

    # Wait for completion
    await asyncio.sleep(8)

    print(f"\nWorker stats:")
    print(f"Code Editor: {code_editor.state.tasks_completed} completed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_usage())
