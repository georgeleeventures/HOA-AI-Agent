"""Shared email data models used across all providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Attachment:
    filename: str
    mime_type: str
    data: bytes


@dataclass
class ParsedEmail:
    message_id: str
    sender: str
    recipients_to: list[str]
    recipients_cc: list[str]
    subject: str
    body_text: str
    body_html: str = ""
    attachments: list[Attachment] = field(default_factory=list)
    in_reply_to: str | None = None
    references: list[str] = field(default_factory=list)
    received_at: datetime | None = None
    raw_headers: dict = field(default_factory=dict)
