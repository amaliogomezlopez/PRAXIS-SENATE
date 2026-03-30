"""
Ejemplos de uso del sistema multi-agente
"""
import asyncio
from main import MultiAgentSystem


async def example_1_basic_tasks():
    """Ejemplo 1: Tareas básicas de creación de archivos"""
    print("=" * 60)
    print("EJEMPLO 1: Tareas Básicas")
    print("=" * 60)

    system = MultiAgentSystem(num_workers=2)
    await system.start()

    # Enviar tareas
    task1 = await system.submit_task("Create a hello world Python file")
    print(f"✓ Submitted task: {task1}")

    task2 = await system.submit_task("Create a configuration file")
    print(f"✓ Submitted task: {task2}")

    # Esperar un poco para que se procesen
    await asyncio.sleep(5)

    # Obtener estadísticas
    stats = await system.state_manager.get_stats()
    print(f"\n📊 Stats: {stats}")

    await system.stop()
    print("\n✅ Example 1 completed\n")


async def example_2_web_tasks():
    """Ejemplo 2: Tareas que involucran acceso web"""
    print("=" * 60)
    print("EJEMPLO 2: Tareas Web")
    print("=" * 60)

    system = MultiAgentSystem(num_workers=3)
    await system.start()

    # Tareas web
    task1 = await system.submit_task("Search for Python best practices")
    task2 = await system.submit_task("Download data from GitHub API")
    task3 = await system.submit_task("Find information about asyncio patterns")

    print(f"✓ Submitted {3} web tasks")

    await asyncio.sleep(8)

    stats = await system.state_manager.get_stats()
    print(f"\n📊 Stats: {stats}")

    # Ver cambios de archivos
    file_changes = await system.state_manager.get_recent_file_changes()
    print(f"\n📁 File changes: {len(file_changes)}")
    for change in file_changes:
        print(f"  - {change.action}: {change.path}")

    await system.stop()
    print("\n✅ Example 2 completed\n")


async def example_3_parallel_processing():
    """Ejemplo 3: Procesamiento paralelo de múltiples tareas"""
    print("=" * 60)
    print("EJEMPLO 3: Procesamiento Paralelo")
    print("=" * 60)

    system = MultiAgentSystem(num_workers=4)
    await system.start()

    # Enviar múltiples tareas simultáneamente
    tasks = [
        "Create data analysis script",
        "Search for machine learning tutorials",
        "Analyze code quality",
        "Download documentation",
        "Create test files",
        "Search for best practices",
    ]

    submitted_tasks = []
    for task_desc in tasks:
        task_id = await system.submit_task(task_desc)
        submitted_tasks.append(task_id)
        print(f"✓ Submitted: {task_desc}")

    print(f"\n⏳ Processing {len(submitted_tasks)} tasks in parallel...")

    # Esperar procesamiento
    await asyncio.sleep(10)

    # Ver todas las tareas
    all_tasks = await system.state_manager.get_all_tasks()
    print(f"\n📋 Total tasks in system: {len(all_tasks)}")

    completed = sum(1 for t in all_tasks if t.status.value == "completed")
    print(f"✅ Completed: {completed}")

    in_progress = sum(1 for t in all_tasks if t.status.value == "in_progress")
    print(f"⏳ In progress: {in_progress}")

    failed = sum(1 for t in all_tasks if t.status.value == "failed")
    print(f"❌ Failed: {failed}")

    await system.stop()
    print("\n✅ Example 3 completed\n")


async def example_4_with_dashboard():
    """Ejemplo 4: Sistema completo con dashboard interactivo"""
    print("=" * 60)
    print("EJEMPLO 4: Sistema con Dashboard Interactivo")
    print("=" * 60)
    print("\n🎨 Iniciando dashboard visual...")
    print("   Presiona Ctrl+C para salir\n")

    system = MultiAgentSystem(num_workers=3)
    await system.start()

    # Crear un task que envíe tareas periódicamente
    async def submit_periodic_tasks():
        tasks = [
            "Create configuration file",
            "Analyze system performance",
            "Search for optimization tips",
            "Create documentation",
            "Download resources",
            "Analyze code structure",
        ]

        for i, task_desc in enumerate(tasks):
            await asyncio.sleep(3)  # Esperar 3 segundos entre tareas
            await system.submit_task(task_desc)

    # Ejecutar tareas periódicas en background
    periodic_task = asyncio.create_task(submit_periodic_tasks())

    # Ejecutar dashboard
    try:
        await system.run_with_dashboard()
    finally:
        periodic_task.cancel()
        await system.stop()

    print("\n✅ Example 4 completed\n")


async def example_5_error_handling():
    """Ejemplo 5: Manejo de errores y detección de problemas"""
    print("=" * 60)
    print("EJEMPLO 5: Manejo de Errores")
    print("=" * 60)

    system = MultiAgentSystem(num_workers=2)
    await system.start()

    # Tareas que podrían generar problemas
    await system.submit_task("Create file with invalid path //invalid//path")
    await system.submit_task("Download from invalid URL")
    await system.submit_task("Analyze non-existent file")

    print("✓ Submitted tasks that may cause problems")
    print("⏳ Processing...")

    await asyncio.sleep(6)

    # Ver problemas detectados
    problems = await system.state_manager.get_open_problems()
    print(f"\n⚠️  Problems detected: {len(problems)}")
    for problem in problems:
        print(f"  - [{problem.severity}] {problem.description}")

    await system.stop()
    print("\n✅ Example 5 completed\n")


async def run_all_examples():
    """Ejecutar todos los ejemplos secuencialmente"""
    print("\n" + "=" * 60)
    print(" MULTI-AGENT SYSTEM - EXAMPLES")
    print("=" * 60 + "\n")

    await example_1_basic_tasks()
    await asyncio.sleep(1)

    await example_2_web_tasks()
    await asyncio.sleep(1)

    await example_3_parallel_processing()
    await asyncio.sleep(1)

    # Nota: example_4 se ejecuta por separado porque es interactivo
    print("=" * 60)
    print("Para ejecutar el dashboard interactivo, usa:")
    print("  python example_usage.py --dashboard")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import sys

    if "--dashboard" in sys.argv or "-d" in sys.argv:
        # Ejecutar ejemplo con dashboard
        asyncio.run(example_4_with_dashboard())
    elif "--errors" in sys.argv or "-e" in sys.argv:
        # Ejecutar ejemplo de manejo de errores
        asyncio.run(example_5_error_handling())
    else:
        # Ejecutar todos los ejemplos automáticos
        asyncio.run(run_all_examples())
