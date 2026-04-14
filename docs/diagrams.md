# Diagramas de Arquitectura - Sistema Multi-Agente

## 📐 Diagrama de Componentes

```
┌────────────────────────────────────────────────────────────────────────┐
│                          MULTI-AGENT SYSTEM                             │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                        USER INTERFACE                             │ │
│  │  • submit_task(description)                                       │ │
│  │  • get_stats()                                                    │ │
│  │  • monitor_progress()                                             │ │
│  └────────────────────────┬─────────────────────────────────────────┘ │
│                           │                                             │
│                           ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                    MANAGER AGENT                                  │ │
│  │  ┌────────────────────────────────────────────────────────────┐  │ │
│  │  │ Task Reception & Decomposition                             │  │ │
│  │  │  • receive_task()                                          │  │ │
│  │  │  • analyze_description()                                   │  │ │
│  │  │  • create_subtasks()                                       │  │ │
│  │  └────────────────────────────────────────────────────────────┘  │ │
│  │  ┌────────────────────────────────────────────────────────────┐  │ │
│  │  │ Worker Coordination                                        │  │ │
│  │  │  • assign_to_worker()  [Round-Robin]                       │  │ │
│  │  │  • monitor_execution()                                     │  │ │
│  │  │  • collect_results()                                       │  │ │
│  │  └────────────────────────────────────────────────────────────┘  │ │
│  │  ┌────────────────────────────────────────────────────────────┐  │ │
│  │  │ Analysis & Problem Detection                               │  │ │
│  │  │  • analyze_outputs()                                       │  │ │
│  │  │  • detect_gaps()                                           │  │ │
│  │  │  • create_problems()                                       │  │ │
│  │  └────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────┬─────────────────────────────────────────┘ │
│                           │                                             │
│         ┌─────────────────┼─────────────────┬───────────────┐          │
│         │                 │                 │               │          │
│         ▼                 ▼                 ▼               ▼          │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐  ┌────────────┐  │
│  │  WORKER 1  │    │  WORKER 2  │    │  WORKER 3  │  │  WORKER N  │  │
│  │            │    │            │    │            │  │            │  │
│  │ ┌────────┐ │    │ ┌────────┐ │    │ ┌────────┐ │  │ ┌────────┐ │  │
│  │ │FileOps │ │    │ │FileOps │ │    │ │FileOps │ │  │ │FileOps │ │  │
│  │ └────────┘ │    │ └────────┘ │    │ └────────┘ │  │ └────────┘ │  │
│  │ ┌────────┐ │    │ ┌────────┐ │    │ ┌────────┐ │  │ ┌────────┐ │  │
│  │ │WebTools│ │    │ │WebTools│ │    │ │WebTools│ │  │ │WebTools│ │  │
│  │ └────────┘ │    │ └────────┘ │    │ └────────┘ │  │ └────────┘ │  │
│  │ ┌────────┐ │    │ ┌────────┐ │    │ ┌────────┐ │  │ ┌────────┐ │  │
│  │ │Analysis│ │    │ │Analysis│ │    │ │Analysis│ │  │ │Analysis│ │  │
│  │ └────────┘ │    │ └────────┘ │    │ └────────┘ │  │ └────────┘ │  │
│  └──────┬─────┘    └──────┬─────┘    └──────┬─────┘  └──────┬─────┘  │
│         │                 │                 │               │          │
│         └─────────────────┴─────────────────┴───────────────┘          │
│                                   │                                     │
│                                   ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                         EVENT BUS                                 │ │
│  │  ┌────────────────────────────────────────────────────────────┐  │ │
│  │  │ Event Types:                                               │  │ │
│  │  │  • TASK_CREATED      • TASK_ASSIGNED    • TASK_STARTED    │  │ │
│  │  │  • TASK_COMPLETED    • TASK_FAILED      • FILE_MODIFIED   │  │ │
│  │  │  • PROBLEM_DETECTED  • PROGRESS_UPDATE  • AGENT_MESSAGE   │  │ │
│  │  └────────────────────────────────────────────────────────────┘  │ │
│  │  ┌────────────────────────────────────────────────────────────┐  │ │
│  │  │ Pub/Sub Mechanism:                                         │  │ │
│  │  │  • subscribe(event_type, callback)                         │  │ │
│  │  │  • publish(event)                                          │  │ │
│  │  │  • async processing queue                                  │  │ │
│  │  └────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────┬─────────────────────────────────────────┘ │
│                           │                                             │
│         ┌─────────────────┼─────────────────┬───────────────┐          │
│         │                 │                 │               │          │
│         ▼                 ▼                 ▼               ▼          │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐  ┌────────────┐  │
│  │   STATE    │    │  DASHBOARD │    │   LOGGER   │  │  MONITOR   │  │
│  │  MANAGER   │    │    (CLI)   │    │            │  │            │  │
│  │            │    │            │    │            │  │            │  │
│  │ • Tasks    │    │ • Stats    │    │ • Events   │  │ • Metrics  │  │
│  │ • Problems │    │ • Tasks    │    │ • Errors   │  │ • Health   │  │
│  │ • Files    │    │ • Files    │    │ • Info     │  │ • Status   │  │
│  │ • Stats    │    │ • Problems │    │            │  │            │  │
│  │            │    │ • Activity │    │            │  │            │  │
│  └────────────┘    └────────────┘    └────────────┘  └────────────┘  │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

## 🔄 Diagrama de Flujo de Tarea

```
START
  │
  ▼
┌─────────────────────────────────┐
│ User submits task               │
│ "Create Python config file"     │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Manager.submit_user_task()      │
│ • Creates Task object           │
│ • Status: PENDING               │
│ • Assigns ID: task_abc123       │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ EventBus.publish()              │
│ Event: TASK_CREATED             │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Manager._decompose_task()       │
│ Analyzes: "Create Python..."    │
│ Identifies: file creation       │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Manager creates subtasks:       │
│ • task_abc123_sub_0             │
│   Type: create_file             │
│   Params: {path, content}       │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Manager._assign_to_worker()     │
│ Algorithm: Round-robin          │
│ Selected: worker_02             │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ EventBus.publish()              │
│ Event: TASK_ASSIGNED            │
│ Data: {task_id, worker_id}      │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Worker.assign_task()            │
│ Task added to worker queue      │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Worker._execute_task()          │
│ • Updates status: IN_PROGRESS   │
│ • Publishes: TASK_STARTED       │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Worker.process_task()           │
│ Routes to handler based on type │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Worker._handle_create_file()    │
│ • Calls FileOperations          │
│ • Creates file in workspace     │
│ • Returns result                │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ StateManager.add_file_change()  │
│ • Path: output/config.py        │
│ • Action: created               │
│ • Agent: worker_02              │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ EventBus.publish()              │
│ Event: FILE_MODIFIED            │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Worker updates Task             │
│ • Status: COMPLETED             │
│ • Result: {success: true...}    │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ EventBus.publish()              │
│ Event: TASK_COMPLETED           │
│ Data: {task_id, result}         │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Manager._on_task_completed()    │
│ Receives event notification     │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Manager._check_parent_completion│
│ Are all subtasks done?          │
│ Yes → Continue                  │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Manager._analyze_results()      │
│ • Collects subtask results      │
│ • Creates summary               │
│ • Stores in parent task         │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Manager updates parent Task     │
│ • Status: COMPLETED             │
│ • Result: analysis summary      │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Dashboard reflects changes      │
│ • Updates stats panel           │
│ • Shows completed task          │
│ • Displays file change          │
└────────────┬────────────────────┘
             │
             ▼
            END
```

## 🔀 Diagrama de Eventos

```
TASK LIFECYCLE EVENTS
──────────────────────────────────────────────────────────────

User              Manager           Worker            EventBus         Dashboard
 │                   │                 │                  │                 │
 │ submit_task()     │                 │                  │                 │
 ├──────────────────>│                 │                  │                 │
 │                   │                 │                  │                 │
 │                   │ TASK_CREATED    │                  │                 │
 │                   ├────────────────────────────────────>│                 │
 │                   │                 │                  │                 │
 │                   │                 │                  │   EVENT         │
 │                   │                 │                  ├────────────────>│
 │                   │                 │                  │                 │
 │                   │ decompose       │                  │    Update UI    │
 │                   │ + assign        │                  │   ┌──────────┐  │
 │                   │                 │                  │   │📋 New    │  │
 │                   │ TASK_ASSIGNED   │                  │   │   Task   │  │
 │                   ├────────────────────────────────────>│   └──────────┘  │
 │                   │                 │                  │                 │
 │                   │  assign_task()  │                  │                 │
 │                   ├────────────────>│                  │                 │
 │                   │                 │                  │                 │
 │                   │                 │ TASK_STARTED     │                 │
 │                   │                 ├─────────────────>│                 │
 │                   │                 │                  │                 │
 │                   │                 │                  │   EVENT         │
 │                   │<────────────────┤                  ├────────────────>│
 │                   │                 │                  │                 │
 │                   │                 │ execute_task()   │    Update UI    │
 │                   │                 │ ┌──────────┐    │   ┌──────────┐  │
 │                   │                 │ │File      │    │   │⏳ In     │  │
 │                   │                 │ │Operation │    │   │Progress  │  │
 │                   │                 │ └──────────┘    │   └──────────┘  │
 │                   │                 │                  │                 │
 │                   │                 │ FILE_MODIFIED    │                 │
 │                   │                 ├─────────────────>│                 │
 │                   │                 │                  │                 │
 │                   │                 │                  │   EVENT         │
 │                   │                 │                  ├────────────────>│
 │                   │                 │                  │                 │
 │                   │                 │ TASK_COMPLETED   │    Update UI    │
 │                   │                 ├─────────────────>│   ┌──────────┐  │
 │                   │                 │                  │   │📝 File   │  │
 │                   │                 │                  │   │  Change  │  │
 │                   │<────────────────┤                  │   └──────────┘  │
 │                   │                 │                  │                 │
 │                   │                 │                  │   EVENT         │
 │                   │                 │                  ├────────────────>│
 │                   │                 │                  │                 │
 │                   │ analyze_results │                  │    Update UI    │
 │                   │ ┌──────────┐   │                  │   ┌──────────┐  │
 │                   │ │Check all │   │                  │   │✅ Task   │  │
 │                   │ │subtasks  │   │                  │   │Complete  │  │
 │                   │ └──────────┘   │                  │   └──────────┘  │
 │                   │                 │                  │                 │
 │  task_complete    │                 │                  │                 │
 │<──────────────────┤                 │                  │                 │
 │                   │                 │                  │                 │

ERROR SCENARIO
──────────────────────────────────────────────────────────────

 │                   │                 │                  │                 │
 │                   │                 │ execute_task()   │                 │
 │                   │                 │ ❌ Exception!    │                 │
 │                   │                 │                  │                 │
 │                   │                 │ TASK_FAILED      │                 │
 │                   │                 ├─────────────────>│                 │
 │                   │                 │                  │                 │
 │                   │<────────────────┤                  │   EVENT         │
 │                   │                 │                  ├────────────────>│
 │                   │                 │                  │                 │
 │                   │ detect_problem  │                  │    Update UI    │
 │                   │ ┌──────────┐   │                  │   ┌──────────┐  │
 │                   │ │Create    │   │                  │   │❌ Task   │  │
 │                   │ │Problem   │   │                  │   │  Failed  │  │
 │                   │ └──────────┘   │                  │   └──────────┘  │
 │                   │                 │                  │                 │
 │                   │ PROBLEM_DETECTED│                  │                 │
 │                   ├────────────────────────────────────>│                 │
 │                   │                 │                  │                 │
 │                   │                 │                  │   EVENT         │
 │                   │                 │                  ├────────────────>│
 │                   │                 │                  │                 │
 │                   │                 │                  │    Update UI    │
 │                   │                 │                  │   ┌──────────┐  │
 │                   │                 │                  │   │⚠️  Open  │  │
 │                   │                 │                  │   │ Problem  │  │
 │                   │                 │                  │   └──────────┘  │
```

## 🏗️ Diagrama de Clases

```
┌─────────────────────────────────────────────────────────────────┐
│                        <<abstract>>                              │
│                        AgentBase                                 │
├─────────────────────────────────────────────────────────────────┤
│ - agent_id: str                                                  │
│ - event_bus: EventBus                                            │
│ - state_manager: StateManager                                    │
│ - _running: bool                                                 │
│ - _task_queue: Queue                                             │
├─────────────────────────────────────────────────────────────────┤
│ + start(): async                                                 │
│ + stop(): async                                                  │
│ # _log(message, level): async                                    │
│ # _publish_progress(message, progress): async                    │
│ + process_task(task): async <<abstract>>                         │
└──────────────┬──────────────────────────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
       ▼                ▼
┌────────────────┐  ┌────────────────────────────────────────────┐
│ ManagerAgent   │  │         WorkerAgent                        │
├────────────────┤  ├────────────────────────────────────────────┤
│ - workers: List│  │ - file_ops: FileOperations                 │
│ - user_tasks:  │  │ - web_tools: WebTools                      │
│   Queue        │  │ - current_task: Optional[str]              │
├────────────────┤  ├────────────────────────────────────────────┤
│ + add_worker() │  │ + run(): async                             │
│ + submit_user_ │  │ + assign_task(data): async                 │
│   task()       │  │ + process_task(data): async                │
│ + run(): async │  │ - _handle_create_file(): async             │
│ - _process_    │  │ - _handle_read_file(): async               │
│   user_task()  │  │ - _handle_update_file(): async             │
│ - _decompose_  │  │ - _handle_delete_file(): async             │
│   task()       │  │ - _handle_web_request(): async             │
│ - _assign_to_  │  │ - _handle_search_web(): async              │
│   worker()     │  │ - _handle_code_analysis(): async           │
│ - _on_task_    │  │                                            │
│   completed()  │  │                                            │
│ - _on_task_    │  │                                            │
│   failed()     │  │                                            │
│ - _analyze_    │  │                                            │
│   results()    │  │                                            │
└────────────────┘  └────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        EventBus                                  │
├─────────────────────────────────────────────────────────────────┤
│ - _subscribers: Dict[EventType, List[Callable]]                  │
│ - _event_queue: Queue                                            │
│ - _running: bool                                                 │
├─────────────────────────────────────────────────────────────────┤
│ + subscribe(event_type, callback)                                │
│ + publish(event): async                                          │
│ + start(): async                                                 │
│ + stop()                                                         │
│ - _process_event(event): async                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      StateManager                                │
├─────────────────────────────────────────────────────────────────┤
│ - _lock: Lock                                                    │
│ - _tasks: Dict[str, Task]                                        │
│ - _problems: Dict[str, Problem]                                  │
│ - _file_changes: List[FileChange]                                │
│ - _agent_status: Dict[str, str]                                  │
├─────────────────────────────────────────────────────────────────┤
│ + add_task(task): async                                          │
│ + update_task(task_id, **kwargs): async                          │
│ + get_task(task_id): async                                       │
│ + get_all_tasks(): async                                         │
│ + add_problem(problem): async                                    │
│ + get_open_problems(): async                                     │
│ + add_file_change(change): async                                 │
│ + get_recent_file_changes(limit): async                          │
│ + update_agent_status(agent_id, status): async                   │
│ + get_stats(): async                                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     FileOperations                               │
├─────────────────────────────────────────────────────────────────┤
│ - workspace_dir: Path                                            │
├─────────────────────────────────────────────────────────────────┤
│ + create_file(path, content): async                              │
│ + read_file(path): async                                         │
│ + update_file(path, content): async                              │
│ + delete_file(path): async                                       │
│ + list_files(directory): async                                   │
│ + search_files(pattern, directory): async                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        WebTools                                  │
├─────────────────────────────────────────────────────────────────┤
│ - timeout: ClientTimeout                                         │
│ - _session: Optional[ClientSession]                              │
├─────────────────────────────────────────────────────────────────┤
│ + get_request(url, headers): async                               │
│ + post_request(url, data, json_data, headers): async             │
│ + download_file(url, destination): async                         │
│ + search_web(query): async                                       │
│ + close(): async                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      CLIDashboard                                │
├─────────────────────────────────────────────────────────────────┤
│ - event_bus: EventBus                                            │
│ - state_manager: StateManager                                    │
│ - console: Console                                               │
│ - _running: bool                                                 │
│ - _messages: List[Dict]                                          │
├─────────────────────────────────────────────────────────────────┤
│ + run(refresh_rate): async                                       │
│ + stop()                                                         │
│ - _on_event(event): async                                        │
│ - _create_stats_panel(): Panel                                   │
│ - _create_tasks_panel(): Panel                                   │
│ - _create_files_panel(): Panel                                   │
│ - _create_problems_panel(): Panel                                │
│ - _create_activity_panel(): Panel                                │
│ - _generate_layout(): async Layout                               │
└─────────────────────────────────────────────────────────────────┘
```

## 🎯 Diagrama de Estados de Tarea

```
                    ┌──────────────┐
                    │   CREATED    │
                    │  (by User)   │
                    └──────┬───────┘
                           │
                           │ Manager receives
                           │
                           ▼
                    ┌──────────────┐
                    │   PENDING    │◄───────────┐
                    │ (in Manager) │            │
                    └──────┬───────┘            │
                           │                    │
                           │ Decomposed         │ Retry
                           │                    │ (future)
                           ▼                    │
                    ┌──────────────┐            │
                    │  SUBTASKS    │            │
                    │   CREATED    │            │
                    └──────┬───────┘            │
                           │                    │
                           │ Assigned           │
                           │                    │
                           ▼                    │
                    ┌──────────────┐            │
                    │ IN_PROGRESS  │            │
                    │ (by Worker)  │            │
                    └──────┬───────┘            │
                           │                    │
                    ┌──────┴───────┐            │
                    │              │            │
                    ▼              ▼            │
            ┌──────────────┐  ┌──────────────┐ │
            │  COMPLETED   │  │    FAILED    │─┘
            │              │  │              │
            └──────┬───────┘  └──────┬───────┘
                   │                 │
                   │                 │ Problem
                   │                 │ Created
                   ▼                 ▼
            ┌──────────────┐  ┌──────────────┐
            │   ANALYZED   │  │   PROBLEM    │
            │  (by Manager)│  │  REPORTED    │
            └──────────────┘  └──────────────┘
```

## 🔄 Diagrama de Procesamiento Paralelo

```
TIME ────────────────────────────────────────────────────────────────►

MANAGER  [Receive Task A]────┐
                              │
                              └─[Decompose A]──┐
                                               │
                                               └─[Assign A1]──┐
                                                              │
         [Receive Task B]────┐                               │
                              │                              │
                              └─[Decompose B]──┐             │
                                               │             │
                                               └─[Assign B1]─┤
                                                             │
         [Receive Task C]────┐                              │
                              │                              │
                              └─[Decompose C]──┐             │
                                               │             │
                                               └─[Assign C1]─┤
                                                             │
                                                             ▼
WORKER 1                            [Process A1]──────[Complete A1]
                                              │
                                              └──[Process C1]──[Complete C1]

WORKER 2                            [Process B1]──────────[Complete B1]

WORKER 3                            [Idle]───────────────────[Idle]
                                    ▲                        ▲
                                    │                        │
                          Available but no tasks yet   Still available
```

## 📊 Diagrama de Dashboard Layout

```
╔════════════════════════════════════════════════════════════════════╗
║              🤖 Multi-Agent System Dashboard                      ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                     ║
║  ┌─────────────────────┬──────────────────────────────────────┐   ║
║  │  📊 Statistics      │  📋 Recent Tasks                     │   ║
║  ├─────────────────────┼──────────────────────────────────────┤   ║
║  │ Total Tasks:     12 │ ID         Status      Description   │   ║
║  │ ✅ Completed:     8 │ task_abc   ✅ Complete  Create file  │   ║
║  │ ⏳ In Progress:   2 │ task_def   ⏳ Progress  Download     │   ║
║  │ 📋 Pending:       1 │ task_ghi   📋 Pending   Analyze      │   ║
║  │ ❌ Failed:        1 │                                      │   ║
║  │ ⚠️ Problems:      0 │                                      │   ║
║  │ 📝 File Changes:  5 │                                      │   ║
║  └─────────────────────┴──────────────────────────────────────┤   ║
║  │  ⚠️ Open Problems                                          │   ║
║  ├────────────────────────────────────────────────────────────┤   ║
║  │ Severity  Description                Time                  │   ║
║  │ ✅ All Clear - No problems detected                        │   ║
║  └────────────────────────────────────────────────────────────┘   ║
║                                                                     ║
║  ┌─────────────────────────────────────────────────────────────┐  ║
║  │  📁 File Changes                                            │  ║
║  ├─────────────────────────────────────────────────────────────┤  ║
║  │ Time      Action     Path                    Agent          │  ║
║  │ 15:30:42  ➕ created  output/result.txt       worker_01     │  ║
║  │ 15:30:40  ✏️ modified config/settings.json   worker_02     │  ║
║  │ 15:30:38  🗑️ deleted  tmp/cache.txt          worker_03     │  ║
║  └─────────────────────────────────────────────────────────────┘  ║
║                                                                     ║
║  ┌─────────────────────────────────────────────────────────────┐  ║
║  │  📡 Activity Feed                                           │  ║
║  ├─────────────────────────────────────────────────────────────┤  ║
║  │ Time      Source        Message                             │  ║
║  │ 15:30:42  manager_01    ✅ Task completed: task_abc123      │  ║
║  │ 15:30:40  worker_02     📝 File modified: config.json       │  ║
║  │ 15:30:38  worker_01     ▶️ Started: task_abc123_sub_0       │  ║
║  │ 15:30:36  manager_01    📋 Task created: Analyze data       │  ║
║  │ 15:30:34  worker_03     💬 Processing file operations       │  ║
║  └─────────────────────────────────────────────────────────────┘  ║
║                                                                     ║
╠════════════════════════════════════════════════════════════════════╣
║  ⏰ 2026-03-18 15:30:45 | Press Ctrl+C to exit                    ║
╚════════════════════════════════════════════════════════════════════╝
```

---

Estos diagramas ilustran la arquitectura, flujos de trabajo y componentes del sistema multi-agente implementado.
