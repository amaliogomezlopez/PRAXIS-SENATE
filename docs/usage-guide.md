# PRAXIS-SENATE Usage Guide

Complete guide to running and using the PRAXIS-SENATE multi-agent orchestration system.

---

## Prerequisites

- Python 3.10+
- Docker (optional, for isolated task execution)
- An LLM API key (MiniMax, OpenAI, Anthropic, Google, or OpenRouter)

## Installation

```bash
cd multi_agent_system
pip install -r requirements.txt
```

## Configuration

### 1. Set up environment variables

Copy the example and fill in your API keys:

```bash
cp multi_agent_system/.env.example multi_agent_system/.env
```

Edit `.env`:

```env
MINIMAX_API_KEY=your-key-here
MINIMAX_BASE_URL=https://api.minimax.chat/v1
LLM_MODEL=MiniMax-Text-01
```

### 2. Provider configuration

Edit `multi_agent_system/config/providers.yaml` to enable/disable LLM providers and set priorities. The system supports automatic fallback between providers.

---

## Running the System

### Option A: Web Dashboard (recommended)

Start the FastAPI server with the web dashboard:

```bash
cd multi_agent_system
uvicorn api.server:create_app --factory --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000/dashboard` in your browser.

The dashboard provides:
- **Kanban board** — drag-and-drop task management across columns (Pending → In Progress → Completed / Failed / Halted)
- **Task inspector** — click any task card to see subtasks, commands, results, and agent reasoning
- **Retry failed tasks** — one-click retry from the task inspector
- **Live elapsed timers** — real-time duration on in-progress tasks
- **Global stats bar** — total tasks, success rate, average duration
- **Search & filter** — find tasks by description
- **Desktop notifications** — get notified when tasks complete or fail
- **LLM transparency panels** — see agent thinking, prompts, and responses in real time
- **Role editor** — create and edit agent role definitions
- **Human-in-the-Loop** — halt tasks, provide feedback, and resume

### Option B: CLI Interactive Dashboard

```bash
cd multi_agent_system
python main_extended.py
```

This launches the Rich-based interactive CLI with a 10-option menu:
1. Submit new task
2. View task status
3. List all tasks
4. Manage roles
5. View system stats
6. Send feedback to agent
7. View event log
8. Halt a task
9. Resume a task
10. Exit

### Option C: Programmatic Usage

```python
import asyncio
from multi_agent_system.main_extended import MultiAgentSystem

async def main():
    system = MultiAgentSystem()
    await system.initialize(num_workers=3)
    await system.start()

asyncio.run(main())
```

### Option D: Direct Mode (Existing Project)

Run the agent system directly on a local project folder without Docker isolation:

```bash
cd multi_agent_system
python main_extended.py --workspace /path/to/your/project --mode direct
```

This skips Docker container isolation and executes commands directly in the target folder. Use `--mode docker` (default) for isolated execution.

**Warning**: Direct mode executes commands without sandbox isolation. Only use on trusted tasks.

---

## Execution Modes

| Mode | Flag | Description |
|------|------|-------------|
| **Docker** (default) | `--mode docker` | Commands run in isolated Docker containers with resource limits |
| **Direct** | `--mode direct` | Commands run directly on the host filesystem at the specified workspace |

### When to use each mode

- **Docker mode**: Running untrusted tasks, CI/CD pipelines, automated research where safety matters
- **Direct mode**: Working on your own projects, debugging, development workflows where you trust the agent

---

## Task Lifecycle

```
PENDING → IN_PROGRESS → COMPLETED
                      → FAILED (retryable)
                      → HALTED (by human, resumable)
```

1. **Submit** — user creates a task via dashboard, CLI, or API
2. **Decompose** — SeniorAgent uses LLM to break the task into subtasks
3. **Critique** (optional) — CriticAgent reviews the decomposition for risks/gaps
4. **Execute** — WorkerAgents execute subtasks (file ops, web requests, commands)
5. **Analyze** — SeniorAgent reviews results and detects quality gaps
6. **Complete** — parent task completes when all subtasks finish

---

## API Reference

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/tasks` | Create a new task |
| `GET` | `/api/tasks` | List all tasks |
| `GET` | `/api/tasks/{id}` | Get task details |
| `PATCH` | `/api/tasks/{id}` | Update task (status, etc.) |
| `DELETE` | `/api/tasks/{id}` | Delete a task |
| `POST` | `/api/tasks/{id}/halt` | Halt a running task |
| `POST` | `/api/tasks/{id}/resume` | Resume a halted task |
| `POST` | `/api/tasks/{id}/feedback` | Send human feedback to task |
| `POST` | `/api/tasks/{id}/retry` | Retry a failed task |

### Agents & Events

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/agents` | List active agents and status |
| `GET` | `/api/events/stream` | SSE event stream |
| `WS` | `/api/events/ws` | WebSocket event stream |
| `GET` | `/api/critiques` | List critique results |
| `GET` | `/api/roles` | List available roles |
| `POST` | `/api/roles` | Create a new role |

---

## Human-in-the-Loop (HITL)

The system supports real-time human intervention:

### Halt a task
```bash
curl -X POST http://localhost:8000/api/tasks/{task_id}/halt
```

### Send feedback
```bash
curl -X POST http://localhost:8000/api/tasks/{task_id}/feedback \
  -H "Content-Type: application/json" \
  -d '{"feedback": "Also handle edge case X"}'
```

### Resume
```bash
curl -X POST http://localhost:8000/api/tasks/{task_id}/resume
```

Feedback is injected as `[HUMAN FEEDBACK]: ...` into the next LLM call for the worker, ensuring the agent adapts its behavior based on your input.

---

## Agent Roles

Roles are defined as Markdown files in `multi_agent_system/roles/`. Each role provides:
- System prompt context for the LLM
- Behavioral guidelines
- Tool access permissions
- Quality criteria

Built-in roles: `architect`, `coder`, `researcher`, `reviewer`, `critic`

### Creating a custom role

Create a new `.md` file in `roles/`:

```markdown
# Data Analyst

You are a data analyst agent. Your responsibilities:
- Analyze datasets and extract insights
- Generate statistical summaries
- Create data visualizations
- Validate data quality

## Guidelines
- Always validate data before analysis
- Provide confidence intervals where applicable
- Flag any data quality issues immediately
```

---

## Troubleshooting

### System won't start
- Check that `.env` has valid API keys
- Verify provider is `enabled: true` in `providers.yaml`
- Check logs: `tail -f multi_agent_system/data/*.log`

### Tasks stuck in PENDING
- Ensure workers are running (check `/api/agents`)
- Check LLM provider connectivity
- Review SeniorAgent logs for decomposition failures

### Docker issues
- Run without Docker: `--mode direct`
- Verify Docker is running: `docker info`
- Check image exists: `docker images praxix-senate-agent`

### LLM errors
- Verify API key is valid and has credit
- Check rate limits
- Enable fallback: set `fallback_enabled: true` in `providers.yaml`

---

## Further Reading

- [Architecture](architecture.md) — system design and agent execution model
- [Diagrams](diagrams.md) — visual architecture diagrams
- [Features](features.md) — detailed feature documentation
- [Quick Start](quickstart.md) — 5-minute setup guide
- [QA Report](qa-report.md) — quality audit and test results
- [Audit Report](audit-report.md) — comprehensive security and UX audit
