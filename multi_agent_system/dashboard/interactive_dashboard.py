"""
Interactive Dashboard - Real-time control and intervention
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.prompt import Prompt, Confirm
from core.event_bus import EventBus, Event, EventType
from core.state_manager import StateManager, TaskStatus
from workers.role_manager import RoleManager


logger = logging.getLogger(__name__)


class InteractiveDashboard:
    """Interactive dashboard with user intervention capabilities"""

    def __init__(
        self,
        event_bus: EventBus,
        state_manager: StateManager,
        role_manager: RoleManager,
        system
    ):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.role_manager = role_manager
        self.system = system
        self.console = Console()
        self._running = False
        self._messages: List[Dict[str, str]] = []
        self._max_messages = 15
        self._commands_history: List[str] = []
        self._paused_agents: set = set()

        # Subscribe to events
        for event_type in EventType:
            self.event_bus.subscribe(event_type, self._on_event)

    async def _on_event(self, event: Event):
        """Handle incoming events"""
        message = self._format_event(event)
        self._messages.append({
            "timestamp": event.timestamp.strftime("%H:%M:%S"),
            "source": event.source,
            "message": message,
            "level": self._get_event_level(event.type)
        })

        if len(self._messages) > self._max_messages:
            self._messages.pop(0)

    def _format_event(self, event: Event) -> str:
        """Format event for display"""
        if event.type == EventType.TASK_CREATED:
            return f"Task created: {event.data.get('description', 'N/A')[:40]}"
        elif event.type == EventType.TASK_ASSIGNED:
            return f"Task assigned to {event.data.get('worker_id', 'N/A')}"
        elif event.type == EventType.TASK_STARTED:
            return f"Started task {event.data.get('task_id', 'N/A')[:12]}"
        elif event.type == EventType.TASK_COMPLETED:
            return f"Completed task {event.data.get('task_id', 'N/A')[:12]}"
        elif event.type == EventType.TASK_FAILED:
            return f"Failed task {event.data.get('task_id', 'N/A')[:12]}"
        elif event.type == EventType.FILE_MODIFIED:
            return f"{event.data.get('action')}: {event.data.get('path')}"
        elif event.type == EventType.PROBLEM_DETECTED:
            return f"Problem: {event.data.get('description', 'N/A')[:40]}"
        else:
            return f"{event.type.value}"

    def _get_event_level(self, event_type: EventType) -> str:
        """Get event level for coloring"""
        if event_type in [EventType.TASK_FAILED, EventType.PROBLEM_DETECTED]:
            return "error"
        elif event_type == EventType.TASK_COMPLETED:
            return "success"
        else:
            return "info"

    async def run(self, refresh_rate: float = 1.0):
        """Run interactive dashboard"""
        self._running = True
        self.console.clear()

        # Display welcome message
        self.console.print(Panel.fit(
            "[bold cyan]Multi-Agent System - Interactive Dashboard[/]\n"
            "[dim]Type 'help' for available commands[/]",
            border_style="cyan"
        ))

        # Start background refresh task
        refresh_task = asyncio.create_task(self._auto_refresh(refresh_rate))
        command_task = asyncio.create_task(self._command_loop())

        try:
            await asyncio.gather(refresh_task, command_task)
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Dashboard stopped by user[/]")
        finally:
            self._running = False
            refresh_task.cancel()
            command_task.cancel()

    async def _auto_refresh(self, interval: float):
        """Auto-refresh dashboard display"""
        while self._running:
            try:
                await asyncio.sleep(interval)
                self._display_status()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in auto-refresh: {e}")

    async def _command_loop(self):
        """Interactive command loop — continuously shows menu"""
        while self._running:
            try:
                await self.show_menu()
            except asyncio.CancelledError:
                break
            except EOFError:
                break
            except Exception as e:
                logger.error(f"Error in command loop: {e}")
                self.console.print(f"[red]Error: {e}[/]")

    def _display_status(self):
        """Display current system status summary"""
        try:
            msg_count = len(self._messages)
            latest = self._messages[-1] if self._messages else None
            status_line = f"[dim]Events: {msg_count}"
            if latest:
                status_line += f" | Last: {latest['message'][:40]}"
            status_line += "[/]"
            self.console.print(status_line)
        except Exception:
            pass

    async def show_menu(self):
        """Show interactive menu"""
        self.console.print("\n[bold cyan]═══ Dashboard Menu ═══[/]\n")

        choices = {
            "1": "Add Task",
            "2": "View Tasks",
            "3": "Manage Agents",
            "4": "Manage Roles",
            "5": "Correct Agent",
            "6": "Pause/Resume Agent",
            "7": "View Statistics",
            "8": "View Problems",
            "9": "View File Changes",
            "0": "Exit"
        }

        for key, value in choices.items():
            self.console.print(f"  [{key}] {value}")

        choice = Prompt.ask("\nSelect option", choices=list(choices.keys()))

        if choice == "1":
            await self.add_task()
        elif choice == "2":
            await self.view_tasks()
        elif choice == "3":
            await self.manage_agents()
        elif choice == "4":
            await self.manage_roles()
        elif choice == "5":
            await self.correct_agent()
        elif choice == "6":
            await self.pause_resume_agent()
        elif choice == "7":
            await self.view_statistics()
        elif choice == "8":
            await self.view_problems()
        elif choice == "9":
            await self.view_file_changes()
        elif choice == "0":
            self._running = False

    async def add_task(self):
        """Add a new task"""
        self.console.print("\n[bold]Add New Task[/]")
        description = Prompt.ask("Task description")

        if self.system and hasattr(self.system, 'manager'):
            task_id = await self.system.manager.submit_user_task(description)
            self.console.print(f"[green]✓ Task created: {task_id}[/]")
        else:
            self.console.print("[red]✗ System manager not available[/]")

    async def view_tasks(self):
        """View all tasks"""
        self.console.print("\n[bold]Current Tasks[/]")

        tasks = await self.state_manager.get_all_tasks()

        if not tasks:
            self.console.print("[dim]No tasks found[/]")
            return

        table = Table(show_header=True, border_style="blue")
        table.add_column("ID", style="cyan", width=15)
        table.add_column("Status", width=12)
        table.add_column("Description", style="white")
        table.add_column("Assigned To", style="magenta", width=12)

        for task in tasks[:20]:
            status_color = {
                TaskStatus.PENDING: "yellow",
                TaskStatus.IN_PROGRESS: "blue",
                TaskStatus.COMPLETED: "green",
                TaskStatus.FAILED: "red"
            }.get(task.status, "white")

            table.add_row(
                task.id[:15],
                f"[{status_color}]{task.status.value}[/{status_color}]",
                task.description[:50],
                task.assigned_to[:12] if task.assigned_to else "-"
            )

        self.console.print(table)

    async def manage_agents(self):
        """Manage agents (CRUD)"""
        self.console.print("\n[bold]Agent Management[/]")

        choices = {
            "1": "List Agents",
            "2": "Create Agent",
            "3": "Delete Agent",
            "4": "View Agent Details",
            "5": "Back"
        }

        for key, value in choices.items():
            self.console.print(f"  [{key}] {value}")

        choice = Prompt.ask("Select option", choices=list(choices.keys()))

        if choice == "1":
            await self._list_agents()
        elif choice == "2":
            await self._create_agent()
        elif choice == "3":
            await self._delete_agent()
        elif choice == "4":
            await self._view_agent_details()

    async def _list_agents(self):
        """List all agents"""
        if not hasattr(self.system, 'manager') or not self.system.manager:
            self.console.print("[red]No manager available[/]")
            return

        workers = self.system.manager.workers

        table = Table(show_header=True, border_style="green")
        table.add_column("Agent ID", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Status", style="white")
        table.add_column("Current Task", style="magenta")

        for worker in workers:
            status = "Running" if worker._running else "Stopped"
            current_task = getattr(worker, 'current_task', None) or "-"

            table.add_row(
                worker.agent_id,
                "Worker",
                status,
                current_task[:20] if isinstance(current_task, str) else str(current_task)[:20]
            )

        self.console.print(table)

    async def _create_agent(self):
        """Create a new agent"""
        self.console.print("\n[bold]Create New Agent[/]")

        agent_id = Prompt.ask("Agent ID")
        roles = self.role_manager.list_roles()

        if not roles:
            self.console.print("[yellow]No roles available. Create a role first.[/]")
            return

        self.console.print("\nAvailable roles:")
        for i, role_name in enumerate(roles, 1):
            self.console.print(f"  {i}. {role_name}")

        role_choice = Prompt.ask("Select role", choices=[str(i) for i in range(1, len(roles) + 1)])
        role_name = roles[int(role_choice) - 1]

        self.console.print(f"[green]✓ Agent {agent_id} created with role {role_name}[/]")
        self.console.print("[yellow]Note: Agent integration pending in system[/]")

    async def _delete_agent(self):
        """Delete an agent"""
        agent_id = Prompt.ask("Agent ID to delete")
        confirm = Confirm.ask(f"Are you sure you want to delete {agent_id}?")

        if confirm:
            self.console.print(f"[green]✓ Agent {agent_id} deleted[/]")
            self.console.print("[yellow]Note: Agent deletion pending in system[/]")

    async def _view_agent_details(self):
        """View agent details"""
        agent_id = Prompt.ask("Agent ID")
        self.console.print(f"\n[bold]Agent: {agent_id}[/]")
        self.console.print("[yellow]Detailed view pending implementation[/]")

    async def manage_roles(self):
        """Manage roles (CRUD)"""
        self.console.print("\n[bold]Role Management[/]")

        choices = {
            "1": "List Roles",
            "2": "Create Role",
            "3": "Edit Role",
            "4": "Delete Role",
            "5": "View Role Details",
            "6": "Back"
        }

        for key, value in choices.items():
            self.console.print(f"  [{key}] {value}")

        choice = Prompt.ask("Select option", choices=list(choices.keys()))

        if choice == "1":
            await self._list_roles()
        elif choice == "2":
            await self._create_role()
        elif choice == "3":
            await self._edit_role()
        elif choice == "4":
            await self._delete_role()
        elif choice == "5":
            await self._view_role_details()

    async def _list_roles(self):
        """List all roles"""
        roles = self.role_manager.list_roles()

        table = Table(show_header=True, border_style="magenta")
        table.add_column("Role Name", style="cyan")
        table.add_column("Specialization", style="white")

        for role_name in roles:
            role = self.role_manager.get_role(role_name)
            if role:
                table.add_row(
                    role.name,
                    role.specialization[:60]
                )

        self.console.print(table)

    async def _create_role(self):
        """Create a new role"""
        self.console.print("\n[bold]Create New Role[/]")

        name = Prompt.ask("Role name")
        specialization = Prompt.ask("Specialization")
        instructions = Prompt.ask("Instructions")
        constraints = Prompt.ask("Constraints")

        role = self.role_manager.create_role(
            name=name,
            specialization=specialization,
            instructions=instructions,
            constraints=constraints
        )

        self.console.print(f"[green]✓ Role '{role.name}' created successfully[/]")

    async def _edit_role(self):
        """Edit an existing role"""
        roles = self.role_manager.list_roles()
        if not roles:
            self.console.print("[yellow]No roles available[/]")
            return

        self.console.print("\nAvailable roles:")
        for i, role_name in enumerate(roles, 1):
            self.console.print(f"  {i}. {role_name}")

        choice = Prompt.ask("Select role to edit", choices=[str(i) for i in range(1, len(roles) + 1)])
        role_name = roles[int(choice) - 1]

        role = self.role_manager.get_role(role_name)
        if not role:
            self.console.print("[red]Role not found[/]")
            return

        self.console.print(f"\n[bold]Editing: {role.name}[/]")
        self.console.print("[dim]Press Enter to keep current value[/]\n")

        specialization = Prompt.ask("Specialization", default=role.specialization)
        instructions = Prompt.ask("Instructions", default=role.instructions)
        constraints = Prompt.ask("Constraints", default=role.constraints)

        self.role_manager.update_role(
            name=role_name,
            specialization=specialization,
            instructions=instructions,
            constraints=constraints
        )

        self.console.print(f"[green]✓ Role '{role_name}' updated successfully[/]")

    async def _delete_role(self):
        """Delete a role"""
        role_name = Prompt.ask("Role name to delete")
        confirm = Confirm.ask(f"Are you sure you want to delete role '{role_name}'?")

        if confirm:
            if self.role_manager.delete_role(role_name):
                self.console.print(f"[green]✓ Role '{role_name}' deleted[/]")
            else:
                self.console.print(f"[red]✗ Failed to delete role '{role_name}'[/]")

    async def _view_role_details(self):
        """View role details"""
        role_name = Prompt.ask("Role name")
        role = self.role_manager.get_role(role_name)

        if not role:
            self.console.print(f"[red]✗ Role '{role_name}' not found[/]")
            return

        self.console.print(f"\n[bold cyan]Role: {role.name}[/]\n")
        self.console.print(Panel.fit(role.specialization, title="Specialization", border_style="green"))
        self.console.print(Panel.fit(role.instructions, title="Instructions", border_style="blue"))
        self.console.print(Panel.fit(role.constraints, title="Constraints", border_style="red"))

    async def correct_agent(self):
        """Send correction to an agent"""
        self.console.print("\n[bold]Correct Agent[/]")

        agent_id = Prompt.ask("Agent ID")
        correction = Prompt.ask("Correction message")

        if self.system and hasattr(self.system.manager, 'receive_correction'):
            await self.system.manager.receive_correction(agent_id, correction)
            self.console.print(f"[green]✓ Correction sent to {agent_id}[/]")
        else:
            self.console.print("[yellow]Correction feature pending implementation[/]")

    async def pause_resume_agent(self):
        """Pause or resume an agent"""
        self.console.print("\n[bold]Pause/Resume Agent[/]")

        agent_id = Prompt.ask("Agent ID")
        action = Prompt.ask("Action", choices=["pause", "resume"])

        if action == "pause":
            self._paused_agents.add(agent_id)
            self.console.print(f"[yellow]⏸ Agent {agent_id} paused[/]")
        else:
            self._paused_agents.discard(agent_id)
            self.console.print(f"[green]▶ Agent {agent_id} resumed[/]")

    async def view_statistics(self):
        """View system statistics"""
        self.console.print("\n[bold]System Statistics[/]")

        stats = await self.state_manager.get_stats()

        table = Table(show_header=False, border_style="cyan")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow bold")

        table.add_row("Total Tasks", str(stats.get("total_tasks", 0)))
        table.add_row("Completed", str(stats.get("completed", 0)))
        table.add_row("In Progress", str(stats.get("in_progress", 0)))
        table.add_row("Pending", str(stats.get("pending", 0)))
        table.add_row("Failed", str(stats.get("failed", 0)))
        table.add_row("Open Problems", str(stats.get("open_problems", 0)))
        table.add_row("File Changes", str(stats.get("file_changes", 0)))

        self.console.print(table)

    async def view_problems(self):
        """View detected problems"""
        self.console.print("\n[bold]Detected Problems[/]")

        problems = await self.state_manager.get_open_problems()

        if not problems:
            self.console.print("[green]✓ No problems detected[/]")
            return

        table = Table(show_header=True, border_style="red")
        table.add_column("Time", style="cyan", width=8)
        table.add_column("Severity", width=10)
        table.add_column("Description", style="white")

        for problem in problems:
            severity_color = {
                "low": "blue",
                "medium": "yellow",
                "high": "red"
            }.get(problem.severity, "white")

            table.add_row(
                problem.detected_at.strftime("%H:%M:%S"),
                f"[{severity_color}]{problem.severity}[/{severity_color}]",
                problem.description[:60]
            )

        self.console.print(table)

    async def view_file_changes(self):
        """View file changes"""
        self.console.print("\n[bold]Recent File Changes[/]")

        changes = await self.state_manager.get_recent_file_changes()

        if not changes:
            self.console.print("[dim]No file changes recorded[/]")
            return

        table = Table(show_header=True, border_style="yellow")
        table.add_column("Time", style="cyan", width=8)
        table.add_column("Action", width=10)
        table.add_column("Path", style="white")
        table.add_column("Agent", style="magenta", width=12)

        for change in changes:
            action_color = {
                "created": "green",
                "modified": "yellow",
                "deleted": "red"
            }.get(change.action, "white")

            table.add_row(
                change.timestamp.strftime("%H:%M:%S"),
                f"[{action_color}]{change.action}[/{action_color}]",
                change.path,
                change.agent[:12]
            )

        self.console.print(table)

    def stop(self):
        """Stop the dashboard"""
        self._running = False
