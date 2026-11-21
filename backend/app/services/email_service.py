import smtplib
import socket
import logging
import uuid
from email.message import EmailMessage
from email.utils import make_msgid, formatdate
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.config import settings

logger = logging.getLogger("meetme.email_service")

class GmailSMTPService:
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.email = settings.SMTP_EMAIL
        self.password = settings.SMTP_PASSWORD
        self.from_name = settings.SMTP_FROM_NAME
        self.timeout = settings.SMTP_TIMEOUT

    @property
    def is_configured(self) -> bool:
        """Returns True if valid Gmail SMTP credentials are configured."""
        return bool(self.email and self.password and "[YOUR" not in self.password)

    def test_connection(self) -> Dict[str, Any]:
        """
        Tests the Gmail SMTP connection and authentication with STARTTLS.
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "Gmail SMTP credentials not configured (SMTP_EMAIL or SMTP_PASSWORD missing)."
            }

        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.email, self.password)
                return {
                    "success": True,
                    "message": f"Successfully authenticated with Gmail SMTP server ({self.host}:{self.port})."
                }
        except smtplib.SMTPAuthenticationError as auth_err:
            logger.error(f"Gmail SMTP Authentication Error: {auth_err}")
            return {
                "success": False,
                "error": f"Authentication failed: Invalid Gmail address or Google App Password ({auth_err.smtp_code})."
            }
        except (smtplib.SMTPConnectError, socket.timeout, socket.gaierror) as conn_err:
            logger.error(f"Gmail SMTP Connection Error: {conn_err}")
            return {
                "success": False,
                "error": f"Connection failed to {self.host}:{self.port} - {str(conn_err)}"
            }
        except smtplib.SMTPException as smtp_err:
            logger.error(f"Gmail SMTP Error: {smtp_err}")
            return {
                "success": False,
                "error": f"SMTP Exception: {str(smtp_err)}"
            }
        except Exception as e:
            logger.error(f"Unexpected SMTP Error: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }

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
        Sends an email using Python's native smtplib over Gmail STARTTLS.
        Includes idempotency checks, detailed status tracking, and fallback for unconfigured environments.
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
                    "provider": "Gmail SMTP",
                    "id": existing_email.message_id or existing_email.id,
                    "message": "Duplicate send skipped; email previously dispatched successfully."
                }

        # 2. Prepare EmailMessage with RFC compliant headers
        msg = EmailMessage()
        msg["Subject"] = subject
        sender_address = f"{self.from_name} <{self.email}>" if self.email else f"MEETME Platform <notifications@meetme.ai>"
        msg["From"] = sender_address
        msg["To"] = f"{recipient_name} <{to}>" if recipient_name else to
        msg["Date"] = formatdate(localtime=True)
        
        # Unique message-id
        generated_msg_id = make_msgid(domain=self.email.split("@")[-1] if "@" in self.email else "meetme.ai")
        msg["Message-ID"] = generated_msg_id
        if idempotency_key:
            msg["X-MEETME-Idempotency-Key"] = idempotency_key

        # Plain-text and HTML alternative content
        plain_text_content = text or "Please view this email in an HTML-compatible client."
        msg.set_content(plain_text_content)
        msg.add_alternative(html, subtype="html")

        # 3. If Gmail SMTP credentials are not configured, queue locally for testing/dev
        if not self.is_configured:
            logger.info(f"[DEV/TEST MODE] Gmail SMTP not configured. Simulated dispatch to {to}. Subject: '{subject}'")
            status = "QUEUED_DEV"
            result = {
                "success": True,
                "status": status,
                "provider": "Gmail SMTP (Simulated)",
                "id": generated_msg_id,
                "message": "Email logged and queued in dev/test mode. Configure SMTP_EMAIL and SMTP_PASSWORD for live delivery."
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
                    status=status,
                    provider="Gmail SMTP",
                    message_id=generated_msg_id,
                    provider_message_id=generated_msg_id,
                    idempotency_key=idempotency_key,
                    sent_at=datetime.utcnow()
                )
                db.add(log_entry)
                await db.commit()

            return result

        # 4. Perform actual native SMTP STARTTLS delivery
        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.email, self.password)
                server.send_message(msg)

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
            return self._record_failure(db, workspace_id, to, recipient_name, subject, html, plain_text_content, email_type, task_ids, idempotency_key, generated_msg_id, err_msg)

        except (smtplib.SMTPConnectError, socket.timeout, socket.gaierror) as conn_err:
            err_msg = f"Gmail SMTP Connection Timeout/Error connecting to {self.host}:{self.port}: {str(conn_err)}"
            logger.error(err_msg)
            return self._record_failure(db, workspace_id, to, recipient_name, subject, html, plain_text_content, email_type, task_ids, idempotency_key, generated_msg_id, err_msg)

        except smtplib.SMTPException as smtp_err:
            err_msg = f"Gmail SMTP Protocol Error: {str(smtp_err)}"
            logger.error(err_msg)
            return self._record_failure(db, workspace_id, to, recipient_name, subject, html, plain_text_content, email_type, task_ids, idempotency_key, generated_msg_id, err_msg)

        except Exception as e:
            err_msg = f"Unexpected error during Gmail SMTP send: {str(e)}"
            logger.error(err_msg)
            return self._record_failure(db, workspace_id, to, recipient_name, subject, html, plain_text_content, email_type, task_ids, idempotency_key, generated_msg_id, err_msg)

    async def _record_failure(
        self,
        db: Optional[AsyncSession],
        workspace_id: Optional[str],
        to: str,
        recipient_name: Optional[str],
        subject: str,
        html: str,
        plain_text: str,
        email_type: str,
        task_ids: List[str],
        idempotency_key: Optional[str],
        message_id: str,
        error_message: str
    ) -> Dict[str, Any]:
        from backend.app.models.schema import EmailLog
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
                body_text=plain_text,
                status="FAILED",
                provider="Gmail SMTP",
                message_id=message_id,
                error_message=error_message,
                idempotency_key=idempotency_key
            )
            db.add(log_entry)
            await db.commit()

        return {
            "success": False,
            "status": "FAILED",
            "provider": "Gmail SMTP",
            "id": None,
            "error": error_message
        }

email_service = GmailSMTPService()
