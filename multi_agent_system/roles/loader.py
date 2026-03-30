"""
Role Loader - Automatically loads agent role files into prompts
"""
import os
from pathlib import Path
from typing import Dict, Optional
from enum import Enum


class AgentRole(Enum):
    """Agent role types"""
    SENIOR = "senior"
    WORKER = "worker"
    CRITIC = "critic"


class RoleLoader:
    """Loads agent role and task files for prompt injection"""

    def __init__(self, roles_dir: str = None):
        if roles_dir is None:
            roles_dir = Path(__file__).parent

        self.roles_dir = Path(roles_dir)
        self._cache: Dict[AgentRole, str] = {}

    def load_role(self, role: AgentRole) -> str:
        """
        Load role file for given agent type.

        Args:
            role: The agent role to load

        Returns:
            The role file content
        """
        if role in self._cache:
            return self._cache[role]

        role_file = self.roles_dir / f"{role.value.upper()}_AGENT.md"

        if not role_file.exists():
            raise FileNotFoundError(f"Role file not found: {role_file}")

        with open(role_file, 'r', encoding='utf-8') as f:
            content = f.read()

        self._cache[role] = content
        return content

    def load_all_roles(self) -> str:
        """
        Load all role files combined.

        Returns:
            Combined role content
        """
        roles_content = []

        for role in AgentRole:
            try:
                content = self.load_role(role)
                roles_content.append(f"\n{'='*60}\n{content}\n")
            except FileNotFoundError:
                pass

        return "\n".join(roles_content)

    def clear_cache(self):
        """Clear the role cache"""
        self._cache.clear()

    def get_system_prompt(self, role: AgentRole, agent_id: str = None, context: Dict = None) -> str:
        """
        Generate full system prompt with role loaded.

        Args:
            role: The agent role
            agent_id: Optional agent ID to inject
            context: Optional context variables

        Returns:
            Complete system prompt
        """
        role_content = self.load_role(role)

        # Build context section if provided
        context_section = ""
        if context:
            context_lines = ["# CURRENT CONTEXT"]
            for key, value in context.items():
                context_lines.append(f"- {key}: {value}")
            context_section = "\n".join(context_lines) + "\n"

        # Build agent ID section
        id_section = ""
        if agent_id:
            id_section = f"# YOUR AGENT ID\n> {agent_id}\n\n"

        return f"""{role_content}

{id_section}{context_section}---
# INSTRUCTIONS
- Read your role definition above
- Use the task database commands as specified
- Always include task updates in your responses
- Follow the safety guidelines strictly
"""


# Global instance
_role_loader: Optional[RoleLoader] = None


def get_role_loader(roles_dir: str = None) -> RoleLoader:
    """Get or create global role loader instance"""
    global _role_loader
    if _role_loader is None:
        _role_loader = RoleLoader(roles_dir)
    return _role_loader


def load_agent_role(role: AgentRole) -> str:
    """Convenience function to load a role"""
    return get_role_loader().load_role(role)


def get_system_prompt(role: AgentRole, agent_id: str = None, context: Dict = None) -> str:
    """Convenience function to get a system prompt"""
    return get_role_loader().get_system_prompt(role, agent_id, context)
