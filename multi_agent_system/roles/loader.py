"""
Role Loader - Automatically loads agent role files into prompts.
Supports Jinja2 template variables in role .md files (e.g. {{ max_retries }}).
"""
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

try:
    from jinja2 import Environment, BaseLoader, TemplateSyntaxError, UndefinedError
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

logger = logging.getLogger(__name__)

# Regex to discover {{ variable_name }} patterns in raw markdown
_TEMPLATE_VAR_RE = re.compile(r'\{\{\s*(\w+)\s*\}\}')


class AgentRole(Enum):
    """Agent role types"""
    SENIOR = "senior"
    WORKER = "worker"
    CRITIC = "critic"


# Default values for template variables per role.
# Keys are variable names found inside {{ ... }} in each .md file.
ROLE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "SENIOR_AGENT": {
        "max_retries": 3,
        "decomposition_depth": 2,
        "timeout_seconds": 120,
    },
    "WORKER_AGENT": {
        "max_retries": 3,
        "core_skills": "Python, JavaScript, TypeScript",
        "execution_timeout": 60,
    },
    "CRITIC_AGENT": {
        "strictness_level": "medium",
        "max_critique_rounds": 2,
        "approval_threshold": 0.7,
    },
}


class RoleLoader:
    """Loads agent role and task files for prompt injection, with Jinja2 template support."""

    def __init__(self, roles_dir: str = None):
        if roles_dir is None:
            roles_dir = Path(__file__).parent

        self.roles_dir = Path(roles_dir)
        self._raw_cache: Dict[str, str] = {}  # raw template text keyed by stem
        self._rendered_cache: Dict[str, str] = {}  # rendered text
        self._template_vars: Dict[str, Dict[str, Any]] = {}  # user overrides

        if JINJA2_AVAILABLE:
            self._jinja_env = Environment(
                loader=BaseLoader(),
                keep_trailing_newline=True,
                undefined=__import__('jinja2').Undefined,
            )
        else:
            self._jinja_env = None

    # ── raw I/O ──────────────────────────────────────────

    def _read_raw(self, stem: str) -> str:
        """Read and cache the raw .md file content."""
        if stem in self._raw_cache:
            return self._raw_cache[stem]

        role_file = self.roles_dir / f"{stem}.md"
        if not role_file.exists():
            raise FileNotFoundError(f"Role file not found: {role_file}")

        with open(role_file, 'r', encoding='utf-8') as f:
            content = f.read()

        self._raw_cache[stem] = content
        return content

    # ── template discovery ───────────────────────────────

    def discover_variables(self, stem: str) -> List[Dict[str, Any]]:
        """
        Discover all {{ var }} placeholders in a role file.

        Returns list of dicts with keys: name, default, current.
        """
        raw = self._read_raw(stem)
        var_names = list(dict.fromkeys(_TEMPLATE_VAR_RE.findall(raw)))  # dedup, preserve order

        defaults = ROLE_DEFAULTS.get(stem, {})
        overrides = self._template_vars.get(stem, {})

        result = []
        for name in var_names:
            default_val = defaults.get(name, "")
            current_val = overrides.get(name, default_val)
            result.append({
                "name": name,
                "default": default_val,
                "current": current_val,
            })
        return result

    # ── template rendering ───────────────────────────────

    def _render(self, stem: str) -> str:
        """Render a role template with current variables."""
        raw = self._read_raw(stem)

        # Merge defaults → overrides
        defaults = ROLE_DEFAULTS.get(stem, {})
        merged = {**defaults, **self._template_vars.get(stem, {})}

        if not JINJA2_AVAILABLE or not _TEMPLATE_VAR_RE.search(raw):
            return raw  # no templating needed

        try:
            template = self._jinja_env.from_string(raw)
            rendered = template.render(**merged)
            return rendered
        except (TemplateSyntaxError, UndefinedError) as exc:
            logger.warning(f"Jinja2 render error for {stem}: {exc}. Returning raw content.")
            return raw

    # ── public API ───────────────────────────────────────

    def set_template_vars(self, stem: str, variables: Dict[str, Any]) -> None:
        """Set template variable overrides for a role. Clears rendered cache."""
        if stem not in self._template_vars:
            self._template_vars[stem] = {}
        self._template_vars[stem].update(variables)
        self._rendered_cache.pop(stem, None)

    def get_template_vars(self, stem: str) -> Dict[str, Any]:
        """Get current effective template variables for a role."""
        defaults = ROLE_DEFAULTS.get(stem, {})
        return {**defaults, **self._template_vars.get(stem, {})}

    def load_role(self, role: AgentRole) -> str:
        """Load and render role file for given agent type."""
        stem = f"{role.value.upper()}_AGENT"

        if stem in self._rendered_cache:
            return self._rendered_cache[stem]

        rendered = self._render(stem)
        self._rendered_cache[stem] = rendered
        return rendered

    def load_all_roles(self) -> str:
        """Load all role files combined."""
        roles_content = []
        for role in AgentRole:
            try:
                content = self.load_role(role)
                roles_content.append(f"\n{'='*60}\n{content}\n")
            except FileNotFoundError:
                pass
        return "\n".join(roles_content)

    def clear_cache(self):
        """Clear all caches."""
        self._raw_cache.clear()
        self._rendered_cache.clear()

    def get_system_prompt(self, role: AgentRole, agent_id: str = None, context: Dict = None) -> str:
        """Generate full system prompt with rendered role."""
        role_content = self.load_role(role)

        context_section = ""
        if context:
            context_lines = ["# CURRENT CONTEXT"]
            for key, value in context.items():
                context_lines.append(f"- {key}: {value}")
            context_section = "\n".join(context_lines) + "\n"

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
