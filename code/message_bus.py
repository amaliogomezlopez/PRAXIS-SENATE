"""
Message Bus / Event Queue System
Handles all inter-agent communication using pub/sub pattern
"""

import asyncio
from typing import Dict, List, Callable, Optional, Set
from collections import defaultdict, deque
from datetime import datetime
import logging
from models import MessageEnvelope, MessageType


logger = logging.getLogger(__name__)


class MessageBus:
    """
    In-memory message bus for inter-agent communication
    Implements pub/sub pattern with topic-based routing
    """

    def __init__(self, max_queue_size: int = 1000):
        self.max_queue_size = max_queue_size

        # Topic -> List of subscribers (callbacks)
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)

        # Message queues per topic
        self.queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_queue_size))

        # Message history (for replay)
        self.history: List[MessageEnvelope] = []
        self.max_history_size = 10000

        # Statistics
        self.stats = {
            "messages_published": 0,
            "messages_consumed": 0,
            "messages_dropped": 0
        }

        # Running flag
        self._running = False

    def subscribe(self, topic: str, callback: Callable) -> None:
        """
        Subscribe to a topic

        Args:
            topic: Topic name
            callback: Async callback function to handle messages
        """
        self.subscribers[topic].append(callback)
        logger.info(f"Subscriber added to topic: {topic}")

    def unsubscribe(self, topic: str, callback: Callable) -> None:
        """
        Unsubscribe from a topic

        Args:
            topic: Topic name
            callback: Callback to remove
        """
        if callback in self.subscribers[topic]:
            self.subscribers[topic].remove(callback)
            logger.info(f"Subscriber removed from topic: {topic}")

    async def publish(self, topic: str, message: MessageEnvelope) -> None:
        """
        Publish a message to a topic

        Args:
            topic: Topic name
            message: Message to publish
        """
        # Add to queue
        self.queues[topic].append(message)

        # Add to history
        self.history.append(message)
        if len(self.history) > self.max_history_size:
            self.history.pop(0)

        # Update stats
        self.stats["messages_published"] += 1

        # Notify all subscribers
        for callback in self.subscribers[topic]:
            try:
                await callback(message)
                self.stats["messages_consumed"] += 1
            except Exception as e:
                logger.error(f"Error in subscriber callback: {e}")

        logger.debug(f"Published to {topic}: {message.message_type.value}")

    def get_queue_depth(self, topic: str) -> int:
        """Get current queue depth for a topic"""
        return len(self.queues[topic])

    def get_total_queue_depth(self) -> int:
        """Get total queue depth across all topics"""
        return sum(len(q) for q in self.queues.values())

    def get_history(self,
                   count: Optional[int] = None,
                   message_type: Optional[MessageType] = None,
                   agent_id: Optional[str] = None) -> List[MessageEnvelope]:
        """
        Get message history with optional filtering

        Args:
            count: Number of recent messages (None = all)
            message_type: Filter by message type
            agent_id: Filter by sender agent_id

        Returns:
            List of messages
        """
        messages = self.history

        # Filter by message type
        if message_type:
            messages = [m for m in messages if m.message_type == message_type]

        # Filter by agent
        if agent_id:
            messages = [m for m in messages if m.sender.get("agent_id") == agent_id]

        # Limit count
        if count:
            messages = messages[-count:]

        return messages

    def get_stats(self) -> Dict:
        """Get message bus statistics"""
        return {
            **self.stats,
            "queue_depth": self.get_total_queue_depth(),
            "topics_active": len(self.subscribers),
            "history_size": len(self.history)
        }

    def clear_history(self) -> None:
        """Clear message history"""
        self.history.clear()
        logger.info("Message history cleared")


class ConsumerGroup:
    """
    Consumer group for load balancing
    Multiple workers can join a consumer group to share workload
    """

    def __init__(self, group_id: str, message_bus: MessageBus):
        self.group_id = group_id
        self.message_bus = message_bus
        self.members: Set[str] = set()  # worker_ids
        self.current_index = 0

    def join(self, worker_id: str) -> None:
        """Worker joins the consumer group"""
        self.members.add(worker_id)
        logger.info(f"Worker {worker_id} joined consumer group {self.group_id}")

    def leave(self, worker_id: str) -> None:
        """Worker leaves the consumer group"""
        self.members.discard(worker_id)
        logger.info(f"Worker {worker_id} left consumer group {self.group_id}")

    def get_next_worker(self) -> Optional[str]:
        """
        Get next worker in round-robin fashion

        Returns:
            Worker ID or None if no workers available
        """
        if not self.members:
            return None

        members_list = list(self.members)
        worker_id = members_list[self.current_index % len(members_list)]
        self.current_index += 1
        return worker_id


class MessageRouter:
    """
    Routes messages to appropriate topics based on message type and content
    """

    def __init__(self, message_bus: MessageBus, topic_config: Dict[str, str]):
        """
        Args:
            message_bus: MessageBus instance
            topic_config: Mapping of message types to topics
        """
        self.message_bus = message_bus
        self.topic_config = topic_config

    async def route(self, message: MessageEnvelope) -> None:
        """
        Route message to appropriate topic

        Args:
            message: Message to route
        """
        # Get topic for this message type
        topic = self.topic_config.get(
            message.message_type.value,
            "default"
        )

        # Publish to topic
        await self.message_bus.publish(topic, message)


class PriorityQueue:
    """
    Priority queue for tasks
    Higher priority tasks are processed first
    """

    def __init__(self):
        self.high_priority = deque()
        self.medium_priority = deque()
        self.low_priority = deque()

    def push(self, message: MessageEnvelope, priority: str = "medium") -> None:
        """Add message to queue with priority"""
        if priority == "high":
            self.high_priority.append(message)
        elif priority == "low":
            self.low_priority.append(message)
        else:
            self.medium_priority.append(message)

    def pop(self) -> Optional[MessageEnvelope]:
        """Get highest priority message"""
        if self.high_priority:
            return self.high_priority.popleft()
        elif self.medium_priority:
            return self.medium_priority.popleft()
        elif self.low_priority:
            return self.low_priority.popleft()
        return None

    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return (not self.high_priority and
                not self.medium_priority and
                not self.low_priority)

    def size(self) -> int:
        """Get total queue size"""
        return (len(self.high_priority) +
                len(self.medium_priority) +
                len(self.low_priority))


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def example_usage():
    """Example usage of MessageBus"""

    # Create message bus
    bus = MessageBus()

    # Define subscriber callbacks
    async def task_handler(message: MessageEnvelope):
        print(f"Task received: {message.payload.get('task', {}).get('objective')}")

    async def status_handler(message: MessageEnvelope):
        print(f"Status update: {message.payload.get('current_step')}")

    # Subscribe to topics
    bus.subscribe("task_commands", task_handler)
    bus.subscribe("status_updates", status_handler)

    # Publish messages
    from models import create_task_command, create_status_update, TaskStatus

    task_msg = create_task_command(
        objective="Test task",
        task_type="test",
        sender_id="manager-001"
    )
    await bus.publish("task_commands", task_msg)

    status_msg = create_status_update(
        task_id="task-001",
        sender_id="worker-001",
        status=TaskStatus.IN_PROGRESS,
        progress_percent=50,
        current_step="Processing..."
    )
    await bus.publish("status_updates", status_msg)

    # Get stats
    print("\nMessage Bus Stats:")
    print(bus.get_stats())

    # Get history
    print("\nRecent Messages:")
    for msg in bus.get_history(count=10):
        print(f"  {msg.timestamp}: {msg.message_type.value}")


if __name__ == "__main__":
    asyncio.run(example_usage())
