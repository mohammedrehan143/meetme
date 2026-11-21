import os
import json
import httpx
import logging
from typing import Dict, Any, Optional, List
from backend.app.core.config import settings

logger = logging.getLogger("meetme.groq")

class GroqService:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self.base_url = "https://api.groq.com/openai/v1"

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict[str, str]] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Executes a chat completion call with Groq.
        """
        if not self.api_key:
            logger.warning("GROQ_API_KEY not configured. Falling back to local agent pipeline.")
            return {"fallback": True, "error": "GROQ_API_KEY_MISSING"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    return {
                        "content": content,
                        "usage": usage,
                        "fallback": False
                    }
                else:
                    logger.error(f"Groq API error {response.status_code}: {response.text}")
                    return {
                        "fallback": True,
                        "error": f"Groq HTTP {response.status_code}: {response.text}"
                    }
            except Exception as e:
                logger.error(f"Exception during Groq completion: {str(e)}")
                return {"fallback": True, "error": str(e)}

    async def transcribe_audio(self, audio_bytes: bytes, filename: str = "meeting.webm") -> Optional[str]:
        """
        Transcribes audio using Groq Whisper model.
        """
        if not self.api_key:
            logger.warning("GROQ_API_KEY not set for Whisper transcription.")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        files = {
            "file": (filename, audio_bytes, "audio/webm")
        }
        data = {
            "model": settings.GROQ_WHISPER_MODEL,
            "response_format": "json"
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/audio/transcriptions",
                    headers=headers,
                    files=files,
                    data=data
                )
                if response.status_code == 200:
                    result = response.json()
                    return result.get("text", "")
                else:
                    logger.error(f"Groq Whisper error: {response.text}")
                    return None
            except Exception as e:
                logger.error(f"Groq Whisper exception: {str(e)}")
                return None

groq_service = GroqService()
