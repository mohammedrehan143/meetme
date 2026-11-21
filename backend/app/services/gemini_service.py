import json
import httpx
import logging
from typing import Dict, Any, Optional, List
from backend.app.core.config import settings

logger = logging.getLogger("meetme.gemini")

class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL or "gemini-1.5-pro"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and "[YOUR" not in self.api_key)

    async def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_mime_type: Optional[str] = "application/json",
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        Executes a content generation call using Google Gemini REST API.
        """
        if not self.is_configured:
            return {"fallback": True, "error": "GEMINI_API_KEY_MISSING"}

        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 4096
            }
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        if response_mime_type:
            payload["generationConfig"]["responseMimeType"] = response_mime_type

        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        text = "".join(p.get("text", "") for p in parts)
                        return {
                            "content": text,
                            "fallback": False
                        }
                    return {"fallback": True, "error": "No candidates returned"}
                else:
                    logger.error(f"Gemini API error {response.status_code}: {response.text}")
                    return {"fallback": True, "error": f"Gemini HTTP {response.status_code}: {response.text}"}
            except Exception as e:
                logger.error(f"Exception during Gemini completion: {str(e)}")
                return {"fallback": True, "error": str(e)}

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict[str, str]] = None,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        Wrapper providing OpenAI/Groq compatible chat completion format over Gemini.
        """
        # Convert messages to prompt string
        full_prompt = ""
        system_inst = None
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system_inst = content
            else:
                full_prompt += f"{role.upper()}: {content}\n"

        mime_type = "application/json" if response_format and response_format.get("type") == "json_object" else None
        return await self.generate_content(
            prompt=full_prompt,
            system_instruction=system_inst,
            response_mime_type=mime_type,
            temperature=temperature
        )

gemini_service = GeminiService()
