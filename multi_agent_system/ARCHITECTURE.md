# Arquitectura del Sistema Multi-Agente

## 📐 Diseño General

El sistema implementa un patrón de arquitectura **Manager-Worker** con comunicación asíncrona basada en eventos.

```
┌─────────────────────────────────────────────────────────────────┐
│                         USUARIO                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MANAGER AGENT                                 │
│  • Recibe tareas                                                │
│  • Descompone en subtareas                                      │
│  • Asigna a workers                                             │
│  • Analiza resultados                                           │
│  • Detecta problemas                                            │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ├──────────────┬──────────────┬──────────────┐
           ▼              ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
    │ Worker 1 │   │ Worker 2 │   │ Worker 3 │   │ Worker N │
    │          │   │          │   │          │   │          │
    │ • Files  │   │ • Files  │   │ • Files  │   │ • Files  │
    │ • Web    │   │ • Web    │   │ • Web    │   │ • Web    │
    │ • Code   │   │ • Code   │   │ • Code   │   │ • Code   │
    └──────────┘   └──────────┘   └──────────┘   └──────────┘
           │              │              │              │
           └──────────────┴──────────────┴──────────────┘
                         │
                         ▼
           ┌─────────────────────────────┐
           │      EVENT BUS              │
           │  (Comunicación Asíncrona)   │
           └─────────────────────────────┘
                         │
                         ▼
           ┌─────────────────────────────┐
           │    STATE MANAGER            │
           │  (Estado Compartido)        │
           └─────────────────────────────┘
                         │
                         ▼
           ┌─────────────────────────────┐
           │    CLI DASHBOARD            │
           │  (Visualización Real-Time)  │
           └─────────────────────────────┘
```

## 🏗️ Componentes Principales

### 1. EventBus (Sistema de Eventos)

**Ubicación**: `core/event_bus.py`

**Responsabilidad**: Comunicación desacoplada entre componentes

```python
class EventBus:
    - subscribe(event_type, callback)    # Suscribirse a eventos
    - publish(event)                      # Publicar eventos
    - start()                             # Iniciar procesamiento
    - stop()                              # Detener procesamiento
```

**Tipos de Eventos**:
- `TASK_CREATED`: Nueva tarea creada
- `TASK_ASSIGNED`: Tarea asignada a worker
- `TASK_STARTED`: Worker inicia tarea
- `TASK_COMPLETED`: Tarea completada exitosamente
- `TASK_FAILED`: Tarea fallida
- `FILE_MODIFIED`: Archivo modificado
- `PROBLEM_DETECTED`: Problema detectado
- `PROGRESS_UPDATE`: Actualización de progreso
- `AGENT_MESSAGE`: Mensaje de agente

**Flujo de Eventos**:
```
[Manager] --TASK_CREATED--> [EventBus] --> [Dashboard]
[Manager] --TASK_ASSIGNED--> [EventBus] --> [Dashboard]
[Worker]  --TASK_STARTED--> [EventBus] --> [Dashboard, Manager]
[Worker]  --FILE_MODIFIED--> [EventBus] --> [Dashboard, StateManager]
[Worker]  --TASK_COMPLETED--> [EventBus] --> [Manager, Dashboard]
```

### 2. StateManager (Gestor de Estado)

**Ubicación**: `core/state_manager.py`

**Responsabilidad**: Mantener estado compartido thread-safe

```python
class StateManager:
    - add_task(task)                      # Agregar tarea
    - update_task(task_id, **kwargs)      # Actualizar tarea
    - get_task(task_id)                   # Obtener tarea
    - get_all_tasks()                     # Obtener todas las tareas
    - add_problem(problem)                # Registrar problema
    - get_open_problems()                 # Obtener problemas abiertos
    - add_file_change(change)             # Registrar cambio de archivo
    - get_stats()                         # Obtener estadísticas
```

**Estructuras de Datos**:
```python
Task:
    - id: str
    - description: str
    - status: TaskStatus (PENDING, IN_PROGRESS, COMPLETED, FAILED)
    - assigned_to: Optional[str]
    - created_at, started_at, completed_at: datetime
    - result: Dict
    - parent_task_id: Optional[str]
    - subtasks: List[str]

Problem:
    - id: str
    - description: str
    - severity: str (low, medium, high)
    - detected_at: datetime
    - resolved: bool

FileChange:
    - path: str
    - action: str (created, modified, deleted)
    - timestamp: datetime
    - agent: str
```

### 3. AgentBase (Clase Base de Agentes)

**Ubicación**: `core/agent_base.py`

**Responsabilidad**: Interface común para todos los agentes

```python
class AgentBase(ABC):
    - start()                             # Iniciar agente
    - stop()                              # Detener agente
    - _log(message, level)                # Enviar log
    - _publish_progress(message, progress)# Publicar progreso
    - process_task(task)                  # [Abstracto] Procesar tarea
```

### 4. ManagerAgent (Agente Manager)

**Ubicación**: `core/manager_agent.py`

**Responsabilidad**: Coordinar workers y gestionar flujo de tareas

```python
class ManagerAgent(AgentBase):
    - submit_user_task(description)       # Recibir tarea del usuario
    - run()                               # Loop principal
    - add_worker(worker)                  # Agregar worker al pool

    # Privados
    - _process_user_task(task_data)       # Procesar tarea
    - _decompose_task(task)               # Descomponer en subtareas
    - _assign_to_worker(task_id, spec)    # Asignar a worker
    - _on_task_completed(event)           # Manejar completado
    - _on_task_failed(event)              # Manejar fallo
    - _check_parent_completion(task)      # Verificar completado
    - _analyze_results(task)              # Analizar resultados
```

**Estrategia de Descomposición**:

El manager analiza la descripción de la tarea y la descompone usando patrones:

```python
"Create file" → create_file task
"Analyze" → code_analysis task
"Search" / "Find" → search_web task
"Download" → web_request task
```

**Asignación de Workers**:
- Estrategia: Round-robin basado en hash del task_id
- Balance de carga: Distribuye uniformemente entre workers disponibles

### 5. WorkerAgent (Agentes Worker)

**Ubicación**: `core/worker_agent.py`

**Responsabilidad**: Ejecutar tareas específicas

```python
class WorkerAgent(AgentBase):
    - run()                               # Loop principal
    - assign_task(task_data)              # Recibir tarea
    - process_task(task_data)             # Procesar tarea

    # Handlers específicos
    - _handle_create_file(params)         # Crear archivo
    - _handle_read_file(params)           # Leer archivo
    - _handle_update_file(params)         # Actualizar archivo
    - _handle_delete_file(params)         # Eliminar archivo
    - _handle_web_request(params)         # Petición web
    - _handle_search_web(params)          # Búsqueda web
    - _handle_code_analysis(params)       # Análisis de código
```

**Tipos de Tareas Soportadas**:
1. **Operaciones de Archivos**: create, read, update, delete
2. **Operaciones Web**: GET/POST requests, search, download
3. **Análisis**: Code analysis, data processing

### 6. FileOperations (Operaciones de Archivos)

**Ubicación**: `tools/file_operations.py`

**Responsabilidad**: Operaciones de I/O asíncronas

```python
class FileOperations:
    - create_file(path, content)          # Crear archivo
    - read_file(path)                     # Leer archivo
    - update_file(path, content)          # Actualizar archivo
    - delete_file(path)                   # Eliminar archivo
    - list_files(directory)               # Listar archivos
    - search_files(pattern, directory)    # Buscar archivos
```

**Características**:
- Workspace aislado: `/workspace/agent_workspace`
- I/O asíncrono usando `asyncio.run_in_executor`
- Manejo de errores robusto
- Creación automática de directorios

### 7. WebTools (Herramientas Web)

**Ubicación**: `tools/web_tools.py`

**Responsabilidad**: Acceso a internet

```python
class WebTools:
    - get_request(url, headers)           # GET request
    - post_request(url, data, json_data)  # POST request
    - download_file(url, destination)     # Descargar archivo
    - search_web(query)                   # Búsqueda web
    - close()                             # Cerrar sesión
```

**Características**:
- Cliente HTTP asíncrono con `aiohttp`
- Timeout configurable
- Reutilización de sesión HTTP
- Soporte para headers personalizados

### 8. CLIDashboard (Dashboard Visual)

**Ubicación**: `dashboard/cli_dashboard.py`

**Responsabilidad**: Visualización en tiempo real

```python
class CLIDashboard:
    - run(refresh_rate)                   # Ejecutar dashboard
    - stop()                              # Detener dashboard

    # Panels
    - _create_stats_panel()               # Panel de estadísticas
    - _create_tasks_panel()               # Panel de tareas
    - _create_files_panel()               # Panel de archivos
    - _create_problems_panel()            # Panel de problemas
    - _create_activity_panel()            # Panel de actividad
```

**Características**:
- Actualización en tiempo real (1 segundo por defecto)
- 5 paneles informativos
- Colores y emojis para mejor legibilidad
- Suscripción a todos los eventos del sistema

## 🔄 Flujos de Trabajo

### Flujo 1: Creación y Ejecución de Tarea

```
1. Usuario → Manager.submit_user_task("Create file")
2. Manager crea Task (PENDING)
3. Manager publica TASK_CREATED
4. Manager descompone en subtareas
5. Manager crea Subtask (PENDING)
6. Manager asigna a Worker
7. Manager publica TASK_ASSIGNED
8. Worker recibe tarea en cola
9. Worker actualiza Task (IN_PROGRESS)
10. Worker publica TASK_STARTED
11. Worker ejecuta operación (file_ops.create_file)
12. Worker registra FileChange
13. Worker publica FILE_MODIFIED
14. Worker actualiza Task (COMPLETED)
15. Worker publica TASK_COMPLETED
16. Manager recibe evento TASK_COMPLETED
17. Manager verifica si todas las subtareas están completas
18. Manager analiza resultados
19. Manager actualiza tarea padre (COMPLETED)
20. Dashboard refleja todos los cambios en tiempo real
```

### Flujo 2: Detección de Problemas

```
1. Worker intenta ejecutar tarea
2. Ocurre excepción (ej: archivo no encontrado)
3. Worker actualiza Task (FAILED)
4. Worker publica TASK_FAILED con error
5. Manager recibe TASK_FAILED
6. Manager crea Problem (severity: high)
7. Manager publica PROBLEM_DETECTED
8. StateManager registra Problem
9. Dashboard muestra problema en panel
10. Manager marca tarea padre como FAILED
```

### Flujo 3: Procesamiento Paralelo

```
Manager recibe 4 tareas simultáneas:

Tarea A → Subtarea A1 → Worker 1 (ejecuta en paralelo)
Tarea B → Subtarea B1 → Worker 2 (ejecuta en paralelo)
Tarea C → Subtarea C1 → Worker 3 (ejecuta en paralelo)
Tarea D → Subtarea D1 → Worker 1 (cola, espera)

Workers procesan de manera asíncrona e independiente.
Manager coordina sin bloquear.
EventBus distribuye eventos a todos los suscriptores.
```

## 🎯 Patrones de Diseño Implementados

### 1. Observer Pattern (EventBus)
- Suscriptores reciben notificaciones de eventos
- Desacoplamiento entre productores y consumidores

### 2. Command Pattern (Tasks)
- Tareas encapsulan operaciones como objetos
- Facilita queuing, logging, undo

### 3. Strategy Pattern (Task Types)
- Diferentes estrategias de ejecución según tipo de tarea
- Extensible para nuevos tipos

### 4. Singleton Pattern (StateManager, EventBus)
- Estado compartido único
- Punto central de comunicación

### 5. Factory Pattern (Task Creation)
- Manager crea tareas basado en descripción
- Abstrae lógica de creación

## 🔐 Concurrencia y Sincronización

### AsyncIO
- Todo el sistema es asíncrono usando `asyncio`
- No bloquea threads
- Eficiente para I/O-bound tasks

### Thread-Safety
- `StateManager` usa `asyncio.Lock` para proteger estado
- Operaciones atómicas
- Sin race conditions

### Queues
- Manager y Workers usan `asyncio.Queue`
- FIFO para procesamiento ordenado
- Backpressure automático

## 📊 Complejidad y Performance

### Escalabilidad
- **Workers**: O(1) para agregar workers
- **Tasks**: O(n) donde n = número de tareas
- **Events**: O(m) donde m = número de suscriptores

### Latencia
- Event propagation: ~1-10ms
- Task assignment: ~1-5ms
- File operations: ~10-100ms (I/O bound)
- Web requests: ~100-1000ms (network bound)

### Throughput
- Puede procesar decenas de tareas por segundo
- Limitado por I/O, no por CPU
- Escalable horizontalmente agregando workers

## 🛡️ Manejo de Errores

### Niveles de Manejo

1. **Worker Level**: Try-catch en cada handler
2. **Task Level**: Estado FAILED + error message
3. **Manager Level**: Problem detection + logging
4. **System Level**: Graceful shutdown en signals

### Recovery Strategies

- **Retry**: No implementado (futuro)
- **Fallback**: Tarea marcada como FAILED
- **Circuit Breaker**: No implementado (futuro)
- **Timeout**: Configurado en web requests

## 🚀 Extensibilidad

### Agregar Nuevo Tipo de Tarea

1. Definir tipo en Manager: `_decompose_task()`
2. Implementar handler en Worker: `_handle_nuevo_tipo()`
3. Agregar caso en `process_task()`

### Agregar Nueva Herramienta

1. Crear clase en `tools/`
2. Inyectar en WorkerAgent
3. Usar en handlers

### Agregar Nuevo Panel en Dashboard

1. Crear método `_create_nuevo_panel()`
2. Agregar a layout en `_generate_layout()`

## 📈 Métricas y Monitoreo

### Métricas Disponibles

- Total tasks, completed, failed, in progress, pending
- Open problems count
- File changes count
- Agent status (active, idle, stopped)

### Logging

- Agent messages con niveles (info, warning, error)
- Activity feed en dashboard
- Timestamps para auditoría

## 🔮 Futuras Mejoras

### Corto Plazo
- Retry automático de tareas fallidas
- Priorización de tareas
- Persistencia de estado (SQLite)

### Medio Plazo
- API REST para control remoto
- Dashboard web (React/Vue)
- Métricas avanzadas (Prometheus)

### Largo Plazo
- ML para optimización de asignación
- Auto-scaling de workers
- Distributed execution (multi-node)
