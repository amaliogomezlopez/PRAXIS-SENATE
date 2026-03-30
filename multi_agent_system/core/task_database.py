"""
Centralized Task Database - Shared task management for all agents

This module provides a centralized task database where:
- Senior Agent creates tasks and assigns to workers
- Workers read tasks, update status, and add comments
- Critic Agent reads task results for feedback
- All agents can query task state
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path


class TaskStatus(Enum):
    """Task status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    """Task priority enumeration"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    URGENT = 5


@dataclass
class TaskComment:
    """Comment on a task"""
    id: str
    agent_id: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Task:
    """Task in the centralized database"""
    id: str
    type: str  # "decomposition", "execution", "review", "analysis"
    description: str
    instructions: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_to: Optional[str] = None
    created_by: str = "senior_agent"
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    comments: List[TaskComment] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # Task IDs this depends on
    tags: List[str] = field(default_factory=list)
    parent_task_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        d = asdict(self)
        d['status'] = self.status.value
        d['priority'] = self.priority.value
        d['comments'] = [asdict(c) for c in self.comments]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create from dictionary"""
        data = data.copy()
        data['status'] = TaskStatus(data.get('status', 'pending'))
        data['priority'] = TaskPriority(data.get('priority', 2))
        if 'comments' in data:
            data['comments'] = [
                TaskComment(**c) if isinstance(c, dict) else c
                for c in data['comments']
            ]
        return cls(**data)


class TaskDatabase:
    """
    Centralized task database with persistence.

    This is the single source of truth for all tasks in the system.
    All agents interact with this database to manage tasks.
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "tasks.json"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = asyncio.Lock()
        self._tasks: Dict[str, Task] = {}
        self._subscribers: List[asyncio.Queue] = []

        # Load existing tasks
        asyncio.create_task(self._load())

    async def _load(self):
        """Load tasks from file"""
        async with self._lock:
            if self.db_path.exists():
                try:
                    with open(self.db_path, 'r') as f:
                        data = json.load(f)
                        for task_data in data.get('tasks', []):
                            task = Task.from_dict(task_data)
                            self._tasks[task.id] = task
                except json.JSONDecodeError:
                    pass

    async def _save(self):
        """Save tasks to file"""
        async with self._lock:
            data = {
                'tasks': [t.to_dict() for t in self._tasks.values()],
                'last_updated': datetime.now().isoformat()
            }
            # Write atomically
            tmp_path = self.db_path.with_suffix('.tmp')
            with open(tmp_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            tmp_path.replace(self.db_path)

    async def _notify_subscribers(self, event_type: str, task: Task):
        """Notify subscribers of task changes"""
        event = {
            'type': event_type,
            'task': task.to_dict(),
            'timestamp': datetime.now().isoformat()
        }
        for queue in self._subscribers[:]:  # Copy to avoid mutation issues
            try:
                await queue.put(event)
            except Exception:
                self._subscribers.remove(queue)

    # === Task Operations ===

    async def create_task(
        self,
        description: str,
        task_type: str = "execution",
        assigned_to: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        instructions: str = "",
        dependencies: List[str] = None,
        tags: List[str] = None,
        created_by: str = "senior_agent",
        parent_task_id: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Task:
        """
        Create a new task.

        Args:
            description: Task description
            task_type: Type of task
            assigned_to: Agent ID to assign to
            priority: Task priority
            instructions: Detailed instructions
            dependencies: List of task IDs this depends on
            tags: Tags for categorization
            created_by: Agent ID that created this task
            parent_task_id: Parent task ID if subtask
            metadata: Additional metadata

        Returns:
            Created Task object
        """
        task_id = f"task_{uuid.uuid4().hex[:12]}"

        task = Task(
            id=task_id,
            type=task_type,
            description=description,
            instructions=instructions,
            priority=priority,
            assigned_to=assigned_to,
            created_by=created_by,
            dependencies=dependencies or [],
            tags=tags or [],
            parent_task_id=parent_task_id,
            metadata=metadata or {}
        )

        async with self._lock:
            self._tasks[task_id] = task

        await self._save()
        await self._notify_subscribers('TASK_CREATED', task)

        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        async with self._lock:
            return self._tasks.get(task_id)

    async def update_task(
        self,
        task_id: str,
        status: TaskStatus = None,
        result: Dict[str, Any] = None,
        error: str = None,
        assigned_to: str = None
    ) -> Optional[Task]:
        """
        Update task status and result.

        Args:
            task_id: Task ID to update
            status: New status
            result: Task result data
            error: Error message if failed
            assigned_to: New assignee

        Returns:
            Updated Task or None if not found
        """
        async with self._lock:
            if task_id not in self._tasks:
                return None

            task = self._tasks[task_id]

            if status:
                task.status = status
                if status == TaskStatus.IN_PROGRESS and not task.started_at:
                    task.started_at = datetime.now()
                elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                    task.completed_at = datetime.now()

            if result is not None:
                task.result = result

            if error is not None:
                task.error = error

            if assigned_to is not None:
                task.assigned_to = assigned_to

        await self._save()

        event_type = f"TASK_{task.status.value.upper()}"
        await self._notify_subscribers(event_type, task)

        return task

    async def add_comment(
        self,
        task_id: str,
        agent_id: str,
        content: str
    ) -> Optional[Task]:
        """Add a comment to a task"""
        async with self._lock:
            if task_id not in self._tasks:
                return None

            task = self._tasks[task_id]
            comment = TaskComment(
                id=f"comment_{uuid.uuid4().hex[:8]}",
                agent_id=agent_id,
                content=content
            )
            task.comments.append(comment)

        await self._save()
        await self._notify_subscribers('TASK_COMMENT', task)

        return task

    async def query_tasks(
        self,
        status: TaskStatus = None,
        assigned_to: str = None,
        task_type: str = None,
        tags: List[str] = None,
        created_by: str = None,
        parent_task_id: str = None,
        limit: int = 100
    ) -> List[Task]:
        """
        Query tasks with filters.

        Args:
            status: Filter by status
            assigned_to: Filter by assignee
            task_type: Filter by type
            tags: Filter by tags (any match)
            created_by: Filter by creator
            parent_task_id: Filter by parent task
            limit: Maximum results

        Returns:
            List of matching tasks
        """
        async with self._lock:
            results = list(self._tasks.values())

            if status:
                results = [t for t in results if t.status == status]

            if assigned_to:
                results = [t for t in results if t.assigned_to == assigned_to]

            if task_type:
                results = [t for t in results if t.type == task_type]

            if created_by:
                results = [t for t in results if t.created_by == created_by]

            if parent_task_id:
                results = [t for t in results if t.parent_task_id == parent_task_id]

            if tags:
                results = [t for t in results if any(tag in t.tags for tag in tags)]

            # Sort by priority (descending) then created_at (ascending)
            results.sort(key=lambda t: (-t.priority.value, t.created_at))

            return results[:limit]

    async def get_my_tasks(self, agent_id: str, status: TaskStatus = None) -> List[Task]:
        """Get tasks assigned to a specific agent"""
        return await self.query_tasks(assigned_to=agent_id, status=status)

    async def get_subtasks(self, parent_task_id: str) -> List[Task]:
        """Get all subtasks of a parent task"""
        return await self.query_tasks(parent_task_id=parent_task_id)

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        async with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                await self._save()
                return True
        return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get task statistics"""
        async with self._lock:
            tasks = list(self._tasks.values())

            return {
                "total": len(tasks),
                "by_status": {
                    s.value: len([t for t in tasks if t.status == s])
                    for s in TaskStatus
                },
                "by_priority": {
                    p.value: len([t for t in tasks if t.priority == p])
                    for p in TaskPriority
                },
                "unassigned": len([t for t in tasks if not t.assigned_to]),
                "completed": len([t for t in tasks if t.status == TaskStatus.COMPLETED]),
                "failed": len([t for t in tasks if t.status == TaskStatus.FAILED]),
                "in_progress": len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS])
            }

    # === Subscription ===

    def subscribe(self) -> asyncio.Queue:
        """Subscribe to task changes"""
        queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from task changes"""
        if queue in self._subscribers:
            self._subscribers.remove(queue)


# Global task database instance
_task_db: Optional[TaskDatabase] = None


async def get_task_database(db_path: str = None) -> TaskDatabase:
    """Get or create global task database"""
    global _task_db
    if _task_db is None:
        _task_db = TaskDatabase(db_path)
        await asyncio.sleep(0.1)  # Allow initial load
    return _task_db
