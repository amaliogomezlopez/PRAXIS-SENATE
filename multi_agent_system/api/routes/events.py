"""
Event streaming endpoints (SSE and WebSocket)
"""
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from sse_starlette.sse import EventSourceResponse
from typing import List, Dict, Any, Optional
from datetime import datetime

router = APIRouter(prefix="/api/events", tags=["events"])


class EventBroadcaster:
    """Bridge EventBus → WebSocket/SSE clients + Task Database events"""

    def __init__(self):
        self._ws_clients: List[WebSocket] = []
        self._sse_queues: List[asyncio.Queue] = []
        self._task_db_subscriptions: Dict[int, asyncio.Queue] = {}
        self._task_db = None
        self._task_listener_task: Optional[asyncio.Task] = None

    def set_task_database(self, task_db):
        """Set the task database and start listening for changes"""
        self._task_db = task_db
        if task_db and not self._task_listener_task:
            self._task_listener_task = asyncio.create_task(self._listen_to_task_db())

    async def _listen_to_task_db(self):
        """Listen to task database changes and broadcast them"""
        if not self._task_db:
            return

        queue = self._task_db.subscribe()
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
                await self.broadcast_task_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                break

    async def broadcast_task_event(self, event: Dict[str, Any]):
        """Broadcast a task database event"""
        # Format: {type, task, timestamp}
        event_data = {
            "type": event.get('type', 'TASK_UPDATED'),
            "data": event.get('task', {}),
            "timestamp": event.get('timestamp', datetime.now().isoformat()),
            "source": "task_database"
        }

        # Send to WebSocket clients
        for ws in self._ws_clients[:]:
            try:
                await ws.send_json(event_data)
            except Exception:
                self._ws_clients.remove(ws)

        # Send to SSE queues
        for queue in self._sse_queues[:]:
            try:
                await queue.put(event_data)
            except Exception:
                self._sse_queues.remove(queue)

    async def broadcast(self, event):
        """Broadcast EventBus event to all connected clients"""
        # Handle both Event objects and dicts
        if hasattr(event, 'type'):
            # It's an Event object
            event_data = {
                "type": event.type.value,
                "data": event.data,
                "timestamp": event.timestamp.isoformat(),
                "source": event.source
            }
        else:
            event_data = event

        # Send to WebSocket clients
        for ws in self._ws_clients[:]:
            try:
                await ws.send_json(event_data)
            except Exception:
                self._ws_clients.remove(ws)

        # Send to SSE queues
        for queue in self._sse_queues[:]:
            try:
                await queue.put(event_data)
            except Exception:
                self._sse_queues.remove(queue)

    def add_ws_client(self, ws: WebSocket):
        self._ws_clients.append(ws)

    def remove_ws_client(self, ws: WebSocket):
        if ws in self._ws_clients:
            self._ws_clients.remove(ws)

    def create_sse_queue(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self._sse_queues.append(queue)
        return queue

    def remove_sse_queue(self, queue: asyncio.Queue):
        if queue in self._sse_queues:
            self._sse_queues.remove(queue)


# Global broadcaster instance
broadcaster = EventBroadcaster()


async def event_generator(event_types: List[str] = None):
    """Generate SSE events"""
    queue = broadcaster.create_sse_queue()
    try:
        while True:
            event_data = await queue.get()
            if event_types and event_data["type"] not in event_types:
                continue
            yield {
                "event": event_data["type"],
                "data": json.dumps(event_data)
            }
    finally:
        broadcaster.remove_sse_queue(queue)


@router.get("/stream")
async def stream_events(event_types: str = None):
    """SSE endpoint for real-time updates"""
    types = event_types.split(",") if event_types else None
    return EventSourceResponse(event_generator(types))


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for dashboard"""
    await websocket.accept()
    broadcaster.add_ws_client(websocket)

    try:
        while True:
            # Keep connection alive, receive messages from client
            data = await websocket.receive_text()
            # Handle client messages
            if data == "ping":
                await websocket.send_text("pong")
            elif data.startswith("subscribe:"):
                # Allow clients to subscribe to specific event types
                subscription = data.split(":", 1)[1]
                await websocket.send_json({
                    "type": "subscribed",
                    "subscription": subscription
                })
    except WebSocketDisconnect:
        broadcaster.remove_ws_client(websocket)
    except Exception:
        broadcaster.remove_ws_client(websocket)


@router.get("/tasks/subscribe")
async def subscribe_to_tasks(request: Request):
    """
    SSE endpoint specifically for task updates.
    Subscribes to the centralized task database.
    """
    async def task_event_generator():
        queue = broadcaster.create_sse_queue() if not hasattr(broadcaster, '_task_db') or not broadcaster._task_db else asyncio.Queue()

        # If task db is set, create subscription
        if broadcaster._task_db:
            db_queue = broadcaster._task_db.subscribe()
        else:
            db_queue = None

        try:
            while True:
                if db_queue:
                    try:
                        event = await asyncio.wait_for(db_queue.get(), timeout=30.0)
                        yield {
                            "event": event.get('type', 'TASK_UPDATED'),
                            "data": json.dumps(event)
                        }
                    except asyncio.TimeoutError:
                        # Send keepalive
                        yield {"event": "keepalive", "data": "{}"}
                        continue
                else:
                    await asyncio.sleep(1)
        finally:
            if db_queue and hasattr(broadcaster._task_db, 'unsubscribe'):
                broadcaster._task_db.unsubscribe(db_queue)
            broadcaster.remove_sse_queue(queue)

    return EventSourceResponse(task_event_generator())
