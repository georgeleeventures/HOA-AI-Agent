import asyncio
import base64
import email.utils
import logging
import re
from datetime import datetime, timezone
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import settings

logger = logging.getLogger(__name__)

TOKEN_URI = "https://oauth2.googleapis.com/token"


class GmailClient:
    def __init__(self):
        credentials = Credentials(
            token=None,
            refresh_token=settings.gmail_refresh_token,
            client_id=settings.gmail_client_id,
            client_secret=settings.gmail_client_secret,
            token_uri=TOKEN_URI,
        )
        self.service = build("gmail", "v1", credentials=credentials)

    async def fetch_all_messages(
        self, query: str = "", page_token: str | None = None
    ) -> tuple[list[dict], str | None]:
        """List messages with pagination. Returns (messages_metadata, next_page_token)."""

        def _list():
            kwargs = {"userId": "me", "maxResults": 500}
            if query:
                kwargs["q"] = query
            if page_token:
                kwargs["pageToken"] = page_token
            return self.service.users().messages().list(**kwargs).execute()

        result = await asyncio.to_thread(_list)
        messages = result.get("messages", [])
        next_token = result.get("nextPageToken")
        return messages, next_token

    async def fetch_message(self, message_id: str) -> dict:
        """Fetch a single message with full content."""

        def _get():
            return (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

        return await asyncio.to_thread(_get)

    async def fetch_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Download and decode an attachment."""

        def _get():
            return (
                self.service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )

        result = await asyncio.to_thread(_get)
        data = result.get("data", "")
        return base64.urlsafe_b64decode(data)

    async def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: str | None = None,
    ) -> dict:
        """Compose and send an email, optionally in an existing thread."""

        def _send():
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            send_body: dict = {"raw": raw}
            if thread_id:
                send_body["threadId"] = thread_id
            return (
                self.service.users()
                .messages()
                .send(userId="me", body=send_body)
                .execute()
            )

        return await asyncio.to_thread(_send)

    async def setup_watch(self, topic_name: str) -> dict:
        """Register Pub/Sub push notifications for new inbox messages."""

        def _watch():
            body = {
                "labelIds": ["INBOX"],
                "topicName": topic_name,
            }
            return self.service.users().watch(userId="me", body=body).execute()

        return await asyncio.to_thread(_watch)

    def parse_message(self, message: dict) -> dict:
        """Extract structured data from a raw Gmail API message."""
        headers = message.get("payload", {}).get("headers", [])
        header_map = {}
        for h in headers:
            name = h["name"].lower()
            # Keep all headers for auth parsing, but map common ones
            if name not in header_map:
                header_map[name] = h["value"]

        sender = header_map.get("from", "")
        # Extract just the email address from "Name <email>" format
        sender_email = self._extract_email(sender)

        recipients_to = self._parse_recipient_list(header_map.get("to", ""))
        recipients_cc = self._parse_recipient_list(header_map.get("cc", ""))

        subject = header_map.get("subject", "")

        # Parse date
        date_str = header_map.get("date", "")
        received_at = self._parse_date(date_str)

        # Extract body text and attachments
        payload = message.get("payload", {})
        body_text = ""
        attachments = []
        self._extract_parts(payload, body_text_parts := [], attachments)
        body_text = "\n".join(body_text_parts)

        return {
            "gmail_id": message.get("id", ""),
            "thread_id": message.get("threadId", ""),
            "sender": sender_email,
            "sender_display": sender,
            "recipients": recipients_to + recipients_cc,
            "recipients_to": recipients_to,
            "recipients_cc": recipients_cc,
            "subject": subject,
            "body_text": body_text,
            "attachments": attachments,
            "received_at": received_at,
            "headers": headers,
        }

    def _extract_parts(
        self, part: dict, body_parts: list[str], attachments: list[dict]
    ) -> None:
        """Recursively extract body text and attachment info from MIME parts."""
        mime_type = part.get("mimeType", "")
        filename = part.get("filename", "")

        # If this part has sub-parts, recurse
        if "parts" in part:
            for sub in part["parts"]:
                self._extract_parts(sub, body_parts, attachments)
            return

        body = part.get("body", {})

        # Attachment
        if filename and body.get("attachmentId"):
            attachments.append(
                {
                    "filename": filename,
                    "mime_type": mime_type,
                    "attachment_id": body["attachmentId"],
                    "size": body.get("size", 0),
                }
            )
            return

        # Body text
        data = body.get("data", "")
        if not data:
            return

        decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

        if mime_type == "text/plain":
            body_parts.insert(0, decoded)  # Prefer plain text
        elif mime_type == "text/html" and not body_parts:
            # Strip HTML tags as fallback
            clean = re.sub(r"<[^>]+>", " ", decoded)
            clean = re.sub(r"\s+", " ", clean).strip()
            body_parts.append(clean)

    def _extract_email(self, sender: str) -> str:
        """Extract email address from 'Display Name <email@domain.com>' format."""
        match = re.search(r"<([^>]+)>", sender)
        if match:
            return match.group(1).lower().strip()
        # Might already be just an email
        return sender.lower().strip()

    def _parse_recipient_list(self, header_value: str) -> list[str]:
        """Parse a comma-separated recipient header into a list of emails."""
        if not header_value:
            return []
        addresses = email.utils.getaddresses([header_value])
        return [addr.lower().strip() for _, addr in addresses if addr]

    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse an email date header into a datetime."""
        if not date_str:
            return None
        try:
            parsed = email.utils.parsedate_to_datetime(date_str)
            return parsed.astimezone(timezone.utc)
        except (ValueError, TypeError):
            logger.warning("Failed to parse date: %s", date_str)
            return None
