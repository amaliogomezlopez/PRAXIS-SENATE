# PRAXIS-SENATE

> **Autonomous Multi-Agent Orchestration with Human-in-the-Loop Intelligence**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Stars](https://img.shields.io/github/stars/amaliogomezlopez/PRAXIS-SENATE?style=social)](https://github.com/amaliogomezlopez/PRAXIS-SENATE)

---

## 🎯 What is PRAXIS-SENATE?

PRAXIS-SENATE is a **production-ready multi-agent orchestration system** that combines the power of autonomous AI agents with human oversight. It's designed for developers and teams who want to automate complex workflows while keeping humans in control.

### The Problem We Solve

Building AI agents that work autonomously is hard. They can:
- Make mistakes that compound over time
- veer off into unintended directions
- Lack context about your specific domain or business rules
- Produce code that doesn't match your coding standards

**Traditional solutions** either give agents full autonomy (risky) or require constant manual intervention (tedious).

**PRAXIS-SENATE** solves this by treating humans as **active participants** — not just overseers. You can observe, guide, and redirect agents in real-time through a professional dashboard while they work.

---

## 💡 What Can You Use It For?

| Use Case | Description |
|----------|-------------|
| **Automated Code Generation** | Ask agents to write, test, and debug code in isolated containers |
| **Research & Data Analysis** | Agents can browse web, extract data, and generate reports |
| **Complex Task Automation** | Break down multi-step workflows into executable subtasks |
| **Code Review & Refactoring** | CriticAgent reviews code quality before execution |
| **Educational Prototyping** | Test AI agent behaviors in a safe, observable environment |
| **Custom AI Pipelines** | Build domain-specific workflows with multiple specialized agents |

---

## ✨ Key Features

### 🤖 Multi-Agent Architecture
- **SeniorAgent** — Breaks down complex tasks into subtasks
- **CriticAgent** — Reviews and validates plans before execution
- **WorkerAgents** — Execute tasks in parallel with LLM-powered intelligence

### 🔒 Secure Execution
- All code runs inside **ephemeral Docker containers**
- `auto_remove=True` prevents orphan containers
- **30-second timeout** prevents infinite loops
- Resource limits: 256MB memory, 0.5 CPU
- Read-only filesystem with explicit workspace mounts

### 👤 Human-in-the-Loop (HITL)
- **Halt** any task mid-execution
- **Send feedback** directly to running agents
- **Resume** tasks after providing guidance
- Agents receive your feedback before their next LLM call

### 📊 Professional Dashboard
- Kanban-style task board (Pending → In Progress → Completed/Failed/Halted)
- **Live LLM stream logs** — see exactly what the AI is thinking
- **Activity log** with color-coded events
- **Task Inspector** for detailed task analysis
- Real-time updates via WebSocket/SSE

### 📁 Shared Workspace
- Files created by agents appear in your local `agent_workspace/` folder
- Monitor generated code live in VS Code
- Execution remains safely isolated in Docker containers

### 🛡️ Resilient JSON Parsing
- Multiple fallback strategies for LLM responses
- Handles markdown blocks, extra text, and malformed JSON
- Graceful error handling throughout

---

## 🏗️ Architecture

```mermaid
flowchart TB
    subgraph Frontend["🌐 Dashboard"]
        UI["React-inspired SPA"]
    end

    subgraph Backend["⚙️ FastAPI Server"]
        API["REST API :8000"]
        WS["WebSocket / SSE"]
        Static["Static Files"]
    end

    subgraph Core["🧠 Core System"]
        EB["EventBus (Pub/Sub)"]
        SM["StateManager (SQLite)"]
    end

    subgraph Agents["🤖 Agent Pool"]
        SA["SeniorAgent"]
        CA["CriticAgent"]
        WA["WorkerAgent × N"]
    end

    subgraph Execution["🐳 Docker"]
        EX["Agent Executor"]
        CT["Container (isolated)"]
    end

    subgraph LLM["🤖 LLM Providers"]
        OAI["OpenAI"]
        ANT["Anthropic"]
        GEM["Google Gemini"]
    end

    UI <-->|HTTP/WS| API
    API <-->|Events| WS
    Static -->|Serves| UI
    API --> EB --> SM
    SA --> EB
    CA --> EB
    WA --> EB
    SA <-->|LLM| OAI
    CA <-->|LLM| ANT
    WA --> EX --> CT
    CT -->|mount| WSPC[/"agent_workspace/"]

    style Frontend fill:#1a1a2e,color:#fff
    style Backend fill:#16213e,color:#fff
    style Core fill:#0f3460,color:#fff
    style Agents fill:#533483,color:#fff
    style Execution fill:#e94560,color:#fff
    style LLM fill:#4ecca3,color:#1a1a2e
```

---

## 🔄 Execution Flow

```
┌──────────────────────────────────────────────────────────────┐
│                   TASK LIFECYCLE                              │
└──────────────────────────────────────────────────────────────┘

  ┌─────────┐    ┌─────────┐    ┌─────────────┐    ┌───────────┐
  │  NEW    │───▶│ PENDING │───▶│ IN_PROGRESS │───▶│ COMPLETED │
  └─────────┘    └─────────┘    └──────┬──────┘   └───────────┘
       │             │                  │              ▲
       │             │                  ▼              │
       │             │           ┌───────────┐        │
       │             │           │  HALTED   │◀───────┤ (human feedback)
       │             │           └─────┬─────┘        │
       │             │                 │              │
       │             │          (you intervene)        │
       │             ▼                 ▼              │
       │        ┌─────────┐      ┌───────────┐        │
       └───────▶│ FAILED  │      │  RESUMED  │────────┘
                └─────────┘      └───────────┘
```

| Step | What Happens |
|------|-------------|
| **1** | You submit a task via dashboard |
| **2** | SeniorAgent decomposes into subtasks |
| **3** | CriticAgent reviews quality |
| **4** | Workers execute in Docker containers |
| **5** | You monitor live LLM streams |
| **6** | If errors occur → task HALTS |
| **7** | You inspect and send feedback |
| **8** | Worker resumes with your guidance |

---

## 🚀 Quick Start

### Prerequisites

```bash
# Check Python
python --version   # Should be 3.10+

# Check Docker
docker --version   # Should be 20.10+

# Check pip
pip --version
```

### 1. Clone & Install

```bash
git clone https://github.com/amaliogomezlopez/PRAXIS-SENATE.git
cd PRAXIS-SENATE/multi_agent_system
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys
# You need at least ONE of:
# - OPENAI_API_KEY
# - ANTHROPIC_API_KEY
# - GOOGLE_API_KEY
# - OPENROUTER_API_KEY
# - MINIMAX_API_KEY
```

### 3. Start the Server

**Development (direct):**
```bash
python -m api.server
```

**Production (Docker):**
```bash
cd docker
docker-compose up -d
```

### 4. Open the Dashboard

```
http://localhost:8000/dashboard
```

### 5. Create Your First Task

1. Click **"+ New Task"**
2. Enter a prompt like:
   > "Create a file called `hello.py` in `/workspace/agent_workspace` that prints 'Hello from PRAXIS-SENATE!' and then run it"
3. Watch the task execute in the Kanban board
4. Check `agent_workspace/hello.py` in your project folder

---

## 📖 Usage Guide

### Creating Tasks

Submit complex tasks and watch agents decompose and execute them:

```
"Write a Python script that fetches data from an API, processes it,
and saves the results to a CSV file"
```

### Monitoring

- **Task Board** — Kanban columns show task status at a glance
- **LLM Streams** — Real-time view of agent thinking
- **Activity Log** — Every event timestamped and color-coded
- **Task Inspector** — Click any task for full details

### Human Intervention

1. Click a task card → Task Inspector opens
2. Type feedback in the text area
3. Click **"Send & Resume"**
4. Worker receives your guidance before its next action

### Halting Tasks

1. Click **"Halt"** on any running task
2. Task moves to Halted column
3. Investigate, then send feedback and resume

---

## 🔧 API Reference

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/tasks` | List all tasks |
| `POST` | `/api/tasks` | Create new task |
| `GET` | `/api/tasks/{id}` | Get task details |
| `POST` | `/api/tasks/{id}/halt` | Halt a task |
| `POST` | `/api/tasks/{id}/feedback` | Send human feedback |
| `POST` | `/api/tasks/{id}/resume` | Resume halted task |
| `PATCH` | `/api/tasks/{id}` | Update task |
| `GET` | `/api/stats` | System statistics |
| `GET` | `/health` | Health check |

### Real-time Events

```javascript
// SSE endpoint
GET /api/events/stream

// WebSocket endpoint
GET /api/events/ws
```

---

## 📁 Project Structure

```
multi_agent_system/
├── api/                      # FastAPI server & routes
│   ├── server.py
│   └── routes/
│       ├── tasks.py          # Task CRUD + HITL
│       ├── agents.py         # Agent management
│       └── events.py         # SSE/WebSocket
├── core/                     # Core agent system
│   ├── agent_base.py        # Base agent class
│   ├── senior_agent.py       # Task decomposition
│   ├── worker_agent.py       # Task execution + HITL
│   ├── critic_agent.py       # Quality review
│   ├── manager_agent.py      # Orchestration
│   ├── event_bus.py         # Async pub/sub
│   ├── state_manager.py     # SQLite persistence
│   └── json_utils.py        # Robust JSON parsing
├── dashboard/web/            # Frontend dashboard
│   ├── index.html
│   └── static/
│       ├── css/main.css
│       └── js/app.js
├── docker/                   # Docker configuration
│   ├── Dockerfile.api
│   ├── Dockerfile.agent
│   ├── agent_executor.py    # Container execution
│   └── docker-compose.yml
├── llm/                      # LLM providers
│   ├── base.py
│   ├── manager.py           # Multi-provider router
│   └── providers/           # OpenAI, Anthropic, etc.
├── roles/                    # Agent role prompts
│   ├── WORKER_AGENT.md
│   ├── SENIOR_AGENT.md
│   └── CRITIC_AGENT.md
├── tools/                    # Agent tools
│   ├── file_operations.py
│   └── web_tools.py
├── .env.example             # Environment template
├── .gitignore               # Git ignore rules
├── requirements.txt         # Python dependencies
├── test_e2e_flow.py        # E2E test script
└── README.md
```

---

## 🛡️ Security

| Feature | Description |
|---------|-------------|
| **Docker Isolation** | Commands run in ephemeral containers |
| **auto_remove** | Containers cleaned up automatically |
| **Timeout** | 30-second max prevents resource exhaustion |
| **Whitelist Commands** | Only pre-approved commands allowed |
| **Read-Only FS** | Container filesystem is read-only |
| **Non-Root User** | Agents run as unprivileged user |
| **No API Keys in Code** | All secrets in `.env` file |

---

## 💾 Workspace Management

Files created by agents are stored in `agent_workspace/`:

```bash
# Files persist here (not in containers)
ls agent_workspace/

# Copy from a running container if needed
docker cp <container_id>:/workspace/agent_workspace/output.csv ./
```

---

## 🧪 Testing

```bash
# Start the server
python -m api.server

# In another terminal, run E2E tests
python test_e2e_flow.py
```

---

## 🔮 HITL Deep Dive

When you send feedback to a halted task:

```
Your Feedback → POST /api/tasks/{id}/feedback
                    │
                    ▼
              Stored in task.metadata
                    │
                    ▼
              POST /api/tasks/{id}/resume
                    │
                    ▼
              TASK_RESUMED event published
                    │
                    ▼
              ManagerAgent receives event
                    │
                    ▼
              Worker receives feedback
                    │
                    ▼
              Feedback prepended to next LLM prompt:
              "[URGENT HUMAN OVERRIDE]: {your feedback}"
```

---

## 📝 License

MIT License — free for personal and commercial use.

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional LLM provider integrations
- Enhanced dashboard visualizations
- Performance optimizations
- Extended HITL interaction patterns

---

## 🔗 Links

- **GitHub:** https://github.com/amaliogomezlopez/PRAXIS-SENATE
- **Dashboard:** http://localhost:8000/dashboard
- **API Docs:** http://localhost:8000/docs

---

**Built with ❤️ for multi-agent orchestration**
