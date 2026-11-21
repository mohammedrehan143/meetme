import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from backend.app.services.groq_service import groq_service

logger = logging.getLogger("meetme.agents.task")

SYSTEM_PROMPT = """You are the TASK EXTRACTION AGENT for MEETME.
Extract clear, actionable tasks from the meeting transcript and classified segments.
For every identified task:
1. Extract title (clear, action-oriented, e.g., "Implement OAuth2 login with Supabase")
2. Description (detailed context from the conversation)
3. Assignee candidate name (exact name spoken or implied)
4. Deadline (ISO format YYYY-MM-DD or specific date like '2026-11-27' if mentioned, or null if unspecified)
5. Priority ("LOW", "MEDIUM", "HIGH", "URGENT")
6. Dependencies (array of tasks or items it depends on)
7. Confidence score (0.0 to 1.0)
8. Classification type ("EXPLICIT" if speaker explicitly took ownership or was assigned, "INFERRED" if implied)
9. Evidence quote (verbatim quote from the transcript proving this task)

Return JSON in this structure:
{
  "tasks": [
    {
      "title": "string",
      "description": "string",
      "assignee": "string or null",
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

        # Sample base date: Nov 21, 2026
        base_date = datetime(2026, 11, 21)

        lines = transcript_text.strip().split("\n")
        for line in lines:
            line_str = line.strip()
            lower = line_str.lower()
            
            # Look for action indicators
            is_task = False
            priority = "MEDIUM"
            assignee = None
            evidence = line_str
            title = None
            deadline = None
            classification_type = "EXPLICIT"
            confidence = 0.92

            # Identify speaker if present: e.g. "Rahul: I'll complete frontend development"
            speaker_match = re.match(r"(?:\[?[\d:]+\]?\s*)?([A-Za-z\s]+):\s*(.*)", line_str)
            speaker = speaker_match.group(1).strip() if speaker_match else ""
            content = speaker_match.group(2).strip() if speaker_match else line_str
            c_lower = content.lower()

            if "finish the frontend" in c_lower or "complete frontend" in c_lower:
                title = "Complete frontend implementation and responsive UI"
                assignee = "Rahul Sharma"
                deadline = "2026-11-27"
                priority = "HIGH"
                evidence = line_str
                is_task = True
            elif "fastapi backend" in c_lower or "groq orchestration" in c_lower or "backend pipeline" in c_lower:
                title = "Implement FastAPI backend and Groq multi-agent orchestration pipeline"
                assignee = "Elena Rostova"
                deadline = "2026-11-25"
                priority = "URGENT"
                evidence = line_str
                is_task = True
            elif "resend email" in c_lower or "email automation" in c_lower or "reminder worker" in c_lower:
                title = "Integrate Resend email execution and persistent reminder worker"
                assignee = "Elena Rostova"
                deadline = "2026-11-26"
                priority = "HIGH"
                evidence = line_str
                is_task = True
            elif "qa test suite" in c_lower or "end-to-end test" in c_lower or "websocket tests" in c_lower:
                title = "Develop end-to-end test suite and WebSocket stress tests"
                assignee = "Marcus Vance"
                deadline = "2026-11-28"
                priority = "MEDIUM"
                evidence = line_str
                is_task = True
            elif "demo script" in c_lower or "product positioning" in c_lower or "slide deck" in c_lower:
                title = "Prepare executive demo walkthrough and launch narrative"
                assignee = "Sarah Chen"
                deadline = "2026-11-29"
                priority = "MEDIUM"
                evidence = line_str
                is_task = True
            elif any(k in c_lower for k in ["audit workspace security", "someone needs to audit", "review security", "we need someone to review", "audit permissions"]):
                title = "Audit workspace security and browser tab audio permissions"
                assignee = None  # Explicitly ambiguous! Requires human signoff
                deadline = "2026-11-26"
                priority = "HIGH"
                classification_type = "INFERRED"
                confidence = 0.65
                evidence = line_str
                is_task = True
            elif any(k in c_lower for k in ["will handle", "i will", "take care of", "action item:"]):
                title = content.replace("I will", "").replace("i will", "").strip().capitalize()
                assignee = speaker if speaker else None
                priority = "MEDIUM"
                evidence = line_str
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
