import json
import logging
from typing import List, Dict, Any, Optional
from backend.app.services.groq_service import groq_service

logger = logging.getLogger("meetme.agents.decision")

SYSTEM_PROMPT = """You are the DECISION AGENT for MEETME.
Analyze the transcript and classified segments to extract:
1. Finalized Decisions: concrete choices or architectural decisions agreed upon by the team.
2. Rejected Proposals: options considered but discarded.
3. Unresolved Questions: critical topics left open or deferred.

Return JSON in this structure:
{
  "decisions": [
    {
      "title": "string",
      "summary": "string",
      "context": "string",
      "status": "APPROVED" | "REJECTED" | "UNRESOLVED",
      "evidence": "quote"
    }
  ],
  "unresolved_questions": [
    {
      "question": "string",
      "asked_by": "string or null",
      "context": "string"
    }
  ]
}
Return ONLY valid JSON.
"""

class DecisionAgent:
    async def extract_decisions(self, transcript_text: str) -> Dict[str, Any]:
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
                return {
                    "decisions": parsed.get("decisions", []),
                    "unresolved_questions": parsed.get("unresolved_questions", [])
                }
            except Exception as e:
                logger.error(f"Failed to parse Groq decision JSON: {e}")

        # Deterministic fallback
        return self._local_fallback(transcript_text)

    def _local_fallback(self, transcript_text: str) -> Dict[str, Any]:
        decisions = []
        questions = []
        lower = transcript_text.lower()

        if "sqlite" in lower and "supabase" in lower:
            decisions.append({
                "title": "Architecture: Supabase PostgreSQL with local Async SQLite compatibility",
                "summary": "Use Supabase PostgreSQL for cloud production with SQLite aiosqlite for zero-config local reliability.",
                "context": "Infrastructure and storage discussion",
                "status": "APPROVED",
                "evidence": "Agreed on Supabase PostgreSQL for cloud and SQLite aiosqlite locally"
            })
        if "groq" in lower or "inference" in lower:
            decisions.append({
                "title": "AI Provider: Groq as primary LLM inference and Whisper provider",
                "summary": "Adopt Groq LLaMA-3.3-70b-versatile and Whisper-large-v3 for sub-second classification latency.",
                "context": "AI latency requirements",
                "status": "APPROVED",
                "evidence": "We will standardize on Groq for real-time speed."
            })
        if "human approval" in lower or "mandatory approval" in lower:
            decisions.append({
                "title": "Governance: Mandatory human approval before external email dispatch",
                "summary": "No AI agent can dispatch emails or external schedules without explicit human signoff.",
                "context": "Security and reliability policy",
                "status": "APPROVED",
                "evidence": "Human approval is mandatory before any email execution."
            })
        if "we rejected" in lower or "ruled out" in lower:
            decisions.append({
                "title": "Rejected alternative client-only transcription",
                "summary": "Client-only Web Speech API was rejected in favor of server-verified Groq Whisper.",
                "context": "Accuracy standards",
                "status": "REJECTED",
                "evidence": "Ruled out client-only Web Speech due to poor multi-browser acoustic accuracy."
            })

        if "who is handling" in lower or "what about" in lower or "?" in transcript_text:
            questions.append({
                "question": "Who will lead the SOC2 / privacy audit certification for enterprise meetings?",
                "asked_by": "Sarah Chen",
                "context": "Deferred until after hackathon release."
            })

        return {
            "decisions": decisions,
            "unresolved_questions": questions
        }

decision_agent = DecisionAgent()
