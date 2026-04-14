"""
Sistema de eventos para comunicación entre agentes
"""
import asyncio
import logging
from typing import Dict, List, Callable, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(Enum):
    TASK_CREATED = "task_created"
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    FILE_MODIFIED = "file_modified"
    PROBLEM_DETECTED = "problem_detected"
    PROGRESS_UPDATE = "progress_update"
    AGENT_MESSAGE = "agent_message"
    # Critic agent events
    TASK_DECOMPOSED = "task_decomposed"
    CRITIQUE_RECEIVED = "critique_received"
    CRITIQUE_REQUEST = "critique_request"
    # LLM transparency events
    LLM_PROMPT = "llm_prompt"
    LLM_RESPONSE = "llm_response"
    AGENT_THINKING = "agent_thinking"
    # Task control events
    TASK_HALTED = "task_halted"
    TASK_FEEDBACK = "task_feedback"
    TASK_RESUMED = "task_resumed"


@dataclass
class Event:
    """Evento del sistema"""
    type: EventType
    data: Dict[str, Any]
    timestamp: datetime
    source: str


class EventBus:
    """Bus de eventos asíncrono para comunicación entre agentes"""

    MAX_QUEUE_SIZE = 10000  # Backpressure: prevent unbounded memory growth

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=self.MAX_QUEUE_SIZE)
        self._running = False
        self._event_count = 0
        self._error_count = 0

    def subscribe(self, event_type: EventType, callback: Callable):
        """Suscribirse a un tipo de evento (deduplicated)"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        # Prevent duplicate subscriptions of same callback
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)

    async def publish(self, event: Event):
        """Publicar un evento"""
        try:
            self._event_queue.put_nowait(event)
            self._event_count += 1
        except asyncio.QueueFull:
            logger.warning(
                f"EventBus queue full ({self.MAX_QUEUE_SIZE}), "
                f"dropping oldest event to make room"
            )
            try:
                self._event_queue.get_nowait()  # Drop oldest
            except asyncio.QueueEmpty:
                pass
            await self._event_queue.put(event)
            self._event_count += 1

    async def start(self):
        """Iniciar el procesamiento de eventos"""
        self._running = True
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=0.1
                )
                await self._process_event(event)
            except asyncio.TimeoutError:
                continue

    async def _process_event(self, event: Event):
        """Procesar un evento y notificar a los suscriptores"""
        if event.type in self._subscribers:
            tasks = [
                callback(event)
                for callback in self._subscribers[event.type]
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self._error_count += 1
                    cb_name = self._subscribers[event.type][i].__qualname__
                    logger.error(
                        f"EventBus callback error in {cb_name} "
                        f"for {event.type.value}: {result} "
                        f"(total errors: {self._error_count})"
                    )

    def stop(self):
        """Detener el procesamiento de eventos"""
        self._running = False
