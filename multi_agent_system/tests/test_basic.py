"""
Tests básicos del sistema multi-agente
"""
import asyncio
import sys
sys.path.insert(0, '/workspace/multi_agent_system')

from core import EventBus, StateManager, Task, TaskStatus
from tools import FileOperations, WebTools


async def test_event_bus():
    """Test del sistema de eventos"""
    print("Testing EventBus...")

    event_bus = EventBus()
    events_received = []

    async def handler(event):
        events_received.append(event)

    from core.event_bus import EventType, Event
    from datetime import datetime

    event_bus.subscribe(EventType.TASK_CREATED, handler)

    # Iniciar event bus
    bus_task = asyncio.create_task(event_bus.start())

    # Publicar evento
    test_event = Event(
        type=EventType.TASK_CREATED,
        data={"task_id": "test_123"},
        timestamp=datetime.now(),
        source="test"
    )
    await event_bus.publish(test_event)

    # Esperar procesamiento
    await asyncio.sleep(0.2)

    # Detener
    event_bus.stop()
    bus_task.cancel()

    assert len(events_received) == 1
    assert events_received[0].data["task_id"] == "test_123"

    print("✅ EventBus test passed")


async def test_state_manager():
    """Test del gestor de estado"""
    print("Testing StateManager...")

    state = StateManager()

    # Crear tarea
    task = Task(
        id="task_001",
        description="Test task",
        status=TaskStatus.PENDING
    )

    await state.add_task(task)

    # Recuperar tarea
    retrieved = await state.get_task("task_001")
    assert retrieved is not None
    assert retrieved.description == "Test task"

    # Actualizar tarea
    await state.update_task("task_001", status=TaskStatus.COMPLETED)

    updated = await state.get_task("task_001")
    assert updated.status == TaskStatus.COMPLETED

    # Estadísticas
    stats = await state.get_stats()
    assert stats["total_tasks"] == 1
    assert stats["completed"] == 1

    print("✅ StateManager test passed")


async def test_file_operations():
    """Test de operaciones de archivos"""
    print("Testing FileOperations...")

    file_ops = FileOperations(workspace_dir="/workspace/agent_workspace/test")

    # Crear archivo
    result = await file_ops.create_file("test.txt", "Hello World")
    assert result["success"] is True

    # Leer archivo
    result = await file_ops.read_file("test.txt")
    assert result["success"] is True
    assert result["content"] == "Hello World"

    # Actualizar archivo
    result = await file_ops.update_file("test.txt", "Updated content")
    assert result["success"] is True

    # Leer actualizado
    result = await file_ops.read_file("test.txt")
    assert result["content"] == "Updated content"

    # Listar archivos
    result = await file_ops.list_files()
    assert result["success"] is True
    assert result["count"] > 0

    # Eliminar archivo
    result = await file_ops.delete_file("test.txt")
    assert result["success"] is True

    print("✅ FileOperations test passed")


async def test_web_tools():
    """Test de herramientas web"""
    print("Testing WebTools...")

    web_tools = WebTools(timeout=10)

    # Test GET request (usando API pública)
    result = await web_tools.get_request("https://api.github.com/users/github")
    assert result["success"] is True
    assert result["status_code"] == 200

    await web_tools.close()

    print("✅ WebTools test passed")


async def run_all_tests():
    """Ejecutar todos los tests"""
    print("=" * 60)
    print("RUNNING TESTS")
    print("=" * 60 + "\n")

    try:
        await test_event_bus()
        await test_state_manager()
        await test_file_operations()
        await test_web_tools()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
