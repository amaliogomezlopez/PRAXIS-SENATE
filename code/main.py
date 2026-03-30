"""
Multi-Agent System - Main Entry Point
Demonstrates complete system integration with Manager and Workers
"""

import asyncio
import logging
from typing import Dict, Any
import yaml
from pathlib import Path

from models import TaskStatus
from message_bus import MessageBus
from manager_agent import ManagerAgent
from worker_agent import (
    CodeEditorWorker,
    ResearcherWorker,
    CodeReviewerWorker,
    WorkerAgent
)


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s'
)
logger = logging.getLogger(__name__)


class MultiAgentSystem:
    """
    Main system coordinator
    """

    def __init__(self, config_path: str = "/workspace/config/system_config.yaml"):
        # Load configuration
        self.config = self._load_config(config_path)

        # Initialize message bus
        self.message_bus = MessageBus(
            max_queue_size=self.config['communication']['queue']['max_size']
        )

        # Initialize agents
        self.manager: ManagerAgent = None
        self.workers: Dict[str, WorkerAgent] = {}

        self._running = False

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Default configuration"""
        return {
            'system': {
                'name': 'MultiAgentSystem',
                'mode': 'development'
            },
            'manager': {
                'agent_id': 'senior-manager-001',
                'max_concurrent_tasks': 10
            },
            'workers': {
                'pool_size': 5,
                'specializations': [
                    {'type': 'code_editor', 'count': 2},
                    {'type': 'researcher', 'count': 1},
                    {'type': 'code_reviewer', 'count': 1},
                    {'type': 'file_manager', 'count': 1}
                ]
            },
            'communication': {
                'queue': {'max_size': 1000}
            }
        }

    async def initialize(self) -> None:
        """Initialize all system components"""
        logger.info("=" * 80)
        logger.info("Initializing Multi-Agent System")
        logger.info("=" * 80)

        # Create manager
        manager_config = self.config['manager']
        self.manager = ManagerAgent(
            agent_id=manager_config['agent_id'],
            message_bus=self.message_bus,
            config=manager_config
        )
        await self.manager.start()

        # Create worker pool
        await self._create_worker_pool()

        self._running = True
        logger.info("System initialized successfully")
        logger.info("=" * 80)

    async def _create_worker_pool(self) -> None:
        """Create pool of specialized workers"""
        worker_configs = self.config['workers']['specializations']
        worker_id_counter = 1

        for spec_config in worker_configs:
            spec_type = spec_config['type']
            count = spec_config['count']

            for i in range(count):
                worker_id = f"worker-{worker_id_counter:03d}"
                worker_id_counter += 1

                # Create specialized worker
                worker = self._create_specialized_worker(
                    worker_id,
                    spec_type,
                    self.config
                )

                if worker:
                    self.workers[worker_id] = worker
                    await worker.start()
                    logger.info(f"Created {spec_type} worker: {worker_id}")

    def _create_specialized_worker(self,
                                   worker_id: str,
                                   spec_type: str,
                                   config: Dict) -> WorkerAgent:
        """Create a specialized worker based on type"""
        worker_map = {
            'code_editor': CodeEditorWorker,
            'researcher': ResearcherWorker,
            'code_reviewer': CodeReviewerWorker,
        }

        worker_class = worker_map.get(spec_type)
        if worker_class:
            return worker_class(worker_id, self.message_bus, config)

        # Default worker
        return WorkerAgent(
            agent_id=worker_id,
            specialization=spec_type,
            capabilities=[],
            message_bus=self.message_bus,
            config=config
        )

    async def run(self, user_request: str) -> None:
        """
        Run the system with a user request

        Args:
            user_request: User's request description
        """
        if not self._running:
            await self.initialize()

        logger.info("=" * 80)
        logger.info(f"Processing User Request: {user_request}")
        logger.info("=" * 80)

        # Send request to manager
        response = await self.manager.receive_user_request(user_request)
        logger.info(f"Manager Response: {response}")

        # Wait for completion
        await self._wait_for_completion()

        # Display results
        await self._display_results()

    async def _wait_for_completion(self, timeout: int = 300) -> None:
        """Wait for all tasks to complete"""
        logger.info("\nWaiting for tasks to complete...")

        start_time = asyncio.get_event_loop().time()
        last_stats = None

        while asyncio.get_event_loop().time() - start_time < timeout:
            await asyncio.sleep(2)

            stats = self.manager.get_stats()

            # Log progress if changed
            if stats != last_stats:
                logger.info(
                    f"Progress: {stats['completed']}/{stats['total_tasks']} tasks completed"
                )
                last_stats = stats

            # Check if all done
            active = stats['in_progress'] + stats['pending']
            if active == 0 and stats['total_tasks'] > 0:
                logger.info("All tasks completed!")
                break

        await asyncio.sleep(1)  # Give time for final messages

    async def _display_results(self) -> None:
        """Display final results"""
        logger.info("\n" + "=" * 80)
        logger.info("FINAL RESULTS")
        logger.info("=" * 80)

        stats = self.manager.get_stats()
        logger.info(f"\nTask Summary:")
        logger.info(f"  Total tasks:       {stats['total_tasks']}")
        logger.info(f"  Completed:         {stats['completed']} ✓")
        logger.info(f"  Failed:            {stats['failed']} ✗")
        logger.info(f"  In progress:       {stats['in_progress']}")
        logger.info(f"  Pending:           {stats['pending']}")

        logger.info(f"\nWorker Summary:")
        for worker_id, worker in self.workers.items():
            state = worker.state
            logger.info(
                f"  {worker_id} ({state.specialization}): "
                f"{state.tasks_completed} completed, "
                f"{state.tasks_failed} failed"
            )

        bus_stats = self.message_bus.get_stats()
        logger.info(f"\nMessage Bus Stats:")
        logger.info(f"  Messages published: {bus_stats['messages_published']}")
        logger.info(f"  Messages consumed:  {bus_stats['messages_consumed']}")
        logger.info(f"  Queue depth:        {bus_stats['queue_depth']}")

        # Display task details
        logger.info(f"\nCompleted Tasks:")
        for task_id in self.manager.completed_tasks:
            task = self.manager.tasks[task_id]
            logger.info(f"\n  Task: {task.task_id}")
            logger.info(f"    Objective: {task.objective}")
            logger.info(f"    Assigned to: {task.assigned_to}")
            logger.info(f"    Status: {task.status.value}")
            if task.output_data:
                logger.info(f"    Summary: {task.output_data.get('summary', 'N/A')}")

        logger.info("\n" + "=" * 80)

    async def shutdown(self) -> None:
        """Shutdown the system"""
        logger.info("\nShutting down Multi-Agent System...")

        # Stop manager
        if self.manager:
            await self.manager.stop()

        # Stop all workers
        for worker in self.workers.values():
            await worker.stop()

        self._running = False
        logger.info("System shutdown complete")


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

async def example_simple_task():
    """Example: Simple single task"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Simple Task")
    print("="*80)

    system = MultiAgentSystem()
    await system.run("Review the authentication module for security issues")
    await system.shutdown()


async def example_complex_task():
    """Example: Complex multi-step task"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Complex Multi-Step Task")
    print("="*80)

    system = MultiAgentSystem()
    await system.run(
        "Implement authentication system and create comprehensive tests"
    )
    await system.shutdown()


async def example_multiple_requests():
    """Example: Multiple sequential requests"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Multiple Sequential Requests")
    print("="*80)

    system = MultiAgentSystem()
    await system.initialize()

    requests = [
        "Research best practices for password hashing",
        "Implement user registration endpoint",
        "Create unit tests for authentication",
    ]

    for request in requests:
        await system.run(request)
        await asyncio.sleep(2)

    await system.shutdown()


async def example_with_dashboard():
    """Example: Run with simulated dashboard"""
    print("\n" + "="*80)
    print("EXAMPLE 4: With Dashboard Monitoring")
    print("="*80)

    system = MultiAgentSystem()
    await system.initialize()

    # Start background monitoring
    async def monitor_system():
        """Monitor system stats"""
        while system._running:
            await asyncio.sleep(5)
            stats = system.manager.get_stats()
            bus_stats = system.message_bus.get_stats()

            print(f"\n[MONITOR] Tasks: {stats['in_progress']} active, "
                  f"{stats['completed']} done | "
                  f"Messages: {bus_stats['messages_published']} | "
                  f"Queue: {bus_stats['queue_depth']}")

    monitor_task = asyncio.create_task(monitor_system())

    # Run main task
    await system.run(
        "Implement complete authentication system with tests and documentation"
    )

    # Stop monitoring
    await system.shutdown()
    monitor_task.cancel()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """Main entry point"""
    import sys

    if len(sys.argv) > 1:
        # User provided a request
        request = " ".join(sys.argv[1:])
        system = MultiAgentSystem()
        await system.run(request)
        await system.shutdown()
    else:
        # Run examples
        print("\n" + "="*80)
        print("MULTI-AGENT SYSTEM - DEMONSTRATION")
        print("="*80)

        # Run example
        await example_complex_task()

        print("\n" + "="*80)
        print("DEMONSTRATION COMPLETE")
        print("="*80)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
    except Exception as e:
        logger.error(f"System error: {e}", exc_info=True)
