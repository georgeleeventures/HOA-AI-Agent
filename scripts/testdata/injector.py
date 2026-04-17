"""Inject synthetic emails into Gmail via send or insert."""

from __future__ import annotations

import asyncio
import logging
import time

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .generator import build_mime_message, mime_to_raw_base64
from .scenarios import EmailScenario

logger = logging.getLogger(__name__)

TOKEN_URI = "https://oauth2.googleapis.com/token"


class GmailInjector:
    """Injects synthetic emails into a Gmail account.

    Supports two modes:
    - send: Sends from a test account TO the HOA inbox. Emails arrive with
      valid DKIM/DMARC since they go through Gmail SMTP.
    - insert: Inserts directly into the HOA inbox. Emails have NO auth
      headers, so HOUSEKEEP_TEST_MODE=true is required for the agent to
      process them.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        hoa_email: str,
        hoa_refresh_token: str | None = None,
        sender_refresh_token: str | None = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.hoa_email = hoa_email
        self.message_id_map: dict[str, str] = {}  # scenario_name -> Message-ID

        # Build services
        if hoa_refresh_token:
            hoa_creds = Credentials(
                token=None,
                refresh_token=hoa_refresh_token,
                client_id=client_id,
                client_secret=client_secret,
                token_uri=TOKEN_URI,
            )
            self.hoa_service = build("gmail", "v1", credentials=hoa_creds)
        else:
            self.hoa_service = None

        if sender_refresh_token:
            sender_creds = Credentials(
                token=None,
                refresh_token=sender_refresh_token,
                client_id=client_id,
                client_secret=client_secret,
                token_uri=TOKEN_URI,
            )
            self.sender_service = build("gmail", "v1", credentials=sender_creds)
        else:
            self.sender_service = None

    async def send_email(self, scenario: EmailScenario) -> dict:
        """Send an email from the test sender account TO the HOA inbox.

        This produces emails with valid DKIM/DMARC.
        Requires sender_refresh_token to be set.
        """
        if not self.sender_service:
            raise RuntimeError(
                "sender_refresh_token required for send mode. "
                "Use --sender-token or switch to --method insert."
            )

        mime_msg = build_mime_message(scenario, self.hoa_email, self.message_id_map)
        raw = mime_to_raw_base64(mime_msg)

        body: dict = {"raw": raw}

        # If this is a reply, try to use the parent's threadId
        if scenario.is_reply_to and scenario.is_reply_to in self.message_id_map:
            parent_info = self.message_id_map.get(f"{scenario.is_reply_to}__thread")
            if parent_info:
                body["threadId"] = parent_info

        def _send():
            return (
                self.sender_service.users()
                .messages()
                .send(userId="me", body=body)
                .execute()
            )

        result = await asyncio.to_thread(_send)

        # Store message ID and thread ID for threading
        gmail_id = result.get("id", "")
        thread_id = result.get("threadId", "")
        self.message_id_map[scenario.name] = f"<{gmail_id}@mail.gmail.com>"
        self.message_id_map[f"{scenario.name}__thread"] = thread_id

        logger.info(
            "Sent: %s (gmail_id=%s, thread=%s)",
            scenario.name,
            gmail_id,
            thread_id,
        )
        return result

    async def insert_email(self, scenario: EmailScenario) -> dict:
        """Insert an email directly into the HOA inbox.

        Emails inserted this way have NO authentication headers.
        Requires HOUSEKEEP_TEST_MODE=true for the agent to process them.
        Requires hoa_refresh_token to be set.
        """
        if not self.hoa_service:
            raise RuntimeError(
                "hoa_refresh_token required for insert mode. "
                "Provide --hoa-token or use the GMAIL_REFRESH_TOKEN from .env."
            )

        mime_msg = build_mime_message(scenario, self.hoa_email, self.message_id_map)
        raw = mime_to_raw_base64(mime_msg)

        body: dict = {
            "raw": raw,
            "labelIds": ["INBOX", "UNREAD"],
        }

        # Threading
        if scenario.is_reply_to and scenario.is_reply_to in self.message_id_map:
            parent_thread = self.message_id_map.get(f"{scenario.is_reply_to}__thread")
            if parent_thread:
                body["threadId"] = parent_thread

        def _insert():
            return (
                self.hoa_service.users()
                .messages()
                .insert(userId="me", body=body)
                .execute()
            )

        result = await asyncio.to_thread(_insert)

        gmail_id = result.get("id", "")
        thread_id = result.get("threadId", "")
        self.message_id_map[scenario.name] = f"<{gmail_id}@mail.gmail.com>"
        self.message_id_map[f"{scenario.name}__thread"] = thread_id

        logger.info(
            "Inserted: %s (gmail_id=%s, thread=%s)",
            scenario.name,
            gmail_id,
            thread_id,
        )
        return result

    async def inject_scenario(
        self, scenario: EmailScenario, method: str = "send"
    ) -> dict:
        """Inject a single scenario using the specified method."""
        if method == "send":
            return await self.send_email(scenario)
        elif method == "insert":
            return await self.insert_email(scenario)
        else:
            raise ValueError(f"Unknown injection method: {method}")

    async def inject_all(
        self,
        scenarios: list[EmailScenario],
        method: str = "send",
        delay: float = 2.0,
    ) -> list[dict]:
        """Inject all scenarios sequentially with a delay between each.

        Returns a list of results with scenario metadata.
        """
        results = []

        for i, scenario in enumerate(scenarios):
            logger.info(
                "[%d/%d] Injecting: %s (%s)",
                i + 1,
                len(scenarios),
                scenario.name,
                scenario.intent,
            )

            try:
                result = await self.inject_scenario(scenario, method)
                results.append({
                    "scenario": scenario.name,
                    "intent": scenario.intent,
                    "gmail_id": result.get("id", ""),
                    "thread_id": result.get("threadId", ""),
                    "target_category": scenario.target_category,
                    "target_subcategory": scenario.target_subcategory,
                    "status": "ok",
                })
            except Exception as e:
                logger.error("Failed to inject %s: %s", scenario.name, e)
                results.append({
                    "scenario": scenario.name,
                    "intent": scenario.intent,
                    "gmail_id": "",
                    "thread_id": "",
                    "target_category": scenario.target_category,
                    "target_subcategory": scenario.target_subcategory,
                    "status": f"error: {e}",
                })

            # Delay between sends to avoid rate limits
            if i < len(scenarios) - 1 and delay > 0:
                await asyncio.sleep(delay)

        return results
