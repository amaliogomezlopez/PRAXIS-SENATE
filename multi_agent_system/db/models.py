"""
SQLAlchemy models for database persistence
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Boolean, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class TaskModel(Base):
    """Task database model"""
    __tablename__ = "tasks"

    id = Column(String(100), primary_key=True)
    description = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    assigned_to = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    parent_task_id = Column(String(100), ForeignKey("tasks.id"), nullable=True)

    # Relationships
    subtasks = relationship("SubtaskModel", back_populates="parent_task", lazy="dynamic")
    critiques = relationship("CritiqueModel", back_populates="task", lazy="dynamic")

    def __repr__(self):
        return f"<Task {self.id}: {self.description[:30]}... ({self.status})>"


class SubtaskModel(Base):
    """Subtask database model"""
    __tablename__ = "subtasks"

    id = Column(String(100), primary_key=True)
    task_id = Column(String(100), ForeignKey("tasks.id"), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    assigned_to = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    priority = Column(Integer, default=1)

    # Relationships
    parent_task = relationship("TaskModel", back_populates="subtasks")

    def __repr__(self):
        return f"<Subtask {self.id}: {self.description[:30]}... ({self.status})>"


class CritiqueModel(Base):
    """Critique database model"""
    __tablename__ = "critiques"

    id = Column(String(100), primary_key=True)
    task_id = Column(String(100), ForeignKey("tasks.id"), nullable=False)
    approved = Column(Boolean, nullable=False, default=False)
    reasoning = Column(Text, nullable=True)
    confidence = Column(Integer, nullable=True)  # Store as 0-100
    risks = Column(JSON, nullable=True)
    gaps = Column(JSON, nullable=True)
    suggestions = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    source = Column(String(100), nullable=True)

    # Relationships
    task = relationship("TaskModel", back_populates="critiques")

    def __repr__(self):
        return f"<Critique {self.id}: Task {self.task_id} ({'approved' if self.approved else 'rejected'})>"


class AgentEventModel(Base):
    """Agent event database model"""
    __tablename__ = "agent_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False)
    source = Column(String(100), nullable=False)
    data = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)

    def __repr__(self):
        return f"<AgentEvent {self.id}: {self.event_type} from {self.source}>"
