# PRAXIS-SENATE Implementation To-Do List

> **Last Updated**: 2026-03-26
> **Status**: Major architectural upgrade completed

---

## Completed Priorities

### ✅ Priority 1: API Keys Setup
- [x] Create `.env` file with MiniMax API key
- [x] Ensure `python-dotenv` loading in `config/__init__.py`
- [x] MiniMax provider created and configured as default

### ✅ Priority 2: Web Server with REST API
- [x] FastAPI server with lifespan events
- [x] All REST endpoints implemented
- [x] Routes use proper dependency injection via `request.app.state`

### ✅ Priority 3: Real-time Event Broadcasting
- [x] EventBroadcaster class bridging EventBus → WebSocket/SSE
- [x] SSE endpoint at `GET /api/events/stream`
- [x] WebSocket at `WebSocket /api/events/ws`
- [x] All event types broadcasted

### ✅ Priority 4: HTML Dashboard
- [x] Dashboard at `/dashboard` with all panels
- [x] Real-time updates via WebSocket
- [x] Task submission form with modal
- [x] Agent management (pause/resume)

### ✅ Priority 5: Task Persistence (Database)
- [x] SQLite database with SQLAlchemy models
- [x] Dual-write StateManager
- [x] PersistentStateManager for extended persistence

---

## New Architecture Components

### ✅ Docker Container Security
- [x] `docker/Dockerfile.agent` - Secure agent execution container
- [x] `docker/Dockerfile.api` - Production API container
- [x] `docker/docker-compose.yml` - Orchestration with network isolation
- [x] `docker/agent_executor.py` - Safe command execution in Docker

### ✅ Agent Role MD Files
- [x] `roles/SENIOR_AGENT.md` - Senior agent role definition
- [x] `roles/WORKER_AGENT.md` - Worker agent role definition
- [x] `roles/CRITIC_AGENT.md` - Critic agent role definition
- [x] `roles/loader.py` - Automatic role loading for prompts

### ✅ Centralized Task Management
- [x] `core/task_database.py` - Shared task database
  - Senior creates tasks
  - Workers read/update tasks
  - Critic reads task results
  - Real-time subscriptions
- [x] `core/task_commands.py` - Natural language task commands parser

### ✅ Cybersecurity & Safety
- [x] `security/__init__.py` - Security module with:
  - CommandSafetyValidator (whitelist approach)
  - RateLimiter (API and command rate limiting)
  - InputSanitizer (injection prevention)
  - SecurityAuditor (audit logging)

### ✅ Dashboard Enhancements
- [x] Lateral sidebar menu with task history
- [x] Role file viewer/editor for all agent types
- [x] `api/routes/roles.py` - REST API for role file management
- [x] Real-time sidebar updates as tasks complete

---

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRAXIS-SENATE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│  │   Dashboard  │────▶│  FastAPI     │◀────│   Workers   │   │
│  │   (HTML/JS)  │     │   Server     │     │   (N)       │   │
│  └──────────────┘     └──────────────┘     └──────────────┘   │
│         │                    │                      │            │
│         │ WebSocket          │                      │            │
│         │                    │                      │            │
│         ▼                    ▼                      ▼            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              EventBroadcaster (Real-time)                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│         ┌─────────────────────┼─────────────────────┐            │
│         ▼                     ▼                     ▼            │
│  ┌────────────┐     ┌──────────────┐     ┌────────────┐        │
│  │TaskDatabase│     │  EventBus   │     │   LLM     │        │
│  │(Centralized)│    │             │     │  Manager  │        │
│  └────────────┘     └──────────────┘     └────────────┘        │
│         │                     │                     │            │
│         │                     ▼                     │            │
│         │            ┌──────────────────┐           │            │
│         │            │   SeniorAgent   │◀──────────┘            │
│         │            └──────────────────┘                      │
│         │                     │                               │
│         │                     ▼                               │
│         │            ┌──────────────────┐                       │
│         │            │  CriticAgent    │                       │
│         │            └──────────────────┘                       │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │           Docker Containers (Safe Execution)            │    │
│  │   • Isolated execution                                 │    │
│  │   • Resource limits (CPU, memory)                     │    │
│  │   • Network disabled by default                       │    │
│  │   • Read-only filesystem                              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Task Database Flow

```
Senior Agent                          Worker Agent
     │                                     │
     │ [1] Create Task                     │
     ▼                                     │
┌─────────┐                               │
│   Task  │                               │
│Database │◀──────[3] Update Status────────┤
│         │                               │
└────┬────┘                               │
     │ [2] Read Task                      │
     │ [4] Read Result                    │
     ▼                                     │
┌─────────┐                               │
│ Critic  │◀──────[3] Store Critique──────┘
│ Agent   │
└────┬────┘
     │
     ▼
[5] Feedback to Senior
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/tasks` | Submit new task |
| GET | `/api/tasks` | List tasks (filterable) |
| GET | `/api/tasks/{id}` | Get task details |
| GET | `/api/tasks/{id}/result` | Get task result |
| POST | `/api/tasks/{id}/critique` | Trigger critique |
| GET | `/api/agents` | List all agents |
| POST | `/api/agents/{id}/pause` | Pause agent |
| POST | `/api/agents/{id}/resume` | Resume agent |
| GET | `/api/events/stream` | SSE event stream |
| WS | `/api/events/ws` | WebSocket connection |
| GET | `/api/stats` | System statistics |
| GET | `/api/roles` | List all role files |
| GET | `/api/roles/{filename}` | Get role file content |
| PUT | `/api/roles/{filename}` | Update role file |
| GET | `/health` | Health check |

---

## File Structure (Updated)

```
45-PRAXIS-SENATE/
├── api/
│   ├── __init__.py
│   ├── server.py              ✅ FastAPI app
│   ├── dependencies.py        ✅ Shared dependencies
│   └── routes/
│       ├── __init__.py
│       ├── tasks.py          ✅ Task endpoints
│       ├── agents.py          ✅ Agent endpoints
│       ├── events.py          ✅ SSE/WebSocket
│       ├── critiques.py       ✅ Critique endpoints
│       └── roles.py           ✅ Role file viewer/editor
├── dashboard/
│   └── web/
│       ├── index.html         ✅ Dashboard
│       └── static/
│           ├── css/main.css   ✅ Styles
│           └── js/app.js     ✅ Real-time updates
├── db/
│   ├── __init__.py
│   ├── database.py            ✅ SQLite async
│   └── models.py              ✅ SQLAlchemy models
├── docker/
│   ├── Dockerfile.agent        ✅ Secure container
│   ├── Dockerfile.api          ✅ API container
│   ├── docker-compose.yml      ✅ Orchestration
│   └── agent_executor.py       ✅ Safe execution
├── roles/
│   ├── __init__.py
│   ├── loader.py               ✅ Role loader
│   ├── SENIOR_AGENT.md        ✅ Senior role
│   ├── WORKER_AGENT.md        ✅ Worker role
│   └── CRITIC_AGENT.md        ✅ Critic role
├── core/
│   ├── event_bus.py            ✅ Event system
│   ├── state_manager.py         ✅ State management
│   ├── task_database.py        ✅ Centralized tasks
│   ├── task_commands.py         ✅ Command parser
│   ├── senior_agent.py          ✅ Senior agent
│   ├── worker_agent.py          ✅ Worker agent
│   └── critic_agent.py          ✅ Critic agent
├── security/
│   └── __init__.py             ✅ Security module
├── config/
│   ├── __init__.py             ✅ Config loading
│   └── providers.yaml           ✅ LLM providers
├── requirements.txt             ✅ Updated
├── .env                        ✅ MiniMax key
└── TODOs.md                    ✅ This file
```

---

## Remaining Tasks

### 🟡 Important (Should do)

5. **Agent prompt integration**
   - Load role MD files automatically
   - Inject task context into prompts
   - Parse task commands from responses

6. **Real-time dashboard task subscription**
   - Connect dashboard to TaskDatabase events
   - Show task progress updates
   - Display comments in real-time

7. **Command execution safety**
   - Integrate DockerAgentExecutor
   - Execute dangerous commands in containers
   - Monitor execution

### 🟢 Nice to have

8. **Docker deployment scripts**
   - Build script for containers
   - Deployment automation
   - Health checks

9. **Testing**
   - Unit tests for agents
   - Integration tests
   - Security tests

10. **Documentation**
    - API documentation
    - Architecture diagrams
    - Usage guide

---

## ✅ Completed in This Update

### Dashboard Task History Panel (#12)
- [x] Added lateral sidebar menu
- [x] Task history shows completed/failed tasks
- [x] Click on history item to view task details
- [x] Sidebar toggle button in header

### Dashboard Role File Viewer/Editor (#13)
- [x] Created `/api/roles` API endpoints (list, get, update)
- [x] Role buttons in sidebar for each agent type
- [x] Modal editor for viewing/editing .md role files
- [x] Save and Reset functionality
- [x] Backup created before saving changes

### Phase 1: Core Logic Integration (#5, #6, #7)

**Agent Prompt Integration (#5)**
- [x] SeniorAgent now loads role from `roles/loader.py` and injects as system prompt
- [x] CriticAgent now loads role from `roles/loader.py` and injects as system prompt
- [x] WorkerAgent now has LLM integration with role-based prompts

**Real-time Task Subscription (#6)**
- [x] StateManager now publishes events to EventBus on task changes
- [x] TaskCreated, TaskStarted, TaskCompleted, TaskFailed events trigger properly
- [x] Dashboard WebSocket receives real-time task updates

**Command Execution Safety / Docker (#7)**
- [x] WorkerAgent now has DockerAgentExecutor integrated
- [x] New `execute_command` task type for Docker-based execution
- [x] LLM-based action decision-making for unknown task types
- [x] Commands execute in isolated containers with resource limits

### Phase 2: UI/UX Polish

**Agent Pool Enhancements**
- [x] Agent cards with avatar icons, more padding, visual status indicators
- [x] Status dot with pulse animation for active agents
- [x] Modern rounded buttons with icons (⏸ Pause / ▶ Resume)
- [x] Hover effects and smooth transitions

**Interactive Task Board**
- [x] Enhanced task cards showing Task ID, Description, Assigned Agent, Type, Duration
- [x] Agent badge showing who is working on the task
- [x] Improved hover effects with shadow

**Readable Activity Log**
- [x] Timestamps in HH:MM:SS format
- [x] Color-coded event entries (success/error/info/warning)
- [x] Event icons for each event type
- [x] Border-left color coding

**Toast Notifications**
- [x] Toast system at bottom-right corner
- [x] Success, error, info, warning toast types
- [x] Auto-dismiss and manual close
- [x] Toast events: task created, completed, failed, role saved, agent paused/resumed

**Role Editor Modal**
- [x] Monospace font (Consolas/Monaco) for code editing
- [x] Dark background (#0d1117) distinct from modal
- [x] Subtle border and focus glow

---

## Quick Start

```bash
# Run API server
cd multi_agent_system
python -m api.server

# Access dashboard
http://localhost:8000/dashboard

# Run with Docker
cd docker
docker-compose up --build

# Submit a task (via API)
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"description": "Analyze this project structure"}'
```

---

## Security Features

| Feature | Status | Description |
|---------|--------|-------------|
| Command Whitelist | ✅ | Only safe commands allowed |
| Rate Limiting | ✅ | Prevents API abuse |
| Input Sanitization | ✅ | Prevents injection |
| Audit Logging | ✅ | Tracks security events |
| Docker Isolation | ✅ | Containerized execution |
| Resource Limits | ✅ | CPU/memory constraints |

---

## Remaining Tasks

### 🔴 Critical (For Full Flow)
1. **Test complete agent flow**: Senior → Task Decomposition → Worker Execution → Critic Review
2. **Verify Docker executor** actually runs commands in containers
3. **End-to-end task cycle** with real-time UI updates

### 🟡 Important
4. **Add more role .md files** for specialized agents (ARCHITECT, CODER, RESEARCHER, REVIEWER)
5. **Worker task queue** - ensure workers pick up assigned tasks properly
6. **Task persistence** - save task history across restarts

### 🟢 Nice to have
7. **Agent conversation history** panel
8. **Task dependency visualization**
9. **Performance metrics** dashboard
10. **Export task reports** as JSON/Markdown
4. **Monitor with dashboard** for real-time visibility
