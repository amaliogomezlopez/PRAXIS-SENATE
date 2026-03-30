"""
Extended Example - Demonstrating all features
"""
import asyncio
import logging
from main_extended import MultiAgentSystem


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_automated_workflow():
    """Example: Automated workflow with LLM-powered decomposition"""
    logger.info("Starting automated workflow example...")

    system = MultiAgentSystem()
    await system.initialize(num_workers=3)

    # Start agents
    manager_task = asyncio.create_task(system.manager.run())
    worker_tasks = [asyncio.create_task(w.run()) for w in system.workers]

    # Wait for agents to start
    await asyncio.sleep(1)

    # Submit a complex task
    task_id = await system.manager.submit_user_task(
        "Create a Python web scraper that extracts article titles from a news website and saves them to a JSON file"
    )

    logger.info(f"Submitted task: {task_id}")

    # Wait for task completion
    await asyncio.sleep(10)

    # Get task report
    report = await system.manager.generate_task_report(task_id)
    logger.info(f"\n{'='*60}\nTask Report:\n{'='*60}\n{report}")

    # Get LLM statistics
    stats = system.llm_manager.get_stats()
    logger.info(f"\nLLM Usage Statistics:")
    for provider, provider_stats in stats.items():
        logger.info(f"  {provider}: {provider_stats}")

    # Cleanup
    await system.stop()
    for task in worker_tasks + [manager_task]:
        task.cancel()


async def example_role_management():
    """Example: Role management"""
    logger.info("Starting role management example...")

    system = MultiAgentSystem()
    await system.initialize(num_workers=1)

    # List existing roles
    roles = system.role_manager.list_roles()
    logger.info(f"Existing roles: {roles}")

    # Load and display a role
    coder_role = system.role_manager.get_role("coder")
    if coder_role:
        logger.info(f"\nRole: {coder_role.name}")
        logger.info(f"Specialization: {coder_role.specialization}")
        logger.info(f"Instructions:\n{coder_role.instructions[:200]}...")

    # Create a new role
    custom_role = system.role_manager.create_role(
        name="DataScientist",
        specialization="Expert in data analysis, machine learning, and statistical modeling",
        instructions="Analyze datasets, build ML models, create visualizations, and generate insights",
        constraints="Must validate data quality, document assumptions, and explain model decisions",
        metadata={"skill_level": "expert", "tools": "Python, Pandas, Scikit-learn"}
    )

    logger.info(f"\nCreated new role: {custom_role.name}")

    # List roles again
    roles = system.role_manager.list_roles()
    logger.info(f"Updated roles: {roles}")

    await system.stop()


async def example_user_correction():
    """Example: User correction workflow"""
    logger.info("Starting user correction example...")

    system = MultiAgentSystem()
    await system.initialize(num_workers=2)

    # Start agents
    manager_task = asyncio.create_task(system.manager.run())
    worker_tasks = [asyncio.create_task(w.run()) for w in system.workers]

    await asyncio.sleep(1)

    # Submit a task
    task_id = await system.manager.submit_user_task(
        "Search for Python asyncio tutorials and create a summary document"
    )

    logger.info(f"Submitted task: {task_id}")

    # Wait a bit
    await asyncio.sleep(3)

    # Simulate user correction
    worker_id = system.workers[0].agent_id
    await system.manager.receive_correction(
        worker_id,
        "Please focus on advanced asyncio patterns, not basic tutorials"
    )

    logger.info(f"Sent correction to {worker_id}")

    # Wait for processing
    await asyncio.sleep(5)

    # Cleanup
    await system.stop()
    for task in worker_tasks + [manager_task]:
        task.cancel()


async def example_llm_providers():
    """Example: Testing different LLM providers"""
    logger.info("Starting LLM providers example...")

    system = MultiAgentSystem()

    # Test each provider
    providers = system.llm_manager.get_provider_info()["providers"]

    for provider_name in providers:
        logger.info(f"\nTesting provider: {provider_name}")

        try:
            from llm.base import LLMMessage

            messages = [
                LLMMessage(role="user", content="Say 'Hello from AI!' in exactly 5 words.")
            ]

            result = await system.llm_manager.chat(
                messages,
                provider=provider_name,
                temperature=0.7
            )

            logger.info(f"  Response: {result['response']}")
            logger.info(f"  Provider used: {result['provider']}")
            logger.info(f"  Success: {result['success']}")

        except Exception as e:
            logger.error(f"  Error: {e}")

    # Show statistics
    stats = system.llm_manager.get_stats()
    logger.info(f"\nFinal statistics:")
    for provider, provider_stats in stats.items():
        logger.info(f"  {provider}: {provider_stats}")


def show_menu():
    """Show example menu"""
    print("\n" + "="*60)
    print("Multi-Agent System - Extended Examples")
    print("="*60)
    print("\n1. Automated Workflow (LLM-powered task decomposition)")
    print("2. Role Management (Create/Load/Manage roles)")
    print("3. User Correction Workflow (Interactive feedback)")
    print("4. LLM Providers Testing (Test different AI providers)")
    print("5. Interactive Dashboard (Full system with menu)")
    print("0. Exit")
    print()


async def run_interactive_dashboard():
    """Run full interactive dashboard"""
    system = MultiAgentSystem()
    await system.initialize(num_workers=3)
    await system.start()


async def main():
    """Main menu"""
    while True:
        show_menu()

        try:
            choice = input("Select example (0-5): ").strip()

            if choice == "0":
                print("Goodbye!")
                break
            elif choice == "1":
                await example_automated_workflow()
            elif choice == "2":
                await example_role_management()
            elif choice == "3":
                await example_user_correction()
            elif choice == "4":
                await example_llm_providers()
            elif choice == "5":
                await run_interactive_dashboard()
            else:
                print("Invalid choice. Please try again.")

            input("\nPress Enter to continue...")

        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    asyncio.run(main())
