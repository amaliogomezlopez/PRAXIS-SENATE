"""
Agent endpoints
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from api.dependencies import APISystem

router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentResponse(BaseModel):
    id: str
    type: str  # "senior", "worker", "critic"
    status: str
    current_task: Optional[str] = None
    tasks_completed: int = 0


class PauseResumeResponse(BaseModel):
    agent_id: str
    status: str
    message: str


@router.get("", response_model=List[AgentResponse])
async def list_agents(request: Request):
    """List all agents (manager, workers, critic)"""
    api: APISystem = request.app.state.api_system
    if not api:
        raise HTTPException(status_code=503, detail="System not initialized")

    agents = []

    # Senior agent
    if api.senior_agent:
        agents.append(AgentResponse(
            id=api.senior_agent.agent_id,
            type="senior",
            status=await api.state_manager.get_agent_status(api.senior_agent.agent_id),
            current_task=None,
            tasks_completed=0
        ))

    # Workers
    for worker in api.workers:
        agents.append(AgentResponse(
            id=worker.agent_id,
            type="worker",
            status=await api.state_manager.get_agent_status(worker.agent_id),
            current_task=None,
            tasks_completed=0
        ))

    # Critic
    if api.critic:
        agents.append(AgentResponse(
            id=api.critic.agent_id,
            type="critic",
            status=await api.state_manager.get_agent_status(api.critic.agent_id),
            current_task=None,
            tasks_completed=0
        ))

    return agents


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, request: Request):
    """Get agent status and current task"""
    api: APISystem = request.app.state.api_system
    if not api:
        raise HTTPException(status_code=503, detail="System not initialized")

    agent = api.get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent_type = "senior"
    if "worker" in agent_id:
        agent_type = "worker"
    elif "critic" in agent_id:
        agent_type = "critic"

    return AgentResponse(
        id=agent.agent_id,
        type=agent_type,
        status=await api.state_manager.get_agent_status(agent_id),
        current_task=None,
        tasks_completed=0
    )


@router.post("/{agent_id}/pause", response_model=PauseResumeResponse)
async def pause_agent(agent_id: str, request: Request):
    """Pause an agent"""
    api: APISystem = request.app.state.api_system
    if not api:
        raise HTTPException(status_code=503, detail="System not initialized")

    agent = api.get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update agent status
    await api.state_manager.update_agent_status(agent_id, "paused")

    # Set pause flag if agent supports it
    if hasattr(agent, '_paused'):
        agent._paused = True

    return PauseResumeResponse(
        agent_id=agent_id,
        status="paused",
        message=f"Agent {agent_id} has been paused"
    )


@router.post("/{agent_id}/resume", response_model=PauseResumeResponse)
async def resume_agent(agent_id: str, request: Request):
    """Resume a paused agent"""
    api: APISystem = request.app.state.api_system
    if not api:
        raise HTTPException(status_code=503, detail="System not initialized")

    agent = api.get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update agent status
    await api.state_manager.update_agent_status(agent_id, "running")

    # Clear pause flag if agent supports it
    if hasattr(agent, '_paused'):
        agent._paused = False

    return PauseResumeResponse(
        agent_id=agent_id,
        status="resumed",
        message=f"Agent {agent_id} has been resumed"
    )
