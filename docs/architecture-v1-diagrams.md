# Diagramas de Arquitectura - Sistema Multi-Agente

## 1. Arquitectura General del Sistema

```mermaid
graph TB
    subgraph "USER INTERFACE"
        CLI[CLI Dashboard<br/>- Real-time updates<br/>- Task tracking<br/>- File changes<br/>- Problem list]
        User[Usuario]
    end

    subgraph "ORCHESTRATION LAYER"
        Manager[Senior Agent / Manager<br/>- Task decomposition<br/>- Progress monitoring<br/>- Gap analysis<br/>- User reporting]
    end

    subgraph "COMMUNICATION LAYER"
        EventBus[Event Bus / Message Queue<br/>Topics:<br/>• task_commands<br/>• task_results<br/>• status_updates<br/>• file_changes]
    end

    subgraph "EXECUTION LAYER"
        W1[Worker 1<br/>Code Editor]
        W2[Worker 2<br/>Researcher]
        W3[Worker 3<br/>Reviewer]
        WN[Worker N<br/>Specialist]
    end

    subgraph "STATE LAYER"
        WS[Workspace<br/>File System]
        EL[Event Log<br/>Immutable History]
        TS[Task State<br/>Database]
        MS[Memory Store<br/>Agent Context]
        FC[File Change<br/>Tracker]
    end

    User -->|Commands| CLI
    CLI <-->|Sync| Manager
    Manager -->|Publish Tasks| EventBus
    EventBus -->|Consume| W1
    EventBus -->|Consume| W2
    EventBus -->|Consume| W3
    EventBus -->|Consume| WN
    W1 -->|Publish Results| EventBus
    W2 -->|Publish Results| EventBus
    W3 -->|Publish Results| EventBus
    WN -->|Publish Results| EventBus
    EventBus -->|Status Updates| CLI
    EventBus -->|Results| Manager

    W1 <-->|Read/Write| WS
    W2 <-->|Read/Write| WS
    W3 <-->|Read/Write| WS
    WN <-->|Read/Write| WS

    Manager -->|Log Events| EL
    W1 -->|Log Events| EL
    W2 -->|Log Events| EL
    W3 -->|Log Events| EL
    WN -->|Log Events| EL

    Manager <-->|Task State| TS
    W1 -->|Update State| TS
    W2 -->|Update State| TS
    W3 -->|Update State| TS
    WN -->|Update State| TS

    Manager <-->|Context| MS
    W1 <-->|Context| MS
    W2 <-->|Context| MS
    W3 <-->|Context| MS
    WN <-->|Context| MS

    W1 -->|Track Changes| FC
    W2 -->|Track Changes| FC
    W3 -->|Track Changes| FC
    WN -->|Track Changes| FC
    FC -->|Conflict Alerts| Manager

    style Manager fill:#ff6b6b,stroke:#c92a2a,color:#fff
    style W1 fill:#4ecdc4,stroke:#0b7285,color:#fff
    style W2 fill:#4ecdc4,stroke:#0b7285,color:#fff
    style W3 fill:#4ecdc4,stroke:#0b7285,color:#fff
    style WN fill:#4ecdc4,stroke:#0b7285,color:#fff
    style EventBus fill:#ffd43b,stroke:#f59f00,color:#000
    style CLI fill:#a5d8ff,stroke:#1864ab,color:#000
```

## 2. Flujo de Comunicación Entre Agentes

```mermaid
sequenceDiagram
    participant U as Usuario
    participant CLI as CLI Dashboard
    participant M as Senior Manager
    participant EB as Event Bus
    participant W1 as Worker 1
    participant W2 as Worker 2
    participant ST as State Store

    U->>CLI: Solicita tarea compleja
    CLI->>M: Forward request
    M->>M: Descompone en subtareas
    M->>ST: Registra tareas
    M->>EB: Publica TASK_COMMAND (T1)
    M->>EB: Publica TASK_COMMAND (T2)

    Note over EB,W2: Consumer Group - Balanceo automático

    EB->>W1: Consume T1
    EB->>W2: Consume T2

    W1->>ST: Actualiza estado (IN_PROGRESS)
    W2->>ST: Actualiza estado (IN_PROGRESS)

    W1->>EB: Publica STATUS_UPDATE
    W2->>EB: Publica STATUS_UPDATE
    EB->>CLI: Forward status
    CLI->>U: Muestra progreso

    W1->>ST: Lee/Escribe archivos
    W1->>ST: Registra cambios
    W2->>ST: Lee/Escribe archivos
    W2->>ST: Registra cambios

    W1->>EB: Publica TASK_RESULT
    W2->>EB: Publica TASK_RESULT

    EB->>M: Consume results
    M->>M: Analiza outputs
    M->>M: Detecta gaps
    M->>ST: Actualiza estado global

    alt Requiere trabajo adicional
        M->>EB: Publica nueva TASK_COMMAND
        EB->>W1: Asigna nueva tarea
    else Todo completo
        M->>CLI: Reporte final
        CLI->>U: Muestra resultado
    end
```

## 3. Estados de Tarea (State Machine)

```mermaid
stateDiagram-v2
    [*] --> PENDING: Task creada
    PENDING --> IN_PROGRESS: Worker asignado
    PENDING --> BLOCKED: Dependencia no resuelta

    IN_PROGRESS --> COMPLETED: Ejecución exitosa
    IN_PROGRESS --> FAILED: Error fatal
    IN_PROGRESS --> BLOCKED: Dependencia bloqueada
    IN_PROGRESS --> IN_PROGRESS: Retry después de error

    BLOCKED --> PENDING: Dependencia resuelta
    BLOCKED --> CANCELLED: Timeout o usuario cancela

    FAILED --> PENDING: Retry programado
    FAILED --> CANCELLED: Max retries alcanzado

    COMPLETED --> [*]
    CANCELLED --> [*]

    note right of IN_PROGRESS
        - Heartbeat activo
        - Progress updates
        - File changes tracked
    end note

    note right of FAILED
        - Retry count < max_retries
        - Exponential backoff
        - Error logged
    end note

    note right of BLOCKED
        - Waiting for dependencies
        - Conflict detected
        - Resource unavailable
    end note
```

## 4. Arquitectura de Componentes

```mermaid
graph LR
    subgraph "Core Components"
        MC[Message Coordinator]
        TM[Task Manager]
        AM[Agent Manager]
        SM[State Manager]
    end

    subgraph "Manager Agent"
        TP[Task Planner]
        RG[Result Gatherer]
        GA[Gap Analyzer]
        UR[User Reporter]
    end

    subgraph "Worker Agent"
        TR[Task Receiver]
        TE[Task Executor]
        RR[Result Reporter]
        SU[Status Updater]
    end

    subgraph "Infrastructure"
        MB[Message Bus]
        DB[(Database)]
        FS[File System]
        LG[Logger]
    end

    MC --> MB
    TM --> DB
    AM --> MB
    SM --> DB
    SM --> FS

    TP --> MC
    RG --> MC
    GA --> SM
    UR --> MC

    TR --> MC
    TE --> FS
    RR --> MC
    SU --> MC

    MB --> LG
    DB --> LG
    FS --> LG

    style MC fill:#ffec99,stroke:#fcc419
    style TM fill:#ffec99,stroke:#fcc419
    style AM fill:#ffec99,stroke:#fcc419
    style SM fill:#ffec99,stroke:#fcc419
    style MB fill:#d0bfff,stroke:#9775fa
    style DB fill:#d0bfff,stroke:#9775fa
    style FS fill:#d0bfff,stroke:#9775fa
```

## 5. Flujo de Trabajo Detallado

```mermaid
flowchart TD
    Start([Usuario inicia tarea]) --> ManagerReceive[Manager recibe solicitud]
    ManagerReceive --> Analyze[Analiza complejidad]
    Analyze --> Decision{¿Tarea simple<br/>o compleja?}

    Decision -->|Simple| DirectExec[Ejecuta directamente]
    Decision -->|Compleja| Decompose[Descompone en subtareas]

    Decompose --> CreateGraph[Crea dependency graph]
    CreateGraph --> PrioritizeTasks[Prioriza tareas]
    PrioritizeTasks --> PublishTasks[Publica tasks a Event Bus]

    PublishTasks --> WorkerPool{Pool de Workers}
    WorkerPool -->|Task 1| W1[Worker 1 ejecuta]
    WorkerPool -->|Task 2| W2[Worker 2 ejecuta]
    WorkerPool -->|Task N| WN[Worker N ejecuta]

    W1 --> CheckDeps1{¿Dependencias<br/>satisfechas?}
    W2 --> CheckDeps2{¿Dependencias<br/>satisfechas?}
    WN --> CheckDepsN{¿Dependencias<br/>satisfechas?}

    CheckDeps1 -->|No| Block1[Bloquea tarea]
    CheckDeps2 -->|No| Block2[Bloquea tarea]
    CheckDepsN -->|No| BlockN[Bloquea tarea]

    CheckDeps1 -->|Sí| Execute1[Ejecuta tarea]
    CheckDeps2 -->|Sí| Execute2[Ejecuta tarea]
    CheckDepsN -->|Sí| ExecuteN[Ejecuta tarea]

    Execute1 --> Success1{¿Éxito?}
    Execute2 --> Success2{¿Éxito?}
    ExecuteN --> SuccessN{¿Éxito?}

    Success1 -->|No| Retry1{¿Retry<br/>disponible?}
    Success2 -->|No| Retry2{¿Retry<br/>disponible?}
    SuccessN -->|No| RetryN{¿Retry<br/>disponible?}

    Retry1 -->|Sí| Execute1
    Retry2 -->|Sí| Execute2
    RetryN -->|Sí| ExecuteN

    Retry1 -->|No| FailTask1[Marca como FAILED]
    Retry2 -->|No| FailTask2[Marca como FAILED]
    RetryN -->|No| FailTaskN[Marca como FAILED]

    Success1 -->|Sí| Result1[Publica resultado]
    Success2 -->|Sí| Result2[Publica resultado]
    SuccessN -->|Sí| ResultN[Publica resultado]

    Result1 --> Gather[Manager recopila resultados]
    Result2 --> Gather
    ResultN --> Gather
    FailTask1 --> Gather
    FailTask2 --> Gather
    FailTaskN --> Gather

    Gather --> AnalyzeResults[Analiza outputs]
    AnalyzeResults --> GapCheck{¿Gaps o<br/>problemas?}

    GapCheck -->|Sí| CreateFollowUp[Crea tareas adicionales]
    CreateFollowUp --> PublishTasks

    GapCheck -->|No| Synthesize[Sintetiza resultado final]
    Synthesize --> Report[Reporta a usuario]
    DirectExec --> Report

    Report --> End([Fin])

    style Start fill:#b197fc,stroke:#7950f2,color:#fff
    style End fill:#51cf66,stroke:#2f9e44,color:#fff
    style ManagerReceive fill:#ff8787,stroke:#fa5252
    style Gather fill:#ff8787,stroke:#fa5252
    style W1 fill:#74c0fc,stroke:#339af0
    style W2 fill:#74c0fc,stroke:#339af0
    style WN fill:#74c0fc,stroke:#339af0
```

## 6. Arquitectura de Datos (State Management)

```mermaid
erDiagram
    TASK ||--o{ TASK : "depends on"
    TASK ||--|| AGENT : "assigned to"
    TASK ||--o{ FILE_CHANGE : "produces"
    TASK ||--o{ LOG_ENTRY : "generates"
    AGENT ||--o{ FILE_CHANGE : "creates"
    AGENT ||--o{ LOG_ENTRY : "writes"
    AGENT ||--|| AGENT_STATE : "has"

    TASK {
        string task_id PK
        string parent_task_id FK
        string task_type
        string objective
        string status
        string assigned_to FK
        int priority
        datetime created_at
        datetime completed_at
        json input_data
        json output_data
        int progress_percent
        int retry_count
    }

    AGENT {
        string agent_id PK
        string agent_type
        string specialization
        string status
        int tasks_completed
        int tasks_failed
        float avg_execution_time
    }

    AGENT_STATE {
        string agent_id PK
        string current_task_id FK
        json memory
        datetime last_heartbeat
    }

    FILE_CHANGE {
        string change_id PK
        string task_id FK
        string agent_id FK
        string file_path
        string operation
        datetime timestamp
        int lines_added
        int lines_deleted
        string diff_summary
    }

    LOG_ENTRY {
        string log_id PK
        datetime timestamp
        string level
        string source FK
        string task_id FK
        string message
        json context
    }
```

## 7. Estrategia de Error Handling

```mermaid
flowchart TD
    ErrorOccurs([Error detectado]) --> ClassifyError{Clasificar error}

    ClassifyError -->|Transient| TransientPath[Error transitorio]
    ClassifyError -->|Permanent| PermanentPath[Error permanente]
    ClassifyError -->|Unknown| UnknownPath[Error desconocido]

    TransientPath --> CheckRetries{¿Retries<br/>disponibles?}
    CheckRetries -->|Sí| ExponentialBackoff[Espera con<br/>exponential backoff]
    ExponentialBackoff --> RetryTask[Reintenta tarea]
    RetryTask --> Success{¿Éxito?}
    Success -->|Sí| MarkComplete[Marca COMPLETED]
    Success -->|No| ErrorOccurs

    CheckRetries -->|No| MaxRetriesReached[Max retries alcanzado]

    PermanentPath --> LogError[Registra error detallado]
    MaxRetriesReached --> LogError
    UnknownPath --> LogError

    LogError --> NotifyManager[Notifica a Manager]
    NotifyManager --> ManagerDecision{Manager decide}

    ManagerDecision -->|Reassign| ReassignWorker[Reasigna a otro worker]
    ManagerDecision -->|Escalate| EscalateUser[Escala a usuario]
    ManagerDecision -->|Skip| SkipTask[Marca como CANCELLED]

    ReassignWorker --> PublishNewTask[Publica nueva task]
    PublishNewTask --> Success

    EscalateUser --> UserAction[Usuario toma acción]
    SkipTask --> UpdateDeps[Actualiza dependencias]

    MarkComplete --> End([Fin])
    UserAction --> End
    UpdateDeps --> End

    style ErrorOccurs fill:#ff6b6b,stroke:#c92a2a,color:#fff
    style MarkComplete fill:#51cf66,stroke:#2f9e44,color:#fff
    style End fill:#51cf66,stroke:#2f9e44,color:#fff
    style TransientPath fill:#ffd43b,stroke:#f59f00
    style PermanentPath fill:#ff8787,stroke:#fa5252
```

---

## Próximos Pasos

1. [x] Diagramas de arquitectura completos
2. [ ] Mockup del CLI Dashboard
3. [ ] Implementación del código base
