# CLI Dashboard Design - Sistema Multi-Agente

## Principios de Diseño

### Visual First
- **Poco texto, mucho visual**: Iconos, colores, progress bars
- **Información densa**: Máxima información en mínimo espacio
- **Actualización en tiempo real**: Refresh automático sin parpadeo
- **Responsive**: Adapta a diferentes tamaños de terminal

### Tecnologías
- **Rich** (Python): Renderizado de tablas, progress bars, syntax highlighting
- **Textual** (Python): Reactive UI components, layouts, eventos
- **Alternativa**: Blessed, Curses (más bajo nivel)

---

## Mockup Principal del Dashboard

```
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║ 🤖 Multi-Agent System Dashboard                          Last update: 2026-03-18 21:30 ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                         ║
║  SYSTEM STATUS                                                     Manager: ✅ ACTIVE   ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                                         ║
║  🎯 Current Mission: "Implement authentication system"                                 ║
║  Progress: ████████████████░░░░░░░░ 65% (13/20 tasks)                                  ║
║                                                                                         ║
╠═════════════════════════════════════╦═══════════════════════════════════════════════════╣
║ 👥 AGENTS (5 active)                ║ 📊 TASK QUEUE                                     ║
╠═════════════════════════════════════╬═══════════════════════════════════════════════════╣
║                                     ║                                                   ║
║  ┌────────────────────────────────┐ ║  Pending:    ⏳ 5 tasks                          ║
║  │ 🔵 worker-001 BUSY             │ ║  In Progress: ⚙️  3 tasks                         ║
║  │    Code Editor                 │ ║  Completed:   ✅ 10 tasks                         ║
║  │    Task: auth_module.py        │ ║  Failed:      ❌ 2 tasks                          ║
║  │    ▓▓▓▓▓▓▓▓▓░ 85%             │ ║                                                   ║
║  └────────────────────────────────┘ ║                                                   ║
║                                     ║  ┌─────────────────────────────────────────────┐ ║
║  ┌────────────────────────────────┐ ║  │ NEXT IN QUEUE                               │ ║
║  │ 🟢 worker-002 IDLE             │ ║  ├─────────────────────────────────────────────┤ ║
║  │    Researcher                  │ ║  │ 🔴 HIGH  │ Review security tests           │ ║
║  │    Awaiting task...            │ ║  │ 🟡 MED   │ Update documentation            │ ║
║  │                                │ ║  │ 🟢 LOW   │ Refactor utils module           │ ║
║  └────────────────────────────────┘ ║  └─────────────────────────────────────────────┘ ║
║                                     ║                                                   ║
║  ┌────────────────────────────────┐ ║                                                   ║
║  │ 🔵 worker-003 BUSY             │ ║                                                   ║
║  │    Code Reviewer               │ ║                                                   ║
║  │    Task: test_auth.py          │ ║                                                   ║
║  │    ▓▓▓▓▓░░░░░ 45%             │ ║                                                   ║
║  └────────────────────────────────┘ ║                                                   ║
║                                     ║                                                   ║
║  ┌────────────────────────────────┐ ║                                                   ║
║  │ 🔵 worker-004 BUSY             │ ║                                                   ║
║  │    File Manager                │ ║                                                   ║
║  │    Task: config_setup          │ ║                                                   ║
║  │    ▓▓▓▓▓▓▓▓▓▓ 92%             │ ║                                                   ║
║  └────────────────────────────────┘ ║                                                   ║
║                                     ║                                                   ║
║  ┌────────────────────────────────┐ ║                                                   ║
║  │ 🟢 worker-005 IDLE             │ ║                                                   ║
║  │    API Specialist              │ ║                                                   ║
║  │    Awaiting task...            │ ║                                                   ║
║  └────────────────────────────────┘ ║                                                   ║
║                                     ║                                                   ║
╠═════════════════════════════════════╩═══════════════════════════════════════════════════╣
║                                                                                         ║
║  📁 FILE CHANGES (Last 10)                                                              ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                                         ║
║  ┌───────┬────────────────────────────────────────┬──────────┬────────────┬──────────┐ ║
║  │ Time  │ File                                   │ Agent    │ Action     │ Changes  │ ║
║  ├───────┼────────────────────────────────────────┼──────────┼────────────┼──────────┤ ║
║  │ 21:28 │ 📄 auth/models.py                      │ worker-1 │ ✏️ MODIFY   │ +25 -10  │ ║
║  │ 21:27 │ 📄 auth/validators.py                  │ worker-1 │ ➕ CREATE  │ +120 -0  │ ║
║  │ 21:25 │ 📄 tests/test_auth.py                  │ worker-3 │ ✏️ MODIFY   │ +45 -5   │ ║
║  │ 21:23 │ 📄 config/settings.py                  │ worker-4 │ ✏️ MODIFY   │ +8 -3    │ ║
║  │ 21:20 │ 📄 README.md                           │ worker-2 │ ✏️ MODIFY   │ +15 -0   │ ║
║  └───────┴────────────────────────────────────────┴──────────┴────────────┴──────────┘ ║
║                                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                         ║
║  ⚠️  PROBLEMS & ISSUES (3 open)                                                         ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                                         ║
║  ┌─────────────────────────────────────────────────────────────────────────────────┐  ║
║  │ 🔴 ERROR   │ worker-003 │ Task: test_coverage                                   │  ║
║  │            │ Test coverage below 80% threshold (current: 65%)                   │  ║
║  │            │ Retry 1/3 scheduled in 5s                                          │  ║
║  └─────────────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                         ║
║  ┌─────────────────────────────────────────────────────────────────────────────────┐  ║
║  │ 🟡 WARNING │ worker-001 │ Task: auth_module                                     │  ║
║  │            │ File conflict detected: auth/models.py modified by worker-002      │  ║
║  │            │ Waiting for manager resolution...                                  │  ║
║  └─────────────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                         ║
║  ┌─────────────────────────────────────────────────────────────────────────────────┐  ║
║  │ 🔵 INFO    │ worker-004 │ Task: dependency_install                              │  ║
║  │            │ Large download in progress (450MB / 1.2GB) - 37%                   │  ║
║  │            │ ETA: 2m 15s                                                        │  ║
║  └─────────────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                         ║
║  📝 RECENT ACTIVITY LOG                                                                 ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                                         ║
║  21:30:15  ℹ️  [worker-001] Started task: refactor_auth_module                          ║
║  21:30:10  ✅ [worker-004] Completed task: setup_database_migrations (45.2s)            ║
║  21:30:05  ⚠️  [manager] Detected gap: Missing unit tests for password validator        ║
║  21:30:00  📤 [worker-003] Published result: code_review_complete                       ║
║  21:29:55  ℹ️  [worker-002] Fetching documentation from external API...                 ║
║  21:29:50  🔄 [worker-001] Retry attempt 2/3 for task: auth_validation                  ║
║  21:29:45  ❌ [worker-005] Failed task: external_api_call - Timeout after 30s           ║
║                                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                         ║
║  💡 MANAGER INSIGHTS                                                                    ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                                         ║
║  • Authentication module is 85% complete                                               ║
║  • Identified 3 missing test cases - creating follow-up tasks                          ║
║  • File conflict in auth/models.py requires manual resolution                          ║
║  • Estimated completion: 15 minutes (3 tasks remaining)                                ║
║                                                                                         ║
╚═════════════════════════════════════════════════════════════════════════════════════════╝

Press [q] to quit | [r] to refresh | [d] for details | [l] for full logs | [h] for help
```

---

## Vista Detallada de Tarea (Detail View)

```
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║ 🔍 Task Details: auth_module_refactor                                                  ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                         ║
║  ID:          task-7f3a2b1c-4e8d-9a6f-1c2d-5e8f3a7b9c1d                               ║
║  Status:      🔵 IN_PROGRESS                                                            ║
║  Priority:    🔴 HIGH                                                                   ║
║  Assigned to: worker-001 (Code Editor)                                                 ║
║  Created:     2026-03-18 21:20:30                                                      ║
║  Started:     2026-03-18 21:25:15                                                      ║
║  Duration:    5m 45s / 10m (timeout)                                                   ║
║                                                                                         ║
║  Progress:    ▓▓▓▓▓▓▓▓▓░░░░░░░░░░░ 85%                                                 ║
║                                                                                         ║
║  ┌─────────────────────────────────────────────────────────────────────────────────┐  ║
║  │ OBJECTIVE                                                                       │  ║
║  ├─────────────────────────────────────────────────────────────────────────────────┤  ║
║  │ Refactor authentication module to use dependency injection pattern             │  ║
║  │ and improve testability. Maintain backward compatibility with                  │  ║
║  │ existing API endpoints.                                                         │  ║
║  └─────────────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                         ║
║  ┌─────────────────────────────────────────────────────────────────────────────────┐  ║
║  │ INPUT FILES                                                                     │  ║
║  ├─────────────────────────────────────────────────────────────────────────────────┤  ║
║  │ 📄 /workspace/auth/models.py                                                    │  ║
║  │ 📄 /workspace/auth/services.py                                                  │  ║
║  │ 📄 /workspace/tests/test_auth.py                                                │  ║
║  └─────────────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                         ║
║  ┌─────────────────────────────────────────────────────────────────────────────────┐  ║
║  │ COMPLETION CRITERIA                                                             │  ║
║  ├─────────────────────────────────────────────────────────────────────────────────┤  ║
║  │ ✅ All existing tests pass                                                      │  ║
║  │ ✅ Code coverage >= 80%                                                         │  ║
║  │ 🔄 No breaking changes to public API                          [CHECKING...]    │  ║
║  │ ⏳ Documentation updated                                       [PENDING]        │  ║
║  └─────────────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                         ║
║  ┌─────────────────────────────────────────────────────────────────────────────────┐  ║
║  │ EXECUTION STEPS                                                                 │  ║
║  ├─────────────────────────────────────────────────────────────────────────────────┤  ║
║  │ ✅ Step 1: Analyze current code structure               [COMPLETED - 1m 20s]   │  ║
║  │ ✅ Step 2: Design dependency injection pattern          [COMPLETED - 45s]      │  ║
║  │ 🔄 Step 3: Refactor services module                     [IN PROGRESS - 2m 15s] │  ║
║  │ ⏳ Step 4: Update tests                                  [PENDING]              │  ║
║  │ ⏳ Step 5: Run full test suite                           [PENDING]              │  ║
║  └─────────────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                         ║
║  ┌─────────────────────────────────────────────────────────────────────────────────┐  ║
║  │ FILES MODIFIED (3)                                                              │  ║
║  ├─────────────────────────────────────────────────────────────────────────────────┤  ║
║  │ 21:28  📄 auth/models.py              ✏️ MODIFY    +25 -10                      │  ║
║  │ 21:27  📄 auth/validators.py          ➕ CREATE    +120 -0                      │  ║
║  │ 21:26  📄 auth/services.py            ✏️ MODIFY    +58 -23                      │  ║
║  └─────────────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                         ║
║  ┌─────────────────────────────────────────────────────────────────────────────────┐  ║
║  │ DEPENDENCIES                                                                    │  ║
║  ├─────────────────────────────────────────────────────────────────────────────────┤  ║
║  │ ✅ setup_database_schema                                 [COMPLETED]            │  ║
║  │ ✅ install_dependencies                                  [COMPLETED]            │  ║
║  └─────────────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                         ║
║  ┌─────────────────────────────────────────────────────────────────────────────────┐  ║
║  │ BLOCKED BY THIS TASK                                                            │  ║
║  ├─────────────────────────────────────────────────────────────────────────────────┤  ║
║  │ ⏳ integration_tests                                     [WAITING]              │  ║
║  │ ⏳ deploy_to_staging                                     [WAITING]              │  ║
║  └─────────────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                         ║
╚═════════════════════════════════════════════════════════════════════════════════════════╝

Press [ESC] to return | [f] follow logs | [k] kill task
```

---

## Vista de Logs en Tiempo Real

```
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║ 📋 Live Logs - All Agents                                      [Auto-scroll: ON]  [▼]  ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                         ║
║ Filters: [ALL] [Manager] [Workers] [Errors Only] [My Tasks]   Search: [____________]  ║
║                                                                                         ║
║ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                                         ║
║ 21:30:45  🟢 DEBUG   [worker-001] Reading file: /workspace/auth/models.py              ║
║ 21:30:44  🔵 INFO    [worker-001] Applying refactoring pattern: dependency_injection   ║
║ 21:30:43  🔵 INFO    [worker-003] Running test suite: tests/test_auth.py               ║
║ 21:30:42  🟢 DEBUG   [worker-003] Test passed: test_user_authentication (0.45s)        ║
║ 21:30:41  🟢 DEBUG   [worker-003] Test passed: test_password_validation (0.23s)        ║
║ 21:30:40  🟡 WARNING [manager] Detected potential gap: Missing error handling          ║
║ 21:30:39  🔵 INFO    [manager] Analyzing task results from worker-004                  ║
║ 21:30:38  🔵 INFO    [worker-004] Task completed successfully                          ║
║ 21:30:37  🟢 DEBUG   [worker-004] Writing file: /workspace/config/settings.py          ║
║ 21:30:36  🔵 INFO    [worker-002] Fetching API documentation from external source      ║
║ 21:30:35  🔴 ERROR   [worker-005] Connection timeout to external API                   ║
║ 21:30:34  🟡 WARNING [worker-005] Retry attempt 2/3                                    ║
║ 21:30:33  🔵 INFO    [manager] Creating follow-up task: update_api_docs                ║
║ 21:30:32  🟢 DEBUG   [EventBus] Publishing message: TASK_RESULT                        ║
║ 21:30:31  🟢 DEBUG   [EventBus] Message consumed by: manager                           ║
║ 21:30:30  🔵 INFO    [worker-001] Starting task: refactor_auth_module                  ║
║ 21:30:29  🔵 INFO    [manager] Assigned task-7f3a2b to worker-001                      ║
║ 21:30:28  🟢 DEBUG   [manager] Task decomposition completed: 5 subtasks created        ║
║ 21:30:27  🔵 INFO    [manager] Received user request: Implement authentication         ║
║                                                                                         ║
║ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                                         ║
║ Lines: 1,247 | Showing: Last 100 | Errors: 3 | Warnings: 12                            ║
║                                                                                         ║
╚═════════════════════════════════════════════════════════════════════════════════════════╝

Press [ESC] to return | [↑↓] scroll | [/] search | [p] pause | [c] clear
```

---

## Panel de Estadísticas

```
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║ 📊 System Statistics & Metrics                                                         ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                         ║
║  SESSION OVERVIEW                                                                      ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                                         ║
║  Session started:    2026-03-18 21:00:00                                               ║
║  Uptime:             30m 45s                                                           ║
║  Total tasks:        20                                                                ║
║  Completed:          ✅ 10 (50%)                                                        ║
║  In progress:        🔵 3 (15%)                                                         ║
║  Failed:             ❌ 2 (10%)                                                         ║
║  Pending:            ⏳ 5 (25%)                                                         ║
║                                                                                         ║
║  ┌─────────────────────────────────────────────────────────────────────────────────┐  ║
║  │ COMPLETION RATE OVER TIME                                                       │  ║
║  ├─────────────────────────────────────────────────────────────────────────────────┤  ║
║  │         ╭─╮                                                                     │  ║
║  │      ╭──╯ ╰─╮    ╭─╮                                                           │  ║
║  │   ╭──╯      ╰────╯ ╰──╮                                                         │  ║
║  │ ──╯                   ╰────                                                     │  ║
║  │ 21:00  21:10  21:20  21:30                                                      │  ║
║  └─────────────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                         ║
║  AGENT PERFORMANCE                                                                     ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                                         ║
║  ┌───────────┬───────────┬─────────┬──────────┬────────────┬─────────────────────┐   ║
║  │ Agent     │ Tasks     │ Success │ Failed   │ Avg Time   │ Utilization         │   ║
║  ├───────────┼───────────┼─────────┼──────────┼────────────┼─────────────────────┤   ║
║  │ worker-01 │ 5         │ 4       │ 1        │ 2m 34s     │ ▓▓▓▓▓▓▓░░░ 72%      │   ║
║  │ worker-02 │ 2         │ 2       │ 0        │ 1m 15s     │ ▓▓▓░░░░░░░ 25%      │   ║
║  │ worker-03 │ 4         │ 3       │ 1        │ 3m 02s     │ ▓▓▓▓▓▓▓▓░░ 85%      │   ║
║  │ worker-04 │ 3         │ 3       │ 0        │ 4m 20s     │ ▓▓▓▓▓▓▓▓▓░ 90%      │   ║
║  │ worker-05 │ 1         │ 0       │ 1        │ N/A        │ ▓░░░░░░░░░ 15%      │   ║
║  └───────────┴───────────┴─────────┴──────────┴────────────┴─────────────────────┘   ║
║                                                                                         ║
║  FILE OPERATIONS                                                                       ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                                         ║
║  Files created:      8                                                                 ║
║  Files modified:     15                                                                ║
║  Files deleted:      2                                                                 ║
║  Total lines added:  +1,245                                                            ║
║  Total lines removed: -387                                                             ║
║  Net change:         +858 lines                                                        ║
║                                                                                         ║
║  SYSTEM RESOURCES                                                                      ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                                         ║
║  CPU Usage:    ▓▓▓▓░░░░░░░░░░░░░░░░ 22%                                               ║
║  Memory:       ▓▓▓▓▓▓▓░░░░░░░░░░░░░ 35% (2.1GB / 6GB)                                 ║
║  Queue depth:  ▓▓░░░░░░░░░░░░░░░░░░ 8/50                                              ║
║  Msg/sec:      12.5 (avg: 10.2)                                                        ║
║                                                                                         ║
╚═════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## Componentes Visuales Clave

### 1. Iconos y Símbolos

```python
# Status Icons
ICONS = {
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "pending": "⏳",
    "in_progress": "🔄",
    "idle": "💤",
    "busy": "⚙️",
    "blocked": "🚫",
}

# Priority Icons
PRIORITY = {
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢",
}

# Agent Status
AGENT_STATUS = {
    "active": "🔵",
    "idle": "🟢",
    "error": "🔴",
    "offline": "⚫",
}

# File Operations
FILE_OPS = {
    "create": "➕",
    "modify": "✏️",
    "delete": "🗑️",
    "read": "📖",
}
```

### 2. Color Scheme

```python
from rich.theme import Theme

THEME = Theme({
    "success": "bold green",
    "error": "bold red",
    "warning": "bold yellow",
    "info": "bold cyan",
    "debug": "dim white",

    "agent.manager": "bold magenta",
    "agent.worker": "bold cyan",

    "priority.high": "bold red",
    "priority.medium": "bold yellow",
    "priority.low": "bold green",

    "status.active": "bold blue",
    "status.idle": "green",
    "status.busy": "yellow",
})
```

### 3. Layout Components

```python
from rich.layout import Layout

def create_dashboard_layout():
    layout = Layout()

    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=1)
    )

    layout["body"].split_row(
        Layout(name="left", ratio=1),
        Layout(name="right", ratio=2)
    )

    layout["left"].split_column(
        Layout(name="agents"),
        Layout(name="queue")
    )

    layout["right"].split_column(
        Layout(name="files"),
        Layout(name="problems"),
        Layout(name="logs")
    )

    return layout
```

---

## Actualización en Tiempo Real

### Event-Driven Updates

```python
from textual.app import App
from textual.reactive import reactive

class DashboardApp(App):
    # Reactive properties - auto-update UI
    task_count = reactive(0)
    active_agents = reactive([])
    recent_logs = reactive([])

    def on_mount(self):
        # Start background tasks
        self.set_interval(0.5, self.update_dashboard)

    async def update_dashboard(self):
        # Fetch latest state
        tasks = await self.fetch_tasks()
        agents = await self.fetch_agents()
        logs = await self.fetch_logs()

        # Update reactive properties (triggers UI update)
        self.task_count = len(tasks)
        self.active_agents = agents
        self.recent_logs = logs[-10:]
```

---

## Interactividad

### Keyboard Shortcuts

```
Global:
  q       - Quit dashboard
  r       - Refresh all data
  h       - Show help
  /       - Search/filter
  ESC     - Return to main view

Navigation:
  ↑↓      - Scroll up/down
  ←→      - Switch panels
  Tab     - Next panel
  1-9     - Quick jump to section

Task Management:
  d       - Show task details
  k       - Kill selected task
  p       - Pause/resume task
  f       - Follow task logs

Views:
  v       - Toggle view mode (compact/detailed)
  s       - Show statistics
  l       - Full log view
  m       - Manager insights
```

---

## Próximos Pasos

1. [x] Diseño completo del CLI Dashboard
2. [ ] Estructura de datos JSON/YAML
3. [ ] Implementación del código base
