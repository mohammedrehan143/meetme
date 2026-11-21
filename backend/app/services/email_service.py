import smtplib
import socket
import logging
import uuid
import httpx
from email.message import EmailMessage
from email.utils import make_msgid, formatdate
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.config import settings

logger = logging.getLogger("meetme.email_service")

class EmailService:
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.email = settings.SMTP_EMAIL
        self.password = settings.SMTP_PASSWORD
        self.from_name = settings.SMTP_FROM_NAME
        self.timeout = settings.SMTP_TIMEOUT
        self.resend_api_key = settings.RESEND_API_KEY
        self.resend_from_email = settings.RESEND_FROM_EMAIL

    @property
    def is_resend_configured(self) -> bool:
        """Returns True if valid Resend API key is configured."""
        return bool(
            self.resend_api_key 
            and self.resend_api_key.startswith("re_") 
            and "[YOUR" not in self.resend_api_key
        )

    @property
    def is_smtp_configured(self) -> bool:
        """Returns True if valid Gmail SMTP credentials are configured."""
        return bool(self.email and self.password and "[YOUR" not in self.password)

    @property
    def is_configured(self) -> bool:
        return self.is_resend_configured or self.is_smtp_configured

    @property
    def active_provider(self) -> str:
        if self.is_resend_configured:
            return "Resend (HTTPS)"
        elif self.is_smtp_configured:
            return "Gmail SMTP"
        return "None"

    def test_connection(self) -> Dict[str, Any]:
        """
        Validates email provider connectivity.
        Uses Resend HTTPS API (port 443) if configured, or tests Gmail SMTP.
        """
        if self.is_resend_configured:
            try:
                with httpx.Client(timeout=8.0) as client:
                    resp = client.get(
                        "https://api.resend.com/api-keys",
                        headers={"Authorization": f"Bearer {self.resend_api_key}"}
                    )
                    if resp.status_code == 200:
                        return {
                            "success": True,
                            "provider": "Resend (HTTPS)",
                            "message": "Successfully authenticated with Resend API over HTTPS (Port 443). Render Free Tier compatible!"
                        }
                    elif resp.status_code == 403 and "restricted" in resp.text.lower():
                        return {
                            "success": True,
                            "provider": "Resend (HTTPS)",
                            "message": "Authenticated with Resend API (Sending Access) over HTTPS (Port 443). Ready to dispatch emails!"
                        }
                    else:
                        return {
                            "success": False,
                            "provider": "Resend (HTTPS)",
                            "error": f"Resend API authentication failed ({resp.status_code}): {resp.text}"
                        }
            except Exception as e:
                return {
                    "success": False,
                    "provider": "Resend (HTTPS)",
                    "error": f"Resend connection error: {str(e)}"
                }
        elif self.is_smtp_configured:
            try:
                server = self._get_smtp_connection()
                server.quit()
                return {
                    "success": True,
                    "provider": "Gmail SMTP",
                    "message": f"Successfully authenticated with Gmail SMTP server ({self.host})."
                }
            except Exception as e:
                return {
                    "success": False,
                    "provider": "Gmail SMTP",
                    "error": f"SMTP Error: {str(e)}"
                }
        else:
            return {
                "success": False,
                "error": "No email provider configured. Configure RESEND_API_KEY (for Render) or Gmail SMTP credentials."
            }

    def _get_smtp_connection(self):
        """
        Attempts connection via port 587 (STARTTLS) or port 465 (SSL).
        Gracefully tries both to ensure delivery on networks with port filtering.
        """
        ports_to_try = [self.port, 465 if self.port == 587 else 587]
        last_err = None

        for p in ports_to_try:
            try:
                if p == 465:
                    server = smtplib.SMTP_SSL(self.host, 465, timeout=min(self.timeout, 5))
                    server.ehlo()
                    server.login(self.email, self.password)
                    return server
                else:
                    server = smtplib.SMTP(self.host, p, timeout=min(self.timeout, 5))
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(self.email, self.password)
                    return server
            except Exception as e:
                last_err = e
                continue

        raise last_err or Exception("Failed to establish SMTP connection on ports 587/465.")

    async def send_email(
        self,
        to: str,
        subject: str,
        html: str,
        text: Optional[str] = None,
        recipient_name: Optional[str] = None,
        email_type: str = "TASK_ASSIGNMENT",
        task_ids: Optional[List[str]] = None,
        idempotency_key: Optional[str] = None,
        workspace_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Sends an email using Resend HTTPS API (Primary for Render Cloud) or native Gmail SMTP.
        Includes idempotency checks, detailed status tracking, and fallback.
        """
        task_ids = task_ids or []
        from backend.app.models.schema import EmailLog

        # 1. Idempotency Check: prevent duplicate email sends
        if idempotency_key and db:
            existing_stmt = select(EmailLog).where(
                EmailLog.idempotency_key == idempotency_key,
                EmailLog.status.in_(["SENT", "QUEUED_DEV", "QUEUED_LOCAL"])
            )
            existing_res = await db.execute(existing_stmt)
            existing_email = existing_res.scalar_one_or_none()
            if existing_email:
                logger.info(f"Duplicate email prevented via idempotency key: {idempotency_key}")
                return {
                    "success": True,
                    "status": "ALREADY_SENT",
                    "provider": existing_email.provider or "Email Engine",
                    "id": existing_email.message_id or existing_email.id,
                    "message": "Duplicate send skipped; email previously dispatched successfully."
                }

        plain_text_content = text or "Please view this email in an HTML-compatible client."

        # 2. Resend HTTPS API (Primary for Render cloud deployments - Bypasses port blocks)
        if self.is_resend_configured:
            try:
                sender = self.resend_from_email or "MEETME Platform <onboarding@resend.dev>"
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        "https://api.resend.com/emails",
                        headers={
                            "Authorization": f"Bearer {self.resend_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "from": sender,
                            "to": [to],
                            "subject": subject,
                            "html": html,
                            "text": plain_text_content
                        }
                    )

                if resp.status_code in [200, 201]:
                    data = resp.json()
                    msg_id = data.get("id", f"resend_{int(datetime.utcnow().timestamp())}")
                    logger.info(f"Resend HTTPS API successfully delivered email {msg_id} to {to}.")
                    result = {
                        "success": True,
                        "status": "SENT",
                        "provider": "Resend (HTTPS)",
                        "id": msg_id,
                        "message": "Delivered successfully through Resend HTTPS API (Port 443)."
                    }

                    if db and workspace_id:
                        log_entry = EmailLog(
                            workspace_id=workspace_id,
                            task_id=task_ids[0] if task_ids else None,
                            task_ids=task_ids,
                            recipient=recipient_name or to,
                            email_address=to,
                            email_type=email_type,
                            subject=subject,
                            body_html=html,
                            body_text=plain_text_content,
                            status="SENT",
                            provider="Resend (HTTPS)",
                            message_id=msg_id,
                            provider_message_id=msg_id,
                            idempotency_key=idempotency_key,
                            sent_at=datetime.utcnow()
                        )
                        db.add(log_entry)
                        await db.commit()

                    return result
                else:
                    err_msg = f"Resend API error ({resp.status_code}): {resp.text}"
                    logger.error(err_msg)
                    if not self.is_smtp_configured:
                        return self._record_failure(err_msg)
            except Exception as e:
                err_msg = f"Resend connection error: {str(e)}"
                logger.error(err_msg)
                if not self.is_smtp_configured:
                    return self._record_failure(err_msg)

        # 3. Native Gmail SMTP Delivery (Dual port 587/465 fallback)
        if self.is_smtp_configured:
            try:
                msg = EmailMessage()
                msg["Subject"] = subject
                sender_address = f"{self.from_name} <{self.email}>" if self.email else f"MEETME Platform <notifications@meetme.ai>"
                msg["From"] = sender_address
                msg["To"] = f"{recipient_name} <{to}>" if recipient_name else to
                msg["Date"] = formatdate(localtime=True)
                generated_msg_id = make_msgid(domain=self.email.split("@")[-1] if "@" in self.email else "meetme.ai")
                msg["Message-ID"] = generated_msg_id
                if idempotency_key:
                    msg["X-MEETME-Idempotency-Key"] = idempotency_key

                msg.set_content(plain_text_content)
                msg.add_alternative(html, subtype="html")

                server = self._get_smtp_connection()
                try:
                    server.send_message(msg)
                finally:
                    try:
                        server.quit()
                    except Exception:
                        pass

                logger.info(f"Gmail SMTP successfully delivered message {generated_msg_id} to {to}.")
                result = {
                    "success": True,
                    "status": "SENT",
                    "provider": "Gmail SMTP",
                    "id": generated_msg_id,
                    "message": "Delivered successfully through Gmail SMTP."
                }

                if db and workspace_id:
                    log_entry = EmailLog(
                        workspace_id=workspace_id,
                        task_id=task_ids[0] if task_ids else None,
                        task_ids=task_ids,
                        recipient=recipient_name or to,
                        email_address=to,
                        email_type=email_type,
                        subject=subject,
                        body_html=html,
                        body_text=plain_text_content,
                        status="SENT",
                        provider="Gmail SMTP",
                        message_id=generated_msg_id,
                        provider_message_id=generated_msg_id,
                        idempotency_key=idempotency_key,
                        sent_at=datetime.utcnow()
                    )
                    db.add(log_entry)
                    await db.commit()

                return result

            except smtplib.SMTPAuthenticationError as auth_err:
                err_msg = f"Gmail SMTP Authentication Failed: Invalid App Password or Email. Code {auth_err.smtp_code}"
                logger.error(err_msg)
                return self._record_failure(err_msg)

            except (smtplib.SMTPConnectError, socket.timeout, socket.gaierror) as conn_err:
                err_msg = f"Gmail SMTP Connection Timeout/Error connecting to {self.host}: {str(conn_err)}"
                logger.error(err_msg)
                return self._record_failure(err_msg)

            except smtplib.SMTPException as smtp_err:
                err_msg = f"Gmail SMTP Protocol Error: {str(smtp_err)}"
                logger.error(err_msg)
                return self._record_failure(err_msg)

            except Exception as e:
                err_msg = f"Unexpected error during Gmail SMTP send: {str(e)}"
                logger.error(err_msg)
                return self._record_failure(err_msg)

        # 4. If neither Resend nor SMTP is configured: Simulated Dev Dispatch
        generated_msg_id = f"simulated_{int(datetime.utcnow().timestamp())}"
        logger.info(f"[DEV/TEST MODE] No live email service configured. Simulated dispatch to {to}. Subject: '{subject}'")
        return {
            "success": True,
            "status": "QUEUED_DEV",
            "provider": "Simulated Queue",
            "id": generated_msg_id,
            "message": "Email queued in simulated mode. Configure RESEND_API_KEY (for Render) or Gmail SMTP for live delivery."
        }

    def _record_failure(self, error_message: str) -> Dict[str, Any]:
        return {
            "success": False,
            "status": "FAILED",
            "provider": self.active_provider,
            "id": None,
            "error": error_message
        }

email_service = EmailService()
GmailSMTPService = EmailService

