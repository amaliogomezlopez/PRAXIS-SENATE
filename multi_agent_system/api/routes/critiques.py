"""
Critique endpoints
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/critiques", tags=["critiques"])


class CritiqueResponse(BaseModel):
    id: str
    task_id: str
    approved: bool
    reasoning: Optional[str] = None
    confidence: Optional[int] = None
    risks: Optional[List[str]] = None
    gaps: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None
    created_at: datetime
    source: Optional[str] = None


@router.get("", response_model=List[CritiqueResponse])
async def list_critiques(request: Request, task_id: Optional[str] = None):
    """List critique history, optionally filtered by task_id"""
    # Critiques are stored in the CriticAgent's critique_history
    # For now, return empty list until PersistentStateManager is fully integrated
    return []


@router.get("/{critique_id}", response_model=CritiqueResponse)
async def get_critique(critique_id: str, request: Request):
    """Get critique details"""
    # TODO: Implement with PersistentStateManager
    raise HTTPException(status_code=501, detail="Critique retrieval not yet implemented - requires PersistentStateManager integration")


@router.get("/analytics/summary")
async def get_critique_analytics(request: Request):
    """Get critique analytics summary"""
    # TODO: Implement analytics when critiques are stored
    return {
        "total_critiques": 0,
        "approval_rate": 0.0,
        "average_confidence": 0.0,
        "most_common_risks": [],
        "most_common_gaps": []
    }
