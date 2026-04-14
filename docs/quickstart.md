# Guía Rápida - Sistema Multi-Agente

## 🚀 Inicio Rápido (5 minutos)

### 1. Instalación

```bash
cd /workspace/multi_agent_system
pip install -r requirements.txt
```

### 2. Ejecutar Demo Básica

```bash
python demo_simple.py
```

Verás el sistema procesando 4 tareas automáticamente y mostrando resultados.

### 3. Ejecutar con Dashboard Interactivo

```bash
python main.py
```

Presiona `Ctrl+C` para salir.

## 📋 Comandos Principales

### Tests
```bash
python tests/test_basic.py
```

### Ejemplos
```bash
# Todos los ejemplos automáticos
python example_usage.py

# Dashboard interactivo con tareas periódicas
python example_usage.py --dashboard

# Ejemplo de manejo de errores
python example_usage.py --errors
```

## 💻 Uso Programático

### Ejemplo Mínimo

```python
import asyncio
from main import MultiAgentSystem

async def main():
    # Crear sistema
    system = MultiAgentSystem(num_workers=3)

    # Iniciar
    await system.start()

    # Enviar tarea
    await system.submit_task("Create a Python script")

    # Esperar
    await asyncio.sleep(5)

    # Detener
    await system.stop()

asyncio.run(main())
```

### Ejemplo con Múltiples Tareas

```python
import asyncio
from main import MultiAgentSystem

async def main():
    system = MultiAgentSystem(num_workers=4)
    await system.start()

    # Enviar varias tareas
    tasks = [
        "Create configuration file",
        "Search for best practices",
        "Download documentation",
        "Analyze code quality"
    ]

    for task in tasks:
        await system.submit_task(task)
        await asyncio.sleep(0.5)  # Pequeña pausa

    # Esperar procesamiento
    await asyncio.sleep(10)

    # Ver resultados
    stats = await system.state_manager.get_stats()
    print(f"Completadas: {stats['completed']}/{stats['total_tasks']}")

    await system.stop()

asyncio.run(main())
```

### Ejemplo con Monitoreo

```python
import asyncio
from main import MultiAgentSystem

async def main():
    system = MultiAgentSystem(num_workers=3)
    await system.start()

    # Enviar tarea
    task_id = await system.submit_task("Create data analysis script")

    # Monitorear progreso
    for i in range(10):
        await asyncio.sleep(1)
        task = await system.state_manager.get_task(task_id)
        print(f"Status: {task.status.value}")

        if task.status.value in ["completed", "failed"]:
            break

    # Ver detalles
    if task.status.value == "completed":
        print(f"Resultado: {task.result}")
    else:
        print(f"Error: {task.error}")

    await system.stop()

asyncio.run(main())
```

## 🎨 Personalización

### Cambiar Número de Workers

```python
# 5 workers en lugar de 3
system = MultiAgentSystem(num_workers=5)
```

### Sin Dashboard (Headless)

```python
system = MultiAgentSystem(num_workers=3)
await system.start()

# Tu código aquí...

# Ejecutar por tiempo limitado
await system.run_without_dashboard(duration=30.0)
```

### Agregar Tipo de Tarea Personalizada

Editar `core/worker_agent.py`:

```python
async def process_task(self, task_data: Dict[str, Any]):
    task_type = task_data.get("type")

    # Tu nueva tarea
    if task_type == "custom_task":
        return await self._handle_custom_task(task_data["params"])

    # ... resto del código

async def _handle_custom_task(self, params: Dict):
    # Tu implementación
    result = do_something(params)
    return {"success": True, "result": result}
```

Editar `core/manager_agent.py`:

```python
async def _decompose_task(self, task: Task):
    description_lower = task.description.lower()

    # Tu palabra clave
    if "mi_operacion" in description_lower:
        subtasks.append({
            "description": "Ejecutar operación personalizada",
            "type": "custom_task",
            "params": {"data": "..."}
        })
```

## 🔍 Debugging y Troubleshooting

### Ver Estado del Sistema

```python
# Obtener estadísticas
stats = await system.state_manager.get_stats()
print(stats)

# Ver todas las tareas
tasks = await system.state_manager.get_all_tasks()
for task in tasks:
    print(f"{task.id}: {task.status.value} - {task.description}")

# Ver problemas
problems = await system.state_manager.get_open_problems()
for problem in problems:
    print(f"[{problem.severity}] {problem.description}")

# Ver cambios de archivos
changes = await system.state_manager.get_recent_file_changes()
for change in changes:
    print(f"{change.action}: {change.path} by {change.agent}")
```

### Logs en Tiempo Real

El dashboard muestra logs automáticamente. Para acceder programáticamente:

```python
# Suscribirse a eventos
from core.event_bus import EventType

async def my_handler(event):
    print(f"Event: {event.type.value} - {event.data}")

system.event_bus.subscribe(EventType.AGENT_MESSAGE, my_handler)
```

### Verificar Workers

```python
# Ver estado de workers
for worker in system.workers:
    status = await system.state_manager.get_agent_status(worker.agent_id)
    print(f"{worker.agent_id}: {status}")

    if worker.current_task:
        print(f"  Processing: {worker.current_task}")
```

## 📊 Monitoreo Avanzado

### Crear Dashboard Personalizado

```python
from core.event_bus import EventBus, Event, EventType
from core.state_manager import StateManager

class MyMonitor:
    def __init__(self, event_bus: EventBus, state: StateManager):
        self.event_bus = event_bus
        self.state = state

        # Suscribirse a eventos
        self.event_bus.subscribe(EventType.TASK_COMPLETED, self.on_complete)

    async def on_complete(self, event: Event):
        task_id = event.data.get("task_id")
        print(f"✅ Task {task_id} completed!")

# Usar
monitor = MyMonitor(system.event_bus, system.state_manager)
```

### Métricas Personalizadas

```python
import time
from collections import defaultdict

class Metrics:
    def __init__(self):
        self.task_times = defaultdict(list)

    async def track_task(self, system, task_id):
        start = time.time()

        # Esperar hasta completar
        while True:
            task = await system.state_manager.get_task(task_id)
            if task.status.value in ["completed", "failed"]:
                break
            await asyncio.sleep(0.1)

        duration = time.time() - start
        self.task_times[task.description].append(duration)

        print(f"Task '{task.description}' took {duration:.2f}s")

# Usar
metrics = Metrics()
task_id = await system.submit_task("Test task")
await metrics.track_task(system, task_id)
```

## 🎯 Casos de Uso Comunes

### Caso 1: Procesamiento de Archivos en Lote

```python
async def process_files():
    system = MultiAgentSystem(num_workers=5)
    await system.start()

    files = ["file1.txt", "file2.txt", "file3.txt"]

    for file in files:
        await system.submit_task(f"Analyze {file}")

    await asyncio.sleep(len(files) * 2)  # Esperar procesamiento

    stats = await system.state_manager.get_stats()
    print(f"Procesados: {stats['completed']} archivos")

    await system.stop()
```

### Caso 2: Web Scraping Paralelo

```python
async def scrape_websites():
    system = MultiAgentSystem(num_workers=10)
    await system.start()

    urls = [
        "https://example1.com",
        "https://example2.com",
        # ... más URLs
    ]

    for url in urls:
        await system.submit_task(f"Download data from {url}")

    await asyncio.sleep(30)

    # Ver resultados
    tasks = await system.state_manager.get_all_tasks()
    for task in tasks:
        if task.status.value == "completed":
            print(f"✅ {task.description}")

    await system.stop()
```

### Caso 3: Pipeline de Datos

```python
async def data_pipeline():
    system = MultiAgentSystem(num_workers=4)
    await system.start()

    # Fase 1: Obtención
    await system.submit_task("Download raw data")
    await asyncio.sleep(3)

    # Fase 2: Procesamiento
    await system.submit_task("Analyze downloaded data")
    await asyncio.sleep(3)

    # Fase 3: Reporte
    await system.submit_task("Create analysis report")
    await asyncio.sleep(3)

    # Ver resultados finales
    file_changes = await system.state_manager.get_recent_file_changes()
    print(f"Archivos generados: {len(file_changes)}")

    await system.stop()
```

## ⚙️ Configuración Avanzada

### Workspace Personalizado

```python
from tools import FileOperations

# Cambiar directorio de trabajo
file_ops = FileOperations(workspace_dir="/custom/path")

# Pasar a workers
worker = WorkerAgent(
    agent_id="worker_01",
    event_bus=event_bus,
    state_manager=state_manager,
    file_ops=file_ops,  # Custom file ops
    web_tools=web_tools
)
```

### Timeout de Web Requests

```python
from tools import WebTools

# Timeout de 60 segundos
web_tools = WebTools(timeout=60)
```

### Refresh Rate del Dashboard

```python
# Actualizar cada 0.5 segundos
await system.dashboard.run(refresh_rate=0.5)
```

## 🛡️ Mejores Prácticas

### 1. Manejo de Errores

```python
try:
    system = MultiAgentSystem(num_workers=3)
    await system.start()

    # Tu código aquí...

except Exception as e:
    print(f"Error: {e}")
finally:
    await system.stop()
```

### 2. Graceful Shutdown

```python
import signal

loop = asyncio.get_event_loop()

def shutdown():
    asyncio.create_task(system.stop())

for sig in (signal.SIGTERM, signal.SIGINT):
    loop.add_signal_handler(sig, shutdown)
```

### 3. Validación de Resultados

```python
task_id = await system.submit_task("Create file")
await asyncio.sleep(5)

task = await system.state_manager.get_task(task_id)

if task.status.value == "completed":
    if task.result and task.result.get("success"):
        print("✅ Tarea exitosa")
    else:
        print("⚠️ Tarea completada con warnings")
elif task.status.value == "failed":
    print(f"❌ Tarea fallida: {task.error}")
```

### 4. Limitación de Tareas

```python
MAX_CONCURRENT_TASKS = 10

async def submit_with_limit(system, tasks):
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

    async def limited_submit(task):
        async with semaphore:
            await system.submit_task(task)
            await asyncio.sleep(0.1)

    await asyncio.gather(*[limited_submit(t) for t in tasks])
```

## 🔧 Solución de Problemas Comunes

### Problema: Workers no procesan tareas

**Solución**:
```python
# Verificar que event bus está corriendo
# Verificar que workers están activos
for worker in system.workers:
    status = await system.state_manager.get_agent_status(worker.agent_id)
    print(f"{worker.agent_id}: {status}")
```

### Problema: Tareas quedan en PENDING

**Solución**:
```python
# Verificar que hay workers disponibles
print(f"Workers: {len(system.workers)}")

# Verificar que el manager está corriendo
manager_status = await system.state_manager.get_agent_status(system.manager.agent_id)
print(f"Manager: {manager_status}")
```

### Problema: Dashboard no se actualiza

**Solución**:
- Asegúrate de que Rich está instalado: `pip install rich`
- Verifica que tu terminal soporta colores
- Intenta reducir el refresh rate

### Problema: Memoria crece indefinidamente

**Solución**:
```python
# Limpiar mensajes del dashboard periódicamente
system.dashboard._max_messages = 50  # Limitar mensajes

# Limpiar tareas viejas (implementar tu propia lógica)
async def cleanup_old_tasks():
    tasks = await system.state_manager.get_all_tasks()
    # Filtrar y eliminar tareas antiguas
```

## 📚 Recursos Adicionales

- **README.md**: Documentación general
- **ARCHITECTURE.md**: Detalles de arquitectura
- **tests/**: Tests de componentes
- **example_usage.py**: Ejemplos completos

## 🆘 Ayuda

Si encuentras problemas:
1. Revisa los logs en el dashboard
2. Verifica el estado del sistema
3. Ejecuta los tests: `python tests/test_basic.py`
4. Consulta ARCHITECTURE.md para detalles de implementación
