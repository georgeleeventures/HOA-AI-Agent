"""Gmail adapter wrapping the existing GmailClient as an EmailProvider."""

from __future__ import annotations

import asyncio
import base64
from email.mime.text import MIMEText

from app.email.models import Attachment, ParsedEmail
from app.email.provider import EmailProvider
from app.gmail.client import GmailClient


class GmailProvider(EmailProvider):
    def __init__(self, gmail_client: GmailClient | None = None):
        self.client = gmail_client or GmailClient()

    async def send(
        self,
        from_email: str,
        to: str,
        subject: str,
        body: str,
        in_reply_to: str | None = None,
        references: list[str] | None = None,
    ) -> str:
        result = await self.client.send_message(
            to=to, subject=subject, body=body, thread_id=None
        )
        return result.get("id", "")

    async def fetch_email(self, email_id: str) -> ParsedEmail:
        raw = await self.client.fetch_message(email_id)
        parsed = self.client.parse_message(raw)

        attachments = []
        for att in parsed.get("attachments", []):
            data = await self.client.fetch_attachment(
                email_id, att["attachment_id"]
            )
            attachments.append(
                Attachment(
                    filename=att["filename"],
                    mime_type=att["mime_type"],
                    data=data,
                )
            )

        return ParsedEmail(
            message_id=parsed["gmail_id"],
            sender=parsed["sender"],
            recipients_to=parsed.get("recipients_to", []),
            recipients_cc=parsed.get("recipients_cc", []),
            subject=parsed.get("subject", ""),
            body_text=parsed.get("body_text", ""),
            attachments=attachments,
            received_at=parsed.get("received_at"),
            raw_headers={
                h["name"]: h["value"]
                for h in parsed.get("headers", [])
            },
        )
