"""
Multi-Agent System - Extended Version
Main entry point with LLM integration, roles, and interactive dashboard
"""
import asyncio
import logging
import os
from pathlib import Path
from core.event_bus import EventBus
from core.state_manager import StateManager
from core.senior_agent import SeniorAgent
from core.worker_agent import WorkerAgent
from core.critic_agent import CriticAgent
from tools.file_operations import FileOperations
from tools.web_tools import WebTools
from llm.manager import LLMManager
from llm.providers import OpenAIProvider, AnthropicProvider, GoogleProvider, OpenRouterProvider, MiniMaxProvider
from workers.role_manager import RoleManager
from dashboard.interactive_dashboard import InteractiveDashboard
from config import load_config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MultiAgentSystem:
    """Main system orchestrator"""

    def __init__(self, config_path: str = None):
        self.config = load_config(config_path)

        # Core components
        self.event_bus = EventBus()
        self.state_manager = StateManager()

        # LLM Manager
        self.llm_manager = self._setup_llm_manager()

        # Role Manager
        roles_dir = Path(__file__).parent / "roles"
        self.role_manager = RoleManager(str(roles_dir))

        # Tools
        self.file_ops = FileOperations()
        self.web_tools = WebTools()

        # Agents
        self.manager: SeniorAgent = None
        self.workers = []
        self.critic: CriticAgent = None

        # Dashboard
        self.dashboard: InteractiveDashboard = None

    def _setup_llm_manager(self) -> LLMManager:
        """Setup LLM manager with configured providers"""
        llm_config = self.config.get("llm", {})

        llm_manager = LLMManager(
            retry_count=llm_config.get("retry_count", 3),
            fallback_enabled=llm_config.get("fallback_enabled", True)
        )

        providers_config = llm_config.get("providers", {})

        # Register OpenAI
        if providers_config.get("openai", {}).get("enabled"):
            openai_cfg = providers_config["openai"]
            api_key = openai_cfg.get("api_key")

            if api_key and api_key != "":
                try:
                    provider = OpenAIProvider(
                        api_key=api_key,
                        model=openai_cfg.get("model", "gpt-4"),
                        **openai_cfg.get("config", {})
                    )
                    llm_manager.register_provider(
                        "openai",
                        provider,
                        priority=openai_cfg.get("priority", 1),
                        set_as_default=True
                    )
                    logger.info("Registered OpenAI provider")
                except Exception as e:
                    logger.warning(f"Failed to register OpenAI: {e}")

        # Register Anthropic
        if providers_config.get("anthropic", {}).get("enabled"):
            anthropic_cfg = providers_config["anthropic"]
            api_key = anthropic_cfg.get("api_key")

            if api_key and api_key != "":
                try:
                    provider = AnthropicProvider(
                        api_key=api_key,
                        model=anthropic_cfg.get("model", "claude-3-sonnet-20240229"),
                        **anthropic_cfg.get("config", {})
                    )
                    llm_manager.register_provider(
                        "anthropic",
                        provider,
                        priority=anthropic_cfg.get("priority", 2)
                    )
                    logger.info("Registered Anthropic provider")
                except Exception as e:
                    logger.warning(f"Failed to register Anthropic: {e}")

        # Register Google
        if providers_config.get("google", {}).get("enabled"):
            google_cfg = providers_config["google"]
            api_key = google_cfg.get("api_key")

            if api_key and api_key != "":
                try:
                    provider = GoogleProvider(
                        api_key=api_key,
                        model=google_cfg.get("model", "gemini-pro"),
                        **google_cfg.get("config", {})
                    )
                    llm_manager.register_provider(
                        "google",
                        provider,
                        priority=google_cfg.get("priority", 3)
                    )
                    logger.info("Registered Google provider")
                except Exception as e:
                    logger.warning(f"Failed to register Google: {e}")

        # Register OpenRouter
        if providers_config.get("openrouter", {}).get("enabled"):
            openrouter_cfg = providers_config["openrouter"]
            api_key = openrouter_cfg.get("api_key")

            if api_key and api_key != "":
                try:
                    provider = OpenRouterProvider(
                        api_key=api_key,
                        model=openrouter_cfg.get("model", "anthropic/claude-3-sonnet"),
                        **openrouter_cfg.get("config", {})
                    )
                    llm_manager.register_provider(
                        "openrouter",
                        provider,
                        priority=openrouter_cfg.get("priority", 4)
                    )
                    logger.info("Registered OpenRouter provider")
                except Exception as e:
                    logger.warning(f"Failed to register OpenRouter: {e}")

        # Register MiniMax
        if providers_config.get("minimax", {}).get("enabled"):
            minimax_cfg = providers_config["minimax"]
            api_key = minimax_cfg.get("api_key")

            if api_key and api_key != "":
                try:
                    provider = MiniMaxProvider(
                        api_key=api_key,
                        model=minimax_cfg.get("model", "MiniMax-Text-01"),
                        **minimax_cfg.get("config", {})
                    )
                    llm_manager.register_provider(
                        "minimax",
                        provider,
                        priority=minimax_cfg.get("priority", 1),
                        set_as_default=True
                    )
                    logger.info("Registered MiniMax provider")
                except Exception as e:
                    logger.warning(f"Failed to register MiniMax: {e}")

        # Log registered providers
        provider_info = llm_manager.get_provider_info()
        logger.info(f"LLM Manager initialized with providers: {provider_info['providers']}")
        logger.info(f"Default provider: {provider_info['default_provider']}")

        return llm_manager

    async def initialize(self, num_workers: int = 3):
        """Initialize the system"""
        logger.info("Initializing Multi-Agent System...")

        # Get critic config
        critic_config = self.config.get("critic", {})

        # Create CriticAgent if enabled
        if critic_config.get("enabled", False):
            self.critic = CriticAgent(
                agent_id="critic_01",
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                llm_manager=self.llm_manager,
                config=critic_config
            )
            logger.info("CriticAgent enabled")
        else:
            logger.info("CriticAgent disabled")

        # Create manager (Senior Agent) with critic config
        self.manager = SeniorAgent(
            agent_id="senior_agent",
            event_bus=self.event_bus,
            state_manager=self.state_manager,
            llm_manager=self.llm_manager,
            critic_config=critic_config
        )

        # Create workers
        for i in range(num_workers):
            worker = WorkerAgent(
                agent_id=f"worker_{i+1}",
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                file_ops=self.file_ops,
                web_tools=self.web_tools
            )
            self.workers.append(worker)
            self.manager.add_worker(worker)

        # Create dashboard
        self.dashboard = InteractiveDashboard(
            event_bus=self.event_bus,
            state_manager=self.state_manager,
            role_manager=self.role_manager,
            system=self
        )

        logger.info(f"System initialized with 1 manager and {num_workers} workers")

    async def start(self):
        """Start the system"""
        logger.info("Starting Multi-Agent System...")

        # Start manager
        manager_task = asyncio.create_task(self.manager.run())

        # Start workers
        worker_tasks = [asyncio.create_task(worker.run()) for worker in self.workers]

        # Start critic if enabled
        critic_task = None
        if self.critic:
            critic_task = asyncio.create_task(self.critic.run())

        # Start dashboard in interactive mode
        dashboard_task = asyncio.create_task(self._run_dashboard())

        # Wait for all tasks
        try:
            if critic_task:
                await asyncio.gather(manager_task, *worker_tasks, critic_task, dashboard_task)
            else:
                await asyncio.gather(manager_task, *worker_tasks, dashboard_task)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await self.stop()

    async def _run_dashboard(self):
        """Run dashboard in menu mode"""
        await asyncio.sleep(2)  # Wait for agents to start

        while True:
            try:
                await self.dashboard.show_menu()

                if not self.dashboard._running:
                    break

                await asyncio.sleep(0.5)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Dashboard error: {e}")
                await asyncio.sleep(1)

    async def stop(self):
        """Stop the system"""
        logger.info("Stopping system...")

        if self.manager:
            await self.manager.stop()

        for worker in self.workers:
            await worker.stop()

        if self.critic:
            await self.critic.stop()

        if self.dashboard:
            self.dashboard.stop()

        logger.info("System stopped")


async def main():
    """Main entry point"""
    # Create system
    system = MultiAgentSystem()

    # Initialize
    await system.initialize(num_workers=3)

    # Start
    await system.start()


if __name__ == "__main__":
    asyncio.run(main())
