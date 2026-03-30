#!/usr/bin/env python3
"""
End-to-End Test Script for PRAXIS-SENATE Multi-Agent System

This script:
1. Submits a complex task via REST API
2. Subscribes to SSE events for real-time updates
3. Prints all state changes to console
4. Verifies the complete workflow

Usage:
    python test_e2e_flow.py [--server http://localhost:8000]
"""
import asyncio
import json
import logging
import time
import argparse
from datetime import datetime
import requests
import sseclient
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("E2E_Test")


class E2ETestRunner:
    """Runs end-to-end tests against the PRAXIS-SENATE API"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api"
        self.running = True
        self.events_received = []
        self.task_id = None

    def check_server(self) -> bool:
        """Check if server is running and healthy"""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5)
            if resp.status_code == 200:
                logger.info(f"✓ Server is healthy: {resp.json()}")
                return True
            else:
                logger.error(f"✗ Server returned status {resp.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            logger.error(f"✗ Cannot connect to server at {self.base_url}")
            logger.error("  Make sure the server is running: python -m api.server")
            return False
        except Exception as e:
            logger.error(f"✗ Server check failed: {e}")
            return False

    def get_stats(self) -> dict:
        """Get system statistics"""
        try:
            resp = requests.get(f"{self.api_base}/stats", timeout=5)
            if resp.status_code == 200:
                return resp.json()
            return {}
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}

    def submit_task(self, description: str) -> str:
        """Submit a new task via REST API"""
        logger.info(f"Submitting task: {description[:80]}...")

        try:
            resp = requests.post(
                f"{self.api_base}/tasks",
                json={"description": description},
                timeout=30
            )

            if resp.status_code == 200:
                data = resp.json()
                task_id = data.get("task_id")
                logger.info(f"✓ Task submitted successfully: {task_id}")
                return task_id
            else:
                logger.error(f"✗ Failed to submit task: {resp.status_code} - {resp.text}")
                return None

        except requests.exceptions.Timeout:
            logger.error("✗ Task submission timed out")
            return None
        except Exception as e:
            logger.error(f"✗ Task submission failed: {e}")
            return None

    def get_task(self, task_id: str) -> dict:
        """Get task details"""
        try:
            resp = requests.get(f"{self.api_base}/tasks/{task_id}", timeout=5)
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.warning(f"Failed to get task {task_id}: {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"Failed to get task: {e}")
            return None

    def list_tasks(self) -> list:
        """List all tasks"""
        try:
            resp = requests.get(f"{self.api_base}/tasks", timeout=5)
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            return []

    def subscribe_sse(self, callback=None):
        """Subscribe to SSE events stream"""
        logger.info("Starting SSE subscription for events...")

        try:
            # Use sseclient-py to consume SSE
            response = requests.get(
                f"{self.api_base}/events/stream",
                stream=True,
                timeout=60
            )

            client = sseclient.SSEClient(response)

            for event in client.events():
                if not self.running:
                    break

                try:
                    data = json.loads(event.data) if event.data else {}
                    event_type = event.type

                    self.events_received.append({
                        "type": event_type,
                        "data": data,
                        "timestamp": datetime.now().isoformat()
                    })

                    # Log the event
                    self._log_event(event_type, data)

                    # Call callback if provided
                    if callback:
                        callback(event_type, data)

                except json.JSONDecodeError:
                    logger.warning(f"Received non-JSON event: {event.data}")

        except requests.exceptions.ConnectionError:
            logger.error("SSE connection failed - server may not support SSE")
        except requests.exceptions.Timeout:
            logger.warning("SSE connection timed out")
        except Exception as e:
            logger.error(f"SSE subscription error: {e}")

    def _log_event(self, event_type: str, data: dict):
        """Log an event in a formatted way"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        icons = {
            "task_created": "📝",
            "task_assigned": "👤",
            "task_started": "▶️",
            "task_completed": "✅",
            "task_failed": "❌",
            "task_halted": "⏸",
            "critique_received": "🔍",
            "problem_detected": "⚠️",
            "llm_prompt": "📤",
            "llm_response": "📥",
            "agent_thinking": "💭",
            "task_decomposed": "📋",
        }

        icon = icons.get(event_type, "📌")
        print(f"\n[{timestamp}] {icon} {event_type}")

        # Print relevant data
        if task_id := data.get("task_id"):
            print(f"       Task: {task_id[:20]}...")
        if agent := data.get("agent"):
            print(f"       Agent: {agent}")
        if status := data.get("status"):
            print(f"       Status: {status}")
        if error := data.get("error"):
            print(f"       Error: {error[:100]}...")
        if approved := data.get("approved"):
            print(f"       Approved: {approved}")
        if description := data.get("description"):
            print(f"       Description: {description[:80]}...")

    def run_test(self, task_description: str = None):
        """Run the complete E2E test"""
        logger.info("=" * 60)
        logger.info("PRAXIS-SENATE E2E Test Suite")
        logger.info("=" * 60)

        # Check server
        if not self.check_server():
            logger.error("Server is not available. Aborting test.")
            return False

        # Get initial stats
        stats = self.get_stats()
        logger.info(f"Initial stats: {stats}")

        # Default complex task
        if task_description is None:
            task_description = (
                "Write a Python script that calculates the first 50 Fibonacci numbers, "
                "saves it to a file called fibonacci.py, executes it, and verifies the output. "
                "The script should use proper error handling and include comments."
            )

        # Start SSE subscription in background thread
        sse_thread = threading.Thread(target=self.subscribe_sse, daemon=True)
        sse_thread.start()

        # Give SSE time to connect
        time.sleep(1)

        # Submit the task
        self.task_id = self.submit_task(task_description)

        if not self.task_id:
            logger.error("Failed to submit task. Aborting test.")
            return False

        # Wait for task processing (with timeout)
        logger.info("Monitoring task progress...")
        max_wait = 120  # 2 minutes timeout
        start_time = time.time()
        last_status = None

        while time.time() - start_time < max_wait:
            task = self.get_task(self.task_id)

            if task:
                status = task.get("status")
                if status != last_status:
                    logger.info(f"Task status changed: {last_status} -> {status}")
                    last_status = status

                # Task completed or failed
                if status in ["completed", "failed", "halted"]:
                    break

            time.sleep(2)

        # Final task state
        final_task = self.get_task(self.task_id)
        if final_task:
            logger.info("\n" + "=" * 60)
            logger.info("Final Task State:")
            logger.info("=" * 60)
            logger.info(f"  ID: {final_task.get('id')}")
            logger.info(f"  Description: {final_task.get('description')[:80]}...")
            logger.info(f"  Status: {final_task.get('status')}")
            logger.info(f"  Assigned To: {final_task.get('assigned_to')}")

            if result := final_task.get('result'):
                logger.info(f"  Result: {json.dumps(result, indent=2)[:500]}")

            if error := final_task.get('error'):
                logger.info(f"  Error: {error}")

            # Determine success
            success = final_task.get('status') == 'completed'

            if success:
                logger.info("\n✅ TEST PASSED - Task completed successfully!")
            else:
                logger.warning(f"\n⚠️ TEST ENDED - Task status: {final_task.get('status')}")

            return success
        else:
            logger.error("Could not retrieve final task state")
            return False

    def stop(self):
        """Stop the test runner"""
        self.running = False


def main():
    parser = argparse.ArgumentParser(description="E2E Test for PRAXIS-SENATE")
    parser.add_argument(
        "--server",
        default="http://localhost:8000",
        help="Base URL of the server (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--task",
        default=None,
        help="Custom task description (optional)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    runner = E2ETestRunner(base_url=args.server)

    try:
        success = runner.run_test(task_description=args.task)
        exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        runner.stop()
        exit(1)


if __name__ == "__main__":
    main()
