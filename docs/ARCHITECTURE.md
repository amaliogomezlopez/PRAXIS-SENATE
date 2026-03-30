# PRAXIS-SENATE Architecture

## Agent Execution Model

### Current Design (v1)
```
┌─────────────────────────────────────────────────────────┐
│                    API Server Process                    │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐               │
│  │ Senior  │  │ Worker1 │  │ Worker2 │  (Threads)    │
│  │ Agent   │  │         │  │         │               │
│  └────┬────┘  └────┬────┘  └────┬────┘               │
│       │             │             │                     │
│       └─────────────┼─────────────┘                     │
│                     │                                   │
│              Shared Workspace                           │
│              (same process)                             │
└─────────────────────────────────────────────────────────┘
```

### Recommended Design (v2) - Task Isolation
```
┌─────────────────────────────────────────────────────────┐
│                    API Server Process                    │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐               │
│  │ Senior  │  │ Worker1 │  │ Worker2 │  (Lightweight)│
│  │ Agent   │  │ Agent   │  │ Agent   │               │
│  └────┬────┘  └────┬────┘  └────┬────┘               │
│       │             │             │                     │
│       └─────────────┼─────────────┘                     │
│                     │ Message Bus                      │
└──────────┬──────────┴───────────────┬──────────────────┘
           │                          │
           ▼                          ▼
┌──────────────────┐     ┌──────────────────────────────┐
│  Task Database   │     │   Docker Agent Executor    │
│  (Shared State) │     │   (Spawns containers)     │
└──────────────────┘     └──────────────┬─────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
             ┌───────────┐    ┌───────────┐    ┌───────────┐
             │ Container │    │ Container │    │ Container │
             │  Task 1  │    │  Task 2  │    │  Task 3  │
             │ (isolated)│    │ (isolated)│    │ (isolated)│
             └───────────┘    └───────────┘    └───────────┘
```

### Execution Philosophy

**Agents are coordinators, not executors.**

1. **Agent (Senior/Worker/Critic)**: Lightweight LLM-powered coordinator
   - Makes decisions
   - Decomposes tasks
   - Analyzes results
   - Communicates via event bus

2. **Task Executor (Docker)**: Executes commands in isolation
   - Spawned per task or batch
   - Resource-limited (CPU, memory)
   - Network-disabled by default
   - Read-only filesystem

3. **Shared Workspace**: Volume mount for agent collaboration
   ```
   /workspace/
   ├── agent_workspace/     # Shared working directory
   │   ├── senior/         # Senior agent files
   │   ├── worker_1/       # Worker 1 files
   │   ├── worker_2/       # Worker 2 files
   │   └── output/         # Generated outputs
   ├── data/              # Task database
   └── logs/              # Execution logs
   ```

### Docker Container Model

**One container per task execution**, not per agent.

- Agent runs in API server process (coordinator)
- When agent needs to execute a command:
  1. Command validated by SafeCommandValidator
  2. Docker container spawned with:
     - Task-specific workspace
     - Resource limits (256MB RAM, 0.5 CPU)
     - Network disabled
     - Read-only filesystem (except workspace)
  3. Command executed
  4. Container destroyed
  5. Output returned to agent

### Benefits

1. **Security**: Commands run in isolated containers
2. **Resource Control**: Limits on CPU, memory per task
3. **Scalability**: Containers spawned on-demand
4. **Simplicity**: Agents stay lightweight
5. **Debugging**: Easy to inspect container logs

### Multi-Worker Configuration

Default: 3 workers = 3 concurrent task capacity

```
┌─────────────────────────────────────────────────────────┐
│                    API Server                           │
│  Senior Agent (1) - Task decomposition                  │
│       │                                                 │
│  Event Bus (publishes tasks)                           │
│       │                                                 │
│  ┌────┴────┐                                          │
│  ▼         ▼         ▼                                 │
│ Worker1  Worker2  Worker3  (concurrent task execution) │
│   │         │         │                                 │
│   ▼         ▼         ▼                                 │
│ Docker    Docker    Docker  (isolated containers)       │
└─────────────────────────────────────────────────────────┘
```

Each worker can execute 1 task at a time (configurable pool size).

### File Isolation

Agents should only access their designated workspace:

| Agent | Workspace | Permissions |
|-------|-----------|------------|
| Senior | `/workspace/senior/` | Read/Write |
| Worker 1 | `/workspace/worker_1/` | Read/Write |
| Worker 2 | `/workspace/worker_2/` | Read/Write |
| Worker N | `/workspace/worker_n/` | Read/Write |
| All | `/workspace/shared/` | Read/Write |

This prevents Worker 1 from accidentally modifying Worker 2's files.

### Command Validation Flow

```
Agent decides to run: git clone https://github.com/user/repo

     │
     ▼
SafeCommandValidator.is_command_safe(command)
     │
     ├─── ALLOWED ──▶ Docker Agent Executor
     │                      │
     │                      ▼
     │                 Spawn Container
     │                      │
     │                      ▼
     │                 Execute Command
     │                      │
     │                      ▼
     │                 Return Result
     │
     └─── BLOCKED ──▶ Log Security Event
                            │
                            ▼
                       Audit Log
```

### Example: Task Execution Flow

1. User submits: "Analyze this code and create a report"

2. Senior Agent:
   - Decomposes into tasks
   - Creates task records in TaskDatabase
   - Assigns to Worker 1

3. Worker 1:
   - Queries TaskDatabase for assigned tasks
   - Updates task status to IN_PROGRESS
   - Decides to run: `python analyze.py --input ./code/`

4. Docker Agent Executor:
   - Validates command
   - Spawns container with workspace mounted
   - Executes command with limits
   - Returns output

5. Worker 1:
   - Updates task status to COMPLETED
   - Adds result comment
   - Notifies Senior via event bus

6. Senior Agent:
   - Collects results
   - Analyzes with Critic
   - Generates final report
