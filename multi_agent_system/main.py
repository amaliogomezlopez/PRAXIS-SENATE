"""
Sistema Multi-Agente - Punto de entrada principal
"""
import asyncio
import signal
from typing import List
from core import EventBus, StateManager, ManagerAgent, WorkerAgent
from tools import FileOperations, WebTools
from dashboard import CLIDashboard


class MultiAgentSystem:
    """Sistema multi-agente completo"""

    def __init__(self, num_workers: int = 3):
        self.num_workers = num_workers

        # Componentes centrales
        self.event_bus = EventBus()
        self.state_manager = StateManager()

        # Herramientas compartidas
        self.file_ops = FileOperations()
        self.web_tools = WebTools()

        # Agentes
        self.manager = ManagerAgent(
            agent_id="manager_01",
            event_bus=self.event_bus,
            state_manager=self.state_manager
        )

        self.workers: List[WorkerAgent] = []
        for i in range(num_workers):
            worker = WorkerAgent(
                agent_id=f"worker_{i+1:02d}",
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                file_ops=self.file_ops,
                web_tools=self.web_tools
            )
            self.workers.append(worker)
            self.manager.add_worker(worker)

        # Dashboard
        self.dashboard = CLIDashboard(
            event_bus=self.event_bus,
            state_manager=self.state_manager
        )

        # Tareas en ejecución
        self._tasks = []
        self._running = False

    async def start(self):
        """Iniciar el sistema"""
        print("🚀 Starting Multi-Agent System...")
        print(f"   Manager: {self.manager.agent_id}")
        print(f"   Workers: {len(self.workers)}")
        print()

        self._running = True

        # Iniciar event bus
        event_bus_task = asyncio.create_task(self.event_bus.start())
        self._tasks.append(event_bus_task)

        # Iniciar manager
        manager_task = asyncio.create_task(self.manager.run())
        self._tasks.append(manager_task)

        # Iniciar workers
        for worker in self.workers:
            worker_task = asyncio.create_task(worker.run())
            self._tasks.append(worker_task)

        # Pequeña pausa para que se inicialicen
        await asyncio.sleep(0.5)

    async def stop(self):
        """Detener el sistema"""
        print("\n🛑 Stopping Multi-Agent System...")

        self._running = False

        # Detener agentes
        await self.manager.stop()
        for worker in self.workers:
            await worker.stop()

        # Detener event bus
        self.event_bus.stop()

        # Cerrar herramientas
        await self.web_tools.close()

        # Cancelar tareas
        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def submit_task(self, description: str):
        """Enviar tarea al sistema"""
        return await self.manager.submit_user_task(description)

    async def run_with_dashboard(self):
        """Ejecutar sistema con dashboard"""
        await self.start()

        # Configurar manejador de señales para shutdown graceful
        loop = asyncio.get_event_loop()

        def signal_handler():
            asyncio.create_task(self.stop())

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)

        # Ejecutar dashboard
        try:
            await self.dashboard.run(refresh_rate=1.0)
        except KeyboardInterrupt:
            pass
        finally:
            await self.stop()

    async def run_without_dashboard(self, duration: float = 30.0):
        """Ejecutar sistema sin dashboard (para testing)"""
        await self.start()

        try:
            await asyncio.sleep(duration)
        except KeyboardInterrupt:
            pass
        finally:
            await self.stop()


async def main():
    """Función principal"""
    # Crear sistema con 3 workers
    system = MultiAgentSystem(num_workers=3)

    # Iniciar sistema
    await system.start()

    # Enviar algunas tareas de ejemplo
    print("📋 Submitting example tasks...\n")

    await system.submit_task("Create a Python script to analyze data")
    await asyncio.sleep(1)

    await system.submit_task("Search for information about asyncio")
    await asyncio.sleep(1)

    await system.submit_task("Download and analyze GitHub repository data")
    await asyncio.sleep(1)

    # Ejecutar con dashboard
    print("🎨 Starting dashboard...\n")
    await system.run_with_dashboard()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
