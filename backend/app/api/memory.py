from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, or_
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.schema import Decision, Commitment, DecisionConflict, DecisionResolution
from backend.app.services.conflict_service import conflict_service

router = APIRouter(prefix="/api/memory", tags=["memory"])

class ResolveConflictRequest(BaseModel):
    action: str # "ACCEPT_NEW" | "RETAIN_PREVIOUS" | "MANUAL_EDIT" | "MARK_UNRESOLVED"
    notes: Optional[str] = None
    user_id: Optional[str] = None
    custom_decision_payload: Optional[Dict[str, Any]] = None

@router.get("/decisions")
async def list_decisions(
    workspace_id: Optional[str] = None,
    status: Optional[str] = None, # ACTIVE, SUPERSEDED, CONFLICTED, OBSOLETE
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    ws_id = workspace_id or settings.DEFAULT_WORKSPACE_ID
    stmt = select(Decision).where(Decision.workspace_id == ws_id)
    if status:
        stmt = stmt.where(Decision.status == status)
    if category:
        stmt = stmt.where(Decision.category == category)
    if search:
        stmt = stmt.where(or_(
            Decision.title.ilike(f"%{search}%"),
            Decision.summary.ilike(f"%{search}%")
        ))
    stmt = stmt.order_by(desc(Decision.created_at)).limit(limit)
    res = await db.execute(stmt)
    decisions = res.scalars().all()
    return [
        {
            "id": d.id,
            "workspace_id": d.workspace_id,
            "meeting_id": d.meeting_id,
            "title": d.title,
            "summary": d.summary,
            "context": d.context,
            "category": d.category,
            "status": d.status,
            "decided_by_name": d.decided_by_name,
            "evidence_quote": d.evidence_quote,
            "superseded_by_id": d.superseded_by_id,
            "confidence": d.confidence,
            "created_at": d.created_at.isoformat() if d.created_at else None
        }
        for d in decisions
    ]

@router.get("/commitments")
async def list_commitments(
    workspace_id: Optional[str] = None,
    assignee_name: Optional[str] = None,
    status: Optional[str] = None, # PENDING, IN_PROGRESS, COMPLETED, OVERDUE, DELAYED
    is_delayed: Optional[bool] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    ws_id = workspace_id or settings.DEFAULT_WORKSPACE_ID
    stmt = select(Commitment).where(Commitment.workspace_id == ws_id)
    if assignee_name:
        stmt = stmt.where(Commitment.assignee_name.ilike(f"%{assignee_name}%"))
    if status:
        stmt = stmt.where(Commitment.status == status)
    if is_delayed is True:
        stmt = stmt.where(Commitment.delay_count > 0)
    stmt = stmt.order_by(desc(Commitment.created_at)).limit(limit)
    res = await db.execute(stmt)
    commitments = res.scalars().all()
    return [
        {
            "id": c.id,
            "workspace_id": c.workspace_id,
            "meeting_id": c.meeting_id,
            "task_id": c.task_id,
            "title": c.title,
            "description": c.description,
            "assignee_name": c.assignee_name,
            "assignee_email": c.assignee_email,
            "original_deadline": c.original_deadline,
            "current_deadline": c.current_deadline,
            "status": c.status,
            "delay_count": c.delay_count,
            "blockers": c.blockers or [],
            "completion_evidence": c.completion_evidence,
            "related_meeting_ids": c.related_meeting_ids or [],
            "confidence": c.confidence,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in commitments
    ]

@router.get("/conflicts")
async def list_conflicts(
    workspace_id: Optional[str] = None,
    status: Optional[str] = None, # UNRESOLVED, ACCEPTED_NEW, RETAINED_PREVIOUS, MANUAL_EDIT
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    ws_id = workspace_id or settings.DEFAULT_WORKSPACE_ID
    stmt = select(DecisionConflict).where(DecisionConflict.workspace_id == ws_id)
    if status:
        stmt = stmt.where(DecisionConflict.status == status)
    stmt = stmt.order_by(desc(DecisionConflict.created_at)).limit(limit)
    res = await db.execute(stmt)
    conflicts = res.scalars().all()

    # Enrich with previous and new decision titles
    enriched = []
    for cf in conflicts:
        prev_title = "Previous Decision"
        if cf.previous_decision_id:
            p_res = await db.execute(select(Decision).where(Decision.id == cf.previous_decision_id))
            pd = p_res.scalar_one_or_none()
            if pd:
                prev_title = pd.title

        new_title = "New Decision"
        if cf.new_decision_id:
            n_res = await db.execute(select(Decision).where(Decision.id == cf.new_decision_id))
            nd = n_res.scalar_one_or_none()
            if nd:
                new_title = nd.title

        enriched.append({
            "id": cf.id,
            "workspace_id": cf.workspace_id,
            "previous_decision_id": cf.previous_decision_id,
            "previous_decision_title": prev_title,
            "new_decision_id": cf.new_decision_id,
            "new_decision_title": new_title,
            "previous_meeting_id": cf.previous_meeting_id,
            "new_meeting_id": cf.new_meeting_id,
            "conflict_type": cf.conflict_type,
            "explanation": cf.explanation,
            "confidence": cf.confidence,
            "suggested_resolution": cf.suggested_resolution,
            "status": cf.status,
            "source_evidence_prev": cf.source_evidence_prev,
            "source_evidence_new": cf.source_evidence_new,
            "created_at": cf.created_at.isoformat() if cf.created_at else None
        })
    return enriched

@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict_endpoint(
    conflict_id: str,
    payload: ResolveConflictRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        res = await conflict_service.resolve_conflict(
            db=db,
            conflict_id=conflict_id,
            action=payload.action,
            user_id=payload.user_id,
            resolution_notes=payload.notes,
            custom_decision_payload=payload.custom_decision_payload
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
