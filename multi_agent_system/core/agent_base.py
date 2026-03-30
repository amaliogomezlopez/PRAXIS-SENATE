"""
Clase base para todos los agentes del sistema
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from core.event_bus import EventBus, Event, EventType
from core.state_manager import StateManager
from datetime import datetime


class AgentBase(ABC):
    """Clase base abstracta para todos los agentes"""

    def __init__(
        self,
        agent_id: str,
        event_bus: EventBus,
        state_manager: StateManager
    ):
        self.agent_id = agent_id
        self.event_bus = event_bus
        self.state_manager = state_manager
        self._running = False
        self._task_queue: asyncio.Queue = asyncio.Queue()

    async def start(self):
        """Iniciar el agente"""
        self._running = True
        await self.state_manager.update_agent_status(self.agent_id, "active")
        await self._log("Agent started")

    async def stop(self):
        """Detener el agente"""
        self._running = False
        await self.state_manager.update_agent_status(self.agent_id, "stopped")
        await self._log("Agent stopped")

    async def _log(self, message: str, level: str = "info"):
        """Enviar mensaje de log"""
        event = Event(
            type=EventType.AGENT_MESSAGE,
            data={
                "agent_id": self.agent_id,
                "message": message,
                "level": level
            },
            timestamp=datetime.now(),
            source=self.agent_id
        )
        await self.event_bus.publish(event)

    async def _publish_progress(self, message: str, progress: float):
        """Publicar progreso"""
        event = Event(
            type=EventType.PROGRESS_UPDATE,
            data={
                "agent_id": self.agent_id,
                "message": message,
                "progress": progress
            },
            timestamp=datetime.now(),
            source=self.agent_id
        )
        await self.event_bus.publish(event)

    @abstractmethod
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Procesar una tarea - debe ser implementado por subclases"""
        pass
