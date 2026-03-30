"""
Task Command Parser - Parse task commands from agent text

Agents use simple commands in their responses to interact with the task database.
This parser extracts and executes those commands.
"""
import re
import json
import logging
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParsedCommand:
    """A parsed task command"""
    command_type: str  # "create", "update", "query", "read", "comment", "critique_store"
    params: Dict[str, Any]
    raw_text: str


class TaskCommandParser:
    """
    Parser for task commands embedded in agent text.

    Commands are formatted as:
    [COMMAND_TYPE]
    param1: value1
    param2: value2
    [/COMMAND_TYPE]
    """

    # Command patterns
    PATTERNS = {
        'create': r'\[TASK_CREATE\](.*?)\[/TASK_CREATE\]',
        'update': r'\[TASK_UPDATE\](.*?)\[/TASK_UPDATE\]',
        'query': r'\[TASK_QUERY\](.*?)\[/TASK_QUERY\]',
        'read': r'\[TASK_READ\](.*?)\[/TASK_READ\]',
        'comment': r'\[TASK_COMMENT\](.*?)\[/TASK_COMMENT\]',
        'critique_store': r'\[CRITIQUE_STORE\](.*?)\[/CRITIQUE_STORE\]',
    }

    # Expected fields for each command type
    REQUIRED_FIELDS = {
        'create': ['id', 'type', 'description'],
        'update': ['id'],
        'query': ['filter', 'value'],
        'read': ['id'],
        'comment': ['id', 'content'],
        'critique_store': ['task_id', 'critique', 'approved'],
    }

    def __init__(self, task_database):
        self.db = task_database

    def parse(self, text: str) -> List[ParsedCommand]:
        """
        Parse all task commands from text.

        Args:
            text: Agent response text

        Returns:
            List of parsed commands
        """
        commands = []

        for cmd_type, pattern in self.PATTERNS.items():
            matches = re.finditer(pattern, text, re.DOTALL)
            for match in matches:
                params = self._parse_params(match.group(1))
                commands.append(ParsedCommand(
                    command_type=cmd_type,
                    params=params,
                    raw_text=match.group(0)
                ))

        return commands

    def _parse_params(self, param_text: str) -> Dict[str, Any]:
        """Parse parameters from command block"""
        params = {}

        # Match key: value patterns
        lines = param_text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Handle multiline values (after the key:)
            if ':' in line:
                key, _, value = line.partition(':')
                key = key.strip().lower()
                value = value.strip()

                # Handle JSON-like values
                if value.startswith('[') or value.startswith('{'):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        pass

                params[key] = value

        return params

    async def execute(self, command: ParsedCommand, agent_id: str = "system") -> Dict[str, Any]:
        """
        Execute a parsed command.

        Args:
            command: Parsed command to execute
            agent_id: Agent executing the command

        Returns:
            Execution result dictionary
        """
        try:
            if command.command_type == 'create':
                return await self._execute_create(command, agent_id)

            elif command.command_type == 'update':
                return await self._execute_update(command, agent_id)

            elif command.command_type == 'query':
                return await self._execute_query(command, agent_id)

            elif command.command_type == 'read':
                return await self._execute_read(command)

            elif command.command_type == 'comment':
                return await self._execute_comment(command, agent_id)

            elif command.command_type == 'critique_store':
                return await self._execute_critique_store(command, agent_id)

            else:
                return {"error": f"Unknown command type: {command.command_type}"}

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {"error": str(e), "command": command.command_type}

    async def _execute_create(self, command: ParsedCommand, agent_id: str) -> Dict[str, Any]:
        """Execute task create command"""
        params = command.params

        # Validate required fields
        for field in ['id', 'type', 'description']:
            if field not in params:
                return {"error": f"Missing required field: {field}"}

        task = await self.db.create_task(
            description=params['description'],
            task_type=params.get('type', 'execution'),
            assigned_to=params.get('assigned_to'),
            priority=params.get('priority', 2),
            instructions=params.get('instructions', ''),
            created_by=agent_id,
            tags=params.get('tags', []),
            metadata=params.get('metadata', {})
        )

        return {
            "success": True,
            "task_id": task.id,
            "task": task.to_dict()
        }

    async def _execute_update(self, command: ParsedCommand, agent_id: str) -> Dict[str, Any]:
        """Execute task update command"""
        params = command.params

        if 'id' not in params:
            return {"error": "Missing required field: id"}

        from .task_database import TaskStatus

        # Parse status if provided
        status = None
        if 'status' in params:
            try:
                status = TaskStatus(params['status'])
            except ValueError:
                return {"error": f"Invalid status: {params['status']}"}

        # Parse result if provided
        result = None
        if 'result' in params:
            result = params['result']

        task = await self.db.update_task(
            task_id=params['id'],
            status=status,
            result=result,
            error=params.get('error')
        )

        if not task:
            return {"error": f"Task not found: {params['id']}"}

        # Add comment if provided
        if 'comment' in params:
            await self.db.add_comment(
                task_id=params['id'],
                agent_id=agent_id,
                content=params['comment']
            )

        return {
            "success": True,
            "task": task.to_dict()
        }

    async def _execute_query(self, command: ParsedCommand, agent_id: str) -> Dict[str, Any]:
        """Execute task query command"""
        params = command.params

        from .task_database import TaskStatus

        # Parse filter and value
        filter_type = params.get('filter', '')
        value = params.get('value', '')

        # Build query filters
        query_kwargs = {}
        if filter_type == 'status':
            try:
                query_kwargs['status'] = TaskStatus(value)
            except ValueError:
                return {"error": f"Invalid status: {value}"}
        elif filter_type == 'assigned_to':
            query_kwargs['assigned_to'] = value
        elif filter_type == 'type':
            query_kwargs['task_type'] = value
        elif filter_type == 'created_by':
            query_kwargs['created_by'] = value

        tasks = await self.db.query_tasks(**query_kwargs)

        return {
            "success": True,
            "count": len(tasks),
            "tasks": [t.to_dict() for t in tasks]
        }

    async def _execute_read(self, command: ParsedCommand) -> Dict[str, Any]:
        """Execute task read command"""
        params = command.params

        if 'id' not in params:
            return {"error": "Missing required field: id"}

        task = await self.db.get_task(params['id'])

        if not task:
            return {"error": f"Task not found: {params['id']}"}

        return {
            "success": True,
            "task": task.to_dict()
        }

    async def _execute_comment(self, command: ParsedCommand, agent_id: str) -> Dict[str, Any]:
        """Execute task comment command"""
        params = command.params

        if 'id' not in params:
            return {"error": "Missing required field: id"}
        if 'content' not in params:
            return {"error": "Missing required field: content"}

        task = await self.db.add_comment(
            task_id=params['id'],
            agent_id=agent_id,
            content=params['content']
        )

        if not task:
            return {"error": f"Task not found: {params['id']}"}

        return {
            "success": True,
            "comment_id": task.comments[-1].id if task.comments else None
        }

    async def _execute_critique_store(self, command: ParsedCommand, agent_id: str) -> Dict[str, Any]:
        """Execute critique store command"""
        params = command.params

        if 'task_id' not in params:
            return {"error": "Missing required field: task_id"}

        # Add critique as a comment on the task
        critique_text = params.get('critique', '')
        approved = params.get('approved', False)
        confidence = params.get('confidence', 0.5)

        critique_content = f"""**CRITIQUE by {agent_id}**
Approved: {approved}
Confidence: {confidence}
---
{critique_text}"""

        if 'risks' in params:
            critique_content += f"\n\n**Risks:** {params['risks']}"
        if 'gaps' in params:
            critique_content += f"\n\n**Gaps:** {params['gaps']}"
        if 'suggestions' in params:
            critique_content += f"\n\n**Suggestions:** {params['suggestions']}"

        task = await self.db.add_comment(
            task_id=params['task_id'],
            agent_id=agent_id,
            content=critique_content
        )

        if not task:
            return {"error": f"Task not found: {params['task_id']}"}

        return {
            "success": True,
            "approved": approved,
            "task": task.to_dict()
        }

    async def parse_and_execute_all(self, text: str, agent_id: str = "system") -> Dict[str, Any]:
        """
        Parse all commands in text and execute them.

        Args:
            text: Agent response text
            agent_id: Agent executing commands

        Returns:
            Dictionary with execution results
        """
        commands = self.parse(text)

        if not commands:
            return {"executed": False, "reason": "No commands found"}

        results = []
        for cmd in commands:
            result = await self.execute(cmd, agent_id)
            results.append({
                "command": cmd.command_type,
                "params": cmd.params,
                "result": result
            })

        return {
            "executed": True,
            "count": len(results),
            "results": results
        }


async def create_task_parser(db) -> TaskCommandParser:
    """Create a task parser with database connection"""
    return TaskCommandParser(db)
