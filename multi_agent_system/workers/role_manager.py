"""
Role Manager - Manages worker roles defined in markdown files
"""
import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class Role:
    """Represents a worker role"""
    name: str
    specialization: str
    instructions: str
    constraints: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Convert role to markdown format"""
        md = f"""# Role: {self.name}

## Specialization
{self.specialization}

## Instructions
{self.instructions}

## Constraints
{self.constraints}

## Metadata
- Created: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}
- Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M:%S')}
"""
        if self.metadata:
            for key, value in self.metadata.items():
                md += f"- {key}: {value}\n"

        return md

    @classmethod
    def from_markdown(cls, content: str, name: str = None) -> 'Role':
        """Parse role from markdown content"""
        # Extract role name from header
        name_match = re.search(r'^# Role:\s*(.+)$', content, re.MULTILINE)
        role_name = name_match.group(1).strip() if name_match else (name or "Unknown")

        # Extract sections
        specialization = cls._extract_section(content, "Specialization")
        instructions = cls._extract_section(content, "Instructions")
        constraints = cls._extract_section(content, "Constraints")

        # Extract metadata
        created_at = datetime.now()
        updated_at = datetime.now()
        metadata = {}

        metadata_section = cls._extract_section(content, "Metadata")
        if metadata_section:
            for line in metadata_section.split('\n'):
                if line.strip().startswith('-'):
                    parts = line.strip()[1:].split(':', 1)
                    if len(parts) == 2:
                        key, value = parts
                        key = key.strip()
                        value = value.strip()

                        if key == "Created":
                            try:
                                created_at = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                            except:
                                pass
                        elif key == "Updated":
                            try:
                                updated_at = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                            except:
                                pass
                        else:
                            metadata[key] = value

        return cls(
            name=role_name,
            specialization=specialization,
            instructions=instructions,
            constraints=constraints,
            created_at=created_at,
            updated_at=updated_at,
            metadata=metadata
        )

    @staticmethod
    def _extract_section(content: str, section_name: str) -> str:
        """Extract content from a markdown section"""
        pattern = rf'^## {section_name}\s*\n(.*?)(?=\n## |\Z)'
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        return match.group(1).strip() if match else ""


class RoleManager:
    """Manages worker roles stored as markdown files"""

    def __init__(self, roles_dir: str = "roles"):
        self.roles_dir = Path(roles_dir)
        self.roles_dir.mkdir(parents=True, exist_ok=True)
        self.roles: Dict[str, Role] = {}
        self._load_all_roles()

    def _load_all_roles(self):
        """Load all roles from markdown files"""
        if not self.roles_dir.exists():
            logger.warning(f"Roles directory not found: {self.roles_dir}")
            return

        for file_path in self.roles_dir.glob("*.md"):
            try:
                role = self.load_role(file_path.stem)
                if role:
                    logger.info(f"Loaded role: {role.name}")
            except Exception as e:
                logger.error(f"Failed to load role from {file_path}: {e}")

    def create_role(
        self,
        name: str,
        specialization: str,
        instructions: str,
        constraints: str,
        metadata: Optional[Dict] = None
    ) -> Role:
        """
        Create a new role and save it as markdown

        Args:
            name: Role name (will be used as filename)
            specialization: What this role specializes in
            instructions: Detailed instructions for the role
            constraints: Constraints and limitations
            metadata: Additional metadata

        Returns:
            Created Role object
        """
        role = Role(
            name=name,
            specialization=specialization,
            instructions=instructions,
            constraints=constraints,
            metadata=metadata or {}
        )

        # Save to file
        file_path = self.roles_dir / f"{self._sanitize_filename(name)}.md"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(role.to_markdown())

        # Cache in memory
        self.roles[name] = role

        logger.info(f"Created role: {name} at {file_path}")
        return role

    def load_role(self, name: str) -> Optional[Role]:
        """
        Load a role from markdown file

        Args:
            name: Role name (filename without .md)

        Returns:
            Role object or None if not found
        """
        file_path = self.roles_dir / f"{self._sanitize_filename(name)}.md"

        if not file_path.exists():
            logger.warning(f"Role file not found: {file_path}")
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            role = Role.from_markdown(content, name)
            self.roles[role.name] = role
            return role

        except Exception as e:
            logger.error(f"Failed to load role {name}: {e}")
            return None

    def update_role(
        self,
        name: str,
        specialization: Optional[str] = None,
        instructions: Optional[str] = None,
        constraints: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[Role]:
        """
        Update an existing role

        Args:
            name: Role name
            specialization: New specialization (None = keep current)
            instructions: New instructions (None = keep current)
            constraints: New constraints (None = keep current)
            metadata: New metadata (None = keep current)

        Returns:
            Updated Role object or None if not found
        """
        role = self.get_role(name)
        if not role:
            logger.warning(f"Role not found for update: {name}")
            return None

        # Update fields
        if specialization is not None:
            role.specialization = specialization
        if instructions is not None:
            role.instructions = instructions
        if constraints is not None:
            role.constraints = constraints
        if metadata is not None:
            role.metadata.update(metadata)

        role.updated_at = datetime.now()

        # Save to file
        file_path = self.roles_dir / f"{self._sanitize_filename(name)}.md"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(role.to_markdown())

        logger.info(f"Updated role: {name}")
        return role

    def delete_role(self, name: str) -> bool:
        """
        Delete a role

        Args:
            name: Role name

        Returns:
            True if deleted, False if not found
        """
        file_path = self.roles_dir / f"{self._sanitize_filename(name)}.md"

        if not file_path.exists():
            logger.warning(f"Role file not found for deletion: {file_path}")
            return False

        try:
            file_path.unlink()
            self.roles.pop(name, None)
            logger.info(f"Deleted role: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete role {name}: {e}")
            return False

    def get_role(self, name: str) -> Optional[Role]:
        """
        Get a role by name (from cache or load from file)

        Args:
            name: Role name

        Returns:
            Role object or None if not found
        """
        if name in self.roles:
            return self.roles[name]
        return self.load_role(name)

    def list_roles(self) -> List[str]:
        """
        List all available role names

        Returns:
            List of role names
        """
        roles = set()

        # From memory
        roles.update(self.roles.keys())

        # From files
        if self.roles_dir.exists():
            for file_path in self.roles_dir.glob("*.md"):
                roles.add(file_path.stem)

        return sorted(list(roles))

    def get_all_roles(self) -> Dict[str, Role]:
        """
        Get all roles

        Returns:
            Dictionary of role name -> Role object
        """
        # Ensure all roles are loaded
        for name in self.list_roles():
            if name not in self.roles:
                self.load_role(name)

        return self.roles.copy()

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitize role name for use as filename"""
        # Replace spaces and special characters with underscores
        return re.sub(r'[^\w\-]', '_', name.lower())
