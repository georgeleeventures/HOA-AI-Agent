import base64
import json
import logging

from fastapi import APIRouter, Request, Response

from app.database import get_pool
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Track the last history ID to fetch only new messages.
# In production, this should be stored in the database.
_last_history_id: str | None = None

# Lazy-initialized handler (set up on first webhook call)
_email_handler = None


async def _get_handler():
    """Lazy-initialize the email handler with all dependencies."""
    global _email_handler
    if _email_handler is not None:
        return _email_handler

    from app.gmail.client import GmailClient
    from app.documents.processor import DocumentProcessor
    from app.knowledge.embeddings import EmbeddingService
    from app.knowledge.rag import RAGPipeline
    from app.email_agent.handler import EmailHandler

    pool = await get_pool()
    gmail_client = GmailClient()
    doc_processor = DocumentProcessor()
    embedding_service = EmbeddingService()
    rag_pipeline = RAGPipeline(pool, embedding_service)

    _email_handler = EmailHandler(
        pool=pool,
        gmail_client=gmail_client,
        rag_pipeline=rag_pipeline,
        document_processor=doc_processor,
        embedding_service=embedding_service,
    )
    return _email_handler


@router.post("/gmail")
async def gmail_webhook(request: Request) -> Response:
    """Handle Gmail Pub/Sub push notifications.

    Google sends a POST with a Pub/Sub message when new emails arrive.
    The message contains a historyId we use to fetch new messages.
    """
    global _last_history_id

    try:
        body = await request.json()
        message = body.get("message", {})
        data = message.get("data", "")

        # Decode the Pub/Sub message
        decoded = json.loads(base64.b64decode(data))
        new_history_id = decoded.get("historyId")
        logger.info("Gmail webhook received, historyId=%s", new_history_id)

        if not new_history_id:
            return Response(status_code=200)

        handler = await _get_handler()

        # Fetch new messages since last known history ID
        if _last_history_id:
            try:
                from app.gmail.client import GmailClient

                gmail = GmailClient()
                history = gmail.service.users().history().list(
                    userId="me",
                    startHistoryId=_last_history_id,
                    historyTypes=["messageAdded"],
                ).execute()

                changes = history.get("history", [])
                for change in changes:
                    for msg_added in change.get("messagesAdded", []):
                        gmail_id = msg_added["message"]["id"]
                        logger.info("Processing new email: %s", gmail_id)
                        try:
                            await handler.handle_incoming_email(gmail_id)
                        except Exception:
                            logger.exception(
                                "Failed to handle email %s", gmail_id
                            )
            except Exception:
                logger.exception("Failed to fetch history since %s", _last_history_id)

        _last_history_id = new_history_id

    except Exception:
        logger.exception("Error processing Gmail webhook")

    # Always return 200 to acknowledge the Pub/Sub message
    return Response(status_code=200)
