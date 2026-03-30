# Multi-Agent System - Extended Guide

## Table of Contents

1. [Overview](#overview)
2. [New Features](#new-features)
3. [Architecture](#architecture)
4. [Installation & Setup](#installation--setup)
5. [Configuration](#configuration)
6. [Usage Guide](#usage-guide)
7. [API Reference](#api-reference)
8. [Examples](#examples)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The Extended Multi-Agent System is a production-ready framework for orchestrating AI-powered agents with the following capabilities:

- **Multi-Provider LLM Integration**: Support for OpenAI, Anthropic, Google, and OpenRouter
- **Role-Based Workers**: Define agent roles using markdown files
- **Interactive Dashboard**: Real-time monitoring and user intervention
- **Intelligent Task Decomposition**: LLM-powered task breakdown and analysis
- **Automatic Fallback**: Provider failover and retry logic

---

## New Features

### 1. Multi-Provider LLM System

The system supports multiple LLM providers with automatic fallback:

```python
from llm.manager import LLMManager
from llm.providers import OpenAIProvider, AnthropicProvider

# Create manager
llm_manager = LLMManager(retry_count=3, fallback_enabled=True)

# Register providers
llm_manager.register_provider("openai", OpenAIProvider(...), priority=1)
llm_manager.register_provider("anthropic", AnthropicProvider(...), priority=2)

# Use with automatic fallback
result = await llm_manager.chat(messages)
```

**Features:**
- Plugin architecture for easy provider addition
- Priority-based fallback
- Exponential backoff retry logic
- Usage statistics tracking
- Support for provider-specific parameters

### 2. Role Management System

Define worker roles using markdown files stored in the `roles/` directory:

```markdown
# Role: Coder

## Specialization
Expert software developer specializing in Python...

## Instructions
- Write production-ready code
- Follow PEP 8 guidelines
...

## Constraints
- Must write syntactically correct code
- Cannot use deprecated APIs
...
```

**Programmatic Access:**

```python
from workers.role_manager import RoleManager

role_manager = RoleManager("roles/")

# Create role
role = role_manager.create_role(
    name="DataScientist",
    specialization="Expert in data analysis...",
    instructions="Analyze datasets...",
    constraints="Must validate data quality..."
)

# Load role
role = role_manager.get_role("coder")

# Update role
role_manager.update_role("coder", instructions="Updated instructions...")

# Delete role
role_manager.delete_role("old_role")
```

### 3. Interactive Dashboard

Real-time dashboard with full CRUD capabilities:

```python
from dashboard.interactive_dashboard import InteractiveDashboard

dashboard = InteractiveDashboard(
    event_bus=event_bus,
    state_manager=state_manager,
    role_manager=role_manager,
    system=system
)

# Run interactive menu
await dashboard.show_menu()
```

**Features:**
- Add/view/manage tasks
- Create/edit/delete agents
- Manage roles (CRUD operations)
- Send corrections to agents
- Pause/resume agents
- View real-time statistics
- Monitor file changes
- Track problems and issues

### 4. Enhanced Senior Agent

The SeniorAgent uses LLM for intelligent task management:

```python
from core.senior_agent import SeniorAgent

senior = SeniorAgent(
    agent_id="senior",
    event_bus=event_bus,
    state_manager=state_manager,
    llm_manager=llm_manager
)

# Submit task - automatically decomposed by LLM
task_id = await senior.submit_user_task(
    "Create a web scraper for news articles"
)

# Send correction
await senior.receive_correction(
    worker_id="worker_1",
    correction="Focus on advanced patterns"
)

# Generate report
report = await senior.generate_task_report(task_id)
```

**Capabilities:**
- LLM-powered task decomposition
- Intelligent result analysis
- Gap detection
- User correction processing
- Automatic task reassignment
- Quality scoring

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────┐
│                 User Interface                      │
│           (Interactive Dashboard)                   │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│              Senior Agent                           │
│         (LLM-Powered Manager)                       │
│  ┌──────────────┐  ┌──────────────┐                │
│  │ Task         │  │ Result       │                │
│  │ Decomposer   │  │ Analyzer     │                │
│  └──────────────┘  └──────────────┘                │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│           Worker Agents Pool                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ Worker 1 │  │ Worker 2 │  │ Worker 3 │         │
│  │ (Coder)  │  │(Research)│  │(Reviewer)│         │
│  └──────────┘  └──────────┘  └──────────┘         │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│          Shared Infrastructure                      │
│  ┌──────────────┐  ┌──────────────┐                │
│  │ Event Bus    │  │ State        │                │
│  │              │  │ Manager      │                │
│  └──────────────┘  └──────────────┘                │
│  ┌──────────────┐  ┌──────────────┐                │
│  │ LLM Manager  │  │ Role         │                │
│  │              │  │ Manager      │                │
│  └──────────────┘  └──────────────┘                │
└─────────────────────────────────────────────────────┘
```

### LLM Provider Architecture

```
┌─────────────────────────────────────────────────────┐
│               LLM Manager                           │
│  ┌────────────────────────────────────────────┐    │
│  │ Fallback Logic + Retry Mechanism           │    │
│  └────────────────────────────────────────────┘    │
└──────┬──────────┬──────────┬──────────┬────────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
   ┌──────┐  ┌──────┐  ┌──────┐  ┌────────┐
   │OpenAI│  │Claude│  │Gemini│  │OpenRtr │
   │ GPT-4│  │  3.5 │  │ Pro  │  │Multi   │
   └──────┘  └──────┘  └──────┘  └────────┘
   Priority:   Priority:  Priority:  Priority:
      1          2          3          4
```

### Directory Structure

```
multi_agent_system/
├── llm/                        # LLM system
│   ├── __init__.py
│   ├── base.py                 # Base classes
│   ├── manager.py              # LLMManager
│   └── providers/
│       ├── openai.py
│       ├── anthropic.py
│       ├── google.py
│       └── openrouter.py
├── workers/                    # Role management
│   ├── __init__.py
│   └── role_manager.py
├── roles/                      # Role definitions (markdown)
│   ├── coder.md
│   ├── researcher.md
│   ├── reviewer.md
│   └── architect.md
├── config/                     # Configuration
│   ├── __init__.py
│   └── providers.yaml
├── core/                       # Core agents
│   ├── senior_agent.py         # Enhanced manager
│   ├── worker_agent.py
│   ├── event_bus.py
│   └── state_manager.py
├── dashboard/                  # UI
│   ├── cli_dashboard.py
│   └── interactive_dashboard.py
├── tools/                      # Utilities
│   ├── file_operations.py
│   └── web_tools.py
├── main_extended.py            # Main entry point
├── example_extended.py         # Examples
├── requirements.txt
└── .env.example
```

---

## Installation & Setup

### Prerequisites

- Python 3.10 or higher
- API keys for at least one LLM provider

### Installation Steps

1. **Clone or navigate to the directory:**
   ```bash
   cd /workspace/multi_agent_system
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```

4. **Edit `.env` with your API keys:**
   ```bash
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...
   GOOGLE_API_KEY=AIza...
   OPENROUTER_API_KEY=sk-or-...
   ```

5. **Verify installation:**
   ```bash
   python example_extended.py
   ```

---

## Configuration

### Provider Configuration

Edit `config/providers.yaml` to configure LLM providers:

```yaml
llm:
  providers:
    openai:
      enabled: true
      api_key: "${OPENAI_API_KEY}"
      model: "gpt-4"
      priority: 1
      config:
        base_url: "https://api.openai.com/v1"

    anthropic:
      enabled: true
      api_key: "${ANTHROPIC_API_KEY}"
      model: "claude-3-sonnet-20240229"
      priority: 2

  default_provider: "openai"
  fallback_enabled: true
  retry_count: 3
  default_temperature: 0.7
  max_tokens: 4096
```

**Configuration Options:**

- `enabled`: Enable/disable provider
- `api_key`: API key (supports env variables with `${VAR}`)
- `model`: Model identifier
- `priority`: Lower = higher priority for fallback
- `config`: Provider-specific configuration
- `default_provider`: Primary provider to use
- `fallback_enabled`: Enable automatic fallback
- `retry_count`: Number of retries per provider

### Role Configuration

Roles are defined in markdown files in the `roles/` directory. See [Role Management](#2-role-management-system) for details.

---

## Usage Guide

### Quick Start

**Option 1: Interactive Dashboard**

```bash
python main_extended.py
```

This launches the interactive menu where you can:
- Add tasks
- Manage agents
- Manage roles
- View real-time statistics
- Intervene and correct agents

**Option 2: Programmatic Usage**

```python
import asyncio
from main_extended import MultiAgentSystem

async def main():
    # Create system
    system = MultiAgentSystem()

    # Initialize with 3 workers
    await system.initialize(num_workers=3)

    # Submit task
    task_id = await system.manager.submit_user_task(
        "Create a Python script to analyze CSV data"
    )

    # Wait for completion
    await asyncio.sleep(10)

    # Get report
    report = await system.manager.generate_task_report(task_id)
    print(report)

    # Cleanup
    await system.stop()

asyncio.run(main())
```

### Common Workflows

#### 1. Submit and Monitor Task

```python
# Submit task
task_id = await manager.submit_user_task("Build a REST API")

# Monitor via events
async def on_task_completed(event):
    print(f"Task {event.data['task_id']} completed!")

event_bus.subscribe(EventType.TASK_COMPLETED, on_task_completed)
```

#### 2. Correct an Agent

```python
# Send correction
await manager.receive_correction(
    worker_id="worker_1",
    correction="Please use FastAPI instead of Flask"
)
```

#### 3. Create Custom Role

```python
role = role_manager.create_role(
    name="APIDesigner",
    specialization="Expert in RESTful API design",
    instructions="Design scalable APIs following REST principles",
    constraints="Must follow OpenAPI 3.0 specification"
)
```

#### 4. Check LLM Statistics

```python
stats = llm_manager.get_stats()
for provider, data in stats.items():
    print(f"{provider}: {data['success']} successful, {data['failures']} failed")
```

---

## API Reference

### LLMManager

#### Methods

**`register_provider(name, provider, priority, set_as_default)`**
- Register a new LLM provider
- Parameters:
  - `name` (str): Provider identifier
  - `provider` (LLMProvider): Provider instance
  - `priority` (int): Priority (lower = higher priority)
  - `set_as_default` (bool): Set as default provider

**`async chat(messages, provider, temperature, max_tokens, **kwargs)`**
- Send chat messages with fallback
- Parameters:
  - `messages` (List[LLMMessage]): Conversation messages
  - `provider` (str, optional): Specific provider to use
  - `temperature` (float): Sampling temperature (0.0-1.0)
  - `max_tokens` (int, optional): Max response tokens
- Returns: Dict with `response`, `provider`, `success`

**`async complete(prompt, provider, temperature, max_tokens, **kwargs)`**
- Send completion request
- Parameters: Same as `chat` but takes a string prompt
- Returns: Dict with `response`, `provider`, `success`

**`get_stats()`**
- Get usage statistics for all providers
- Returns: Dict[str, Dict[str, int]]

### RoleManager

#### Methods

**`create_role(name, specialization, instructions, constraints, metadata)`**
- Create a new role
- Returns: Role object

**`load_role(name)`**
- Load role from markdown file
- Returns: Role object or None

**`update_role(name, specialization, instructions, constraints, metadata)`**
- Update existing role
- Returns: Updated Role object or None

**`delete_role(name)`**
- Delete a role
- Returns: bool (success/failure)

**`get_role(name)`**
- Get role by name
- Returns: Role object or None

**`list_roles()`**
- List all available roles
- Returns: List[str]

### SeniorAgent

#### Methods

**`async submit_user_task(description, context)`**
- Submit a task for processing
- Returns: task_id (str)

**`async receive_correction(worker_id, correction)`**
- Receive correction from user
- Analyzes correction and takes appropriate action

**`async generate_task_report(task_id)`**
- Generate detailed task report
- Returns: Markdown-formatted report (str)

### InteractiveDashboard

#### Methods

**`async show_menu()`**
- Display interactive menu
- Blocks until user selects an option

**`async add_task()`**
- Add new task interactively

**`async manage_agents()`**
- Agent management menu (CRUD)

**`async manage_roles()`**
- Role management menu (CRUD)

**`async correct_agent()`**
- Send correction to an agent

**`async view_statistics()`**
- View system statistics

---

## Examples

### Example 1: Automated Research Task

```python
import asyncio
from main_extended import MultiAgentSystem

async def research_task():
    system = MultiAgentSystem()
    await system.initialize(num_workers=3)

    # Start agents
    await system.manager.start()
    for worker in system.workers:
        await worker.start()

    # Submit research task
    task_id = await system.manager.submit_user_task(
        "Research the top 5 Python web frameworks, "
        "compare their features, and create a comparison table"
    )

    print(f"Task submitted: {task_id}")

    # Wait for completion
    await asyncio.sleep(15)

    # Generate report
    report = await system.manager.generate_task_report(task_id)
    print("\n" + "="*60)
    print(report)
    print("="*60)

    await system.stop()

asyncio.run(research_task())
```

### Example 2: Multi-Provider Testing

```python
from llm.manager import LLMManager
from llm.providers import OpenAIProvider, AnthropicProvider
from llm.base import LLMMessage

async def test_providers():
    manager = LLMManager()

    # Register providers
    manager.register_provider(
        "openai",
        OpenAIProvider(api_key="sk-...", model="gpt-4"),
        priority=1
    )
    manager.register_provider(
        "anthropic",
        AnthropicProvider(api_key="sk-ant-...", model="claude-3-sonnet"),
        priority=2
    )

    # Test with fallback
    messages = [LLMMessage(role="user", content="Explain asyncio in 50 words")]

    result = await manager.chat(messages)
    print(f"Provider used: {result['provider']}")
    print(f"Response: {result['response']}")

    # View stats
    print("\nStatistics:")
    for provider, stats in manager.get_stats().items():
        print(f"  {provider}: {stats}")

asyncio.run(test_providers())
```

### Example 3: Role-Based Workflow

```python
from workers.role_manager import RoleManager

# Initialize
role_manager = RoleManager("roles/")

# Create custom role
role = role_manager.create_role(
    name="SecurityAuditor",
    specialization="Cybersecurity expert specializing in code auditing",
    instructions="""
    - Review code for security vulnerabilities
    - Check for SQL injection risks
    - Validate input sanitization
    - Ensure proper authentication
    """,
    constraints="""
    - Must follow OWASP Top 10 guidelines
    - Cannot approve code with critical issues
    - Must provide specific remediation steps
    """
)

print(f"Created role: {role.name}")

# List all roles
roles = role_manager.list_roles()
print(f"Available roles: {roles}")

# Load and use role
security_role = role_manager.get_role("SecurityAuditor")
print(f"\nSpecialization: {security_role.specialization}")
print(f"\nInstructions:\n{security_role.instructions}")
```

---

## Troubleshooting

### Common Issues

**Issue: "No providers registered"**

**Solution:** Ensure at least one provider is configured with a valid API key in `.env`:
```bash
OPENAI_API_KEY=sk-your-key-here
```

**Issue: "All providers failed"**

**Causes:**
- Invalid API keys
- Network connectivity issues
- Rate limiting

**Solutions:**
1. Check API keys in `.env`
2. Verify network connectivity
3. Check provider dashboard for rate limits
4. Review logs for specific errors

**Issue: "Role not found"**

**Solution:** Ensure the role markdown file exists in `roles/` directory:
```bash
ls roles/
# Should show: coder.md, researcher.md, etc.
```

**Issue: "Task decomposition returns generic subtasks"**

**Causes:**
- LLM provider unavailable
- Falling back to simple decomposition

**Solutions:**
1. Check LLM provider status
2. Verify API keys
3. Check logs for LLM errors

### Debug Mode

Enable detailed logging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Check System Health

```python
# Check LLM providers
provider_info = llm_manager.get_provider_info()
print(f"Providers: {provider_info['providers']}")
print(f"Default: {provider_info['default_provider']}")

# Check statistics
stats = await state_manager.get_stats()
print(f"Tasks: {stats['total_tasks']}")
print(f"Completed: {stats['completed']}")
print(f"Failed: {stats['failed']}")

# Check roles
roles = role_manager.list_roles()
print(f"Available roles: {roles}")
```

---

## Advanced Topics

### Custom Provider Integration

To add a new LLM provider:

1. Create provider class:

```python
from llm.base import LLMProvider, LLMMessage

class CustomProvider(LLMProvider):
    async def chat(self, messages, temperature, max_tokens, **kwargs):
        # Implement API call
        pass

    async def complete(self, prompt, temperature, max_tokens, **kwargs):
        # Implement completion
        pass
```

2. Register provider:

```python
custom = CustomProvider(api_key="...", model="...")
llm_manager.register_provider("custom", custom, priority=5)
```

### Custom Event Handlers

Subscribe to specific events:

```python
from core.event_bus import EventType

async def on_problem_detected(event):
    problem = event.data
    print(f"ALERT: {problem['description']}")
    # Send notification, log, etc.

event_bus.subscribe(EventType.PROBLEM_DETECTED, on_problem_detected)
```

### Performance Tuning

**Adjust worker pool size:**
```python
await system.initialize(num_workers=5)  # More workers = more parallelism
```

**Optimize LLM settings:**
```yaml
llm:
  retry_count: 2          # Faster failure
  default_temperature: 0.3  # More deterministic
  max_tokens: 2000        # Faster responses
```

**Enable caching (future feature):**
```python
# TODO: Implement result caching
```

---

## Contributing

To extend the system:

1. Add new providers in `llm/providers/`
2. Create roles in `roles/` directory
3. Extend dashboard in `dashboard/interactive_dashboard.py`
4. Add examples in `example_extended.py`

---

## License

See LICENSE file for details.

---

## Support

For issues and questions:
- Check logs for detailed error messages
- Review examples in `example_extended.py`
- Consult API reference above

---

**System Version:** 2.0 Extended
**Last Updated:** 2026-03-18
