import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from backend.app.models.schema import (
    WorkspaceMember, Task, Decision, WeeklyDigest, EmailLog
)
from backend.app.services.email_service import email_service

logger = logging.getLogger("meetme.services.digest")

class DigestService:
    """
    Generates isolated, member-specific personalized weekly execution digests.
    Strict privacy isolation: members only see tasks and decisions relevant to them.
    """

    async def generate_member_digest(
        self,
        db: AsyncSession,
        workspace_id: str,
        member: WorkspaceMember,
        period_days: int = 7
    ) -> WeeklyDigest:
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)

        # 1. Fetch tasks assigned strictly to this member
        task_stmt = select(Task).where(
            Task.workspace_id == workspace_id,
            and_(
                Task.assignee_email == member.email
            )
        )
        task_res = await db.execute(task_stmt)
        member_tasks = task_res.scalars().all()

        completed_tasks = [t for t in member_tasks if t.status == "COMPLETED"]
        in_progress_tasks = [t for t in member_tasks if t.status in ["IN_PROGRESS", "ASSIGNED", "APPROVED"]]
        awaiting_approval_tasks = [t for t in member_tasks if t.status in ["AWAITING_APPROVAL", "DETECTED"]]
        overdue_tasks = [t for t in member_tasks if t.status == "OVERDUE"]

        # 2. Decisions involving this member or workspace wide
        dec_stmt = select(Decision).where(
            Decision.workspace_id == workspace_id,
            Decision.status == "ACTIVE"
        ).order_by(desc(Decision.created_at)).limit(5)
        dec_res = await db.execute(dec_stmt)
        recent_decisions = dec_res.scalars().all()

        # Build structured JSON payload
        content = {
            "member_name": member.full_name,
            "member_email": member.email,
            "member_role": member.role or "Team Member",
            "period_start": period_start.strftime("%Y-%m-%d"),
            "period_end": period_end.strftime("%Y-%m-%d"),
            "metrics": {
                "total_assigned": len(member_tasks),
                "completed": len(completed_tasks),
                "in_progress": len(in_progress_tasks),
                "awaiting_approval": len(awaiting_approval_tasks),
                "overdue": len(overdue_tasks)
            },
            "completed_tasks": [{"id": t.id, "title": t.title, "deadline": t.deadline} for t in completed_tasks],
            "in_progress_tasks": [{"id": t.id, "title": t.title, "deadline": t.deadline, "priority": t.priority} for t in in_progress_tasks],
            "overdue_tasks": [{"id": t.id, "title": t.title, "deadline": t.deadline} for t in overdue_tasks],
            "recent_decisions": [{"title": d.title, "summary": d.summary, "category": d.category} for d in recent_decisions]
        }

        # Generate responsive HTML email
        html_body = self._format_digest_html(content)

        # Upsert or save digest record
        digest = WeeklyDigest(
            workspace_id=workspace_id,
            member_id=member.id,
            recipient_email=member.email,
            recipient_name=member.full_name,
            period_start=period_start,
            period_end=period_end,
            content_json=content,
            html_body=html_body,
            status="GENERATED"
        )
        db.add(digest)
        await db.commit()
        await db.refresh(digest)
        return digest

    def _format_digest_html(self, content: Dict[str, Any]) -> str:
        metrics = content["metrics"]
        in_progress_items = "".join([
            f"<li style='margin-bottom: 8px;'><strong>{t['title']}</strong> &mdash; <span style='color: #FF7900;'>Due: {t.get('deadline') or 'Unset'}</span> [{t.get('priority', 'MEDIUM')}]</li>"
            for t in content.get("in_progress_tasks", [])
        ]) or "<li style='color: #737373;'>No tasks currently in progress.</li>"

        completed_items = "".join([
            f"<li style='margin-bottom: 8px; color: #A3A3A3;'><strike>{t['title']}</strike> <span style='color: #B6FF00;'>✓</span></li>"
            for t in content.get("completed_tasks", [])
        ]) or "<li style='color: #737373;'>No tasks completed this period.</li>"

        overdue_items = "".join([
            f"<li style='margin-bottom: 8px; color: #EF4444;'><strong>{t['title']}</strong> &mdash; Overdue since {t.get('deadline')}</li>"
            for t in content.get("overdue_tasks", [])
        ])

        overdue_block = f"""
        <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 6px; padding: 16px; margin-bottom: 20px;">
            <div style="color: #EF4444; font-weight: 700; margin-bottom: 8px; font-size: 13px;">⚠️ OVERDUE ACTION ITEMS</div>
            <ul style="margin: 0; padding-left: 20px; font-size: 13px;">{overdue_items}</ul>
        </div>
        """ if overdue_items else ""

        decisions_items = "".join([
            f"<li style='margin-bottom: 8px;'><strong>{d['title']}</strong>: {d.get('summary', '')}</li>"
            for d in content.get("recent_decisions", [])
        ]) or "<li style='color: #737373;'>No architectural decisions recorded this period.</li>"

        return f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 650px; margin: 0 auto; background: #0D0D0D; color: #E5E5E5; border: 1px solid #262626; border-radius: 8px; overflow: hidden;">
            <div style="background: #141414; padding: 24px; border-bottom: 1px solid #262626; display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <div style="font-size: 18px; font-weight: 800; color: #FFFFFF; letter-spacing: 0.5px;">MEETME <span style="color: #FF7900;">DIGEST</span></div>
                    <div style="font-size: 12px; color: #A3A3A3; margin-top: 4px;">Personalized Execution Brief &mdash; {content['period_start']} to {content['period_end']}</div>
                </div>
                <div style="background: rgba(255, 121, 0, 0.15); color: #FF7900; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-family: monospace; border: 1px solid rgba(255, 121, 0, 0.3);">
                    WEEKLY
                </div>
            </div>
            <div style="padding: 24px;">
                <p style="font-size: 15px; margin-top: 0; color: #FFFFFF;">
                    Hello <strong>{content['member_name']}</strong>,
                </p>
                <p style="font-size: 13px; line-height: 1.6; color: #A3A3A3;">
                    Here is your personal action item brief for this week.
                </p>

                <!-- Metric Cards -->
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 20px 0;">
                    <div style="background: #1A1A1A; border: 1px solid #262626; border-radius: 6px; padding: 12px; text-align: center;">
                        <div style="font-size: 20px; font-weight: 800; color: #FFFFFF;">{metrics['total_assigned']}</div>
                        <div style="font-size: 10px; color: #737373; text-transform: uppercase; margin-top: 4px;">Assigned</div>
                    </div>
                    <div style="background: #1A1A1A; border: 1px solid #262626; border-radius: 6px; padding: 12px; text-align: center;">
                        <div style="font-size: 20px; font-weight: 800; color: #B6FF00;">{metrics['completed']}</div>
                        <div style="font-size: 10px; color: #737373; text-transform: uppercase; margin-top: 4px;">Completed</div>
                    </div>
                    <div style="background: #1A1A1A; border: 1px solid #262626; border-radius: 6px; padding: 12px; text-align: center;">
                        <div style="font-size: 20px; font-weight: 800; color: #FF7900;">{metrics['in_progress']}</div>
                        <div style="font-size: 10px; color: #737373; text-transform: uppercase; margin-top: 4px;">In Progress</div>
                    </div>
                    <div style="background: #1A1A1A; border: 1px solid #262626; border-radius: 6px; padding: 12px; text-align: center;">
                        <div style="font-size: 20px; font-weight: 800; color: #EF4444;">{metrics['overdue']}</div>
                        <div style="font-size: 10px; color: #737373; text-transform: uppercase; margin-top: 4px;">Overdue</div>
                    </div>
                </div>

                {overdue_block}

                <!-- Active Tasks -->
                <div style="background: #141414; border: 1px solid #262626; border-radius: 6px; padding: 16px; margin-bottom: 20px;">
                    <div style="color: #FF7900; font-weight: 700; margin-bottom: 12px; font-size: 13px;">YOUR ACTIVE ACTION ITEMS</div>
                    <ul style="margin: 0; padding-left: 20px; font-size: 13px; line-height: 1.6;">{in_progress_items}</ul>
                </div>

                <!-- Recently Completed -->
                <div style="background: #141414; border: 1px solid #262626; border-radius: 6px; padding: 16px; margin-bottom: 20px;">
                    <div style="color: #B6FF00; font-weight: 700; margin-bottom: 12px; font-size: 13px;">COMPLETED RECENTLY</div>
                    <ul style="margin: 0; padding-left: 20px; font-size: 13px; line-height: 1.6;">{completed_items}</ul>
                </div>

                <!-- Decisions -->
                <div style="background: #141414; border: 1px solid #262626; border-radius: 6px; padding: 16px; margin-bottom: 20px;">
                    <div style="color: #FFFFFF; font-weight: 700; margin-bottom: 12px; font-size: 13px;">KEY ARCHITECTURAL DECISIONS</div>
                    <ul style="margin: 0; padding-left: 20px; font-size: 13px; line-height: 1.6; color: #A3A3A3;">{decisions_items}</ul>
                </div>

                <div style="text-align: center; margin-top: 24px; padding-top: 16px; border-top: 1px solid #262626;">
                    <a href="https://meetme-lake.vercel.app/tasks" style="background: #FF7900; color: #000000; text-decoration: none; padding: 10px 20px; font-weight: 700; font-size: 13px; border-radius: 4px; display: inline-block;">
                        Open Task Ledger &rarr;
                    </a>
                </div>
            </div>
        </div>
        """

    async def send_digest(self, db: AsyncSession, digest_id: str) -> Dict[str, Any]:
        """
        Dispatches the weekly digest email using the active email provider.
        """
        stmt = select(WeeklyDigest).where(WeeklyDigest.id == digest_id)
        res = await db.execute(stmt)
        digest = res.scalar_one_or_none()
        if not digest:
            raise ValueError(f"Weekly digest {digest_id} not found.")

        idempotency_key = f"weekly_digest_{digest.member_id}_{digest.period_start.strftime('%Y%m%d')}"
        subject = f"MEETME Weekly Execution Digest &mdash; {digest.period_start.strftime('%b %d')} - {digest.period_end.strftime('%b %d')}"

        send_res = await email_service.send_email(
            to=digest.recipient_email,
            subject=subject,
            html=digest.html_body,
            text="Please open this email in an HTML-compatible client to view your weekly digest.",
            recipient_name=digest.recipient_name,
            email_type="WEEKLY_DIGEST",
            idempotency_key=idempotency_key
        )

        if send_res.get("success"):
            digest.status = "SENT"
            digest.sent_at = datetime.utcnow()
            await db.commit()
            logger.info(f"Dispatched weekly digest to {digest.recipient_email} (Provider: {send_res.get('provider')})")

        return send_res

digest_service = DigestService()
