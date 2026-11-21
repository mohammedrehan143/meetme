import httpx
import logging
from typing import Dict, Any, Optional
from backend.app.core.config import settings

logger = logging.getLogger("meetme.resend")

class ResendService:
    def __init__(self):
        self.api_key = settings.RESEND_API_KEY
        self.from_email = settings.RESEND_FROM_EMAIL
        self.base_url = "https://api.resend.com/emails"

    async def send_email(
        self,
        to: str,
        subject: str,
        html: str,
        text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends an email using Resend API, or falls back to local queue log if API key is missing.
        """
        if not self.api_key:
            logger.info(f"[TEST MODE] Email to {to} queued locally. Subject: {subject}")
            return {
                "success": True,
                "status": "QUEUED_LOCAL",
                "provider": "LocalQueue",
                "id": f"local_mail_{id(to)}_{hash(subject)}",
                "message": "Email logged and queued locally (no RESEND_API_KEY configured)."
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "from": self.from_email,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        if text:
            payload["text"] = text

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                response = await client.post(self.base_url, headers=headers, json=payload)
                if response.status_code in (200, 201):
                    data = response.json()
                    logger.info(f"Resend success: message id {data.get('id')}")
                    return {
                        "success": True,
                        "status": "SENT",
                        "provider": "Resend",
                        "id": data.get("id"),
                        "message": "Delivered through Resend API."
                    }
                else:
                    error_msg = f"Resend API error {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "status": "FAILED",
                        "provider": "Resend",
                        "id": None,
                        "error": error_msg
                    }
            except Exception as e:
                logger.error(f"Resend connection error: {str(e)}")
                return {
                    "success": False,
                    "status": "FAILED",
                    "provider": "Resend",
                    "id": None,
                    "error": str(e)
                }

resend_service = ResendService()
