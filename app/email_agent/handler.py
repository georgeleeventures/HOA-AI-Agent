import json
import logging
import os
import time

import asyncpg

from app.gmail.client import GmailClient
from app.knowledge.rag import RAGPipeline
from app.knowledge.embeddings import EmbeddingService
from app.documents.processor import DocumentProcessor
from app.documents.store import DocumentStore
from app.email_agent.auth import verify_sender, parse_auth_results

logger = logging.getLogger(__name__)

UNAUTHORIZED_RESPONSE = (
    "Thank you for your email. I don't have you on file as an authorized "
    "member of this HOA. If you believe this is an error, please contact "
    "your HOA administrator to add your email address.\n\n"
    "For privacy and security, I'm unable to share any HOA information "
    "with unverified contacts."
)


class EmailHandler:
    def __init__(
        self,
        pool: asyncpg.Pool,
        gmail_client: GmailClient,
        rag_pipeline: RAGPipeline,
        document_processor: DocumentProcessor,
        embedding_service: EmbeddingService,
    ):
        self.pool = pool
        self.gmail = gmail_client
        self.rag = rag_pipeline
        self.doc_processor = document_processor
        self.doc_store = DocumentStore(pool)
        self.embedding_service = embedding_service

    async def handle_incoming_email(self, gmail_id: str, hoa_id: str) -> None:
        """Main entry point for processing an incoming email."""
        try:
            raw_message = await self.gmail.fetch_message(gmail_id)
            parsed = self.gmail.parse_message(raw_message)
        except Exception:
            logger.exception("Failed to fetch/parse email %s", gmail_id)
            return

        # Verify sender
        auth_results = parse_auth_results(parsed.get("headers", []))
        resident = await verify_sender(self.pool, parsed["sender"], auth_results, hoa_id)

        if resident is None:
            logger.info("Unauthorized email from %s", parsed["sender"])
            await self.gmail.send_message(
                to=parsed["sender"],
                subject=f"Re: {parsed.get('subject', '')}",
                body=UNAUTHORIZED_RESPONSE,
                thread_id=parsed.get("thread_id"),
            )
            await self._log_audit(
                user_email=parsed["sender"],
                channel="email",
                action="unauthorized_attempt",
                query=parsed.get("subject", ""),
                response_summary="Unauthorized response sent",
                documents_cited=[],
                hoa_id=hoa_id,
            )
            return

        # Classify intent and route
        intent = self._classify_intent(parsed)
        logger.info(
            "Processing email from %s (role=%s, intent=%s)",
            resident["email"],
            resident["role"],
            intent,
        )

        if intent == "document_forward":
            await self._handle_document_forward(parsed, resident, hoa_id)
        elif intent == "thread_cc":
            await self._handle_thread_cc(parsed, resident, hoa_id)
        elif intent == "correction":
            await self._handle_correction(parsed, resident, hoa_id)
        else:
            await self._handle_question(parsed, resident, hoa_id)

    async def _handle_question(self, parsed: dict, resident: dict, hoa_id: str) -> None:
        """Handle a direct question via email."""
        question = parsed.get("body_text", "").strip()
        if not question:
            question = parsed.get("subject", "")

        start = time.monotonic()
        result = await self.rag.query(
            question=question,
            user_role=resident["role"],
            hoa_id=hoa_id,
        )
        response_time_ms = int((time.monotonic() - start) * 1000)

        # Format response with citations
        answer = result["answer"]
        if result.get("sources"):
            answer += "\n\n---\nSources:\n"
            for src in result["sources"]:
                answer += f"- {src['document_title']} ({src['category']} > {src['subcategory']})\n"

        await self.gmail.send_message(
            to=parsed["sender"],
            subject=f"Re: {parsed.get('subject', '')}",
            body=answer,
            thread_id=parsed.get("thread_id"),
        )

        confidence = result.get("confidence", "none")
        is_flagged = confidence in ("low", "none")
        action = "clarification_requested" if result.get("needs_clarification") else "question"

        await self._log_audit(
            user_email=resident["email"],
            channel="email",
            action=action,
            query=question,
            response_summary=result["answer"][:500],
            documents_cited=[
                {"title": s["document_title"], "category": s["category"]}
                for s in result.get("sources", [])
            ],
            full_response=result["answer"],
            confidence=confidence,
            avg_similarity_score=result.get("avg_similarity_score"),
            thread_id=parsed.get("thread_id"),
            is_flagged=is_flagged,
            flag_reason="low_confidence" if is_flagged else None,
            response_time_ms=response_time_ms,
            hoa_id=hoa_id,
        )

    async def _handle_document_forward(self, parsed: dict, resident: dict, hoa_id: str) -> None:
        """Handle a forwarded document (email with attachments)."""
        attachments = parsed.get("attachments", [])
        if not attachments:
            await self._handle_question(parsed, resident, hoa_id)
            return

        filed_docs = []
        for att in attachments:
            try:
                # Download attachment
                data = await self.gmail.fetch_attachment(
                    parsed["gmail_id"], att["attachment_id"]
                )

                # Save to disk
                att_dir = f"/app/attachments/{parsed['gmail_id']}"
                os.makedirs(att_dir, exist_ok=True)
                file_path = os.path.join(att_dir, att["filename"])
                with open(file_path, "wb") as f:
                    f.write(data)

                # Process: extract text, classify
                doc_data = await self.doc_processor.process_file(
                    file_path=file_path,
                    mime_type=att["mime_type"],
                    source_email_id=parsed["gmail_id"],
                )
                doc_data["source_filename"] = att["filename"]
                doc_data["file_path"] = file_path

                # Store document
                doc_id = await self.doc_store.store_document(doc_data, hoa_id)

                # Generate embeddings
                if doc_data.get("content"):
                    await self.embedding_service.embed_document(
                        self.pool, doc_id, doc_data["content"], hoa_id
                    )

                filed_docs.append(
                    f"- {att['filename']} -> {doc_data['category']} > "
                    f"{doc_data['subcategory']} ({doc_data.get('title', 'Untitled')})"
                )
            except Exception:
                logger.exception("Failed to process attachment %s", att.get("filename"))
                filed_docs.append(f"- {att.get('filename', 'unknown')} -> Failed to process")

        # Send confirmation
        confirmation = "Got it! Here's what I filed:\n\n" + "\n".join(filed_docs)
        confirmation += (
            "\n\nThese documents are now searchable. Anyone authorized can "
            "ask questions and I'll reference them."
        )

        await self.gmail.send_message(
            to=parsed["sender"],
            subject=f"Re: {parsed.get('subject', '')}",
            body=confirmation,
            thread_id=parsed.get("thread_id"),
        )

        await self._log_audit(
            user_email=resident["email"],
            channel="email",
            action="document_forward",
            query=f"Forwarded {len(attachments)} attachment(s)",
            response_summary=confirmation[:500],
            documents_cited=[],
            hoa_id=hoa_id,
        )

    async def _handle_thread_cc(self, parsed: dict, resident: dict, hoa_id: str) -> None:
        """Silently track an email thread the agent is CC'd on."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO emails (gmail_id, thread_id, sender, recipients, subject,
                                    body_text, has_attachments, is_processed, received_at,
                                    hoa_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, $8, $9)
                ON CONFLICT (gmail_id) DO NOTHING
                """,
                parsed["gmail_id"],
                parsed.get("thread_id"),
                parsed["sender"],
                parsed.get("recipients", []),
                parsed.get("subject"),
                parsed.get("body_text"),
                bool(parsed.get("attachments")),
                parsed.get("received_at"),
                hoa_id,
            )

        await self._log_audit(
            user_email=resident["email"],
            channel="email",
            action="thread_cc",
            query=parsed.get("subject", ""),
            response_summary="Silently tracked (no response sent)",
            documents_cited=[],
            hoa_id=hoa_id,
        )

    def _classify_intent(self, parsed: dict) -> str:
        """Determine the intent of an incoming email."""
        # Check if the agent is in Cc (not To) -> thread tracking
        recipients_to = [r.lower() for r in parsed.get("recipients_to", [])]
        recipients_cc = [r.lower() for r in parsed.get("recipients_cc", [])]

        hoa_email = parsed.get("hoa_inbox_email", "").lower()

        # If we're only in CC, silently track
        if hoa_email in recipients_cc and hoa_email not in recipients_to:
            return "thread_cc"

        # If there are attachments and it looks forwarded, treat as document forward
        if parsed.get("attachments"):
            subject = parsed.get("subject", "").lower()
            if subject.startswith("fwd:") or subject.startswith("fw:"):
                return "document_forward"
            # If attachments are documents (not images in signatures), treat as forward
            doc_types = {"application/pdf", "application/msword",
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                         "application/vnd.ms-excel",
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
            if any(att.get("mime_type") in doc_types for att in parsed["attachments"]):
                return "document_forward"

        # Check for correction/dispute in thread replies
        if parsed.get("thread_id"):
            correction_signals = [
                "that's wrong", "that is wrong", "incorrect", "not correct",
                "that's not right", "inaccurate", "bad answer", "wrong answer",
                "actually,", "correction:", "you're wrong", "this is wrong",
            ]
            body_lower = parsed.get("body_text", "").lower()
            if any(sig in body_lower for sig in correction_signals):
                return "correction"

        return "question"

    async def _handle_correction(self, parsed: dict, resident: dict, hoa_id: str) -> None:
        """Handle a user disputing a previous answer."""
        thread_id = parsed.get("thread_id")
        correction_text = parsed.get("body_text", "").strip()

        # Flag the original audit entry for this thread
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE audit_log
                    SET is_flagged = TRUE,
                        flag_reason = 'user_disputed'
                    WHERE thread_id = $1
                      AND user_email = $2
                      AND hoa_id = $3
                      AND action = 'question'
                      AND is_flagged = FALSE
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    thread_id,
                    resident["email"],
                    hoa_id,
                )
        except Exception:
            logger.exception("Failed to flag original audit entry")

        # Reply to user
        await self.gmail.send_message(
            to=parsed["sender"],
            subject=f"Re: {parsed.get('subject', '')}",
            body=(
                "Thank you for the correction. I've flagged this for review "
                "by your HOA administrator. They'll be able to update the "
                "answer so future questions get the right information."
            ),
            thread_id=thread_id,
        )

        # Log the correction itself
        await self._log_audit(
            user_email=resident["email"],
            channel="email",
            action="correction",
            query=correction_text,
            response_summary="Correction acknowledged, original flagged for review",
            documents_cited=[],
            thread_id=thread_id,
            is_flagged=True,
            flag_reason="user_disputed",
            hoa_id=hoa_id,
        )

    async def _log_audit(
        self,
        user_email: str,
        channel: str,
        action: str,
        query: str,
        response_summary: str,
        documents_cited: list,
        full_response: str | None = None,
        confidence: str | None = None,
        avg_similarity_score: float | None = None,
        thread_id: str | None = None,
        is_flagged: bool = False,
        flag_reason: str | None = None,
        response_time_ms: int | None = None,
        hoa_id: str | None = None,
    ) -> str | None:
        """Write an entry to the audit log. Returns the audit entry ID."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO audit_log (user_email, channel, action, query,
                                           response_summary, full_response,
                                           confidence, avg_similarity_score,
                                           thread_id, is_flagged, flag_reason,
                                           response_time_ms, documents_cited,
                                           hoa_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    RETURNING id
                    """,
                    user_email,
                    channel,
                    action,
                    query,
                    response_summary,
                    full_response,
                    confidence,
                    avg_similarity_score,
                    thread_id,
                    is_flagged,
                    flag_reason,
                    response_time_ms,
                    json.dumps(documents_cited),
                    hoa_id,
                )
                return str(row["id"]) if row else None
        except Exception:
            logger.exception("Failed to write audit log")
            return None
