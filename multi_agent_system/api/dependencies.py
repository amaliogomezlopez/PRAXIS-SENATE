"""
Shared dependencies for API routes
"""
from typing import Optional
from fastapi import Request, HTTPException
from core.event_bus import EventBus, Event, EventType
from core.state_manager import StateManager, Task, TaskStatus
from core.senior_agent import SeniorAgent
from core.worker_agent import WorkerAgent
from core.critic_agent import CriticAgent


class APISystem:
    """Container for system components accessible to routes"""

    def __init__(
        self,
        event_bus: EventBus,
        state_manager: StateManager,
        senior_agent: SeniorAgent,
        workers: list,
        critic: Optional[CriticAgent] = None
    ):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.senior_agent = senior_agent
        self.workers = workers
        self.critic = critic

    def get_agent_by_id(self, agent_id: str):
        """Get agent by ID"""
        if self.senior_agent and self.senior_agent.agent_id == agent_id:
            return self.senior_agent
        for worker in self.workers:
            if worker.agent_id == agent_id:
                return worker
        if self.critic and self.critic.agent_id == agent_id:
            return self.critic
        return None

    def get_all_agents(self) -> list:
        """Get all agents"""
        agents = []
        if self.senior_agent:
            agents.append(self.senior_agent)
        agents.extend(self.workers)
        if self.critic:
            agents.append(self.critic)
        return agents


async def get_api_system(request: Request) -> APISystem:
    """FastAPI dependency to get API system from app state"""
    api_system = getattr(request.app.state, 'api_system', None)
    if not api_system:
        raise HTTPException(status_code=503, detail="System not initialized")
    return api_system
