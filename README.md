![Senado de Praxis](https://i.postimg.cc/9MPcZn6S/PRAXIS-SENATE.png)

# Sistema Multi-Agente Profesional

Un sistema de orquestación multi-agente con arquitectura Manager-Worker, comunicación asíncrona event-driven, y dashboard CLI visual.

## 🚀 Inicio Rápido

### Ejecutar el Sistema

```bash
# Ejecutar ejemplo integrado
python code/main.py

# Ejecutar con request personalizado
python code/main.py "Implement authentication system"
```

### Uso Programático

```python
from main import MultiAgentSystem
import asyncio

async def main():
    system = MultiAgentSystem()
    await system.run("Tu tarea aquí")
    await system.shutdown()

asyncio.run(main())
```

## 📁 Estructura del Proyecto

```
/workspace/
├── config/
│   └── system_config.yaml         # Configuración del sistema
├── code/
│   ├── models.py                  # Data models (Task, Agent, Message)
│   ├── message_bus.py             # Event Bus / Messaging
│   ├── manager_agent.py           # Senior Manager (Orquestador)
│   ├── worker_agent.py            # Workers especializados
│   └── main.py                    # Entry point / Sistema integrado
├── docs/
│   ├── architecture_design.md     # Diseño arquitectónico detallado
│   ├── architecture_diagrams.md   # Diagramas Mermaid completos
│   └── cli_dashboard_design.md    # Mockup del dashboard CLI
└── REPORTE_FINAL_SISTEMA_MULTIAGENTE.md  # 📖 REPORTE COMPLETO
```

## 📖 Documentación

### Reporte Principal
**[REPORTE_FINAL_SISTEMA_MULTIAGENTE.md](REPORTE_FINAL_SISTEMA_MULTIAGENTE.md)**

Este documento contiene:
- ✅ Respuestas a todas las preguntas sobre comunicación, estado, orquestación
- ✅ Diagrama de arquitectura
- ✅ Diseño del dashboard CLI (mockup)
- ✅ Estructura de datos completa
- ✅ Flujo de trabajo detallado
- ✅ Código base implementado
- ✅ Consideraciones de escalabilidad

### Documentos Técnicos

1. **[docs/architecture_design.md](docs/architecture_design.md)**
   - Patrones de arquitectura
   - Protocolo de mensajes
   - Estado compartido
   - Manejo de errores
   - Escalabilidad

2. **[docs/architecture_diagrams.md](docs/architecture_diagrams.md)**
   - Diagrama de arquitectura general
   - Flujo de comunicación
   - Estados de tarea
   - Componentes del sistema
   - Flujo de trabajo
   - Manejo de errores

3. **[docs/cli_dashboard_design.md](docs/cli_dashboard_design.md)**
   - Mockup completo del dashboard CLI
   - Paneles y componentes visuales
   - Colores, iconos, progress bars
   - Interactividad y atajos de teclado

## ⚙️ Configuración

Editar `config/system_config.yaml`:

```yaml
manager:
  max_concurrent_tasks: 10

workers:
  pool_size: 5
  auto_scale:
    enabled: true
    min_workers: 2
    max_workers: 20
```

## 🎯 Características Principales

- ✅ **1 Agente Senior (Manager)**: Orquestador inteligente
- ✅ **Sub-Agentes (Workers)**: Especializados y escalables
- ✅ **Comunicación Asíncrona**: Event Bus con Pub/Sub
- ✅ **Estado Compartido**: Multi-tier (Filesystem + DB + Memory)
- ✅ **Dashboard CLI**: Visual con progress bars, iconos, colores
- ✅ **Manejo de Errores**: Retry automático, circuit breakers
- ✅ **Escalabilidad**: Auto-scaling horizontal

## 🔧 Extender con Nuevos Workers

```python
from worker_agent import WorkerAgent

class CustomWorker(WorkerAgent):
    def __init__(self, agent_id, message_bus, config):
        super().__init__(
            agent_id=agent_id,
            specialization="custom_type",
            capabilities=["capability1", "capability2"],
            message_bus=message_bus,
            config=config
        )

    async def _perform_work(self, task: Task) -> Dict:
        # Tu lógica aquí
        return {"result": "success"}
```

## 📊 Componentes del Sistema

### Message Bus
- Comunicación asíncrona Pub/Sub
- Consumer groups para balanceo
- Priority queues
- Event sourcing para replay

### Manager Agent
- Descomposición de tareas
- Orquestación de workers
- Análisis de gaps
- Monitoreo de progreso

### Worker Agents
- Especializados (code_editor, researcher, reviewer)
- Ejecución paralela
- Status reporting
- Heartbeat mechanism

## 🚀 Próximos Pasos

1. Implementar dashboard CLI con Rich/Textual
2. Agregar más workers especializados
3. Integrar con LLMs para descomposición inteligente
4. Dashboard web con React + WebSockets
5. Deploy a Kubernetes

## 📝 Licencia

© 2026 - Sistema Multi-Agente Profesional

---

**Para documentación completa, ver:** [REPORTE_FINAL_SISTEMA_MULTIAGENTE.md](REPORTE_FINAL_SISTEMA_MULTIAGENTE.md)
