![Senado de Praxis](https://i.postimg.cc/9MPcZn6S/PRAXIS-SENATE.png)

# PRAXIS SENATE — Multi-Agent Orchestration System

An autonomous multi-agent system with LLM-powered task decomposition, real-time web dashboard, human-in-the-loop controls, and experiment tracking. Built for long-running, loop-based autonomous operation.

## Quick Start

```bash
cd multi_agent_system

# Install dependencies
pip install -r requirements.txt

# Configure LLM providers
cp .env.example .env   # Add your API keys

# Run with web dashboard (default: Docker-isolated execution)
python main_extended.py

# Run in direct mode on an existing project
python main_extended.py --mode direct --workspace /path/to/project
```

The web dashboard opens at `http://localhost:8000`. Use the API or dashboard to submit tasks.

## Architecture

```
SeniorAgent (LLM-powered decomposition + analysis)
  ├── CriticAgent (optional review gate)
  ├── WorkerAgent 1 (file ops, web, commands)
  ├── WorkerAgent 2
  └── WorkerAgent N
      │
      └── DockerAgentExecutor (isolated) or Direct Mode (host FS)

EventBus (async pub/sub with backpressure)
StateManager (SQLite WAL + in-memory, periodic cleanup)
ExperimentTracker (TSV + JSONL result logging)
```

## Execution Modes

| Mode | Flag | Isolation | Use Case |
|------|------|-----------|----------|
| Docker | `--mode docker` (default) | Full container isolation | Untrusted tasks, experimentation |
| Direct | `--mode direct --workspace PATH` | None (host filesystem) | Working on your own projects |

## Key Features

- **LLM-powered task decomposition** — SeniorAgent breaks tasks into subtasks using configurable LLM providers (OpenAI, Anthropic, Google, MiniMax, OpenRouter)
- **Human-in-the-loop** — Halt tasks, inject feedback, resume. Workers incorporate HITL feedback into LLM prompts
- **CriticAgent** — Optional blocking review that can reject and force re-decomposition
- **Real-time dashboard** — Web UI with SSE events, drag-and-drop, live stats
- **Experiment tracking** — Autoresearch-inspired TSV/JSONL logging of task outcomes (keep/discard/crash)
- **Circuit breaker** — Workers back off exponentially on repeated failures
- **Memory management** — Periodic cleanup of completed tasks, bounded queues, capped correction history

## API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/tasks` | POST | Submit a task |
| `/api/tasks` | GET | List tasks (filter by status/agent) |
| `/api/tasks/{id}` | GET | Task details |
| `/api/tasks/{id}/halt` | POST | Halt a running task |
| `/api/tasks/{id}/feedback` | POST | Inject human feedback |
| `/api/tasks/{id}/resume` | POST | Resume halted task |
| `/api/tasks/experiments/results` | GET | Experiment tracking data |
| `/api/events/stream` | GET | SSE event stream |
| `/api/agents` | GET | Agent status |

## CLI Options

```
python main_extended.py [OPTIONS]

  --mode {docker,direct}   Execution mode (default: docker)
  --workspace PATH         Project path for direct mode
  --workers N              Number of worker agents (default: 3)
  --config PATH            Custom config YAML path
```

## Configuration

Environment variables (`.env`):
```
MINIMAX_API_KEY=your_key
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
```

See `config/providers.yaml` for full provider, critic, and execution configuration.

## Project Structure

```
multi_agent_system/
  ├── main_extended.py         # CLI entry point
  ├── api/                     # FastAPI server + routes
  ├── core/                    # EventBus, StateManager, Agents, ExperimentTracker
  ├── llm/                     # Multi-provider LLM manager
  ├── roles/                   # Agent role definitions (.md prompts)
  ├── tools/                   # File operations, web tools
  ├── docker/                  # Docker executor + compose
  ├── dashboard/               # Web + CLI dashboards
  └── data/                    # SQLite DB, experiment logs
docs/
  ├── usage-guide.md           # Comprehensive how-to guide
  ├── architecture.md          # System architecture
  ├── diagrams.md              # Architecture diagrams
  ├── quickstart.md            # Quick start guide
  └── ...                      # Extended docs, QA reports
```

## Documentation

- **[Usage Guide](docs/usage-guide.md)** — Full setup, configuration, and usage instructions
- **[Architecture](docs/architecture.md)** — System design and component interactions
- **[Quick Start](docs/quickstart.md)** — Get running in minutes
- **[Extended Guide](docs/extended-guide.md)** — Deep dive into features
- **[Audit Report](docs/audit-report.md)** — Security and quality audit findings

## License

© 2026 PRAXIS SENATE
