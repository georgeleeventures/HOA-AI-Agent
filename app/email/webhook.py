"""Resend inbound email webhook handler.

HOA resolution is sender-based: a single central inbox (e.g.
``hello@housekeep.click``) receives mail for every HOA, and we identify the
tenant by looking up the sender's email in the ``residents`` table across
all HOAs. Senders that don't belong to any HOA get a polite "not authorized"
reply.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response

from app.database import get_pool

logger = logging.getLogger(__name__)

router = APIRouter()

# Placeholder HOA used for audit_log rows that aren't attributable to a real
# tenant (e.g. unauthorized senders). Matches the "Default HOA" row seeded by
# migration 003. Using a real HOA id avoids the NOT NULL / FK constraints on
# audit_log.hoa_id.
PLATFORM_HOA_ID = "00000000-0000-0000-0000-000000000001"

UNAUTHORIZED_REPLY_BODY = (
    "Thank you for your email. I don't have you on file as a member of any "
    "HOA using HouseKeep.\n\n"
    "If you believe this is an error, please contact your HOA administrator "
    "to invite you. For privacy and security, I'm unable to share any HOA "
    "information with unverified contacts.\n\n"
    "— HouseKeep"
)


@router.post("/email/{webhook_secret}")
async def resend_inbound_webhook(request: Request, webhook_secret: str):
    """Handle inbound email notifications from Resend.

    Flow:
    1. Resend posts a webhook event referencing an email_id.
    2. We fetch the full email via the Resend API to get the sender.
    3. We resolve the HOA by looking up the sender in residents.
    4. If the sender is a known resident, we process via the standard
       EmailHandler pipeline (scoped to that HOA).
    5. Otherwise, we send a polite "not authorized" reply and log the
       attempt to the audit log under the platform HOA.
    """
    from app.config import settings

    if webhook_secret != settings.email_webhook_secret:
        return Response(status_code=401)

    body = await request.json()
    event_type = body.get("type", "")

    if event_type != "email.received":
        return Response(status_code=200)

    data = body.get("data", {})
    email_id = data.get("email_id")

    if not email_id:
        logger.warning("Resend webhook missing email_id: %s", body)
        return Response(status_code=200)

    pool = await get_pool()

    try:
        from app.documents.processor import DocumentProcessor
        from app.documents.store import DocumentStore
        from app.email.resend_provider import ResendProvider
        from app.email_agent.auth import (
            parse_auth_results,
            resolve_hoa_from_email,
            verify_sender,
        )
        from app.email_agent.handler import EmailHandler
        from app.knowledge.embeddings import EmbeddingService
        from app.knowledge.rag import RAGPipeline

        provider = ResendProvider()
        parsed = await provider.fetch_email(email_id)

        sender_email = (parsed.sender or "").strip()
        if not sender_email:
            logger.warning("Resend email %s has no sender; dropping", email_id)
            return Response(status_code=200)

        # Resolve HOA from the sender's email address. A single central inbox
        # (settings.housekeep_inbound_email) serves every HOA, so the sender
        # — not the recipient — tells us which tenant we're operating in.
        hoa = await resolve_hoa_from_email(pool, sender_email)

        if hoa is None:
            await _handle_unauthorized_sender(pool, provider, parsed, sender_email)
            return Response(status_code=200)

        hoa_id = str(hoa["hoa_id"])
        hoa_slug = hoa["hoa_slug"]

        embedding_service = EmbeddingService()
        rag = RAGPipeline(pool, embedding_service)
        doc_processor = DocumentProcessor()

        handler = EmailHandler(
            pool=pool,
            gmail_client=None,
            rag_pipeline=rag,
            document_processor=doc_processor,
            embedding_service=embedding_service,
        )

        # Store email record
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO emails (
                    gmail_id, message_id, thread_id, sender, recipients,
                    subject, body_text, has_attachments, is_processed,
                    received_at, hoa_id, provider
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, TRUE, $9, $10, 'resend')
                ON CONFLICT (gmail_id) DO NOTHING
                """,
                email_id,
                email_id,
                parsed.in_reply_to or email_id,
                parsed.sender,
                parsed.recipients_to + parsed.recipients_cc,
                parsed.subject,
                parsed.body_text,
                bool(parsed.attachments),
                parsed.received_at or datetime.now(timezone.utc).replace(tzinfo=None),
                hoa_id,
            )

        # Double-check DKIM/DMARC + authorization within this HOA. The
        # resolve_hoa_from_email call already proved the sender exists in
        # residents, but verify_sender also enforces SPF/DKIM/DMARC.
        auth_results = parse_auth_results(
            [{"name": k, "value": v} for k, v in parsed.raw_headers.items()]
        )
        resident = await verify_sender(pool, parsed.sender, auth_results, hoa_id)

        if resident is None:
            logger.info(
                "Resend email %s from %s failed auth for hoa %s",
                email_id,
                parsed.sender,
                hoa_id,
            )
            from_email = f"noreply@{settings.resend_sending_domain}"
            await provider.send(
                from_email=from_email,
                to=parsed.sender,
                subject=f"Re: {parsed.subject}",
                body=(
                    "Thank you for your email. I couldn't verify the "
                    "authenticity of this message (SPF/DKIM/DMARC). "
                    "Please try sending again from your registered address."
                ),
                in_reply_to=parsed.message_id,
            )
            return Response(status_code=200)

        # Route by intent
        intent = handler._classify_intent({
            "recipients_to": parsed.recipients_to,
            "recipients_cc": parsed.recipients_cc,
            "hoa_inbox_email": settings.housekeep_inbound_email,
            "attachments": [{"mime_type": a.mime_type} for a in parsed.attachments],
            "subject": parsed.subject,
            "body_text": parsed.body_text,
            "thread_id": parsed.in_reply_to,
        })

        from_email = f"{hoa_slug}@{settings.resend_sending_domain}"

        if intent == "document_forward":
            for att in parsed.attachments:
                att_dir = f"/app/attachments/{email_id}"
                os.makedirs(att_dir, exist_ok=True)
                file_path = os.path.join(att_dir, att.filename)
                with open(file_path, "wb") as f:
                    f.write(att.data)

                doc_data = await doc_processor.process_file(
                    file_path=file_path,
                    mime_type=att.mime_type,
                    source_email_id=email_id,
                )
                doc_data["source_filename"] = att.filename
                doc_data["file_path"] = file_path

                store = DocumentStore(pool)
                doc_id = await store.store_document(doc_data, hoa_id)
                if doc_data.get("content"):
                    await embedding_service.embed_document(
                        pool, doc_id, doc_data["content"], hoa_id
                    )

        elif intent == "question":
            result = await rag.query(
                question=parsed.body_text or parsed.subject,
                user_role=resident["role"],
                hoa_id=hoa_id,
            )
            await provider.send(
                from_email=from_email,
                to=parsed.sender,
                subject=f"Re: {parsed.subject}",
                body=result["answer"],
                in_reply_to=parsed.message_id,
            )

        logger.info(
            "Processed Resend email %s (intent=%s, hoa=%s)",
            email_id,
            intent,
            hoa_id,
        )

    except Exception:
        logger.exception("Failed to process Resend email %s", email_id)

    return Response(status_code=200)


async def _handle_unauthorized_sender(pool, provider, parsed, sender_email: str) -> None:
    """Reply to an unknown sender and record the attempt in the audit log."""
    from app.config import settings

    logger.info("Unauthorized Resend email from %s", sender_email)

    from_email = f"noreply@{settings.resend_sending_domain}"
    subject = parsed.subject or ""
    try:
        await provider.send(
            from_email=from_email,
            to=sender_email,
            subject=f"Re: {subject}" if subject else "About your email to HouseKeep",
            body=UNAUTHORIZED_REPLY_BODY,
            in_reply_to=parsed.message_id,
        )
    except Exception:
        logger.exception("Failed to send unauthorized reply to %s", sender_email)

    # Record the attempt. audit_log.hoa_id is NOT NULL with a FK to hoas, so
    # we use the platform/default HOA as a placeholder for unattributable rows.
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_log (user_email, channel, action, query,
                                       response_summary, documents_cited, hoa_id)
                VALUES ($1, 'email', 'unauthorized_attempt', $2, $3, $4, $5)
                """,
                sender_email,
                subject,
                "Unauthorized sender (not in any HOA); informational reply sent",
                json.dumps([]),
                PLATFORM_HOA_ID,
            )
    except Exception:
        logger.exception("Failed to log unauthorized attempt for %s", sender_email)
