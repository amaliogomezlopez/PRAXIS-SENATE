"""
Dashboard CLI visual con Rich
"""
import asyncio
from typing import Dict, List, Any
from datetime import datetime
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from core.event_bus import EventBus, Event, EventType
from core.state_manager import StateManager


class CLIDashboard:
    """Dashboard CLI visual en tiempo real"""

    def __init__(self, event_bus: EventBus, state_manager: StateManager):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.console = Console()
        self._running = False
        self._messages: List[Dict[str, str]] = []
        self._max_messages = 10

        # Suscribirse a todos los eventos
        for event_type in EventType:
            self.event_bus.subscribe(event_type, self._on_event)

    async def _on_event(self, event: Event):
        """Manejar evento y agregarlo al log"""
        message = self._format_event(event)
        self._messages.append({
            "timestamp": event.timestamp.strftime("%H:%M:%S"),
            "source": event.source,
            "message": message,
            "level": self._get_event_level(event.type)
        })

        # Mantener solo los últimos N mensajes
        if len(self._messages) > self._max_messages:
            self._messages.pop(0)

    def _format_event(self, event: Event) -> str:
        """Formatear evento para mostrar"""
        event_type = event.type.value

        if event.type == EventType.TASK_CREATED:
            return f"📋 Task created: {event.data.get('description', 'N/A')[:50]}"
        elif event.type == EventType.TASK_ASSIGNED:
            return f"👷 Task {event.data.get('task_id', 'N/A')[:12]} → {event.data.get('worker_id', 'N/A')}"
        elif event.type == EventType.TASK_STARTED:
            return f"▶️  Started: {event.data.get('task_id', 'N/A')[:12]}"
        elif event.type == EventType.TASK_COMPLETED:
            return f"✅ Completed: {event.data.get('task_id', 'N/A')[:12]}"
        elif event.type == EventType.TASK_FAILED:
            return f"❌ Failed: {event.data.get('task_id', 'N/A')[:12]}"
        elif event.type == EventType.FILE_MODIFIED:
            return f"📝 {event.data.get('action', 'modified')}: {event.data.get('path', 'N/A')}"
        elif event.type == EventType.PROBLEM_DETECTED:
            return f"⚠️  Problem: {event.data.get('description', 'N/A')[:50]}"
        elif event.type == EventType.PROGRESS_UPDATE:
            return f"⏳ {event.data.get('message', 'N/A')}"
        elif event.type == EventType.AGENT_MESSAGE:
            return f"💬 {event.data.get('message', 'N/A')}"
        else:
            return f"{event_type}"

    def _get_event_level(self, event_type: EventType) -> str:
        """Obtener nivel del evento para colorear"""
        if event_type in [EventType.TASK_FAILED, EventType.PROBLEM_DETECTED]:
            return "error"
        elif event_type in [EventType.TASK_COMPLETED]:
            return "success"
        elif event_type in [EventType.TASK_STARTED, EventType.PROGRESS_UPDATE]:
            return "info"
        else:
            return "normal"

    def _create_stats_panel(self, stats: Dict[str, Any]) -> Panel:
        """Crear panel de estadísticas"""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow bold")

        table.add_row("Total Tasks", str(stats.get("total_tasks", 0)))
        table.add_row("✅ Completed", str(stats.get("completed", 0)))
        table.add_row("⏳ In Progress", str(stats.get("in_progress", 0)))
        table.add_row("📋 Pending", str(stats.get("pending", 0)))
        table.add_row("❌ Failed", str(stats.get("failed", 0)))
        table.add_row("⚠️  Open Problems", str(stats.get("open_problems", 0)))
        table.add_row("📝 File Changes", str(stats.get("file_changes", 0)))

        return Panel(table, title="📊 System Statistics", border_style="blue")

    def _create_tasks_panel(self, tasks: List) -> Panel:
        """Crear panel de tareas"""
        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("ID", style="cyan", width=12)
        table.add_column("Status", width=12)
        table.add_column("Description", style="white")
        table.add_column("Agent", style="magenta", width=10)

        # Mostrar solo tareas recientes
        recent_tasks = sorted(
            tasks,
            key=lambda t: t.created_at,
            reverse=True
        )[:5]

        for task in recent_tasks:
            status_emoji = {
                "pending": "📋",
                "in_progress": "⏳",
                "completed": "✅",
                "failed": "❌"
            }.get(task.status.value, "❓")

            status_color = {
                "pending": "yellow",
                "in_progress": "blue",
                "completed": "green",
                "failed": "red"
            }.get(task.status.value, "white")

            table.add_row(
                task.id[:12],
                f"[{status_color}]{status_emoji} {task.status.value}[/{status_color}]",
                task.description[:40],
                task.assigned_to[:10] if task.assigned_to else "-"
            )

        return Panel(table, title="📋 Recent Tasks", border_style="green")

    def _create_files_panel(self, file_changes: List) -> Panel:
        """Crear panel de archivos modificados"""
        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("Time", style="cyan", width=8)
        table.add_column("Action", width=10)
        table.add_column("Path", style="white")
        table.add_column("Agent", style="magenta", width=10)

        for change in file_changes[-5:]:
            action_emoji = {
                "created": "➕",
                "modified": "✏️ ",
                "deleted": "🗑️ "
            }.get(change.action, "📝")

            action_color = {
                "created": "green",
                "modified": "yellow",
                "deleted": "red"
            }.get(change.action, "white")

            table.add_row(
                change.timestamp.strftime("%H:%M:%S"),
                f"[{action_color}]{action_emoji} {change.action}[/{action_color}]",
                change.path,
                change.agent[:10]
            )

        return Panel(table, title="📁 File Changes", border_style="yellow")

    def _create_problems_panel(self, problems: List) -> Panel:
        """Crear panel de problemas"""
        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("Severity", width=10)
        table.add_column("Description", style="white")
        table.add_column("Time", style="cyan", width=8)

        for problem in problems[-5:]:
            severity_emoji = {
                "low": "ℹ️ ",
                "medium": "⚠️ ",
                "high": "🔴"
            }.get(problem.severity, "❓")

            severity_color = {
                "low": "blue",
                "medium": "yellow",
                "high": "red"
            }.get(problem.severity, "white")

            table.add_row(
                f"[{severity_color}]{severity_emoji} {problem.severity}[/{severity_color}]",
                problem.description[:50],
                problem.detected_at.strftime("%H:%M:%S")
            )

        if not problems:
            table.add_row("[green]✅ All Clear", "No problems detected", "-")

        return Panel(table, title="⚠️  Problems", border_style="red")

    def _create_activity_panel(self) -> Panel:
        """Crear panel de actividad reciente"""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Time", style="dim", width=8)
        table.add_column("Source", style="magenta", width=12)
        table.add_column("Message", style="white")

        for msg in self._messages[-10:]:
            color = {
                "error": "red",
                "success": "green",
                "info": "blue",
                "normal": "white"
            }.get(msg["level"], "white")

            table.add_row(
                msg["timestamp"],
                msg["source"][:12],
                f"[{color}]{msg['message']}[/{color}]"
            )

        return Panel(table, title="📡 Activity Feed", border_style="cyan")

    async def _generate_layout(self) -> Layout:
        """Generar layout del dashboard"""
        layout = Layout()

        # Obtener datos del estado
        stats = await self.state_manager.get_stats()
        tasks = await self.state_manager.get_all_tasks()
        problems = await self.state_manager.get_open_problems()
        file_changes = await self.state_manager.get_recent_file_changes()

        # Crear layout
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )

        # Header
        header_text = Text("🤖 Multi-Agent System Dashboard", style="bold magenta", justify="center")
        layout["header"].update(Panel(header_text, border_style="bright_blue"))

        # Main area
        layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=2)
        )

        # Left column
        layout["left"].split_column(
            Layout(self._create_stats_panel(stats)),
            Layout(self._create_problems_panel(problems))
        )

        # Right column
        layout["right"].split_column(
            Layout(self._create_tasks_panel(tasks)),
            Layout(self._create_files_panel(file_changes)),
            Layout(self._create_activity_panel())
        )

        # Footer
        footer_text = Text(
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Press Ctrl+C to exit",
            style="dim",
            justify="center"
        )
        layout["footer"].update(Panel(footer_text, border_style="dim"))

        return layout

    async def run(self, refresh_rate: float = 1.0):
        """Ejecutar dashboard en tiempo real"""
        self._running = True

        with Live(
            await self._generate_layout(),
            console=self.console,
            refresh_per_second=1/refresh_rate,
            screen=True
        ) as live:
            while self._running:
                try:
                    await asyncio.sleep(refresh_rate)
                    live.update(await self._generate_layout())
                except KeyboardInterrupt:
                    break

    def stop(self):
        """Detener dashboard"""
        self._running = False
