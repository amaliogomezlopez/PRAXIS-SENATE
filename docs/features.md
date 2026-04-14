# Multi-Agent System - Extended Edition

> **Production-ready multi-agent orchestration system with LLM integration, role management, and interactive control**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

### ✨ Core Capabilities

- 🤖 **Multi-Provider LLM Integration** - Support for OpenAI, Anthropic, Google AI, and OpenRouter
- 🎭 **Role-Based Workers** - Define specialized agents using markdown files
- 📊 **Interactive Dashboard** - Real-time monitoring and intervention
- 🧠 **Intelligent Task Decomposition** - LLM-powered task breakdown
- 🔄 **Automatic Fallback** - Provider failover with retry logic
- 📝 **User Corrections** - Real-time feedback and task redirection
- 📈 **Real-Time Analytics** - Track performance and usage statistics

### 🆕 What's New in Extended Edition

1. **LLM System** - Plugin architecture supporting multiple AI providers
2. **Role Manager** - CRUD operations for agent roles via markdown files
3. **Senior Agent** - Enhanced manager with LLM-powered analysis
4. **Interactive Dashboard** - Full control loop with user intervention
5. **Configuration System** - YAML-based provider configuration
6. **Advanced Examples** - Production-ready usage patterns

## Quick Start

### Installation

```bash
# Navigate to directory
cd /workspace/multi_agent_system

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your API keys
```

### Basic Usage

```python
import asyncio
from main_extended import MultiAgentSystem

async def main():
    # Create and initialize system
    system = MultiAgentSystem()
    await system.initialize(num_workers=3)

    # Submit a task
    task_id = await system.manager.submit_user_task(
        "Create a Python web scraper for news articles"
    )

    # Wait for completion
    await asyncio.sleep(10)

    # Get detailed report
    report = await system.manager.generate_task_report(task_id)
    print(report)

    await system.stop()

asyncio.run(main())
```

### Interactive Mode

```bash
# Run interactive dashboard
python main_extended.py

# Or run examples
python example_extended.py
```

## Architecture

```
┌─────────────────────────────────────┐
│     Interactive Dashboard           │
│  (User Control & Monitoring)        │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│       Senior Agent                  │
│  (LLM-Powered Orchestration)        │
│  • Task Decomposition               │
│  • Result Analysis                  │
│  • Gap Detection                    │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│      Worker Pool                    │
│  [Coder] [Researcher] [Reviewer]    │
│  (Role-Based Specialization)        │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│   Infrastructure Layer              │
│  • LLM Manager (Multi-Provider)     │
│  • Event Bus (Communication)        │
│  • State Manager (Persistence)      │
│  • Role Manager (Configurations)    │
└─────────────────────────────────────┘
```

## Configuration

### LLM Providers

Edit `config/providers.yaml`:

```yaml
llm:
  providers:
    openai:
      enabled: true
      api_key: "${OPENAI_API_KEY}"
      model: "gpt-4"
      priority: 1

    anthropic:
      enabled: true
      api_key: "${ANTHROPIC_API_KEY}"
      model: "claude-3-sonnet-20240229"
      priority: 2

  default_provider: "openai"
  fallback_enabled: true
  retry_count: 3
```

### Agent Roles

Create role files in `roles/` directory:

```markdown
# Role: Coder

## Specialization
Expert software developer...

## Instructions
- Write production-ready code
- Follow best practices
...

## Constraints
- Must handle errors
- Cannot use deprecated APIs
...
```

## Examples

### Example 1: Automated Task Processing

```python
from main_extended import MultiAgentSystem

async def process_task():
    system = MultiAgentSystem()
    await system.initialize(num_workers=3)

    # Submit complex task
    task_id = await system.manager.submit_user_task(
        "Research Python async patterns and create a tutorial"
    )

    # System automatically:
    # 1. Decomposes task using LLM
    # 2. Assigns subtasks to workers
    # 3. Analyzes results
    # 4. Detects gaps
    # 5. Generates report

    await asyncio.sleep(15)
    report = await system.manager.generate_task_report(task_id)
    print(report)
```

### Example 2: User Intervention

```python
# Submit task
task_id = await system.manager.submit_user_task("Build a REST API")

# Monitor progress
await asyncio.sleep(5)

# Send correction
await system.manager.receive_correction(
    worker_id="worker_1",
    correction="Use FastAPI instead of Flask"
)

# System analyzes correction and adapts
```

### Example 3: Multi-Provider Fallback

```python
from llm.base import LLMMessage

# System tries providers in priority order
messages = [LLMMessage(role="user", content="Explain asyncio")]

# Automatically falls back if primary fails
result = await system.llm_manager.chat(messages)

print(f"Provider used: {result['provider']}")
print(f"Response: {result['response']}")
```

## API Reference

### Core Classes

- **`MultiAgentSystem`** - Main system orchestrator
- **`SeniorAgent`** - Enhanced manager with LLM integration
- **`WorkerAgent`** - Task executor with role specialization
- **`LLMManager`** - Multi-provider LLM orchestration
- **`RoleManager`** - Role definition management
- **`InteractiveDashboard`** - User interface and control

### Key Methods

```python
# System initialization
await system.initialize(num_workers=3)

# Task submission
task_id = await manager.submit_user_task(description)

# User correction
await manager.receive_correction(worker_id, correction)

# Report generation
report = await manager.generate_task_report(task_id)

# Role management
role = role_manager.create_role(name, specialization, instructions, constraints)
role = role_manager.get_role(name)
role_manager.update_role(name, ...)
role_manager.delete_role(name)

# LLM interaction
result = await llm_manager.chat(messages, provider=None, temperature=0.7)
stats = llm_manager.get_stats()
```

## Project Structure

```
multi_agent_system/
├── llm/                    # LLM integration
│   ├── base.py             # Base classes
│   ├── manager.py          # Multi-provider manager
│   └── providers/          # Provider implementations
│       ├── openai.py
│       ├── anthropic.py
│       ├── google.py
│       └── openrouter.py
├── workers/                # Role management
│   └── role_manager.py
├── roles/                  # Role definitions (.md)
│   ├── coder.md
│   ├── researcher.md
│   ├── reviewer.md
│   └── architect.md
├── config/                 # Configuration
│   ├── __init__.py
│   └── providers.yaml
├── core/                   # Core agents
│   ├── senior_agent.py     # Enhanced manager
│   ├── worker_agent.py
│   ├── event_bus.py
│   └── state_manager.py
├── dashboard/              # User interfaces
│   ├── cli_dashboard.py
│   └── interactive_dashboard.py
├── tools/                  # Utilities
│   ├── file_operations.py
│   └── web_tools.py
├── main_extended.py        # Entry point
├── example_extended.py     # Examples
└── requirements.txt
```

## Use Cases

### Software Development

```python
task = "Create a Python package for data validation with tests and docs"
# System decomposes into:
# 1. Design package architecture
# 2. Implement core validation logic
# 3. Write unit tests
# 4. Generate documentation
# 5. Review code quality
```

### Research & Analysis

```python
task = "Research top 5 machine learning frameworks and compare features"
# System executes:
# 1. Search for framework information
# 2. Extract key features
# 3. Create comparison matrix
# 4. Analyze pros/cons
# 5. Generate recommendation
```

### Content Generation

```python
task = "Write a technical blog post about asyncio with code examples"
# System produces:
# 1. Outline and structure
# 2. Code examples
# 3. Explanations
# 4. Review for accuracy
# 5. Format for publication
```

## Requirements

- Python 3.10+
- API key for at least one LLM provider
- Dependencies: `rich`, `aiohttp`, `pyyaml`, `pydantic`

## Documentation

- **[Extended Guide](EXTENDED_GUIDE.md)** - Complete documentation
- **[Architecture](ARCHITECTURE.md)** - System design
- **[Quick Start](QUICKSTART.md)** - Getting started guide
- **[Examples](example_extended.py)** - Code examples

## Troubleshooting

**No providers registered:**
```bash
# Ensure API keys are set in .env
OPENAI_API_KEY=sk-your-key-here
```

**Task decomposition fails:**
```python
# Check LLM provider status
provider_info = llm_manager.get_provider_info()
print(provider_info['providers'])
```

**Role not found:**
```bash
# Verify role file exists
ls roles/
# Should show .md files
```

## Performance

- **Concurrent Execution:** Workers process subtasks in parallel
- **Smart Fallback:** Automatic provider switching on failure
- **Retry Logic:** Exponential backoff for transient errors
- **Event-Driven:** Asynchronous communication for efficiency

## Roadmap

- [ ] Result caching for repeated queries
- [ ] Worker load balancing
- [ ] Persistent task queue
- [ ] Web-based dashboard
- [ ] Metrics and monitoring
- [ ] Plugin system for custom tools
- [ ] Distributed worker support

## Contributing

Contributions welcome! Areas for improvement:

1. Additional LLM providers
2. New role templates
3. Enhanced dashboard features
4. Performance optimizations
5. Documentation improvements

## License

MIT License - see LICENSE file for details.

## Support

For issues, questions, or contributions:

1. Check [Extended Guide](EXTENDED_GUIDE.md)
2. Review [examples](example_extended.py)
3. Enable debug logging
4. Check LLM provider status

---

**Version:** 2.0 Extended
**Status:** Production Ready
**Last Updated:** 2026-03-18
