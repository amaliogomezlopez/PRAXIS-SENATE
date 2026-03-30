"""
System Verification Script
Run this to verify that all components are working correctly
"""
import asyncio
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def verify_imports():
    """Verify all imports work"""
    logger.info("Verifying imports...")

    try:
        # Core imports
        from core.event_bus import EventBus
        from core.state_manager import StateManager
        from core.worker_agent import WorkerAgent
        from core.senior_agent import SeniorAgent

        # LLM imports
        from llm.manager import LLMManager
        from llm.base import LLMProvider, LLMMessage
        from llm.providers import OpenAIProvider, AnthropicProvider, GoogleProvider, OpenRouterProvider

        # Workers imports
        from workers.role_manager import RoleManager, Role

        # Dashboard imports
        from dashboard.cli_dashboard import CLIDashboard
        from dashboard.interactive_dashboard import InteractiveDashboard

        # Config imports
        from config import load_config

        # Main imports
        from main_extended import MultiAgentSystem

        logger.info("✓ All imports successful")
        return True

    except Exception as e:
        logger.error(f"✗ Import failed: {e}")
        return False


async def verify_configuration():
    """Verify configuration system"""
    logger.info("\nVerifying configuration...")

    try:
        from config import load_config

        config = load_config()
        assert "llm" in config, "LLM config missing"
        assert "providers" in config["llm"], "Providers config missing"

        logger.info("✓ Configuration loaded successfully")
        logger.info(f"  Configured providers: {list(config['llm']['providers'].keys())}")
        return True

    except Exception as e:
        logger.error(f"✗ Configuration verification failed: {e}")
        return False


async def verify_roles():
    """Verify role management system"""
    logger.info("\nVerifying role system...")

    try:
        from workers.role_manager import RoleManager

        # Check roles directory
        roles_dir = Path(__file__).parent / "roles"
        if not roles_dir.exists():
            logger.error("✗ Roles directory not found")
            return False

        # Initialize manager
        role_manager = RoleManager(str(roles_dir))

        # List roles
        roles = role_manager.list_roles()
        logger.info(f"✓ Found {len(roles)} roles: {roles}")

        # Test loading a role
        if roles:
            role = role_manager.get_role(roles[0])
            if role:
                logger.info(f"✓ Successfully loaded role: {role.name}")
                logger.info(f"  Specialization: {role.specialization[:50]}...")
            else:
                logger.error(f"✗ Failed to load role: {roles[0]}")
                return False

        return True

    except Exception as e:
        logger.error(f"✗ Role verification failed: {e}")
        return False


async def verify_llm_manager():
    """Verify LLM manager (without API calls)"""
    logger.info("\nVerifying LLM manager...")

    try:
        from llm.manager import LLMManager
        from llm.providers import OpenAIProvider

        manager = LLMManager(retry_count=1, fallback_enabled=True)

        # Test registration (with dummy API key)
        dummy_provider = OpenAIProvider(api_key="test", model="gpt-4")
        manager.register_provider("test", dummy_provider, priority=1)

        info = manager.get_provider_info()
        assert "test" in info["providers"], "Provider not registered"

        logger.info("✓ LLM manager working correctly")
        logger.info(f"  Registered providers: {info['providers']}")
        logger.info(f"  Default provider: {info['default_provider']}")

        return True

    except Exception as e:
        logger.error(f"✗ LLM manager verification failed: {e}")
        return False


async def verify_agents():
    """Verify agent system"""
    logger.info("\nVerifying agent system...")

    try:
        from core.event_bus import EventBus
        from core.state_manager import StateManager
        from core.senior_agent import SeniorAgent
        from llm.manager import LLMManager

        # Create components
        event_bus = EventBus()
        state_manager = StateManager()
        llm_manager = LLMManager()

        # Create senior agent
        senior = SeniorAgent(
            agent_id="test_senior",
            event_bus=event_bus,
            state_manager=state_manager,
            llm_manager=llm_manager
        )

        logger.info("✓ Agent creation successful")
        logger.info(f"  Agent ID: {senior.agent_id}")

        return True

    except Exception as e:
        logger.error(f"✗ Agent verification failed: {e}")
        return False


async def verify_system_integration():
    """Verify full system integration"""
    logger.info("\nVerifying system integration...")

    try:
        from main_extended import MultiAgentSystem

        # Create system (don't start it)
        system = MultiAgentSystem()

        logger.info("✓ System instantiation successful")
        logger.info(f"  Event bus: {system.event_bus is not None}")
        logger.info(f"  State manager: {system.state_manager is not None}")
        logger.info(f"  LLM manager: {system.llm_manager is not None}")
        logger.info(f"  Role manager: {system.role_manager is not None}")

        # Check provider info
        provider_info = system.llm_manager.get_provider_info()
        logger.info(f"  Available providers: {provider_info['providers']}")

        return True

    except Exception as e:
        logger.error(f"✗ System integration verification failed: {e}")
        return False


async def verify_environment():
    """Verify environment setup"""
    logger.info("\nVerifying environment...")

    checks = []

    # Check Python version
    import sys
    version = sys.version_info
    python_ok = version.major == 3 and version.minor >= 10
    checks.append(("Python 3.10+", python_ok))
    if python_ok:
        logger.info(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
    else:
        logger.error(f"✗ Python version too old: {version.major}.{version.minor}")

    # Check required directories
    required_dirs = ["llm", "workers", "roles", "config", "core", "dashboard", "tools"]
    base_dir = Path(__file__).parent

    for dir_name in required_dirs:
        dir_path = base_dir / dir_name
        exists = dir_path.exists()
        checks.append((f"Directory: {dir_name}", exists))
        if exists:
            logger.info(f"✓ Directory found: {dir_name}")
        else:
            logger.error(f"✗ Directory missing: {dir_name}")

    # Check configuration file
    config_file = base_dir / "config" / "providers.yaml"
    config_exists = config_file.exists()
    checks.append(("Config file", config_exists))
    if config_exists:
        logger.info(f"✓ Configuration file found")
    else:
        logger.error(f"✗ Configuration file missing")

    # Check role files
    roles_dir = base_dir / "roles"
    if roles_dir.exists():
        role_files = list(roles_dir.glob("*.md"))
        checks.append(("Role files", len(role_files) > 0))
        if role_files:
            logger.info(f"✓ Found {len(role_files)} role files")
        else:
            logger.warning("⚠ No role files found")

    all_passed = all(passed for _, passed in checks)
    return all_passed


async def main():
    """Run all verification checks"""
    logger.info("="*60)
    logger.info("Multi-Agent System - Verification Script")
    logger.info("="*60)

    results = {}

    # Run all checks
    results["Environment"] = await verify_environment()
    results["Imports"] = await verify_imports()
    results["Configuration"] = await verify_configuration()
    results["Roles"] = await verify_roles()
    results["LLM Manager"] = await verify_llm_manager()
    results["Agents"] = await verify_agents()
    results["System Integration"] = await verify_system_integration()

    # Summary
    logger.info("\n" + "="*60)
    logger.info("Verification Summary")
    logger.info("="*60)

    all_passed = True
    for check, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{check:.<40} {status}")
        if not passed:
            all_passed = False

    logger.info("="*60)

    if all_passed:
        logger.info("\n🎉 All checks passed! System is ready to use.")
        logger.info("\nNext steps:")
        logger.info("1. Configure API keys in .env file")
        logger.info("2. Run: python main_extended.py")
        logger.info("3. Or run examples: python example_extended.py")
    else:
        logger.error("\n⚠️  Some checks failed. Please review errors above.")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
