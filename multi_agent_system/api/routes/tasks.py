"""
Task endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from core.state_manager import Task, TaskStatus
from core.event_bus import Event, EventType
from api.dependencies import APISystem, get_api_system

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskHaltRequest(BaseModel):
    reason: Optional[str] = None


class TaskFeedbackRequest(BaseModel):
    feedback: str


class TaskCreate(BaseModel):
    description: str
    metadata: Optional[Dict[str, Any]] = None


class TaskResponse(BaseModel):
    id: str
    description: str
    status: str
    assigned_to: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    parent_task_id: Optional[str] = None
    subtasks: List[str] = []
    comments: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class CritiqueRequest(BaseModel):
    task_id: str


@router.post("", response_model=Dict[str, Any])
async def create_task(task: TaskCreate, request: Request):
    """Submit a new task to the SeniorAgent"""
    api: APISystem = request.app.state.api_system
    if not api or not api.senior_agent:
        raise HTTPException(status_code=503, detail="System not initialized")

    try:
        task_id = await api.senior_agent.submit_user_task(task.description)
        return {"task_id": task_id, "status": "submitted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    request: Request,
    status: Optional[str] = None,
    agent_id: Optional[str] = None,
):
    """List all tasks with optional filtering"""
    api: APISystem = request.app.state.api_system
    if not api:
        raise HTTPException(status_code=503, detail="System not initialized")

    tasks = await api.state_manager.get_all_tasks()

    # Filter by status
    if status:
        try:
            status_enum = TaskStatus(status)
            tasks = [t for t in tasks if t.status == status_enum]
        except ValueError:
            pass

    # Filter by agent
    if agent_id:
        tasks = [t for t in tasks if t.assigned_to == agent_id]

    return [
        TaskResponse(
            id=t.id,
            description=t.description,
            status=t.status.value,
            assigned_to=t.assigned_to,
            created_at=t.created_at,
            started_at=t.started_at,
            completed_at=t.completed_at,
            result=t.result,
            error=t.error,
            parent_task_id=t.parent_task_id,
            subtasks=t.subtasks,
            comments=t.comments,
            metadata=t.metadata
        )
        for t in tasks
    ]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, request: Request):
    """Get task details including subtasks"""
    api: APISystem = request.app.state.api_system
    if not api:
        raise HTTPException(status_code=503, detail="System not initialized")

    task = await api.state_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(
        id=task.id,
        description=task.description,
        status=task.status.value,
        assigned_to=task.assigned_to,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        result=task.result,
        error=task.error,
        parent_task_id=task.parent_task_id,
        subtasks=task.subtasks,
        comments=task.comments,
        metadata=task.metadata
    )


@router.get("/{task_id}/result")
async def get_task_result(task_id: str, request: Request):
    """Get task result/analysis"""
    api: APISystem = request.app.state.api_system
    if not api:
        raise HTTPException(status_code=503, detail="System not initialized")

    task = await api.state_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task_id,
        "result": task.result,
        "error": task.error,
        "status": task.status.value
    }


@router.post("/{task_id}/critique")
async def trigger_critique(task_id: str, request: Request):
    """Trigger re-critique for a task"""
    api: APISystem = request.app.state.api_system
    if not api:
        raise HTTPException(status_code=503, detail="System not initialized")

    if not api.critic:
        raise HTTPException(status_code=400, detail="Critic agent is not enabled")

    task = await api.state_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Publish critique request event
    event = Event(
        type=EventType.CRITIQUE_REQUEST,
        data={
            "task_id": task_id,
            "description": task.description,
            "subtasks": task.subtasks
        },
        timestamp=datetime.now(),
        source="api"
    )
    await api.event_bus.publish(event)

    return {"status": "critique_triggered", "task_id": task_id}


@router.post("/{task_id}/halt")
async def halt_task(task_id: str, halt_req: TaskHaltRequest, request: Request):
    """Halt a specific task (human-initiated stop)"""
    api: APISystem = request.app.state.api_system
    if not api:
        raise HTTPException(status_code=503, detail="System not initialized")

    task = await api.state_manager.halt_task(task_id, halt_req.reason)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "status": "halted",
        "task_id": task_id,
        "message": f"Task halted: {halt_req.reason or 'No reason provided'}"
    }


@router.post("/{task_id}/feedback")
async def add_human_feedback(task_id: str, fb_req: TaskFeedbackRequest, request: Request):
    """Add human feedback to a task and retry/continue"""
    api: APISystem = request.app.state.api_system
    if not api:
        raise HTTPException(status_code=503, detail="System not initialized")

    if not fb_req.feedback or not fb_req.feedback.strip():
        raise HTTPException(status_code=400, detail="Feedback cannot be empty")

    task = await api.state_manager.add_human_feedback(task_id, fb_req.feedback)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Publish event for the agent to pick up
    event = Event(
        type=EventType.AGENT_MESSAGE,
        data={
            "task_id": task_id,
            "type": "human_feedback",
            "feedback": fb_req.feedback,
            "source": "human"
        },
        timestamp=datetime.now(),
        source="human"
    )
    await api.event_bus.publish(event)

    return {
        "status": "feedback_added",
        "task_id": task_id,
        "new_status": task.status.value,
        "message": "Human feedback added and task set for retry"
    }


@router.post("/{task_id}/resume")
async def resume_task(task_id: str, request: Request):
    """Resume a halted task - re-queues it for processing"""
    api: APISystem = request.app.state.api_system
    if not api:
        raise HTTPException(status_code=503, detail="System not initialized")

    task = await api.state_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatus.HALTED:
        return {
            "status": "not_halted",
            "task_id": task_id,
            "message": "Task is not halted, cannot resume"
        }

    # Transition to in_progress
    await api.state_manager.update_task(
        task_id,
        status=TaskStatus.IN_PROGRESS
    )

    # Publish resume event
    event = Event(
        type=EventType.TASK_RESUMED,
        data={
            "task_id": task_id,
            "agent_id": task.assigned_to,
            "feedback": task.metadata.get("human_feedback") if task.metadata else None
        },
        timestamp=datetime.now(),
        source="human"
    )
    await api.event_bus.publish(event)

    return {
        "status": "resumed",
        "task_id": task_id,
        "message": "Task resumed successfully"
    }


@router.patch("/{task_id}")
async def update_task_partial(task_id: str, request: Request):
    """Partially update a task (status, result, etc.)"""
    api: APISystem = request.app.state.api_system
    if not api:
        raise HTTPException(status_code=503, detail="System not initialized")

    body = await request.json()
    task = await api.state_manager.update_task(task_id, **body)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "status": "updated",
        "task_id": task_id
    }


@router.post("/{task_id}/retry")
async def retry_task(task_id: str, request: Request):
    """Retry a failed task by creating a new task with the same description"""
    api: APISystem = request.app.state.api_system
    if not api or not api.senior_agent:
        raise HTTPException(status_code=503, detail="System not initialized")

    task = await api.state_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatus.FAILED:
        raise HTTPException(status_code=400, detail="Only failed tasks can be retried")

    try:
        new_task_id = await api.senior_agent.submit_user_task(task.description)
        return {"task_id": new_task_id, "status": "retried", "original_task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
