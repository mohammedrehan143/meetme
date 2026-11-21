from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel, EmailStr

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.schema import WorkspaceMember, Task

router = APIRouter(prefix="/api/team", tags=["team"])

class CreateMemberRequest(BaseModel):
    full_name: str
    email: str
    role: str = "member" # admin, member, viewer
    title: str = "Team Member"
    workspace_id: Optional[str] = None

class UpdateMemberRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    title: Optional[str] = None

@router.get("")
async def list_members(
    workspace_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    if workspace_id:
        stmt = select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
    else:
        stmt = select(WorkspaceMember)
    res = await db.execute(stmt)
    members = res.scalars().all()

    output = []
    for m in members:
        # Count tasks assigned
        t_stmt = select(Task).where(Task.assignee_id == m.id)
        t_res = await db.execute(t_stmt)
        assigned_tasks = t_res.scalars().all()

        output.append({
            "id": m.id,
            "full_name": m.full_name,
            "email": m.email,
            "role": m.role,
            "title": m.title,
            "tasks_count": len(assigned_tasks),
            "completed_tasks": len([t for t in assigned_tasks if t.status == "COMPLETED"]),
            "created_at": m.created_at.isoformat() if m.created_at else None
        })

    return output

@router.post("")
async def create_member(
    payload: CreateMemberRequest,
    db: AsyncSession = Depends(get_db)
):
    ws_id = payload.workspace_id or settings.DEFAULT_WORKSPACE_ID

    # Ensure workspace exists
    from backend.app.models.schema import Workspace
    ws_check = await db.execute(select(Workspace).where(Workspace.id == ws_id))
    if not ws_check.scalar_one_or_none():
        any_ws = (await db.execute(select(Workspace).limit(1))).scalar_one_or_none()
        if any_ws:
            ws_id = any_ws.id
        else:
            ws = Workspace(id=ws_id, name="MEETME Workspace", slug="default")
            db.add(ws)
            await db.flush()

    # Check for existing email in workspace
    check_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == ws_id,
        WorkspaceMember.email == payload.email
    )
    res = await db.execute(check_stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Team member with this email already exists in workspace.")

    member = WorkspaceMember(
        workspace_id=ws_id,
        full_name=payload.full_name,
        email=payload.email,
        role=payload.role,
        title=payload.title
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return {"id": member.id, "full_name": member.full_name, "email": member.email, "title": member.title}

@router.patch("/{member_id}")
async def update_member(
    member_id: str,
    payload: UpdateMemberRequest,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(WorkspaceMember).where(WorkspaceMember.id == member_id)
    res = await db.execute(stmt)
    member = res.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if payload.full_name is not None:
        member.full_name = payload.full_name
    if payload.email is not None:
        member.email = payload.email
    if payload.role is not None:
        member.role = payload.role
    if payload.title is not None:
        member.title = payload.title

    await db.commit()
    await db.refresh(member)
    return {"id": member.id, "full_name": member.full_name, "email": member.email, "title": member.title}
