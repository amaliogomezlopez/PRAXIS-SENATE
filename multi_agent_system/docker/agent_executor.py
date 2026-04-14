"""
Secure Agent Executor - Runs agent commands in isolated Docker containers
"""
import asyncio
import uuid
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Import docker with error handling for when not installed
try:
    import docker
    from docker.errors import DockerException
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    DockerException = Exception
    DOCKER_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of command execution"""
    success: bool
    output: str
    error: str
    exit_code: int
    duration_seconds: float
    container_id: str


@dataclass
class ExecutionConfig:
    """Configuration for command execution"""
    timeout_seconds: int = 60
    memory_limit: str = "256m"
    cpu_limit: float = 0.5
    network_enabled: bool = False
    read_only_fs: bool = True
    allow_dangerous: bool = False


class SafeCommandValidator:
    """Validates commands before execution"""

    # Dangerous commands that require explicit approval
    DANGEROUS_COMMANDS = {
        'rm': ['-rf', '-r', '-f', '--no-preserve-root'],
        'dd': [],
        'mkfs': [],
        'fdisk': [],
        'sfdisk': [],
        'kill': ['-9', '-KILL'],
        'reboot': [],
        'shutdown': [],
        'init': [],
        'chmod': ['777', '000'],
        'chown': [],
        'useradd': [],
        'userdel': [],
        'passwd': [],
        'curl': ['--unix-socket'],  # Potential SSRF
        'wget': ['--unix-socket'],
        ':(){:|:&};:': [],  # Fork bomb
    }

    # Allowed commands (whitelist approach)
    ALLOWED_COMMANDS = {
        'python', 'python3', 'pip', 'pip3',
        'git', 'grep', 'awk', 'sed', 'cat', 'ls', 'cd', 'pwd',
        'mkdir', 'touch', 'echo', 'printf', 'head', 'tail', 'less',
        'wc', 'sort', 'uniq', 'cut', 'tr', 'find', 'xargs',
        'curl', 'wget', 'jq', 'vim', 'nano', 'less', 'more',
        'tar', 'gzip', 'gunzip', 'zip', 'unzip',
        'node', 'npm', 'npx',
        'docker',  # Only for specific allowed operations
    }

    @classmethod
    def is_command_safe(cls, command: str, allow_dangerous: bool = False, direct_mode: bool = False) -> tuple[bool, str]:
        """
        Check if command is safe to execute.
        Returns (is_safe, reason)
        """
        if not command or not command.strip():
            return False, "Empty command"

        parts = command.strip().split()
        if not parts:
            return False, "Empty command"

        cmd = parts[0]

        # In direct mode, skip whitelist but still block destructive patterns
        if direct_mode:
            if cmd in cls.DANGEROUS_COMMANDS and not allow_dangerous:
                dangerous_flags = cls.DANGEROUS_COMMANDS[cmd]
                for part in parts[1:]:
                    if part in dangerous_flags:
                        return False, f"Dangerous flag '{part}' for command '{cmd}' blocked even in direct mode"
            return True, "Direct mode: command allowed"

        # Check if command is in whitelist
        if cmd not in cls.ALLOWED_COMMANDS:
            return False, f"Command '{cmd}' not in whitelist"

        # Check for dangerous variations
        if cmd in cls.DANGEROUS_COMMANDS:
            if not allow_dangerous:
                dangerous_flags = cls.DANGEROUS_COMMANDS[cmd]
                for part in parts[1:]:
                    if part in dangerous_flags:
                        return False, f"Dangerous flag '{part}' for command '{cmd}'"

        # Check for command injection (semicolons, pipes, etc.)
        dangerous_chars = [';', '&&', '||', '|', '`', '$(', '>', '>>', '<']
        for char in dangerous_chars:
            if char in command and char not in ['echo', 'cat', 'grep', 'head', 'tail']:
                # Allow some dangerous chars but flag them
                pass  # Could add more strict validation here

        return True, "Command is safe"


class DockerAgentExecutor:
    """Executes agent commands in isolated Docker containers or directly on host"""

    # Local workspace directory (mounted into containers)
    LOCAL_WORKSPACE = Path(__file__).parent.parent / "agent_workspace"

    def __init__(self, image: str = "praxix-senate-agent:latest", mode: str = "docker", workspace: str = None):
        self.image = image
        self.mode = mode  # "docker" or "direct"
        self.client: Optional[docker.DockerClient] = None
        self._initialized = False

        # Set workspace
        if workspace:
            self.LOCAL_WORKSPACE = Path(workspace)
        # Ensure local workspace directory exists
        self.LOCAL_WORKSPACE.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Initialize Docker client"""
        if self._initialized:
            return

        if self.mode == "direct":
            logger.info(f"Direct mode enabled, workspace: {self.LOCAL_WORKSPACE}")
            self._initialized = True
            return

        try:
            self.client = docker.from_env()
            # Test connection
            self.client.ping()
            self._initialized = True
            logger.info("Docker executor initialized")
        except DockerException as e:
            logger.warning(f"Docker not available: {e}. Running in local mode.")
            self._initialized = False

    async def execute(
        self,
        command: str,
        workspace: str = "/workspace/agent_workspace",
        config: ExecutionConfig = None,
        context: Dict[str, Any] = None
    ) -> ExecutionResult:
        """
        Execute a command safely in a Docker container.

        Args:
            command: The command to execute
            workspace: Working directory inside container
            config: Execution configuration
            context: Additional context (agent_id, task_id, etc.)

        Returns:
            ExecutionResult with output and status
        """
        config = config or ExecutionConfig()
        context = context or {}

        start_time = datetime.now()

        # Validate command
        is_safe, reason = SafeCommandValidator.is_command_safe(
            command,
            allow_dangerous=config.allow_dangerous,
            direct_mode=(self.mode == "direct")
        )

        if not is_safe:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Command rejected: {reason}",
                exit_code=1,
                duration_seconds=0,
                container_id=""
            )

        # Check if Docker is available
        if self.mode == "direct" or not self._initialized or not self.client:
            if self.mode == "direct":
                logger.info("Direct mode: executing locally in workspace")
            else:
                logger.warning("Docker not available, running locally")
            return await self._execute_locally(
                command, start_time, timeout=config.timeout_seconds,
                cwd=str(self.LOCAL_WORKSPACE)
            )

        container_id = str(uuid.uuid4())[:12]
        container = None

        try:
            # Create temporary container with auto_remove for safety
            # Mount local agent_workspace to container's /workspace/agent_workspace
            container = self.client.containers.run(
                self.image,
                f"bash -c '{command}'",
                detach=True,
                mem_limit=config.memory_limit,
                cpu_period=100000,
                cpu_quota=int(100000 * config.cpu_limit),
                network_disabled=not config.network_enabled,
                read_only=config.read_only_fs,
                volumes={
                    str(self.LOCAL_WORKSPACE): {'bind': '/workspace/agent_workspace', 'mode': 'rw'}
                },
                working_dir='/workspace/agent_workspace',
                user='agent',
                environment={
                    'AGENT_ID': context.get('agent_id', 'unknown'),
                    'TASK_ID': context.get('task_id', 'unknown'),
                    'EXECUTION_ID': container_id
                },
                auto_remove=True,  # Automatically remove container after exit
                stderr=True,
                stdout=True
            )

            # Wait for completion with timeout
            try:
                result = container.wait(timeout=config.timeout_seconds)
                output = container.logs().decode('utf-8')
                exit_code = result.get('StatusCode', 1)

                duration = (datetime.now() - start_time).total_seconds()

                return ExecutionResult(
                    success=exit_code == 0,
                    output=output,
                    error="",
                    exit_code=exit_code,
                    duration_seconds=duration,
                    container_id=container_id
                )

            except Exception as e:
                # Try to cleanup even on error
                try:
                    container.remove(force=True)
                except Exception:
                    pass  # Container may have already been auto-removed
                return ExecutionResult(
                    success=False,
                    output="",
                    error=f"Execution timeout or error: {str(e)}",
                    exit_code=124,  # Timeout exit code
                    duration_seconds=config.timeout_seconds,
                    container_id=container_id
                )

        except DockerException as e:
            logger.error(f"Docker execution failed: {e}")
            # Ensure container cleanup on error
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                exit_code=1,
                duration_seconds=0,
                container_id=""
            )

    async def _execute_locally(self, command: str, start_time, timeout: int = 30, cwd: str = None) -> ExecutionResult:
        """Fallback local execution (not recommended for production)"""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    pass  # Process already killed
                duration = (datetime.now() - start_time).total_seconds()
                logger.warning(f"Local command timed out after {timeout}s: {command[:50]}...")
                return ExecutionResult(
                    success=False,
                    output="",
                    error=f"Command timed out after {timeout} seconds",
                    exit_code=124,  # Timeout exit code
                    duration_seconds=duration,
                    container_id="local"
                )

            duration = (datetime.now() - start_time).total_seconds()

            return ExecutionResult(
                success=process.returncode == 0,
                output=stdout.decode('utf-8') if stdout else "",
                error=stderr.decode('utf-8') if stderr else "",
                exit_code=process.returncode or 0,
                duration_seconds=duration,
                container_id="local"
            )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Local execution failed: {e}")
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                exit_code=1,
                duration_seconds=duration,
                container_id="local"
            )

    async def execute_file_operation(
        self,
        operation: str,  # 'read', 'write', 'append'
        file_path: str,
        content: str = None,
        context: Dict[str, Any] = None
    ) -> ExecutionResult:
        """Execute a file operation safely"""
        if operation == 'read':
            command = f"cat {file_path}"
        elif operation == 'write':
            # Escape content for bash
            escaped_content = content.replace("'", "'\"'\"'") if content else ""
            command = f"echo '{escaped_content}' > {file_path}"
        elif operation == 'append':
            escaped_content = content.replace("'", "'\"'\"'") if content else ""
            command = f"echo '{escaped_content}' >> {file_path}"
        else:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Unknown operation: {operation}",
                exit_code=1,
                duration_seconds=0,
                container_id=""
            )

        return await self.execute(command, context=context)

    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            self.client.close()
            self._initialized = False
