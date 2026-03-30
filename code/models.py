"""
Data Models for Multi-Agent System
Defines all core data structures: Task, Agent, Message, FileChange, etc.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import uuid
import json


# ============================================================================
# ENUMERATIONS
# ============================================================================

class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AgentType(Enum):
    """Agent types"""
    MANAGER = "manager"
    WORKER = "worker"


class AgentStatus(Enum):
    """Agent execution status"""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


class MessageType(Enum):
    """Message types for inter-agent communication"""
    TASK_COMMAND = "TASK_COMMAND"
    TASK_RESULT = "TASK_RESULT"
    STATUS_UPDATE = "STATUS_UPDATE"
    FILE_CHANGE = "FILE_CHANGE"
    SYSTEM_EVENT = "SYSTEM_EVENT"
    HEARTBEAT = "HEARTBEAT"


class FileOperation(Enum):
    """File operation types"""
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    READ = "read"


class LogLevel(Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# ============================================================================
# CORE DATA MODELS
# ============================================================================

@dataclass
class Task:
    """Represents a task to be executed by an agent"""
    task_id: str = field(default_factory=lambda: f"task-{uuid.uuid4()}")
    parent_task_id: Optional[str] = None
    task_type: str = ""
    objective: str = ""
    assigned_to: Optional[str] = None  # agent_id
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Input/Output
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None

    # Execution tracking
    dependencies: List[str] = field(default_factory=list)  # task_ids
    progress_percent: int = 0
    retry_count: int = 0
    max_retries: int = 3

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    completion_criteria: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)

    # Budget
    timeout_seconds: int = 300
    max_iterations: int = 10
    max_tool_calls: int = 50

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['status'] = self.status.value
        data['priority'] = self.priority.value
        data['created_at'] = self.created_at.isoformat()
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create from dictionary"""
        data = data.copy()
        data['status'] = TaskStatus(data['status'])
        data['priority'] = TaskPriority(data['priority'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('started_at'):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        return cls(**data)


@dataclass
class AgentConfig:
    """Agent configuration"""
    agent_id: str
    agent_type: AgentType
    specialization: str
    capabilities: List[str] = field(default_factory=list)
    max_concurrent_tasks: int = 1


@dataclass
class AgentState:
    """Current state of an agent"""
    agent_id: str
    agent_type: AgentType
    specialization: str
    status: AgentStatus = AgentStatus.IDLE
    current_task_id: Optional[str] = None

    # Metrics
    tasks_completed: int = 0
    tasks_failed: int = 0
    average_execution_time: float = 0.0
    total_execution_time: float = 0.0

    # Context
    memory: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['agent_type'] = self.agent_type.value
        data['status'] = self.status.value
        data['last_heartbeat'] = self.last_heartbeat.isoformat()
        return data


@dataclass
class MessageEnvelope:
    """Message envelope for inter-agent communication"""
    message_id: str = field(default_factory=lambda: f"msg-{uuid.uuid4()}")
    timestamp: datetime = field(default_factory=datetime.now)
    message_type: MessageType = MessageType.TASK_COMMAND

    # Routing
    sender: Dict[str, str] = field(default_factory=dict)  # {agent_id, agent_type, specialization}
    recipient: Dict[str, str] = field(default_factory=dict)  # {agent_id, routing_key}

    # Payload
    payload: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['message_type'] = self.message_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageEnvelope':
        """Create from dictionary"""
        data = data.copy()
        data['message_type'] = MessageType(data['message_type'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class FileChange:
    """Record of file modification"""
    change_id: str = field(default_factory=lambda: f"change-{uuid.uuid4()}")
    task_id: str = ""
    agent_id: str = ""
    file_path: str = ""
    operation: FileOperation = FileOperation.MODIFY
    timestamp: datetime = field(default_factory=datetime.now)

    # Details
    lines_added: int = 0
    lines_deleted: int = 0
    diff_summary: str = ""

    # Conflict detection
    concurrent_modifications: List[str] = field(default_factory=list)  # change_ids

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['operation'] = self.operation.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class LogEntry:
    """System log entry"""
    log_id: str = field(default_factory=lambda: f"log-{uuid.uuid4()}")
    timestamp: datetime = field(default_factory=datetime.now)
    level: LogLevel = LogLevel.INFO
    source: str = ""  # agent_id
    task_id: Optional[str] = None
    message: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['level'] = self.level.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

    def __str__(self) -> str:
        """Format for display"""
        timestamp_str = self.timestamp.strftime("%H:%M:%S")
        return f"{timestamp_str}  {self.level.value:8}  [{self.source}] {self.message}"


@dataclass
class SystemMetrics:
    """System-wide metrics"""
    timestamp: datetime = field(default_factory=datetime.now)

    # Task metrics
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    pending_tasks: int = 0
    in_progress_tasks: int = 0

    # Agent metrics
    total_agents: int = 0
    active_agents: int = 0
    idle_agents: int = 0
    busy_agents: int = 0

    # Performance
    average_task_duration: float = 0.0
    task_completion_rate: float = 0.0
    task_failure_rate: float = 0.0

    # Resources
    queue_depth: int = 0
    message_throughput: float = 0.0
    file_operations_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_task_command(
    objective: str,
    task_type: str,
    sender_id: str,
    recipient_id: Optional[str] = None,
    input_data: Optional[Dict[str, Any]] = None,
    priority: TaskPriority = TaskPriority.MEDIUM,
    **kwargs
) -> MessageEnvelope:
    """
    Create a TASK_COMMAND message

    Args:
        objective: Task description
        task_type: Type of task
        sender_id: Sender agent ID
        recipient_id: Recipient agent ID (optional)
        input_data: Task input data
        priority: Task priority
        **kwargs: Additional task parameters

    Returns:
        MessageEnvelope with TASK_COMMAND
    """
    task = Task(
        objective=objective,
        task_type=task_type,
        priority=priority,
        input_data=input_data or {},
        **kwargs
    )

    return MessageEnvelope(
        message_type=MessageType.TASK_COMMAND,
        sender={"agent_id": sender_id},
        recipient={"agent_id": recipient_id or "broadcast"},
        payload={"task": task.to_dict()}
    )


def create_task_result(
    task_id: str,
    sender_id: str,
    status: TaskStatus,
    output_data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> MessageEnvelope:
    """
    Create a TASK_RESULT message

    Args:
        task_id: Task ID
        sender_id: Sender agent ID
        status: Final task status
        output_data: Task output data
        **kwargs: Additional result metadata

    Returns:
        MessageEnvelope with TASK_RESULT
    """
    return MessageEnvelope(
        message_type=MessageType.TASK_RESULT,
        sender={"agent_id": sender_id},
        recipient={"agent_id": "manager"},
        payload={
            "task_id": task_id,
            "status": status.value,
            "output_data": output_data or {},
            **kwargs
        }
    )


def create_status_update(
    task_id: str,
    sender_id: str,
    status: TaskStatus,
    progress_percent: int,
    current_step: str = "",
    **kwargs
) -> MessageEnvelope:
    """
    Create a STATUS_UPDATE message

    Args:
        task_id: Task ID
        sender_id: Sender agent ID
        status: Current status
        progress_percent: Progress percentage (0-100)
        current_step: Current execution step
        **kwargs: Additional status info

    Returns:
        MessageEnvelope with STATUS_UPDATE
    """
    return MessageEnvelope(
        message_type=MessageType.STATUS_UPDATE,
        sender={"agent_id": sender_id},
        recipient={"agent_id": "broadcast"},
        payload={
            "task_id": task_id,
            "status": status.value,
            "progress_percent": progress_percent,
            "current_step": current_step,
            **kwargs
        }
    )


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Create a task
    task = Task(
        objective="Refactor authentication module",
        task_type="code_editor",
        priority=TaskPriority.HIGH,
        input_data={"file_path": "/workspace/auth.py"},
        completion_criteria=["all tests pass", "code coverage >= 80%"]
    )

    print("Task created:")
    print(json.dumps(task.to_dict(), indent=2))

    # Create a message
    msg = create_task_command(
        objective="Review code for security issues",
        task_type="code_reviewer",
        sender_id="manager-001",
        recipient_id="worker-003",
        priority=TaskPriority.HIGH
    )

    print("\nMessage created:")
    print(msg.to_json())
