"""
FastAPI Server with REST API and WebSocket support
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from api.routes import tasks, agents, events, critiques, roles
from api.dependencies import APISystem
from core.event_bus import EventBus, Event, EventType
from core.state_manager import StateManager
from core.senior_agent import SeniorAgent
from core.worker_agent import WorkerAgent
from core.critic_agent import CriticAgent
from llm.manager import LLMManager
from llm.providers import OpenAIProvider, AnthropicProvider, GoogleProvider, OpenRouterProvider, MiniMaxProvider
from tools.file_operations import FileOperations
from tools.web_tools import WebTools
from config import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Global system reference
system = None
api_system: APISystem = None


async def setup_event_forwarding(event_bus: EventBus):
    """Forward EventBus events to the broadcaster"""
    from api.routes.events import broadcaster

    async def forward_event(event: Event):
        await broadcaster.broadcast(event)

    # Subscribe to all event types
    for event_type in EventType:
        event_bus.subscribe(event_type, forward_event)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global system, api_system

    logger.info("Initializing Multi-Agent System for API...")

    # Load config
    config = load_config()

    # Create core components
    event_bus = EventBus()
    state_manager = StateManager()
    state_manager.set_event_bus(event_bus)  # Wire StateManager to EventBus for real-time events

    # Setup LLM Manager
    llm_manager = LLMManager(
        retry_count=config.get("llm", {}).get("retry_count", 3),
        fallback_enabled=config.get("llm", {}).get("fallback_enabled", True)
    )

    # Register providers
    providers_config = config.get("llm", {}).get("providers", {})

    for provider_name, provider_cfg in providers_config.items():
        if not provider_cfg.get("enabled"):
            continue

        api_key = provider_cfg.get("api_key", "")
        if not api_key:
            continue

        model = provider_cfg.get("model", "")
        priority = provider_cfg.get("priority", 100)
        set_default = provider_cfg.get("priority", 100) == 1

        try:
            if provider_name == "openai":
                provider = OpenAIProvider(api_key=api_key, model=model, **provider_cfg.get("config", {}))
            elif provider_name == "anthropic":
                provider = AnthropicProvider(api_key=api_key, model=model, **provider_cfg.get("config", {}))
            elif provider_name == "google":
                provider = GoogleProvider(api_key=api_key, model=model, **provider_cfg.get("config", {}))
            elif provider_name == "openrouter":
                provider = OpenRouterProvider(api_key=api_key, model=model, **provider_cfg.get("config", {}))
            elif provider_name == "minimax":
                provider = MiniMaxProvider(api_key=api_key, model=model, **provider_cfg.get("config", {}))
            else:
                continue

            llm_manager.register_provider(provider_name, provider, priority=priority, set_as_default=set_default)
            logger.info(f"Registered {provider_name} provider")
        except Exception as e:
            logger.warning(f"Failed to register {provider_name}: {e}")

    # Create tools
    file_ops = FileOperations()
    web_tools = WebTools()

    # Execution mode from config
    exec_config = config.get("execution", {})
    execution_mode = os.environ.get("PRAXIS_MODE", exec_config.get("mode", "docker"))
    workspace = os.environ.get("PRAXIS_WORKSPACE", exec_config.get("workspace", "")) or None

    # Create critic if enabled
    critic_config = config.get("critic", {})
    critic = None
    if critic_config.get("enabled", False):
        critic = CriticAgent(
            agent_id="critic_01",
            event_bus=event_bus,
            state_manager=state_manager,
            llm_manager=llm_manager,
            config=critic_config
        )

    # Create senior agent
    senior_agent = SeniorAgent(
        agent_id="senior_agent",
        event_bus=event_bus,
        state_manager=state_manager,
        llm_manager=llm_manager,
        critic_config=critic_config
    )

    # Create workers
    num_workers = config.get("workers", {}).get("count", 3)
    workers = []
    for i in range(num_workers):
        worker = WorkerAgent(
            agent_id=f"worker_{i+1}",
            event_bus=event_bus,
            state_manager=state_manager,
            file_ops=file_ops,
            web_tools=web_tools,
            llm_manager=llm_manager,
            execution_mode=execution_mode,
            workspace=workspace
        )
        workers.append(worker)
        senior_agent.add_worker(worker)

    # Create API system wrapper
    api_system = APISystem(
        event_bus=event_bus,
        state_manager=state_manager,
        senior_agent=senior_agent,
        workers=workers,
        critic=critic
    )

    # Store in app state
    app.state.api_system = api_system
    app.state.event_bus = event_bus
    app.state.config = config

    # Setup event forwarding
    await setup_event_forwarding(event_bus)

    # Start event bus processor
    asyncio.create_task(event_bus.start())

    # Start agents
    asyncio.create_task(senior_agent.run())
    for worker in workers:
        asyncio.create_task(worker.run())
    if critic:
        asyncio.create_task(critic.run())

    logger.info("Multi-Agent System initialized")

    yield

    # Shutdown
    logger.info("Shutting down Multi-Agent System...")
    event_bus.stop()
    await senior_agent.stop()
    for worker in workers:
        await worker.stop()
    if critic:
        await critic.stop()
    await web_tools.close()


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="PRAXIS-SENATE API",
        description="Multi-Agent System REST API",
        version="1.0.0",
        lifespan=lifespan
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(tasks.router)
    app.include_router(agents.router)
    app.include_router(events.router)
    app.include_router(critiques.router)
    app.include_router(roles.router)

    # Health check
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "praxix-senate"}

    @app.get("/api/stats")
    async def get_stats():
        """Get system statistics"""
        if not api_system:
            return {"error": "System not initialized"}

        stats = await api_system.state_manager.get_stats()
        llm_info = api_system.senior_agent.llm.get_provider_info() if api_system.senior_agent else {}

        return {
            **stats,
            "llm_provider": llm_info.get("default_provider"),
            "llm_stats": llm_info.get("stats", {})
        }

    # Mount static files for dashboard
    dashboard_path = Path(__file__).parent.parent / "dashboard" / "web"
    if dashboard_path.exists():
        # Mount static files at /dashboard/static
        app.mount("/dashboard/static", StaticFiles(directory=str(dashboard_path / "static")), name="static")

        # Serve index.html at /dashboard and /dashboard/
        @app.get("/dashboard")
        @app.get("/dashboard/")
        async def serve_dashboard():
            return FileResponse(str(dashboard_path / "index.html"))

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
