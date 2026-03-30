# Arquitectura Sistema Multi-Agente Profesional

## 1. PATRÓN DE ARQUITECTURA ELEGIDO

### Patrón Principal: **Supervisor/Manager-Worker con Event-Driven Communication**

**Justificación:**
- Control centralizado con ejecución distribuida (patrón híbrido)
- Observabilidad y debugging simplificados
- Escalabilidad mediante paralelismo controlado
- Recuperación ante fallos con event sourcing

### Componentes Principales

```
┌─────────────────────────────────────────────────────────────┐
│                      USUARIO (CLI)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  AGENTE SENIOR (Manager)                    │
│  - Recibe tareas del usuario                                │
│  - Descompone en subtareas                                  │
│  - Crea prompts para sub-agentes                            │
│  - Monitorea progreso                                       │
│  - Analiza outputs y detecta gaps                           │
│  - Reporta al usuario                                       │
└──────────┬──────────────────────────────────────────────────┘
           │
           │ Publica: TaskCommands
           │ Consume: TaskResults, StatusUpdates
           ▼
┌─────────────────────────────────────────────────────────────┐
│              EVENT BUS / MESSAGE QUEUE                      │
│  Topics:                                                    │
│    - task_commands      (Manager → Workers)                │
│    - task_results       (Workers → Manager)                │
│    - status_updates     (Workers → Dashboard)              │
│    - file_changes       (Workers → FileTracker)            │
└──────────┬──────────────────────────────────────────────────┘
           │
           │ Workers consumen de task_commands
           │ (Consumer Group para balanceo)
           ▼
┌─────────────────────────────────────────────────────────────┐
│                  POOL DE SUB-AGENTES                        │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Worker 1   │  │   Worker 2   │  │   Worker N   │     │
│  │  Especialista│  │  Especialista│  │  Especialista│     │
│  │              │  │              │  │              │     │
│  │ - Recibe     │  │ - Recibe     │  │ - Recibe     │     │
│  │   tarea      │  │   tarea      │  │   tarea      │     │
│  │ - Ejecuta    │  │ - Ejecuta    │  │ - Ejecuta    │     │
│  │ - Reporta    │  │ - Reporta    │  │ - Reporta    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└──────────┬──────────────────────────────────────────────────┘
           │
           │ Acceso a recursos compartidos
           ▼
┌─────────────────────────────────────────────────────────────┐
│                 SHARED STATE LAYER                          │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Workspace  │  │  Event Log   │  │   Memory     │     │
│  │  (Archivos)  │  │  (Historial) │  │   Store      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
           │
           │ Eventos de cambios
           ▼
┌─────────────────────────────────────────────────────────────┐
│                    CLI DASHBOARD                            │
│  - Visualización en tiempo real                            │
│  - Progress tracking                                        │
│  - Lista de problemas                                       │
│  - Archivos modificados                                     │
│  - Logs resumidos                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. COMUNICACIÓN INTER-AGENTES

### 2.1 Protocolo de Mensajes

**Formato Estandarizado (JSON):**

```json
{
  "message_id": "uuid",
  "timestamp": "ISO-8601",
  "message_type": "TASK_COMMAND | TASK_RESULT | STATUS_UPDATE | FILE_CHANGE",
  "sender": {
    "agent_id": "senior | worker-001 | worker-002",
    "agent_type": "manager | worker",
    "agent_specialization": "code_reviewer | file_editor | researcher"
  },
  "recipient": {
    "agent_id": "worker-001 | senior | broadcast",
    "routing_key": "topic partition key"
  },
  "payload": {
    "task_id": "task-uuid",
    "parent_task_id": "parent-uuid | null",
    "priority": "high | medium | low",
    "data": {
      /* Contenido específico del mensaje */
    }
  },
  "metadata": {
    "confidence": 0.95,
    "retry_count": 0,
    "max_retries": 3,
    "timeout_seconds": 300,
    "dependencies": ["task-uuid-1", "task-uuid-2"]
  }
}
```

### 2.2 Tipos de Mensajes

#### TASK_COMMAND (Manager → Worker)
```json
{
  "message_type": "TASK_COMMAND",
  "payload": {
    "task_id": "task-001",
    "task_type": "edit_file | create_file | research | review",
    "data": {
      "objective": "Refactor authentication module",
      "input_files": ["/workspace/auth.py"],
      "output_format": "modified file + summary",
      "constraints": ["preserve existing tests", "maintain API compatibility"],
      "completion_criteria": ["all tests pass", "code coverage >= 80%"]
    }
  },
  "metadata": {
    "budget": {
      "max_iterations": 3,
      "max_tool_calls": 10,
      "timeout_seconds": 600
    }
  }
}
```

#### TASK_RESULT (Worker → Manager)
```json
{
  "message_type": "TASK_RESULT",
  "payload": {
    "task_id": "task-001",
    "status": "completed | failed | partial",
    "data": {
      "summary": "Successfully refactored auth module",
      "files_modified": ["/workspace/auth.py"],
      "files_created": [],
      "test_results": {"passed": 15, "failed": 0},
      "issues_found": [],
      "recommendations": ["Consider adding rate limiting"]
    }
  },
  "metadata": {
    "confidence": 0.92,
    "execution_time_seconds": 45
  }
}
```

#### STATUS_UPDATE (Worker → Dashboard)
```json
{
  "message_type": "STATUS_UPDATE",
  "payload": {
    "task_id": "task-001",
    "status": "in_progress | waiting | blocked",
    "progress_percent": 65,
    "current_step": "Running unit tests",
    "data": {
      "steps_completed": 3,
      "steps_total": 5
    }
  }
}
```

#### FILE_CHANGE (Worker → FileTracker)
```json
{
  "message_type": "FILE_CHANGE",
  "payload": {
    "task_id": "task-001",
    "operation": "create | modify | delete",
    "data": {
      "file_path": "/workspace/auth.py",
      "lines_added": 25,
      "lines_deleted": 10,
      "diff_summary": "Added password validation logic"
    }
  }
}
```

### 2.3 Modelo de Comunicación

**Síncrono vs Asíncrono:**
- **Manager → Worker**: Asíncrono (fire-and-forget con acknowledgment)
- **Worker → Manager**: Asíncrono (event-driven)
- **Worker → Dashboard**: Asíncrono (broadcast)
- **Usuario ↔ Manager**: Síncrono (CLI request-response)

**Implementación:**
- **In-Memory Queue** (desarrollo): Python Queue/asyncio
- **Production-Ready** (escalabilidad): Redis Pub/Sub o RabbitMQ
- **Event Sourcing**: Todos los eventos se persisten para replay

---

## 3. ESTADO COMPARTIDO

### 3.1 Arquitectura de Estado (Blackboard Pattern)

```
┌─────────────────────────────────────────────────────────────┐
│                    SHARED STATE STORE                       │
│                                                             │
│  1. WORKSPACE FILESYSTEM                                    │
│     - /workspace/                                           │
│     - Versionado con Git (opcional)                         │
│     - File watchers para detectar cambios                   │
│                                                             │
│  2. EVENT LOG (Immutable)                                   │
│     - SQLite / JSON Lines file                              │
│     - Todos los mensajes persisten                          │
│     - Permite replay y debugging                            │
│                                                             │
│  3. TASK STATE DATABASE                                     │
│     - SQLite / In-Memory dict                               │
│     - Estado actual de cada tarea                           │
│     - Dependencias entre tareas                             │
│                                                             │
│  4. AGENT MEMORY STORE                                      │
│     - Redis / Python dict                                   │
│     - Context de cada agente                                │
│     - Historial de decisiones                               │
│                                                             │
│  5. FILE CHANGE TRACKER                                     │
│     - Registro de modificaciones                            │
│     - Quien modificó qué y cuándo                           │
│     - Detección de conflictos                               │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Estructura de Datos

#### Task State
```python
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

@dataclass
class Task:
    task_id: str
    parent_task_id: Optional[str]
    task_type: str
    objective: str
    assigned_to: Optional[str]  # agent_id
    status: TaskStatus
    priority: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    # Input/Output
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]

    # Tracking
    dependencies: List[str]  # task_ids
    progress_percent: int
    retry_count: int

    # Metadata
    metadata: Dict[str, Any]
```

#### Agent State
```python
@dataclass
class AgentState:
    agent_id: str
    agent_type: str  # "manager" | "worker"
    specialization: str
    status: str  # "idle" | "busy" | "offline"
    current_task_id: Optional[str]

    # Metrics
    tasks_completed: int
    tasks_failed: int
    average_execution_time: float

    # Context
    memory: Dict[str, Any]
    last_heartbeat: datetime
```

#### File Change Record
```python
@dataclass
class FileChange:
    change_id: str
    task_id: str
    agent_id: str
    file_path: str
    operation: str  # "create" | "modify" | "delete"
    timestamp: datetime

    # Details
    lines_added: int
    lines_deleted: int
    diff_summary: str

    # Conflict detection
    concurrent_modifications: List[str]  # change_ids
```

### 3.3 Logging Centralizado

**Estructura de Log Entry:**
```python
@dataclass
class LogEntry:
    log_id: str
    timestamp: datetime
    level: str  # "DEBUG" | "INFO" | "WARNING" | "ERROR"
    source: str  # agent_id
    task_id: Optional[str]
    message: str
    context: Dict[str, Any]
```

**Almacenamiento:**
- **JSON Lines** para desarrollo
- **SQLite** para queries eficientes
- **Elasticsearch** para producción a escala

---

## 4. ORQUESTACIÓN

### 4.1 Estrategia de Orquestación

**Modelo Híbrido:**
- **Control**: Centralizado (Manager decide qué hacer)
- **Ejecución**: Paralela (Workers ejecutan simultáneamente)
- **Coordinación**: Event-driven (Workers autónomos, reportan vía eventos)

### 4.2 Asignación de Tareas

**Manager Decision Logic:**
```python
def assign_task(task: Task) -> str:
    """
    Selecciona worker apropiado basándose en:
    1. Especialización (match con task_type)
    2. Disponibilidad (status == idle)
    3. Performance histórico (success rate)
    4. Carga actual (queue depth)
    """
    available_workers = get_available_workers(task.task_type)
    best_worker = select_by_criteria(
        available_workers,
        criteria=["specialization_match", "idle_status", "success_rate"]
    )
    return best_worker.agent_id
```

### 4.3 Manejo de Dependencias

**Dependency Graph:**
```python
class TaskDependencyGraph:
    def __init__(self):
        self.graph: Dict[str, List[str]] = {}

    def add_dependency(self, task_id: str, depends_on: str):
        """task_id depende de depends_on"""
        if task_id not in self.graph:
            self.graph[task_id] = []
        self.graph[task_id].append(depends_on)

    def can_execute(self, task_id: str) -> bool:
        """Verifica si todas las dependencias están completadas"""
        dependencies = self.graph.get(task_id, [])
        return all(
            get_task_status(dep_id) == TaskStatus.COMPLETED
            for dep_id in dependencies
        )

    def get_ready_tasks(self) -> List[str]:
        """Retorna tareas listas para ejecutar"""
        return [
            task_id for task_id in self.graph.keys()
            if self.can_execute(task_id)
        ]
```

### 4.4 Paralelismo vs Secuencial

**Reglas de Ejecución:**
1. **Paralelo por defecto**: Tareas sin dependencias se ejecutan simultáneamente
2. **Secuencial cuando necesario**: Dependencias fuerzan orden
3. **Límite de concurrencia**: Max workers simultáneos configurables
4. **Budget enforcement**: Límites de iteraciones y tiempo

---

## 5. MANEJO DE ERRORES Y RECUPERACIÓN

### 5.1 Estrategias de Retry

```python
class RetryStrategy:
    max_retries: int = 3
    retry_delay_seconds: int = 5
    exponential_backoff: bool = True

    def should_retry(self, task: Task, error: Exception) -> bool:
        if task.retry_count >= self.max_retries:
            return False

        # No reintentar errores permanentes
        if isinstance(error, PermanentError):
            return False

        return True

    def get_retry_delay(self, retry_count: int) -> int:
        if self.exponential_backoff:
            return self.retry_delay_seconds * (2 ** retry_count)
        return self.retry_delay_seconds
```

### 5.2 Manejo de Timeouts

- **Task-level timeout**: Cada tarea tiene timeout configurado
- **Worker heartbeat**: Workers envían heartbeat cada 30s
- **Dead worker detection**: Manager detecta workers sin heartbeat
- **Task reassignment**: Tareas de workers muertos se reasignan

### 5.3 Conflictos de Archivos

**Estrategias:**
1. **File Locking**: Bloqueo optimista con timestamps
2. **Conflict Detection**: Detectar modificaciones concurrentes
3. **Automatic Merge**: Merge automático cuando posible
4. **Escalation**: Notificar Manager para resolución manual

```python
class FileConflictResolver:
    def detect_conflict(self, file_path: str, changes: List[FileChange]) -> bool:
        """Detecta si múltiples agentes modificaron el mismo archivo"""
        recent_changes = [
            c for c in changes
            if (datetime.now() - c.timestamp).seconds < 60
        ]
        return len(recent_changes) > 1

    def resolve_conflict(self, file_path: str, changes: List[FileChange]):
        """Intenta resolver conflicto o escala"""
        if can_auto_merge(changes):
            merge_changes(file_path, changes)
        else:
            escalate_to_manager(file_path, changes)
```

### 5.4 Failure Isolation

**Principios:**
- **Fail Fast**: Detectar fallos rápidamente
- **Fail Local**: Errores de un worker no afectan otros
- **Graceful Degradation**: Sistema continúa con capacidad reducida
- **Circuit Breaker**: Detener workers con fallos repetidos

---

## 6. ESCALABILIDAD Y EXTENSIBILIDAD

### 6.1 Puntos de Extensión

1. **Custom Agent Types**: Interfaz para nuevos agentes especializados
2. **Custom Message Types**: Extensión del protocolo de mensajes
3. **Custom State Stores**: Backends alternativos de almacenamiento
4. **Custom Dashboards**: Múltiples vistas (web, CLI, logs)

### 6.2 Escalamiento Horizontal

**Workers:**
- Añadir workers dinámicamente sin restart
- Consumer groups para balanceo automático
- Auto-scaling basado en queue depth

**State:**
- Migración a bases de datos distribuidas (PostgreSQL, Redis Cluster)
- Sharding por task_id o agent_id
- Replicación para alta disponibilidad

### 6.3 Configuración Modular

```yaml
# config.yaml
system:
  name: "MultiAgentSystem"
  mode: "development"  # development | production

manager:
  agent_id: "senior-manager-001"
  max_concurrent_tasks: 10
  task_timeout_default: 300

workers:
  pool_size: 5
  auto_scale:
    enabled: true
    min_workers: 2
    max_workers: 20
    scale_up_threshold: 0.8  # queue utilization
    scale_down_threshold: 0.2

communication:
  backend: "inmemory"  # inmemory | redis | rabbitmq
  message_retention_hours: 24

state:
  workspace_path: "/workspace"
  event_log_path: "/workspace/.multiagent/event_log.jsonl"
  database_type: "sqlite"  # sqlite | postgresql

error_handling:
  max_retries: 3
  retry_delay_seconds: 5
  exponential_backoff: true
  dead_worker_timeout_seconds: 120

dashboard:
  refresh_interval_ms: 500
  show_debug_logs: false
  max_visible_tasks: 20
```

---

## 7. CONSIDERACIONES DE SEGURIDAD

1. **Aislamiento de Workers**: Sandboxing para ejecución de código
2. **Validación de Mensajes**: Schema validation para todos los mensajes
3. **Rate Limiting**: Prevenir abuse de recursos
4. **Auditoría**: Log completo de todas las acciones
5. **Permisos**: Control de acceso a archivos por agente

---

## PRÓXIMOS PASOS

1. [x] Diseño de arquitectura completo
2. [ ] Diagrama Mermaid visual
3. [ ] Mockup del CLI Dashboard
4. [ ] Implementación del código base
5. [ ] Documentación de API
6. [ ] Ejemplos de uso
