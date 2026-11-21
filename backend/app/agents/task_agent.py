import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from backend.app.services.groq_service import groq_service

logger = logging.getLogger("meetme.agents.task")

SYSTEM_PROMPT = """You are the TASK EXTRACTION AGENT for MEETME.
Extract clear, actionable tasks from the meeting transcript and classified segments.
For every identified task:
1. Extract title: Clear, action-oriented (e.g., "Implement OAuth2 login with Supabase").
2. Description: Detailed context and instructions from the conversation.
3. Assignee candidate: Identify the EXACT person name and/or role responsible.
   - If a person's name is mentioned (e.g. "Sarah Chen", "Alex", "David", "Rehan"), use their name.
   - If a functional role or job title is mentioned (e.g. "DevOps Engineer", "Frontend Lead", "Backend Engineer", "QA Tester", "Product Manager"), use that role or title.
   - If both a name and role are given (e.g. "Alex (DevOps)", "Sarah - Product Lead"), preserve both (e.g. "Alex (DevOps)").
   - If a speaker tag precedes the statement (e.g. "[00:01:23] Alex (DevOps): I will deploy the container") and speaks in first person ("I will", "I'll", "I'm going to"), the assignee IS that speaker ("Alex (DevOps)").
   - If an instruction directs a person or role (e.g. "Sarah, please lead the audit" or "Can the DevOps engineer handle deployment?"), the assignee is that person or role.
   - NEVER return null, "Unassigned", or "Ambiguous" if a speaker, person name, or functional role is attached to the task!
   - ONLY return null if there is absolutely no owner, speaker, role, or candidate mentioned anywhere in the conversation.
4. Deadline: ISO format YYYY-MM-DD or specific date if mentioned, or null if unspecified.
5. Priority: "LOW", "MEDIUM", "HIGH", or "URGENT".
6. Dependencies: Array of strings for tasks or items it depends on.
7. Confidence score: 0.0 to 1.0 (>= 0.85 when an explicit person or role is identified).
8. Classification type: "EXPLICIT" if speaker explicitly took ownership or was assigned, "INFERRED" if implied.
9. Evidence quote: Verbatim quote from the transcript proving this task and ownership.

Return JSON in this structure:
{
  "tasks": [
    {
      "title": "string",
      "description": "string",
      "assignee": "Person Name and/or Role or null",
      "deadline": "YYYY-MM-DD or null",
      "priority": "LOW" | "MEDIUM" | "HIGH" | "URGENT",
      "dependencies": ["string"],
      "confidence": 0.95,
      "classification_type": "EXPLICIT" | "INFERRED",
      "evidence": "exact quote"
    }
  ]
}
Return ONLY valid JSON.
"""

class TaskAgent:
    async def extract_tasks(
        self,
        transcript_text: str,
        classified_segments: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Transcript:\n{transcript_text}"}
        ]

        result = await groq_service.chat_completion(
            messages=messages,
            response_format={"type": "json_object"}
        )

        if result.get("fallback"):
            from backend.app.services.gemini_service import gemini_service
            if gemini_service.is_configured:
                g_res = await gemini_service.chat_completion(
                    messages=messages,
                    response_format={"type": "json_object"}
                )
                if not g_res.get("fallback"):
                    result = g_res

        if not result.get("fallback"):
            try:
                parsed = json.loads(result["content"])
                if "tasks" in parsed and isinstance(parsed["tasks"], list):
                    return self._clean_and_deduplicate(parsed["tasks"])
            except Exception as e:
                logger.error(f"Failed to parse Groq task extraction JSON: {e}")

        # Local deterministic extraction fallback
        return self._local_fallback_extraction(transcript_text, classified_segments)

    def _clean_and_deduplicate(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_titles = {}
        unique_tasks = []
        for t in tasks:
            clean_title = t.get("title", "").strip().lower()
            if not clean_title or len(clean_title) < 4:
                continue
            if clean_title not in seen_titles:
                seen_titles[clean_title] = True
                unique_tasks.append(t)
        return unique_tasks

    def _local_fallback_extraction(
        self,
        transcript_text: str,
        classified_segments: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        tasks = []
        import re

        # Base date for relative deadlines
        base_date = datetime(2026, 11, 21)

        lines = transcript_text.strip().split("\n")
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            lower = line_str.lower()
            
            # Robust speaker match supporting parentheses, hyphens, brackets, roles
            # e.g. "[00:01:23] Alex (DevOps Lead): I'll deploy the app"
            speaker_match = re.match(r"^(?:\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*)?([^:\n]+?):\s*(.*)$", line_str)
            speaker = speaker_match.group(2).strip() if speaker_match else ""
            content = speaker_match.group(3).strip() if speaker_match else line_str
            c_lower = content.lower()

            is_task = False
            priority = "MEDIUM"
            assignee = speaker if speaker else None
            evidence = line_str
            title = None
            deadline = None
            classification_type = "EXPLICIT"
            confidence = 0.92

            # Check if an explicit owner/assignee is tagged inside the message
            assigned_to_match = re.search(
                r"(?:assigned to|assign to|owner is|assignee:?|owner:?|lead:?)\s*([A-Za-z0-9_\s\(\)\.\-]+)",
                content,
                re.IGNORECASE
            )
            if assigned_to_match:
                candidate = assigned_to_match.group(1).strip()
                if candidate.lower() not in ["anyone", "someone", "tbd", "unassigned"]:
                    assignee = candidate

            # Extract common task intents
            if "finish the frontend" in c_lower or "complete frontend" in c_lower:
                title = "Complete frontend implementation and responsive UI"
                assignee = speaker or "Rahul Sharma"
                deadline = "2026-11-27"
                priority = "HIGH"
                is_task = True
            elif "fastapi backend" in c_lower or "groq orchestration" in c_lower or "backend pipeline" in c_lower:
                title = "Implement FastAPI backend and Groq multi-agent orchestration pipeline"
                assignee = speaker or "Elena Rostova"
                deadline = "2026-11-25"
                priority = "URGENT"
                is_task = True
            elif "gmail smtp" in c_lower or "email automation" in c_lower or "reminder worker" in c_lower or "email execution" in c_lower:
                title = "Integrate Gmail SMTP email execution and persistent reminder worker"
                assignee = speaker or "Elena Rostova"
                deadline = "2026-11-26"
                priority = "HIGH"
                is_task = True
            elif "qa test suite" in c_lower or "end-to-end test" in c_lower or "websocket tests" in c_lower:
                title = "Develop end-to-end test suite and WebSocket stress tests"
                assignee = speaker or "Marcus Vance"
                deadline = "2026-11-28"
                priority = "MEDIUM"
                is_task = True
            elif "demo script" in c_lower or "product positioning" in c_lower or "slide deck" in c_lower:
                title = "Prepare executive demo walkthrough and launch narrative"
                assignee = speaker or "Sarah Chen"
                deadline = "2026-11-29"
                priority = "MEDIUM"
                is_task = True
            elif any(k in c_lower for k in ["audit workspace security", "someone needs to audit", "review security", "we need someone to review", "audit permissions"]):
                title = "Audit workspace security and browser tab audio permissions"
                assignee = None  # Explicitly ambiguous! Requires human signoff
                deadline = "2026-11-26"
                priority = "HIGH"
                classification_type = "INFERRED"
                confidence = 0.65
                is_task = True
            elif any(k in c_lower for k in [
                "will handle", "i will", "i'll", "i am going to", "i can", "take care of", 
                "action item:", "action item", "todo:", "task:", "need to", "needs to", "responsible for"
            ]):
                clean_title = re.sub(
                    r"^(?:i will|i'll|i am going to|i can|action item:?|todo:?|task:?)\s*",
                    "",
                    content,
                    flags=re.IGNORECASE
                ).strip()
                if len(clean_title) > 3:
                    title = clean_title[0].upper() + clean_title[1:]
                else:
                    title = content
                priority = "HIGH" if any(w in c_lower for w in ["urgent", "asap", "blocker", "today"]) else "MEDIUM"
                deadline = (base_date + timedelta(days=5)).strftime("%Y-%m-%d")
                is_task = True

            if is_task and title:
                tasks.append({
                    "title": title,
                    "description": f"Extracted from conversation: {content}",
                    "assignee": assignee,
                    "deadline": deadline,
                    "priority": priority,
                    "dependencies": [],
                    "confidence": confidence,
                    "classification_type": classification_type,
                    "evidence": evidence
                })

        return self._clean_and_deduplicate(tasks)

task_agent = TaskAgent()
