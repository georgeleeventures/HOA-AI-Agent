import asyncio
import logging
import os

import asyncpg

from app.gmail.client import GmailClient

logger = logging.getLogger(__name__)

ATTACHMENTS_DIR = "/app/attachments"


class IngestionPipeline:
    def __init__(self, gmail_client: GmailClient, pool: asyncpg.Pool):
        self.gmail = gmail_client
        self.pool = pool

    async def ingest_all(self) -> int:
        """Fetch and store ALL historical emails. Returns count of processed emails."""
        total_processed = 0
        page_token = None

        logger.info("Starting baseline email ingestion")

        while True:
            messages, page_token = await self.gmail.fetch_all_messages(
                page_token=page_token
            )

            if not messages:
                break

            for msg_meta in messages:
                try:
                    result = await self.ingest_message(msg_meta["id"])
                    if result:
                        total_processed += 1
                except Exception:
                    logger.exception(
                        "Failed to ingest message %s", msg_meta.get("id")
                    )

            logger.info("Ingested %d emails so far...", total_processed)

            if not page_token:
                break

        logger.info("Baseline ingestion complete: %d emails processed", total_processed)
        return total_processed

    async def ingest_message(self, gmail_id: str) -> dict | None:
        """Fetch and process a single email. Returns parsed email dict or None if skipped."""
        # Check if already processed
        async with self.pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM emails WHERE gmail_id = $1", gmail_id
            )
            if exists:
                return None

        # Fetch and parse
        raw_message = await self.gmail.fetch_message(gmail_id)
        parsed = self.gmail.parse_message(raw_message)

        # Store email in database
        async with self.pool.acquire() as conn:
            email_uuid = await self._store_email(conn, parsed)

        # Download and store attachments
        if parsed.get("attachments"):
            file_paths = await self._store_attachments(
                gmail_id, parsed["attachments"]
            )
            parsed["attachment_paths"] = file_paths

        return parsed

    async def _store_email(self, conn: asyncpg.Connection, parsed: dict) -> str:
        """Insert email into the database. Returns the email UUID."""
        row = await conn.fetchrow(
            """
            INSERT INTO emails (
                gmail_id, thread_id, sender, recipients, subject,
                body_text, has_attachments, is_processed, received_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (gmail_id) DO NOTHING
            RETURNING id
            """,
            parsed["gmail_id"],
            parsed.get("thread_id"),
            parsed["sender"],
            parsed.get("recipients", []),
            parsed.get("subject"),
            parsed.get("body_text"),
            bool(parsed.get("attachments")),
            True,
            parsed.get("received_at"),
        )

        if row:
            return str(row["id"])
        # Already existed — fetch existing ID
        existing = await conn.fetchval(
            "SELECT id FROM emails WHERE gmail_id = $1", parsed["gmail_id"]
        )
        return str(existing)

    async def _store_attachments(
        self, message_id: str, attachments: list[dict]
    ) -> list[str]:
        """Download each attachment and save to disk. Returns list of file paths."""
        file_paths = []
        att_dir = os.path.join(ATTACHMENTS_DIR, message_id)
        os.makedirs(att_dir, exist_ok=True)

        for att in attachments:
            try:
                data = await self.gmail.fetch_attachment(
                    message_id, att["attachment_id"]
                )
                file_path = os.path.join(att_dir, att["filename"])
                await asyncio.to_thread(self._write_file, file_path, data)
                file_paths.append(file_path)
                logger.debug("Saved attachment: %s", file_path)
            except Exception:
                logger.exception(
                    "Failed to download attachment %s from message %s",
                    att.get("filename"),
                    message_id,
                )

        return file_paths

    @staticmethod
    def _write_file(path: str, data: bytes) -> None:
        with open(path, "wb") as f:
            f.write(data)
