"""
Persistent State Manager - StateManager with SQLite persistence
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from core.state_manager import StateManager, Task, TaskStatus, Problem, FileChange
from db.database import get_database, init_database
from db.models import TaskModel, SubtaskModel, CritiqueModel, AgentEventModel


class PersistentStateManager(StateManager):
    """StateManager with SQLite persistence (dual-write mode)"""

    def __init__(self, db_path: str = None, dual_write: bool = True):
        super().__init__()
        self._db = None
        self._db_path = db_path
        self._dual_write = dual_write
        self._initialized = False

    async def initialize(self):
        """Initialize database connection"""
        if not self._initialized:
            self._db = await init_database(self._db_path)
            self._initialized = True
            # Load existing tasks from DB into memory
            await self._load_from_db()

    async def _load_from_db(self):
        """Load tasks from database into memory"""
        if not self._db:
            return

        async with self._db.get_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(TaskModel))
            db_tasks = result.scalars().all()

            for db_task in db_tasks:
                task = Task(
                    id=db_task.id,
                    description=db_task.description,
                    status=TaskStatus(db_task.status),
                    assigned_to=db_task.assigned_to,
                    created_at=db_task.created_at,
                    started_at=db_task.started_at,
                    completed_at=db_task.completed_at,
                    result=db_task.result,
                    error=db_task.error,
                    parent_task_id=db_task.parent_task_id,
                    subtasks=[]  # Will be loaded separately if needed
                )
                self._tasks[task.id] = task

    async def add_task(self, task: Task):
        """Add a new task (dual-write to memory + DB)"""
        await super().add_task(task)

        if self._dual_write and self._db:
            await self._save_task_to_db(task)

    async def update_task(self, task_id: str, **kwargs):
        """Update a task (dual-write to memory + DB)"""
        await super().update_task(task_id, **kwargs)

        if self._dual_write and self._db:
            task = self._tasks.get(task_id)
            if task:
                await self._save_task_to_db(task)

    async def _save_task_to_db(self, task: Task):
        """Save task to database"""
        if not self._db:
            return

        async with self._db.get_session() as session:
            from sqlalchemy import select

            # Check if task exists
            result = await session.execute(
                select(TaskModel).where(TaskModel.id == task.id)
            )
            db_task = result.scalar_one_or_none()

            if db_task:
                # Update existing
                db_task.description = task.description
                db_task.status = task.status.value
                db_task.assigned_to = task.assigned_to
                db_task.started_at = task.started_at
                db_task.completed_at = task.completed_at
                db_task.result = task.result
                db_task.error = task.error
                db_task.parent_task_id = task.parent_task_id
            else:
                # Create new
                db_task = TaskModel(
                    id=task.id,
                    description=task.description,
                    status=task.status.value,
                    assigned_to=task.assigned_to,
                    created_at=task.created_at,
                    started_at=task.started_at,
                    completed_at=task.completed_at,
                    result=task.result,
                    error=task.error,
                    parent_task_id=task.parent_task_id
                )
                session.add(db_task)

            await session.commit()

    async def add_critique(self, critique_data: Dict[str, Any]):
        """Add a critique to database"""
        if not self._db:
            return

        critique_id = critique_data.get("id", f"critique_{uuid.uuid4().hex[:8]}")

        async with self._db.get_session() as session:
            db_critique = CritiqueModel(
                id=critique_id,
                task_id=critique_data.get("task_id"),
                approved=critique_data.get("approved", False),
                reasoning=critique_data.get("reasoning"),
                confidence=critique_data.get("confidence", 0) * 100 if critique_data.get("confidence") else None,
                risks=critique_data.get("risks"),
                gaps=critique_data.get("gaps"),
                suggestions=critique_data.get("suggestions"),
                source=critique_data.get("source")
            )
            session.add(db_critique)
            await session.commit()

    async def get_critiques(self, task_id: str = None) -> List[CritiqueModel]:
        """Get critiques from database"""
        if not self._db:
            return []

        async with self._db.get_session() as session:
            from sqlalchemy import select

            if task_id:
                result = await session.execute(
                    select(CritiqueModel).where(CritiqueModel.task_id == task_id)
                )
            else:
                result = await session.execute(select(CritiqueModel))

            return list(result.scalars().all())

    async def add_agent_event(self, event_type: str, source: str, data: Dict[str, Any] = None):
        """Add an agent event to database"""
        if not self._db:
            return

        async with self._db.get_session() as session:
            db_event = AgentEventModel(
                event_type=event_type,
                source=source,
                data=data,
                timestamp=datetime.now()
            )
            session.add(db_event)
            await session.commit()

    async def close(self):
        """Close database connection"""
        if self._db:
            await self._db.close()
