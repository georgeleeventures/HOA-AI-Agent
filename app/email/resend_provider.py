"""Resend email provider implementation."""

from __future__ import annotations

import base64
import logging

import httpx

from app.config import settings
from app.email.models import Attachment, ParsedEmail
from app.email.provider import EmailProvider

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com"


class ResendProvider(EmailProvider):
    def __init__(self):
        self.api_key = settings.resend_api_key

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def send(
        self,
        from_email: str,
        to: str,
        subject: str,
        body: str,
        in_reply_to: str | None = None,
        references: list[str] | None = None,
    ) -> str:
        """Send email via Resend API. Returns message ID."""
        payload: dict = {
            "from": from_email,
            "to": [to],
            "subject": subject,
            "text": body,
        }

        custom_headers: dict[str, str] = {}
        if in_reply_to:
            custom_headers["In-Reply-To"] = in_reply_to
        if references:
            custom_headers["References"] = " ".join(references)
        if custom_headers:
            payload["headers"] = custom_headers

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{RESEND_API_URL}/emails",
                json=payload,
                headers=self._headers(),
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()

        message_id = data.get("id", "")
        logger.info("Sent email via Resend: to=%s subject=%s id=%s", to, subject, message_id)
        return message_id

    async def fetch_email(self, email_id: str) -> ParsedEmail:
        """Fetch full email content from Resend API."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{RESEND_API_URL}/emails/{email_id}",
                headers=self._headers(),
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()

        # Parse attachments
        attachments = []
        for att in data.get("attachments", []):
            content = att.get("content", "")
            att_data = base64.b64decode(content) if content else b""
            attachments.append(
                Attachment(
                    filename=att.get("filename", "unknown"),
                    mime_type=att.get("content_type", "application/octet-stream"),
                    data=att_data,
                )
            )

        to_field = data.get("to", [])
        cc_field = data.get("cc", [])

        return ParsedEmail(
            message_id=data.get("id", email_id),
            sender=data.get("from", ""),
            recipients_to=to_field if isinstance(to_field, list) else [to_field],
            recipients_cc=cc_field if isinstance(cc_field, list) else [],
            subject=data.get("subject", ""),
            body_text=data.get("text", ""),
            body_html=data.get("html", ""),
            attachments=attachments,
            in_reply_to=(data.get("headers") or {}).get("In-Reply-To"),
            references=(data.get("headers") or {}).get("References", "").split()
            if (data.get("headers") or {}).get("References")
            else [],
            received_at=None,
        )
