"""
Gestor de estado compartido entre agentes con persistencia SQLite
"""
import asyncio
import uuid
import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    HALTED = "halted"  # Human-initiated halt


@dataclass
class Task:
    """Tarea del sistema"""
    id: str
    description: str
    status: TaskStatus
    assigned_to: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    parent_task_id: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)
    comments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Problem:
    """Problema detectado"""
    id: str
    description: str
    severity: str  # "low", "medium", "high"
    detected_at: datetime
    resolved: bool = False
    resolution: Optional[str] = None


@dataclass
class FileChange:
    """Cambio en archivo"""
    path: str
    action: str  # "created", "modified", "deleted"
    timestamp: datetime
    agent: str


class StateManager:
    """Gestor de estado compartido del sistema con persistencia SQLite"""

    def __init__(self, event_bus=None, db_path: str = None):
        self._lock = asyncio.Lock()
        self._tasks: Dict[str, Task] = {}
        self._problems: Dict[str, Problem] = {}
        self._file_changes: List[FileChange] = []
        self._agent_status: Dict[str, str] = {}
        self._event_bus = event_bus

        # Initialize SQLite database
        if db_path is None:
            # Default to project root data directory
            db_path = Path(__file__).parent.parent / "data" / "state.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # Load persisted tasks
        self._load_from_db()

    def _init_db(self):
        """Initialize SQLite database schema"""
        try:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    assigned_to TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    result TEXT,
                    error TEXT,
                    parent_task_id TEXT,
                    subtasks TEXT,
                    comments TEXT,
                    metadata TEXT
                )
            """)
            conn.commit()
            conn.close()
            logger.info(f"State database initialized at {self._db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def _load_from_db(self):
        """Load tasks from SQLite database"""
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks")
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                task = Task(
                    id=row['id'],
                    description=row['description'],
                    status=TaskStatus(row['status']),
                    assigned_to=row['assigned_to'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
                    started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
                    completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                    result=json.loads(row['result']) if row['result'] else None,
                    error=row['error'],
                    parent_task_id=row['parent_task_id'],
                    subtasks=json.loads(row['subtasks']) if row['subtasks'] else [],
                    comments=json.loads(row['comments']) if row['comments'] else [],
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
                self._tasks[task.id] = task

            if rows:
                logger.info(f"Loaded {len(rows)} tasks from database")
        except Exception as e:
            logger.error(f"Failed to load tasks from database: {e}")

    def _save_task_to_db(self, task: Task):
        """Save a single task to SQLite database"""
        try:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO tasks
                (id, description, status, assigned_to, created_at, started_at, completed_at,
                 result, error, parent_task_id, subtasks, comments, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.id,
                task.description,
                task.status.value,
                task.assigned_to,
                task.created_at.isoformat() if task.created_at else datetime.now().isoformat(),
                task.started_at.isoformat() if task.started_at else None,
                task.completed_at.isoformat() if task.completed_at else None,
                json.dumps(task.result) if task.result else None,
                task.error,
                task.parent_task_id,
                json.dumps(task.subtasks) if task.subtasks else None,
                json.dumps(task.comments) if task.comments else None,
                json.dumps(task.metadata) if task.metadata else None
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save task to database: {e}")

    def set_event_bus(self, event_bus):
        """Set the event bus for publishing task events"""
        self._event_bus = event_bus

    async def _publish_event(self, event_type: str, data: Dict[str, Any]):
        """Publish an event to the event bus if available"""
        if self._event_bus:
            from core.event_bus import Event, EventType
            try:
                event = Event(
                    type=EventType[event_type.upper()] if hasattr(EventType, event_type.upper()) else EventType.AGENT_MESSAGE,
                    data=data,
                    timestamp=datetime.now(),
                    source="state_manager"
                )
                await self._event_bus.publish(event)
            except Exception:
                pass  # Don't fail if event publishing fails

    async def add_task(self, task: Task):
        """Agregar una nueva tarea"""
        async with self._lock:
            self._tasks[task.id] = task

        # Persist to database
        self._save_task_to_db(task)

        # Publish task created event
        await self._publish_event("TASK_CREATED", {
            "task_id": task.id,
            "description": task.description,
            "status": task.status.value,
            "assigned_to": task.assigned_to
        })

    async def update_task(self, task_id: str, **kwargs):
        """Actualizar una tarea"""
        async with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                old_status = task.status
                for key, value in kwargs.items():
                    setattr(task, key, value)

                # Persist to database after update
                self._save_task_to_db(task)

                # Determine event type based on status change
                if 'status' in kwargs:
                    new_status = kwargs['status']
                    if new_status == TaskStatus.IN_PROGRESS:
                        await self._publish_event("TASK_STARTED", {
                            "task_id": task_id,
                            "assigned_to": task.assigned_to
                        })
                    elif new_status == TaskStatus.COMPLETED:
                        await self._publish_event("TASK_COMPLETED", {
                            "task_id": task_id,
                            "assigned_to": task.assigned_to,
                            "result": task.result
                        })
                    elif new_status == TaskStatus.FAILED:
                        await self._publish_event("TASK_FAILED", {
                            "task_id": task_id,
                            "error": task.error
                        })
                    elif new_status == TaskStatus.HALTED:
                        await self._publish_event("TASK_HALTED", {
                            "task_id": task_id,
                            "assigned_to": task.assigned_to
                        })

    async def halt_task(self, task_id: str, reason: str = None) -> Optional[Task]:
        """Halt a specific task (human-initiated stop)"""
        async with self._lock:
            if task_id not in self._tasks:
                return None

            task = self._tasks[task_id]
            task.status = TaskStatus.HALTED
            task.error = reason or "Halted by human"
            task.completed_at = datetime.now()

        await self._publish_event("TASK_HALTED", {
            "task_id": task_id,
            "reason": reason,
            "halted_by": "human"
        })

        return task

    async def add_human_feedback(self, task_id: str, feedback: str) -> Optional[Task]:
        """Add human feedback to a task and set it back to pending/in_progress"""
        async with self._lock:
            if task_id not in self._tasks:
                return None

            task = self._tasks[task_id]

            # Add feedback as a comment
            comment = {
                "id": f"comment_{uuid.uuid4().hex[:8]}",
                "agent_id": "human",
                "content": feedback,
                "timestamp": datetime.now()
            }
            task.comments.append(comment)

            # If halted, set back to pending for retry
            if task.status == TaskStatus.HALTED:
                task.status = TaskStatus.PENDING

            # Store human override
            if not task.metadata:
                task.metadata = {}
            task.metadata["human_feedback"] = feedback
            task.metadata["last_feedback_at"] = datetime.now().isoformat()

        await self._publish_event("TASK_FEEDBACK", {
            "task_id": task_id,
            "feedback": feedback,
            "new_status": task.status.value
        })

        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Obtener una tarea"""
        async with self._lock:
            return self._tasks.get(task_id)

    async def get_all_tasks(self) -> List[Task]:
        """Obtener todas las tareas"""
        async with self._lock:
            return list(self._tasks.values())

    async def add_problem(self, problem: Problem):
        """Agregar un problema"""
        async with self._lock:
            self._problems[problem.id] = problem

    async def get_open_problems(self) -> List[Problem]:
        """Obtener problemas abiertos"""
        async with self._lock:
            return [p for p in self._problems.values() if not p.resolved]

    async def add_file_change(self, change: FileChange):
        """Registrar cambio en archivo"""
        async with self._lock:
            self._file_changes.append(change)

    async def get_recent_file_changes(self, limit: int = 10) -> List[FileChange]:
        """Obtener cambios recientes"""
        async with self._lock:
            return self._file_changes[-limit:]

    async def update_agent_status(self, agent_id: str, status: str):
        """Actualizar estado de agente"""
        async with self._lock:
            self._agent_status[agent_id] = status

    async def get_agent_status(self, agent_id: str) -> str:
        """Obtener estado de agente"""
        async with self._lock:
            return self._agent_status.get(agent_id, "idle")

    async def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del sistema"""
        async with self._lock:
            total_tasks = len(self._tasks)
            completed_tasks = sum(
                1 for t in self._tasks.values()
                if t.status == TaskStatus.COMPLETED
            )
            failed_tasks = sum(
                1 for t in self._tasks.values()
                if t.status == TaskStatus.FAILED
            )
            in_progress_tasks = sum(
                1 for t in self._tasks.values()
                if t.status == TaskStatus.IN_PROGRESS
            )

            return {
                "total_tasks": total_tasks,
                "completed": completed_tasks,
                "failed": failed_tasks,
                "in_progress": in_progress_tasks,
                "pending": total_tasks - completed_tasks - failed_tasks - in_progress_tasks,
                "open_problems": len([p for p in self._problems.values() if not p.resolved]),
                "file_changes": len(self._file_changes),
            }
