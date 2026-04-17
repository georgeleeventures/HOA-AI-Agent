"""Abstract email provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.email.models import ParsedEmail


class EmailProvider(ABC):
    @abstractmethod
    async def send(
        self,
        from_email: str,
        to: str,
        subject: str,
        body: str,
        in_reply_to: str | None = None,
        references: list[str] | None = None,
    ) -> str:
        """Send an email. Returns message ID."""

    @abstractmethod
    async def fetch_email(self, email_id: str) -> ParsedEmail:
        """Fetch full email content by ID."""
