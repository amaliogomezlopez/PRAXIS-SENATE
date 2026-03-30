"""
Agent Roles Package
"""
from .loader import AgentRole, RoleLoader, get_role_loader, load_agent_role, get_system_prompt

__all__ = [
    "AgentRole",
    "RoleLoader",
    "get_role_loader",
    "load_agent_role",
    "get_system_prompt"
]
