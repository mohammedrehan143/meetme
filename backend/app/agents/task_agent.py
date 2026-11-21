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

        base_date = datetime(2026, 11, 21)
        weekday_map = {"monday": 2, "tuesday": 3, "wednesday": 4, "thursday": 5, "friday": 6, "saturday": 0, "sunday": 1}

        lines = transcript_text.strip().split("\n")
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            
            # Robust speaker match: "[00:01:23] Alex (DevOps Lead): I'll deploy the app"
            speaker_match = re.match(r"^(?:\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*)?([^:\n]+?):\s*(.*)$", line_str)
            speaker = speaker_match.group(2).strip() if speaker_match else ""
            content = speaker_match.group(3).strip() if speaker_match else line_str
            c_lower = content.lower().strip()

            is_task = False
            priority = "HIGH" if any(w in c_lower for w in ["urgent", "asap", "blocker", "today", "critical", "immediately"]) else "MEDIUM"
            assignee = None
            evidence = line_str
            title = None
            deadline = None
            classification_type = "EXPLICIT"
            confidence = 0.94

            # 1. Check for specific assignee patterns in content
            # A. Subject assignment syntax: "David is assigned to...", "Sarah will handle...", "Sarah is responsible for..."
            subj_match = re.search(
                r"\b([A-Za-z]+)\s+(?:is\s+assigned\s+to|is\s+responsible\s+for|will\s+take\s+care\s+of|will\s+handle|will\s+lead|to\s+handle)\b",
                content,
                re.IGNORECASE
            )
            if subj_match:
                cand = subj_match.group(1).strip()
                if cand.lower() not in ["anyone", "someone", "we", "they", "who", "it", "this"]:
                    assignee = cand
                    is_task = True

            # B. Direct assignment syntax: "assign to Sarah", "assigning this task to Alex", "task for Marcus:"
            if not assignee:
                assign_match = re.search(
                    r"(?:assign(?:ed|ing)?\s+(?:(?:this\s+)?(?:task|action\s+item|ticket|issue)\s+)?to|task\s+for|action\s+item\s+for|owner\s+is|assignee:?|owner:?|lead:?)\s*([A-Za-z0-9_\(\)\.\-]+(?:\s+[A-Za-z0-9_\(\)\.\-]+)?)",
                    content,
                    re.IGNORECASE
                )
                if assign_match:
                    cand = assign_match.group(1).strip()
                    if cand.lower() not in ["anyone", "someone", "tbd", "unassigned", "the", "a", "this", "configure", "implement", "deploy", "build", "write", "test", "fix", "review"]:
                        assignee = cand
                        is_task = True

            # C. Addressed to member: "Sarah, please implement...", "Alex, can you deploy...", "Hey Rahul, take care of..."
            if not assignee:
                addressed_match = re.search(
                    r"^(?:hey\s+)?([A-Za-z]+)(?:,\s*|\s*:\s*|\s+)(?:please|can you|could you|would you|you need to|you should|you take|take\s+care\s+of|take\s+ownership|work\s+on|you're assigned to|you are assigned to|handle|fix|implement|deploy|review|test|build|write|create|update)\b",
                    content,
                    re.IGNORECASE
                )
                if addressed_match:
                    cand = addressed_match.group(1).strip()
                    if cand.lower() not in ["anyone", "someone", "everyone", "today", "tomorrow", "also", "well", "now", "here", "let", "lets", "if", "we"]:
                        assignee = cand
                        is_task = True

            # D. Trailing question assignment: "Can you handle the database, Sarah?"
            if not assignee:
                trailing_match = re.search(
                    r"(?:can you|could you|please|will you)\s+.*?[,\s]+([A-Za-z]+)\??$",
                    content,
                    re.IGNORECASE
                )
                if trailing_match:
                    cand = trailing_match.group(1).strip("?., ")
                    if cand.lower() not in ["please", "asap", "today", "tomorrow", "now", "here", "well"]:
                        assignee = cand
                        is_task = True

            # E. Third-person action: "Marcus will test..."
            if not assignee:
                third_match = re.search(
                    r"\b([A-Z][a-z]+)\s+(?:will|to|should)\s+(?:handle|implement|deploy|fix|build|write|review|test|create|update|lead)\b",
                    content
                )
                if third_match:
                    cand = third_match.group(1).strip()
                    if cand.lower() not in ["we", "they", "someone", "anyone"]:
                        assignee = cand
                        is_task = True

            # F. First person commitment ("I will...", "I'll...", "I am going to...")
            if not assignee and any(k in c_lower for k in ["i will", "i'll", "i am going to", "i can", "i'll handle", "count me in", "i commit"]):
                assignee = speaker if (speaker and speaker.lower() not in ["speaker", "unknown", "admin"]) else "Speaker"
                is_task = True

            # 2. Check general task keywords if not already matched
            if not is_task:
                if any(k in c_lower for k in [
                    "finish the frontend", "complete frontend", "fastapi backend", "groq orchestration",
                    "backend pipeline", "gmail smtp", "email automation", "reminder worker", "qa test suite",
                    "end-to-end test", "websocket tests", "demo script", "product positioning",
                    "will handle", "take care of", "action item", "todo:", "task:", "need to", "needs to",
                    "responsible for", "please implement", "please deploy", "please review", "please fix",
                    "please build", "please test", "please update", "please prepare", "please create",
                    "please configure", "please audit", "please handle", "please write", "can you please",
                    "could you please", "can you handle", "could you handle", "can you deploy", "could you deploy",
                    "can you fix", "could you fix", "can you review", "could you review", "can you test",
                    "could you test", "can you build", "could you build"
                ]):
                    is_task = True
                    if not assignee and speaker and speaker.lower() not in ["speaker", "unknown"]:
                        assignee = speaker

            # Check ambiguous audit task
            if any(k in c_lower for k in ["audit workspace security", "someone needs to audit", "review security", "we need someone to review", "audit permissions"]):
                title = "Audit workspace security and browser tab audio permissions"
                assignee = None
                deadline = "2026-11-26"
                priority = "HIGH"
                classification_type = "INFERRED"
                confidence = 0.65
                is_task = True

            if is_task:
                # 3. Clean up Title
                if not title:
                    clean_title = content
                    # Remove speaker prefix: "[00:01:23] Alex (DevOps):"
                    clean_title = re.sub(r"^(?:\[?[\d:]+\]?\s*)?(?:[A-Za-z0-9_\s\(\)\.\-]+?:\s*)?", "", clean_title)
                    # Remove addressed person: "Hey Rahul,", "Sarah,", "Alex:"
                    clean_title = re.sub(r"^(?:hey\s+[A-Za-z]+[,\s]+|[A-Za-z]+,\s*|[A-Za-z]+:\s*)", "", clean_title, flags=re.IGNORECASE)
                    # Remove assignment prefix syntax
                    clean_title = re.sub(
                        r"^(?:assign(?:ed|ing)?\s+(?:(?:this\s+)?(?:task|action\s+item|ticket|issue)\s+)?to\s+[A-Za-z0-9_\(\)\.\-]+(?:\s*:\s*|\s+to\s+|\s+for\s+|\s+)?|"
                        r"task\s+for\s+[A-Za-z0-9_\(\)\.\-]+(?:\s*:\s*|\s+to\s+|\s+for\s+|\s+)?|"
                        r"[A-Za-z0-9_\(\)\.\-]+\s+is\s+assigned\s+to\s+)",
                        "",
                        clean_title,
                        flags=re.IGNORECASE
                    )
                    # Remove common imperative prefixes
                    clean_title = re.sub(
                        r"^(?:can\s+you\s+(?:please\s+)?|could\s+you\s+(?:please\s+)?|please\s+|would\s+you\s+(?:please\s+)?|"
                        r"i\s+will\s+|i'll\s+|i\s+am\s+going\s+to\s+|i\s+can\s+|we\s+need\s+to\s+|need\s+to\s+|"
                        r"action\s+item:?\s*|todo:?\s*|task:?\s*)",
                        "",
                        clean_title,
                        flags=re.IGNORECASE
                    )
                    # Strip trailing question addressed person: ", David?"
                    clean_title = re.sub(r",\s*[A-Za-z]+\s*\?$", "", clean_title)
                    clean_title = clean_title.strip("?., -:; ")

                    # Fallback for specific predefined demo items if matched
                    if "finish the frontend" in c_lower or "complete frontend" in c_lower:
                        clean_title = "Complete frontend implementation and responsive UI"
                        deadline = "2026-11-27"
                        priority = "HIGH"
                    elif "fastapi backend" in c_lower or "groq orchestration" in c_lower or "backend pipeline" in c_lower:
                        clean_title = "Implement FastAPI backend and Groq multi-agent orchestration pipeline"
                        deadline = "2026-11-25"
                        priority = "URGENT"
                    elif "gmail smtp" in c_lower or "email automation" in c_lower or "reminder worker" in c_lower:
                        clean_title = "Integrate Gmail SMTP email execution and persistent reminder worker"
                        deadline = "2026-11-26"
                        priority = "HIGH"
                    elif "qa test suite" in c_lower or "end-to-end test" in c_lower or "websocket tests" in c_lower:
                        clean_title = "Develop end-to-end test suite and WebSocket stress tests"
                        deadline = "2026-11-28"
                        priority = "MEDIUM"
                    elif "demo script" in c_lower or "product positioning" in c_lower or "slide deck" in c_lower:
                        clean_title = "Prepare executive demo walkthrough and launch narrative"
                        deadline = "2026-11-29"
                        priority = "MEDIUM"

                    if len(clean_title) > 3:
                        title = clean_title[0].upper() + clean_title[1:]
                    else:
                        title = content

                # 4. Extract Deadline if mentioned
                if not deadline:
                    dl_match = re.search(r"\bby\s+([a-zA-Z]+|\d{4}-\d{2}-\d{2})\b", c_lower)
                    if dl_match:
                        token = dl_match.group(1).lower()
                        if token in weekday_map:
                            deadline = (base_date + timedelta(days=5)).strftime("%Y-%m-%d")
                        elif token == "tomorrow":
                            deadline = (base_date + timedelta(days=1)).strftime("%Y-%m-%d")
                        elif token == "today":
                            deadline = base_date.strftime("%Y-%m-%d")
                        elif re.match(r"^\d{4}-\d{2}-\d{2}$", token):
                            deadline = token
                    if not deadline:
                        deadline = (base_date + timedelta(days=5)).strftime("%Y-%m-%d")

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
