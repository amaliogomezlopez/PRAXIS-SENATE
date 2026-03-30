"""
Security Module - Safety and security for agent execution
"""
import asyncio
import hashlib
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ThreatLevel(Enum):
    """Threat level classification"""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class SecurityEvent:
    """Security event for audit logging"""
    timestamp: datetime
    event_type: str
    agent_id: str
    command: str
    threat_level: ThreatLevel
    details: str
    blocked: bool


class CommandSafetyValidator:
    """
    Validates command safety before execution.

    Uses a whitelist approach with dangerous command detection.
    """

    # Commands allowed without restrictions
    SAFE_COMMANDS = {
        'python', 'python3', 'pip', 'pip3',
        'git',
        'grep', 'awk', 'sed', 'cat', 'ls', 'pwd', 'cd', 'mkdir', 'touch',
        'head', 'tail', 'less', 'more', 'wc', 'sort', 'uniq', 'cut', 'tr',
        'echo', 'printf',
        'find', 'xargs',
        'tar', 'gzip', 'gunzip', 'zip', 'unzip',
        'node', 'npm', 'npx',
        'jq', 'vim', 'nano',
        'curl', 'wget',
    }

    # Commands allowed with restrictions
    RESTRICTED_COMMANDS = {
        'rm': {'max_depth': 3, 'forbidden_flags': ['-rf', '-r', '-f']},
        'chmod': {'forbidden_modes': ['777', '000', '6777']},
        'chown': {},
        'useradd': {},
        'userdel': {},
        'passwd': {},
        'docker': {
            'forbidden_subcommands': ['rm', 'rmi', 'stop', 'kill'],
            'allowed_flags': ['pull', 'run', 'ps', 'images']
        },
        'curl': {'forbidden_flags': ['--unix-socket']},
        'wget': {'forbidden_flags': ['--unix-socket']},
    }

    # Patterns that indicate potential injection
    INJECTION_PATTERNS = [
        r';\s*rm\s',
        r'&&\s*rm\s',
        r'\|\s*rm\s',
        r'`.*rm.*`',
        r'\$\(.*rm.*\)',
        r';\s*dd\s',
        r';\s*mkfs',
        r';\s*fdisk',
        r':\(\){.*:\|.*&.*}.;:',
        r'fork\s*-b\s*\d+\s*9999',
    ]

    # Blocked patterns (immediate reject)
    BLOCKED_PATTERNS = [
        r'rm\s+-rf\s+/',
        r'rm\s+-rf\s+/var',
        r'rm\s+-rf\s+/etc',
        r'rm\s+-rf\s+/home',
        r'dd\s+if=.*of=/dev/',
        r'mkfs\.',
        r'fork\s*bomb',
        r':\(\)\{.*:\|.*\}',  # Fork bomb
    ]

    @classmethod
    def validate(cls, command: str) -> Tuple[bool, ThreatLevel, str]:
        """
        Validate a command for safety.

        Args:
            command: Command string to validate

        Returns:
            Tuple of (is_safe, threat_level, reason)
        """
        if not command or not command.strip():
            return False, ThreatLevel.NONE, "Empty command"

        # Check blocked patterns first (immediate reject)
        for pattern in cls.BLOCKED_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, ThreatLevel.CRITICAL, f"Blocked pattern detected: {pattern}"

        # Check for injection attempts
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, ThreatLevel.HIGH, f"Potential injection detected: {pattern}"

        # Parse command
        parts = command.strip().split()
        if not parts:
            return False, ThreatLevel.NONE, "Empty command"

        cmd = parts[0]

        # Check if command is allowed
        if cmd not in cls.SAFE_COMMANDS and cmd not in cls.RESTRICTED_COMMANDS:
            return False, ThreatLevel.MEDIUM, f"Command not in whitelist: {cmd}"

        # Check restricted commands
        if cmd in cls.RESTRICTED_COMMANDS:
            restrictions = cls.RESTRICTED_COMMANDS[cmd]

            # Check forbidden flags
            if 'forbidden_flags' in restrictions:
                for part in parts[1:]:
                    if part in restrictions['forbidden_flags']:
                        return False, ThreatLevel.HIGH, f"Forbidden flag for {cmd}: {part}"

            # Check forbidden modes (for chmod)
            if 'forbidden_modes' in restrictions and cmd == 'chmod':
                for part in parts[1:]:
                    if part in restrictions['forbidden_modes']:
                        return False, ThreatLevel.HIGH, f"Forbidden chmod mode: {part}"

            # Check docker subcommands
            if cmd == 'docker' and len(parts) > 1:
                subcmd = parts[1]
                if subcmd in restrictions.get('forbidden_subcommands', []):
                    return False, ThreatLevel.MEDIUM, f"Docker subcommand not allowed: {subcmd}"

        # Additional validation for potentially dangerous patterns
        if 'rm' in command and ('*' in command or '?' in command):
            # Warn about glob patterns with rm
            return True, ThreatLevel.LOW, "Command contains glob pattern - verified"

        return True, ThreatLevel.NONE, "Command is safe"


class RateLimiter:
    """
    Rate limiter for API and command execution.
    """

    def __init__(self):
        self._requests: Dict[str, List[datetime]] = {}
        self._limits = {
            'api': {'max_requests': 100, 'window_seconds': 60},
            'command': {'max_requests': 10, 'window_seconds': 10},
            'task_create': {'max_requests': 20, 'window_seconds': 60},
        }

    def check_rate_limit(self, key: str, limit_type: str = 'api') -> Tuple[bool, Optional[str]]:
        """
        Check if request is within rate limit.

        Args:
            key: Identifier (e.g., agent_id)
            limit_type: Type of limit to check

        Returns:
            Tuple of (is_allowed, error_message)
        """
        if limit_type not in self._limits:
            limit_type = 'api'

        limit_config = self._limits[limit_type]
        max_requests = limit_config['max_requests']
        window = timedelta(seconds=limit_config['window_seconds'])

        now = datetime.now()

        if key not in self._requests:
            self._requests[key] = []

        # Clean old requests
        self._requests[key] = [
            ts for ts in self._requests[key]
            if now - ts < window
        ]

        # Check limit
        if len(self._requests[key]) >= max_requests:
            return False, f"Rate limit exceeded for {limit_type}: {max_requests} requests per {window}"

        # Record request
        self._requests[key].append(now)

        return True, None

    def reset(self, key: str = None):
        """Reset rate limit for a key or all keys"""
        if key:
            self._requests.pop(key, None)
        else:
            self._requests.clear()


class InputSanitizer:
    """
    Sanitizes user input to prevent injection attacks.
    """

    # Characters that need escaping in different contexts
    SHELL_ESCAPE_CHARS = r'[]{}()$\'`"\<>|;&!#*?'

    @classmethod
    def sanitize_shell_input(cls, user_input: str) -> str:
        """
        Sanitize input for safe shell usage.

        Args:
            user_input: Raw user input

        Returns:
            Sanitized string safe for shell
        """
        if not user_input:
            return ""

        result = user_input

        # Remove null bytes
        result = result.replace('\x00', '')

        # Remove control characters
        result = ''.join(
            c for c in result
            if ord(c) >= 32 or c in '\n\r\t'
        )

        # Trim whitespace
        result = result.strip()

        return result

    @classmethod
    def sanitize_file_path(cls, path: str, allowed_base: str = None) -> str:
        """
        Sanitize a file path to prevent path traversal.

        Args:
            path: File path
            allowed_base: Allowed base directory

        Returns:
            Sanitized path
        """
        # Normalize path
        import os
        path = os.path.normpath(path)

        # Remove leading slashes (prevent absolute path injection)
        path = path.lstrip('/').lstrip('\\')

        # Remove parent directory references
        path = path.replace('..', '')

        # If allowed_base specified, ensure path is within it
        if allowed_base:
            allowed_base = os.path.normpath(allowed_base)
            full_path = os.path.join(allowed_base, path)
            full_path = os.path.normpath(full_path)
            if not full_path.startswith(allowed_base):
                return os.path.basename(path)

        return path

    @classmethod
    def sanitize_json(cls, json_str: str) -> str:
        """
        Sanitize JSON string input.

        Args:
            json_str: JSON string

        Returns:
            Sanitized JSON string
        """
        if not json_str:
            return "{}"

        # Remove any script tags if embedded in JSON
        json_str = re.sub(r'<script[^>]*>.*?</script>', '', json_str, flags=re.IGNORECASE | re.DOTALL)
        json_str = re.sub(r'javascript:', '', json_str, flags=re.IGNORECASE)

        return json_str


class SecurityAuditor:
    """
    Security audit logging.
    """

    def __init__(self, log_path: str = None):
        import logging
        from pathlib import Path

        if log_path is None:
            log_path = Path(__file__).parent.parent / "data" / "security_audit.log"

        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Setup logger
        self.logger = logging.getLogger("security_audit")
        self.logger.setLevel(logging.INFO)

        # File handler
        handler = logging.FileHandler(self.log_path)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)

        # In-memory log for recent events
        self._recent_events: List[SecurityEvent] = []
        self._max_recent = 1000

    def log_event(
        self,
        event_type: str,
        agent_id: str,
        command: str,
        threat_level: ThreatLevel = ThreatLevel.NONE,
        details: str = "",
        blocked: bool = False
    ):
        """
        Log a security event.

        Args:
            event_type: Type of event
            agent_id: Agent that triggered the event
            command: Command that was executed or blocked
            threat_level: Threat level
            details: Additional details
            blocked: Whether the action was blocked
        """
        event = SecurityEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            agent_id=agent_id,
            command=command,
            threat_level=threat_level,
            details=details,
            blocked=blocked
        )

        # Log to file
        log_level = logging.WARNING if blocked or threat_level.value >= ThreatLevel.HIGH.value else logging.INFO
        self.logger.log(
            log_level,
            f"{event_type} | {agent_id} | {command[:100]} | {threat_level.name} | {'BLOCKED' if blocked else 'ALLOWED'}"
        )

        # Keep in memory
        self._recent_events.append(event)
        if len(self._recent_events) > self._max_recent:
            self._recent_events.pop(0)

    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent security events"""
        events = self._recent_events[-limit:]
        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type,
                "agent_id": e.agent_id,
                "command": e.command[:100],
                "threat_level": e.threat_level.name,
                "blocked": e.blocked
            }
            for e in events
        ]

    def get_blocked_events(self, since: datetime = None) -> List[Dict[str, Any]]:
        """Get blocked events"""
        if since:
            events = [e for e in self._recent_events if e.timestamp >= since and e.blocked]
        else:
            events = [e for e in self._recent_events if e.blocked]
        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type,
                "agent_id": e.agent_id,
                "command": e.command,
                "threat_level": e.threat_level.name,
                "details": e.details
            }
            for e in events
        ]


# Global instances
_rate_limiter = RateLimiter()
_security_auditor = SecurityAuditor()


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter"""
    return _rate_limiter


def get_security_auditor() -> SecurityAuditor:
    """Get global security auditor"""
    return _security_auditor
