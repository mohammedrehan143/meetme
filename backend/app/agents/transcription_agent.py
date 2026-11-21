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

            # Check if line starts with Speaker Name: or [00:01:23] Rahul:
            match = re.match(r"(?:\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*)?([A-Za-z\s]+):\s*(.*)", line)
            if match:
                if match.group(1):
                    timestamp = match.group(1)
                if match.group(2):
                    speaker = match.group(2).strip()
                if match.group(3):
                    text = match.group(3).strip()

            lower = text.lower()
            classification = "GENERAL_DISCUSSION"
            confidence = 0.85

            if any(k in lower for k in ["will complete", "i will build", "action item", "take ownership", "please finish", "assigned to", "by friday", "need to implement", "deploying by", "prep the", "write tests"]):
                classification = "TASK"
                confidence = 0.93
            elif any(k in lower for k in ["decided", "agreed", "we will go with", "decision is", "approved the architecture", "conclusion"]):
                classification = "DECISION"
                confidence = 0.95
            elif any(k in lower for k in ["blocked on", "waiting for", "blocker", "stuck because", "cannot proceed", "dependency issue"]):
                classification = "BLOCKER"
                confidence = 0.91
            elif any(k in lower for k in ["i promise", "i'll handle", "count me in", "i commit"]):
                classification = "COMMITMENT"
                confidence = 0.88
            elif any(k in lower for k in ["what if", "can we", "how will", "should we", "who is", "is it possible"]) or text.endswith("?"):
                classification = "QUESTION"
                confidence = 0.87
            elif any(k in lower for k in ["hello everyone", "hi all", "good morning", "see you guys", "bye", "thanks everyone"]):
                classification = "IRRELEVANT"
                confidence = 0.99

            segments.append({
                "speaker": speaker,
                "text": text,
                "classification": classification,
                "confidence": confidence,
                "timestamp": timestamp
            })

        return segments

transcription_agent = TranscriptionAgent()
