"""
Demostración simple del sistema multi-agente sin dashboard
"""
import asyncio
import sys
sys.path.insert(0, '/workspace/multi_agent_system')

from main import MultiAgentSystem


async def demo():
    """Demostración simple"""
    print("=" * 70)
    print(" DEMOSTRACIÓN DEL SISTEMA MULTI-AGENTE")
    print("=" * 70)
    print()

    # Crear sistema con 3 workers
    print("🚀 Inicializando sistema...")
    system = MultiAgentSystem(num_workers=3)

    # Iniciar sistema
    await system.start()
    print("✅ Sistema iniciado")
    print(f"   - Manager: {system.manager.agent_id}")
    print(f"   - Workers: {[w.agent_id for w in system.workers]}")
    print()

    # Enviar tareas
    print("📋 Enviando tareas...")
    print()

    tasks = []

    task1 = await system.submit_task("Create a Python configuration file")
    tasks.append(task1)
    print(f"   ✓ Tarea 1: {task1}")

    await asyncio.sleep(0.5)

    task2 = await system.submit_task("Search for Python best practices")
    tasks.append(task2)
    print(f"   ✓ Tarea 2: {task2}")

    await asyncio.sleep(0.5)

    task3 = await system.submit_task("Download GitHub repository data")
    tasks.append(task3)
    print(f"   ✓ Tarea 3: {task3}")

    await asyncio.sleep(0.5)

    task4 = await system.submit_task("Analyze code quality and create report")
    tasks.append(task4)
    print(f"   ✓ Tarea 4: {task4}")

    print()
    print("⏳ Procesando tareas...")
    print()

    # Esperar procesamiento
    for i in range(8):
        await asyncio.sleep(1)
        stats = await system.state_manager.get_stats()
        print(f"   [{i+1}s] Completadas: {stats['completed']}/{stats['total_tasks']} | "
              f"En progreso: {stats['in_progress']} | "
              f"Pendientes: {stats['pending']}")

    print()

    # Mostrar resultados
    print("📊 RESULTADOS FINALES:")
    print("-" * 70)

    stats = await system.state_manager.get_stats()
    print(f"\n📈 Estadísticas:")
    print(f"   Total de tareas: {stats['total_tasks']}")
    print(f"   ✅ Completadas: {stats['completed']}")
    print(f"   ⏳ En progreso: {stats['in_progress']}")
    print(f"   📋 Pendientes: {stats['pending']}")
    print(f"   ❌ Fallidas: {stats['failed']}")
    print(f"   📝 Cambios de archivos: {stats['file_changes']}")
    print(f"   ⚠️  Problemas abiertos: {stats['open_problems']}")

    # Mostrar archivos modificados
    file_changes = await system.state_manager.get_recent_file_changes()
    if file_changes:
        print(f"\n📁 Archivos modificados ({len(file_changes)}):")
        for change in file_changes:
            emoji = {"created": "➕", "modified": "✏️", "deleted": "🗑️"}.get(change.action, "📝")
            print(f"   {emoji} {change.path} ({change.action}) - {change.agent}")

    # Mostrar tareas completadas
    all_tasks = await system.state_manager.get_all_tasks()
    completed_tasks = [t for t in all_tasks if t.status.value == "completed"]

    if completed_tasks:
        print(f"\n✅ Tareas completadas ({len(completed_tasks)}):")
        for task in completed_tasks:
            print(f"   - {task.id}: {task.description}")
            if task.subtasks:
                print(f"     Subtareas: {len(task.subtasks)}")

    # Mostrar problemas si existen
    problems = await system.state_manager.get_open_problems()
    if problems:
        print(f"\n⚠️  Problemas detectados ({len(problems)}):")
        for problem in problems:
            print(f"   [{problem.severity}] {problem.description}")

    print()
    print("=" * 70)

    # Detener sistema
    print("\n🛑 Deteniendo sistema...")
    await system.stop()
    print("✅ Sistema detenido correctamente")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(demo())
    except KeyboardInterrupt:
        print("\n👋 Interrumpido por el usuario")
