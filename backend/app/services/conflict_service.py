import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from backend.app.models.schema import (
    Decision, DecisionConflict, DecisionResolution, Approval, Meeting, AutomationLog
)
from backend.app.services.groq_service import groq_service

logger = logging.getLogger("meetme.services.conflict")

CONFLICT_DETECTION_PROMPT = """You are the MEETME DECISION CONFLICT & CONTRADICTION DETECTOR.
Compare NEW decisions from the current meeting against HISTORICAL decisions from previous meetings in this workspace.

Analyze each pair to determine if they conflict.
Types of relationships:
- "GENUINE_CONTRADICTION": Directly opposing choices (e.g., "Use MongoDB" vs "Migrate to PostgreSQL", "Build in React" vs "Rebuild in Vue").
- "TECHNICAL_REVERSAL": An earlier architectural consensus is discarded or reversed.
- "REQUIREMENT_CONFLICT": Changes scope or contradictory functional requirements.
- "REFINEMENT": A compatible enhancement or elaboration (NOT a conflict).
- "UNRELATED": Completely different topics or areas (NOT a conflict).

For any genuine conflict, return a structured object:
{
  "conflicts": [
    {
      "previous_decision_id": "string",
      "new_decision_title": "string",
      "conflict_type": "GENUINE_CONTRADICTION" | "TECHNICAL_REVERSAL" | "REQUIREMENT_CONFLICT",
      "explanation": "Clear explanation of why this contradicts the previous decision",
      "confidence": float (0.8 - 1.0),
      "suggested_resolution": "Recommended action (e.g., 'Formally supersede MongoDB with PostgreSQL and update schema migration plan')"
    }
  ]
}

If there are NO conflicts or decisions are compatible refinements/unrelated, return {"conflicts": []}.
Return ONLY valid JSON.
"""

class ConflictService:
    """
    Evaluates new decisions against historical workspace decisions to detect
    direct contradictions, reversals, and scope conflicts.
    """

    async def detect_conflicts(
        self,
        db: AsyncSession,
        workspace_id: str,
        current_meeting_id: str,
        new_decisions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Retrieves active historical decisions and evaluates conflicts with new decisions.
        """
        if not new_decisions:
            return []

        # 1. Fetch active historical decisions from previous meetings in this workspace
        hist_stmt = select(Decision).where(
            Decision.workspace_id == workspace_id,
            Decision.status == "ACTIVE"
        )
        if current_meeting_id:
            hist_stmt = hist_stmt.where(Decision.meeting_id != current_meeting_id)

        hist_res = await db.execute(hist_stmt)
        historical_decisions = hist_res.scalars().all()

        if not historical_decisions:
            return []

        # Prepare context for LLM comparison
        hist_payload = [
            {
                "id": hd.id,
                "title": hd.title,
                "summary": hd.summary,
                "category": hd.category,
                "meeting_id": hd.meeting_id,
                "evidence": hd.evidence_quote
            }
            for hd in historical_decisions
        ]

        messages = [
            {"role": "system", "content": CONFLICT_DETECTION_PROMPT},
            {
                "role": "user",
                "content": f"HISTORICAL DECISIONS:\n{json.dumps(hist_payload, indent=2)}\n\nNEW DECISIONS TO EVALUATE:\n{json.dumps(new_decisions, indent=2)}"
            }
        ]

        llm_conflicts = []
        res = await groq_service.chat_completion(
            messages=messages,
            response_format={"type": "json_object"}
        )

        if not res.get("fallback"):
            try:
                parsed = json.loads(res["content"])
                llm_conflicts = parsed.get("conflicts", [])
            except Exception as e:
                logger.error(f"Failed to parse conflict JSON from Groq: {e}")

        # Deterministic rule-based fallback check (e.g. MongoDB vs PostgreSQL)
        if not llm_conflicts:
            llm_conflicts = self._rule_based_conflict_check(historical_decisions, new_decisions)

        # 2. Persist detected conflicts & create human approval gate records
        persisted_conflicts = []
        for c in llm_conflicts:
            prev_id = c.get("previous_decision_id")
            prev_dec = next((hd for hd in historical_decisions if hd.id == prev_id), None)
            new_title = c.get("new_decision_title", "")
            matching_new = next((nd for nd in new_decisions if nd.get("title", "") == new_title), None)

            if not prev_dec:
                continue

            # Prevent duplicate conflict records
            dup_check = select(DecisionConflict).where(
                DecisionConflict.workspace_id == workspace_id,
                DecisionConflict.previous_decision_id == prev_dec.id,
                DecisionConflict.new_meeting_id == current_meeting_id,
                DecisionConflict.status == "UNRESOLVED"
            )
            dup_res = await db.execute(dup_check)
            if dup_res.scalar_one_or_none():
                continue

            conflict_obj = DecisionConflict(
                workspace_id=workspace_id,
                previous_decision_id=prev_dec.id,
                new_decision_id=matching_new.get("id") if matching_new else None,
                previous_meeting_id=prev_dec.meeting_id,
                new_meeting_id=current_meeting_id,
                conflict_type=c.get("conflict_type", "GENUINE_CONTRADICTION"),
                explanation=c.get("explanation", "Contradicts previous active decision."),
                confidence=float(c.get("confidence", 0.95)),
                suggested_resolution=c.get("suggested_resolution", "Review and choose whether to accept the new decision or retain previous consensus."),
                status="UNRESOLVED",
                source_evidence_prev=prev_dec.evidence_quote,
                source_evidence_new=matching_new.get("evidence") if matching_new else ""
            )
            db.add(conflict_obj)
            await db.flush()

            # Create an Approval record so conflict appears in the Human Approval Gate!
            approval = Approval(
                workspace_id=workspace_id,
                task_id=f"conflict-{conflict_obj.id}",
                meeting_id=current_meeting_id,
                action_category="DECISION_RESOLUTION",
                target_platform="INTERNAL",
                status="PENDING",
                proposed_payload={
                    "conflict_id": conflict_obj.id,
                    "conflict_type": conflict_obj.conflict_type,
                    "previous_decision": {
                        "id": prev_dec.id,
                        "title": prev_dec.title,
                        "summary": prev_dec.summary,
                        "evidence": prev_dec.evidence_quote
                    },
                    "new_decision": {
                        "title": new_title,
                        "summary": matching_new.get("summary", new_title) if matching_new else new_title,
                        "evidence": matching_new.get("evidence", "") if matching_new else ""
                    },
                    "explanation": conflict_obj.explanation,
                    "suggested_resolution": conflict_obj.suggested_resolution
                }
            )
            db.add(approval)
            persisted_conflicts.append(conflict_obj)
            logger.warning(f"DECISION CONFLICT DETECTED in workspace {workspace_id}: '{prev_dec.title}' vs '{new_title}'")

        await db.commit()
        return [
            {
                "id": pc.id,
                "conflict_type": pc.conflict_type,
                "explanation": pc.explanation,
                "previous_decision_id": pc.previous_decision_id,
                "suggested_resolution": pc.suggested_resolution,
                "status": pc.status
            }
            for pc in persisted_conflicts
        ]

    def _rule_based_conflict_check(
        self,
        historical_decisions: List[Decision],
        new_decisions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Deterministic rule-based conflict detector for database, architecture, and framework reversals.
        """
        conflicts = []
        for hd in historical_decisions:
            hd_lower = (hd.title + " " + (hd.summary or "")).lower()
            for nd in new_decisions:
                nd_lower = (nd.get("title", "") + " " + nd.get("summary", "")).lower()

                # Rule 1: MongoDB vs PostgreSQL reversal
                if "mongodb" in hd_lower and ("postgresql" in nd_lower or "postgres" in nd_lower):
                    conflicts.append({
                        "previous_decision_id": hd.id,
                        "new_decision_title": nd.get("title"),
                        "conflict_type": "GENUINE_CONTRADICTION",
                        "explanation": "Contradicts previous consensus adopting MongoDB. New decision proposes migrating to PostgreSQL.",
                        "confidence": 0.98,
                        "suggested_resolution": "Formally accept PostgreSQL as primary database and mark previous MongoDB decision as SUPERSEDED."
                    })
                # Rule 2: PostgreSQL vs MongoDB reversal
                elif ("postgresql" in hd_lower or "postgres" in hd_lower) and "mongodb" in nd_lower:
                    conflicts.append({
                        "previous_decision_id": hd.id,
                        "new_decision_title": nd.get("title"),
                        "conflict_type": "GENUINE_CONTRADICTION",
                        "explanation": "Contradicts previous consensus adopting PostgreSQL. New decision proposes migrating to MongoDB.",
                        "confidence": 0.98,
                        "suggested_resolution": "Review database migration requirement and choose whether to supersede PostgreSQL."
                    })

        return conflicts

    async def resolve_conflict(
        self,
        db: AsyncSession,
        conflict_id: str,
        action: str,  # "ACCEPT_NEW" | "RETAIN_PREVIOUS" | "MANUAL_EDIT" | "MARK_UNRESOLVED"
        user_id: Optional[str] = None,
        resolution_notes: Optional[str] = None,
        custom_decision_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes human resolution of a decision conflict.
        - ACCEPT_NEW: marks previous decision as SUPERSEDED, new decision as ACTIVE.
        - RETAIN_PREVIOUS: retains previous decision as ACTIVE, marks new as REJECTED.
        - MANUAL_EDIT: creates refined consensus decision.
        """
        stmt = select(DecisionConflict).where(DecisionConflict.id == conflict_id)
        res = await db.execute(stmt)
        conflict = res.scalar_one_or_none()
        if not conflict:
            raise ValueError(f"Decision conflict {conflict_id} not found.")

        # Fetch previous decision
        prev_dec = None
        if conflict.previous_decision_id:
            p_stmt = select(Decision).where(Decision.id == conflict.previous_decision_id)
            prev_dec = (await db.execute(p_stmt)).scalar_one_or_none()

        # Fetch new decision
        new_dec = None
        if conflict.new_decision_id:
            n_stmt = select(Decision).where(Decision.id == conflict.new_decision_id)
            new_dec = (await db.execute(n_stmt)).scalar_one_or_none()

        if action == "ACCEPT_NEW":
            conflict.status = "ACCEPTED_NEW"
            if prev_dec:
                prev_dec.status = "SUPERSEDED"
                if new_dec:
                    prev_dec.superseded_by_id = new_dec.id
            if new_dec:
                new_dec.status = "ACTIVE"
        elif action == "RETAIN_PREVIOUS":
            conflict.status = "RETAINED_PREVIOUS"
            if prev_dec:
                prev_dec.status = "ACTIVE"
            if new_dec:
                new_dec.status = "REJECTED"
        elif action == "MANUAL_EDIT":
            conflict.status = "MANUAL_EDIT"
            if custom_decision_payload and prev_dec:
                prev_dec.title = custom_decision_payload.get("title", prev_dec.title)
                prev_dec.summary = custom_decision_payload.get("summary", prev_dec.summary)
                prev_dec.status = "ACTIVE"
        else:
            conflict.status = "UNRESOLVED"

        # Record resolution audit log
        res_record = DecisionResolution(
            conflict_id=conflict.id,
            workspace_id=conflict.workspace_id,
            resolved_by_user_id=user_id,
            action_taken=action,
            resolution_notes=resolution_notes or f"Conflict resolved with action: {action}",
            resolved_at=datetime.utcnow()
        )
        db.add(res_record)

        # Mark corresponding approval record as APPROVED
        appr_stmt = select(Approval).where(
            Approval.workspace_id == conflict.workspace_id,
            Approval.action_category == "DECISION_RESOLUTION",
            Approval.status == "PENDING"
        )
        apprs = (await db.execute(appr_stmt)).scalars().all()
        for a in apprs:
            if a.proposed_payload and a.proposed_payload.get("conflict_id") == conflict_id:
                a.status = "APPROVED"
                a.approval_notes = resolution_notes
                a.approved_at = datetime.utcnow()

        await db.commit()
        return {
            "status": "SUCCESS",
            "conflict_id": conflict_id,
            "action_taken": action,
            "conflict_status": conflict.status,
            "previous_decision_status": prev_dec.status if prev_dec else None,
            "new_decision_status": new_dec.status if new_dec else None
        }

conflict_service = ConflictService()
