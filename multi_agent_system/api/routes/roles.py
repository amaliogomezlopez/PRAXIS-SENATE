"""
Roles API - View, edit, and configure agent role files with Jinja2 template support
"""
import logging
from pathlib import Path
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from roles.loader import get_role_loader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/roles", tags=["roles"])

ROLES_DIR = Path(__file__).parent.parent.parent / "roles"


class RoleUpdate(BaseModel):
    content: str


class TemplateVarsUpdate(BaseModel):
    variables: Dict[str, Any]


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

    backup_path = role_path.with_suffix('.md.bak')
    try:
        backup_path.write_text(role_path.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass

    try:
        role_path.write_text(update.content, encoding="utf-8")
        # Invalidate loader caches so next LLM call picks up the change
        loader = get_role_loader()
        loader.clear_cache()
        logger.info(f"Updated role file: {filename}")
        return {"filename": safe_name, "success": True}
    except Exception as e:
        logger.error(f"Failed to update role file {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update role file")


# ── Template Variables API ───────────────────────────────

@router.get("/{filename}/variables")
async def get_role_variables(filename: str):
    """Discover template variables ({{ var }}) in a role file and their current values."""
    safe_name = Path(filename).name
    stem = safe_name.replace(".md", "")

    role_path = ROLES_DIR / safe_name
    if not role_path.exists():
        raise HTTPException(status_code=404, detail=f"Role file '{filename}' not found")

    try:
        loader = get_role_loader()
        variables = loader.discover_variables(stem)
        return {"filename": safe_name, "variables": variables}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Role file '{filename}' not found")
    except Exception as e:
        logger.error(f"Failed to discover variables for {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to discover variables")


@router.put("/{filename}/variables")
async def update_role_variables(filename: str, update: TemplateVarsUpdate):
    """Update template variable overrides for a role file."""
    safe_name = Path(filename).name
    stem = safe_name.replace(".md", "")

    role_path = ROLES_DIR / safe_name
    if not role_path.exists():
        raise HTTPException(status_code=404, detail=f"Role file '{filename}' not found")

    try:
        loader = get_role_loader()
        loader.set_template_vars(stem, update.variables)
        updated_vars = loader.discover_variables(stem)
        logger.info(f"Updated template variables for {filename}: {update.variables}")
        return {"filename": safe_name, "variables": updated_vars, "success": True}
    except Exception as e:
        logger.error(f"Failed to update variables for {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update variables")


@router.get("/{filename}/rendered")
async def get_rendered_role(filename: str):
    """Get the rendered (Jinja2-processed) content of a role file."""
    safe_name = Path(filename).name
    stem = safe_name.replace(".md", "")

    role_path = ROLES_DIR / safe_name
    if not role_path.exists():
        raise HTTPException(status_code=404, detail=f"Role file '{filename}' not found")

    try:
        loader = get_role_loader()
        rendered = loader._render(stem)
        return {"filename": safe_name, "content": rendered}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Role file '{filename}' not found")
    except Exception as e:
        logger.error(f"Failed to render role {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to render role file")
