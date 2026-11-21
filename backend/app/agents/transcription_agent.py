import json
import logging
from typing import List, Dict, Any, Optional
from backend.app.services.groq_service import groq_service

logger = logging.getLogger("meetme.agents.transcription")

SYSTEM_PROMPT = """You are the TRANSCRIPTION ANALYSIS AGENT for MEETME.
Your job is to analyze transcript segments, detect speaker turns, and classify each statement into one of:
- TASK: A specific action item assigned or to be done
- DECISION: An agreed outcome, policy, or choice finalized
- COMMITMENT: A personal promise or agreement made by a speaker
- QUESTION: An unresolved query requiring clarification
- BLOCKER: An impediment or obstacle preventing progress
- GENERAL_DISCUSSION: Normal meeting dialogue, context, or status update
- IRRELEVANT: Greetings, banter, or unrelated filler

For each statement, return a JSON array of objects:
[
  {
    "speaker": "Speaker Name",
    "text": "Exact or cleaned text segment",
    "classification": "TASK" | "DECISION" | "COMMITMENT" | "QUESTION" | "BLOCKER" | "GENERAL_DISCUSSION" | "IRRELEVANT",
    "confidence": 0.0 - 1.0,
    "timestamp": "HH:MM:SS" or "00:00:00"
  }
]
Return ONLY valid JSON.
"""

class TranscriptionAgent:
    async def analyze(self, transcript_text: str, context: Optional[str] = None) -> List[Dict[str, Any]]:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context: {context or 'General Team Sync'}\n\nTranscript:\n{transcript_text}"}
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
                if isinstance(parsed, list):
                    return parsed
                elif isinstance(parsed, dict):
                    # Check common keys like "segments" or "items"
                    for key in ["segments", "items", "statements", "classifications"]:
                        if key in parsed and isinstance(parsed[key], list):
                            return parsed[key]
                    return [parsed]
            except Exception as e:
                logger.error(f"Failed to parse Groq transcription analysis JSON: {e}")

        # Local deterministic fallback
        return self._local_fallback_analysis(transcript_text)

    def _local_fallback_analysis(self, transcript_text: str) -> List[Dict[str, Any]]:
        lines = transcript_text.strip().split("\n")
        segments = []
        import re

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            speaker = "Speaker"
            text = line
            timestamp = f"00:{i*15//60:02d}:{i*15%60:02d}"

            # Check if line starts with Speaker Name: or [00:01:23] Alex (DevOps Lead):
            match = re.match(r"^(?:\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*)?([^:\n]+?):\s*(.*)$", line)
            if match:
                if match.group(1):
                    timestamp = match.group(1)
                if match.group(2):
                    speaker = match.group(2).strip()
                if match.group(3):
                    text = match.group(3).strip()

            lower = text.lower().strip()
            classification = "GENERAL_DISCUSSION"
            confidence = 0.85

            # 1. Greetings & Bannter -> IRRELEVANT
            if any(k in lower for k in ["hello everyone", "hi all", "good morning", "see you guys", "bye", "thanks everyone", "how are you", "good afternoon"]):
                classification = "IRRELEVANT"
                confidence = 0.99
            # 2. Decisions -> DECISION
            elif any(k in lower for k in ["decided", "we decided", "decision is", "approved the", "agreed to", "we will go with", "conclusion is", "finalized that"]):
                classification = "DECISION"
                confidence = 0.95
            # 3. Blockers -> BLOCKER
            elif any(k in lower for k in ["blocked on", "waiting for", "blocker", "stuck because", "cannot proceed", "dependency issue", "we are blocked"]):
                classification = "BLOCKER"
                confidence = 0.91
            # 4. Explicit task assignments to a person/role, or instructions to a member
            # e.g. "Sarah, please deploy", "Assign this to Rahul", "Alex: fix login", "Task for Elena", "Can you handle the migration, David?"
            elif (
                any(k in lower for k in [
                    "assigned to", "assign to", "assigning to", "assign this to", "assigning this to",
                    "task for", "action item", "todo:", "task:", "action item for",
                    "please finish", "please complete", "please implement", "please review", "please deploy",
                    "please fix", "please build", "please test", "please update", "please prepare",
                    "please create", "please configure", "please audit", "please handle", "please write",
                    "take care of", "take ownership", "will complete", "i will build", "need to implement",
                    "deploying by", "prep the", "write tests", "responsible for", "you are assigned",
                    "you're assigned", "your task is", "can you please", "could you please", "can you handle",
                    "could you handle", "can you take care", "could you take care", "can you implement",
                    "could you implement", "can you review", "could you review", "can you fix", "could you fix",
                    "can you deploy", "could you deploy"
                ])
                # Direct name assignment pattern: "Name, please...", "Name, can you...", "Name, you take...", "Name: please..."
                or bool(re.search(r"^(?:\[?[\d:]+\]?\s*)?(?:[A-Za-z0-9_\s\(\)\.\-]+?:\s*)?(?:hey\s+)?([A-Za-z]+)(?:,\s*|\s+)(?:please|can you|could you|would you|you need to|you should|you take|you're responsible|you are responsible|handle|fix|implement|deploy|review|test|build|write|create|update)\b", text, re.IGNORECASE))
                # Third-person assignment: "Sarah to handle...", "Sarah will do...", "Let's assign Sarah..."
                or bool(re.search(r"(?:assign|assigning|give|passed)\s+(?:this\s+)?(?:task\s+)?(?:to\s+)?([A-Za-z]+)", text, re.IGNORECASE))
                or bool(re.search(r"\b([A-Za-z]+)\s+(?:will|to|should)\s+(?:handle|implement|deploy|fix|build|write|review|test|create|update|lead)\b", text, re.IGNORECASE))
            ):
                classification = "TASK"
                confidence = 0.94
            # 5. Personal Commitments -> COMMITMENT
            elif any(k in lower for k in ["i promise", "i'll handle", "count me in", "i commit", "i'm on it", "i will handle", "i will take care", "i will"]):
                classification = "COMMITMENT"
                confidence = 0.90
            # 6. Questions
            elif any(k in lower for k in ["what if", "how will", "who is", "is it possible", "why is", "what about"]) or text.endswith("?"):
                classification = "QUESTION"
                confidence = 0.87

            segments.append({
                "speaker": speaker,
                "text": text,
                "classification": classification,
                "confidence": confidence,
                "timestamp": timestamp
            })

        return segments

transcription_agent = TranscriptionAgent()
