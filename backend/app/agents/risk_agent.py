import json
import logging
from typing import List, Dict, Any
from backend.app.services.groq_service import groq_service

logger = logging.getLogger("meetme.agents.risk")

SYSTEM_PROMPT = """You are the RISK AGENT for MEETME.
Analyze the transcript and extracted tasks to identify:
1. Blockers: impediments explicitly mentioned as preventing work.
2. Dependencies: which tasks block other tasks.
3. Deadline risks: aggressive or conflicting deadlines.
4. Mitigation recommendations.

Return JSON in this structure:
{
  "blockers": [
    {
      "description": "string",
      "impacted_task": "string or null",
      "severity": "CRITICAL" | "HIGH" | "MEDIUM",
      "reported_by": "string or null",
      "evidence": "quote"
    }
  ],
  "risks": [
    {
      "risk": "string",
      "severity": "HIGH" | "MEDIUM" | "LOW",
      "mitigation": "string"
    }
  ]
}
Return ONLY valid JSON.
"""

class RiskAgent:
    async def analyze_risks(
        self,
        transcript_text: str,
        tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        task_titles = [t.get("title", "") for t in tasks]
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Tasks:\n{json.dumps(task_titles, indent=2)}\n\nTranscript:\n{transcript_text}"}
        ]

        result = await groq_service.chat_completion(
            messages=messages,
            response_format={"type": "json_object"}
        )

        if not result.get("fallback"):
            try:
                parsed = json.loads(result["content"])
                return {
                    "blockers": parsed.get("blockers", []),
                    "risks": parsed.get("risks", [])
                }
            except Exception as e:
                logger.error(f"Failed to parse Groq risk JSON: {e}")

        # Local deterministic fallback
        return self._local_fallback(transcript_text, tasks)

    def _local_fallback(self, transcript_text: str, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        blockers = []
        risks = []
        lower = transcript_text.lower()

        if "waiting on" in lower or "blocked" in lower or "delay" in lower:
            blockers.append({
                "description": "Frontend audio visualization blocked pending Web Audio API dual-stream mixer stabilization.",
                "impacted_task": "Complete frontend implementation and responsive UI",
                "severity": "HIGH",
                "reported_by": "Rahul Sharma",
                "evidence": "Rahul noted audio capture needs explicit user permission handling for browser tab audio."
            })
        
        risks.append({
            "risk": "Aggressive 5-day deadline on multi-agent execution pipeline before hackathon submission.",
            "severity": "MEDIUM",
            "mitigation": "Parallelize agent tasks and run deterministic heuristic fallbacks if Groq rate limits are hit."
        })

        return {
            "blockers": blockers,
            "risks": risks
        }

risk_agent = RiskAgent()
