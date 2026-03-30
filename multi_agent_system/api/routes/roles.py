"""
Roles API - View and edit agent role files
"""
import logging
from pathlib import Path
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/roles", tags=["roles"])

ROLES_DIR = Path(__file__).parent.parent.parent / "roles"


class RoleUpdate(BaseModel):
    content: str


class RoleInfo(BaseModel):
    name: str
    filename: str
    size: int


@router.get("", response_model=List[RoleInfo])
async def list_roles():
    """List all available role files"""
    roles = []
    if ROLES_DIR.exists():
        for f in ROLES_DIR.glob("*.md"):
            roles.append({
                "name": f.stem.replace("_", " ").title(),
                "filename": f.name,
                "size": f.stat().st_size
            })
    return roles


@router.get("/{filename}")
async def get_role(filename: str):
    """Get the content of a role file"""
    # Security: prevent path traversal
    safe_name = Path(filename).name
    role_path = ROLES_DIR / safe_name

    if not role_path.exists():
        raise HTTPException(status_code=404, detail=f"Role file '{filename}' not found")

    if role_path.suffix != ".md":
        raise HTTPException(status_code=400, detail="Only .md files are allowed")

    try:
        content = role_path.read_text(encoding="utf-8")
        return {"filename": safe_name, "content": content}
    except Exception as e:
        logger.error(f"Failed to read role file {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read role file")


@router.put("/{filename}")
async def update_role(filename: str, update: RoleUpdate):
    """Update a role file"""
    safe_name = Path(filename).name
    role_path = ROLES_DIR / safe_name

    if not role_path.exists():
        raise HTTPException(status_code=404, detail=f"Role file '{filename}' not found")

    if role_path.suffix != ".md":
        raise HTTPException(status_code=400, detail="Only .md files are allowed")

    # Create backup before writing
    backup_path = role_path.with_suffix('.md.bak')
    try:
        backup_path.write_text(role_path.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass  # Backup is best effort

    try:
        role_path.write_text(update.content, encoding="utf-8")
        logger.info(f"Updated role file: {filename}")
        return {"filename": safe_name, "success": True}
    except Exception as e:
        logger.error(f"Failed to update role file {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update role file")
