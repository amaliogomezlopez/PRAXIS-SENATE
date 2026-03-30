"""
Herramientas para operaciones de archivos
"""
import os
import asyncio
from pathlib import Path
from typing import Optional, List
from datetime import datetime


class FileOperations:
    """Operaciones de archivos para agentes"""

    def __init__(self, workspace_dir: str = "/workspace/agent_workspace"):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    async def create_file(self, path: str, content: str) -> dict:
        """Crear un nuevo archivo"""
        try:
            file_path = self.workspace_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Ejecutar operación de I/O en executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: file_path.write_text(content)
            )

            return {
                "success": True,
                "path": str(file_path),
                "action": "created",
                "size": len(content)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": path
            }

    async def read_file(self, path: str) -> dict:
        """Leer un archivo"""
        try:
            file_path = self.workspace_dir / path
            if not file_path.exists():
                return {
                    "success": False,
                    "error": "File not found",
                    "path": path
                }

            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                None,
                file_path.read_text
            )

            return {
                "success": True,
                "content": content,
                "path": str(file_path),
                "size": len(content)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": path
            }

    async def update_file(self, path: str, content: str) -> dict:
        """Actualizar un archivo existente"""
        try:
            file_path = self.workspace_dir / path
            if not file_path.exists():
                return {
                    "success": False,
                    "error": "File not found",
                    "path": path
                }

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: file_path.write_text(content)
            )

            return {
                "success": True,
                "path": str(file_path),
                "action": "modified",
                "size": len(content)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": path
            }

    async def delete_file(self, path: str) -> dict:
        """Eliminar un archivo"""
        try:
            file_path = self.workspace_dir / path
            if not file_path.exists():
                return {
                    "success": False,
                    "error": "File not found",
                    "path": path
                }

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                file_path.unlink
            )

            return {
                "success": True,
                "path": str(file_path),
                "action": "deleted"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": path
            }

    async def list_files(self, directory: str = "") -> dict:
        """Listar archivos en un directorio"""
        try:
            dir_path = self.workspace_dir / directory
            if not dir_path.exists():
                return {
                    "success": False,
                    "error": "Directory not found",
                    "path": directory
                }

            loop = asyncio.get_event_loop()
            files = await loop.run_in_executor(
                None,
                lambda: [
                    {
                        "name": f.name,
                        "path": str(f.relative_to(self.workspace_dir)),
                        "is_dir": f.is_dir(),
                        "size": f.stat().st_size if f.is_file() else 0
                    }
                    for f in dir_path.iterdir()
                ]
            )

            return {
                "success": True,
                "files": files,
                "count": len(files)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": directory
            }

    async def search_files(self, pattern: str, directory: str = "") -> dict:
        """Buscar archivos por patrón"""
        try:
            dir_path = self.workspace_dir / directory
            if not dir_path.exists():
                return {
                    "success": False,
                    "error": "Directory not found",
                    "path": directory
                }

            loop = asyncio.get_event_loop()
            matches = await loop.run_in_executor(
                None,
                lambda: [
                    str(f.relative_to(self.workspace_dir))
                    for f in dir_path.rglob(pattern)
                ]
            )

            return {
                "success": True,
                "matches": matches,
                "count": len(matches)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "pattern": pattern
            }
