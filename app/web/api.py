import json
import logging
import time

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from app.database import get_pool
from app.web.routes import get_current_user
from app.web.demo_data import DEMO_DOCUMENTS, DEMO_MAINTENANCE, match_demo_response

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    question: str


class FeedbackRequest(BaseModel):
    audit_id: str
    feedback: str  # "positive" or "negative"
    comment: str | None = None


class AdminAnswerCreate(BaseModel):
    question_pattern: str
    answer: str
    source_audit_id: str | None = None


class AdminAnswerUpdate(BaseModel):
    question_pattern: str | None = None
    answer: str | None = None


class ResidentCreate(BaseModel):
    email: str
    name: str
    unit: str | None = None
    role: str = "resident"


class ResidentUpdate(BaseModel):
    role: str


def _require_auth(request: Request) -> dict:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _require_admin(request: Request) -> dict:
    user = _require_auth(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.post("/chat")
async def chat(request: Request, body: ChatRequest):
    user = _require_auth(request)

    if user.get("is_demo"):
        return match_demo_response(body.question)

    from app.knowledge.embeddings import EmbeddingService
    from app.knowledge.rag import RAGPipeline

    pool = await get_pool()
    embedding_service = EmbeddingService()
    rag = RAGPipeline(pool, embedding_service)

    start = time.monotonic()
    result = await rag.query(
        question=body.question,
        user_role=user.get("role", "resident"),
    )
    response_time_ms = int((time.monotonic() - start) * 1000)

    confidence = result.get("confidence", "none")
    is_flagged = confidence in ("low", "none")

    # Log to audit
    audit_id = None
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO audit_log (user_email, channel, action, query,
                                       response_summary, full_response,
                                       confidence, avg_similarity_score,
                                       is_flagged, flag_reason,
                                       response_time_ms, documents_cited)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING id
                """,
                user["email"],
                "web_chat",
                "question",
                body.question,
                result["answer"][:500],
                result["answer"],
                confidence,
                result.get("avg_similarity_score"),
                is_flagged,
                "low_confidence" if is_flagged else None,
                response_time_ms,
                json.dumps([
                    {"title": s["document_title"], "category": s["category"]}
                    for s in result.get("sources", [])
                ]),
            )
            audit_id = str(row["id"]) if row else None
    except Exception:
        logger.exception("Failed to write audit log")

    result["audit_id"] = audit_id
    return result


@router.post("/chat/feedback")
async def submit_feedback(request: Request, body: FeedbackRequest):
    user = _require_auth(request)

    if user.get("is_demo"):
        return {"status": "ok"}

    pool = await get_pool()

    if body.feedback not in ("positive", "negative"):
        raise HTTPException(status_code=400, detail="Feedback must be 'positive' or 'negative'")

    async with pool.acquire() as conn:
        # Verify the audit entry exists and belongs to this user
        row = await conn.fetchrow(
            "SELECT id, user_email FROM audit_log WHERE id = $1",
            body.audit_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Audit entry not found")
        if row["user_email"] != user["email"]:
            raise HTTPException(status_code=403, detail="Cannot provide feedback on another user's query")

        if body.feedback == "negative":
            notes = f"User feedback: negative"
            if body.comment:
                notes += f" — {body.comment}"
            await conn.execute(
                """
                UPDATE audit_log
                SET is_flagged = TRUE,
                    flag_reason = 'user_disputed',
                    admin_notes = COALESCE(admin_notes || E'\n', '') || $1
                WHERE id = $2
                """,
                notes,
                body.audit_id,
            )

    return {"status": "ok"}


@router.get("/documents")
async def list_documents(
    request: Request,
    category: str | None = None,
    subcategory: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    user = _require_auth(request)

    if user.get("is_demo"):
        docs = DEMO_DOCUMENTS
        if category:
            docs = [d for d in docs if d["category"] == category]
        if subcategory:
            docs = [d for d in docs if d["subcategory"] == subcategory]
        if search:
            s = search.lower()
            docs = [d for d in docs if s in d["title"].lower()]
        return {"documents": docs[offset:offset + limit]}

    from app.documents.store import DocumentStore

    pool = await get_pool()
    store = DocumentStore(pool)
    docs = await store.list_documents(
        category=category,
        subcategory=subcategory,
        search=search,
        limit=limit,
        offset=offset,
    )
    return {"documents": docs}


@router.get("/documents/{doc_id}")
async def get_document(request: Request, doc_id: str):
    user = _require_auth(request)

    if user.get("is_demo"):
        for d in DEMO_DOCUMENTS:
            if d["id"] == doc_id:
                return {**d, "content": "This is a demo document. In a live environment, the full document content would be displayed here."}
        raise HTTPException(status_code=404, detail="Document not found")

    from app.documents.store import DocumentStore

    pool = await get_pool()
    store = DocumentStore(pool)
    doc = await store.get_document(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return doc


@router.get("/maintenance")
async def list_maintenance(
    request: Request,
    limit: int = 50,
    offset: int = 0,
):
    user = _require_auth(request)

    if user.get("is_demo"):
        return {"maintenance": DEMO_MAINTENANCE[offset:offset + limit]}

    pool = await get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, unit, description, issue_type, status, photos,
                   contractor, cost, reported_by, created_at, updated_at
            FROM maintenance_log
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )

    results = []
    for row in rows:
        d = dict(row)
        d["id"] = str(d["id"])
        if isinstance(d.get("photos"), str):
            d["photos"] = json.loads(d["photos"])
        results.append(d)

    return {"maintenance": results}


@router.post("/admin/residents")
async def add_resident(request: Request, body: ResidentCreate):
    _require_admin(request)
    pool = await get_pool()

    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO residents (email, name, unit, role)
                VALUES ($1, $2, $3, $4)
                RETURNING id, email, name, unit, role
                """,
                body.email.lower().strip(),
                body.name,
                body.unit,
                body.role,
            )
            result = dict(row)
            result["id"] = str(result["id"])
            return result
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Failed to add resident. Email may already exist.",
            )


@router.delete("/admin/residents/{resident_id}")
async def remove_resident(request: Request, resident_id: str):
    _require_admin(request)
    pool = await get_pool()

    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM residents WHERE id = $1", resident_id
        )

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Resident not found")
    return {"status": "deleted"}


@router.put("/admin/residents/{resident_id}")
async def update_resident(request: Request, resident_id: str, body: ResidentUpdate):
    _require_admin(request)
    pool = await get_pool()

    valid_roles = {"resident", "board_member", "admin"}
    if body.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE residents SET role = $1, updated_at = NOW()
            WHERE id = $2
            """,
            body.role,
            resident_id,
        )

    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Resident not found")
    return {"status": "updated"}


class FlagRequest(BaseModel):
    is_flagged: bool = True
    flag_reason: str | None = None


class NotesRequest(BaseModel):
    admin_notes: str


@router.get("/admin/audit")
async def get_audit_log(
    request: Request,
    channel: str | None = None,
    action: str | None = None,
    flagged: bool | None = None,
    confidence: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    _require_admin(request)
    pool = await get_pool()

    conditions = []
    params = []
    idx = 1

    if channel:
        conditions.append(f"channel = ${idx}")
        params.append(channel)
        idx += 1
    if action:
        conditions.append(f"action = ${idx}")
        params.append(action)
        idx += 1
    if flagged is not None:
        conditions.append(f"is_flagged = ${idx}")
        params.append(flagged)
        idx += 1
    if confidence:
        conditions.append(f"confidence = ${idx}")
        params.append(confidence)
        idx += 1
    if date_from:
        conditions.append(f"created_at >= ${idx}::timestamp")
        params.append(date_from)
        idx += 1
    if date_to:
        conditions.append(f"created_at <= ${idx}::timestamp")
        params.append(date_to)
        idx += 1
    if search:
        conditions.append(f"query ILIKE ${idx}")
        params.append(f"%{search}%")
        idx += 1

    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    params.append(limit)
    params.append(offset)

    query_sql = f"""
        SELECT id, user_email, channel, action, query,
               response_summary, documents_cited, confidence,
               is_flagged, flag_reason, response_time_ms, created_at
        FROM audit_log
        {where}
        ORDER BY created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query_sql, *params)

        # Also get total count for pagination
        count_sql = f"SELECT COUNT(*) FROM audit_log {where}"
        total = await conn.fetchval(count_sql, *params[:-2]) if params[:-2] else await conn.fetchval(count_sql)

    results = []
    for row in rows:
        d = dict(row)
        d["id"] = str(d["id"])
        if isinstance(d.get("documents_cited"), str):
            d["documents_cited"] = json.loads(d["documents_cited"])
        results.append(d)

    return {"audit_log": results, "total": total}


@router.get("/admin/audit/{audit_id}")
async def get_audit_detail(request: Request, audit_id: str):
    _require_admin(request)
    pool = await get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, user_email, channel, action, query,
                   response_summary, full_response, documents_cited,
                   confidence, avg_similarity_score, thread_id,
                   is_flagged, flag_reason, admin_notes,
                   reviewed_by, reviewed_at, response_time_ms, created_at
            FROM audit_log WHERE id = $1
            """,
            audit_id,
        )

    if not row:
        raise HTTPException(status_code=404, detail="Audit entry not found")

    d = dict(row)
    d["id"] = str(d["id"])
    if isinstance(d.get("documents_cited"), str):
        d["documents_cited"] = json.loads(d["documents_cited"])
    return d


@router.put("/admin/audit/{audit_id}/flag")
async def flag_audit_entry(request: Request, audit_id: str, body: FlagRequest):
    user = _require_admin(request)
    pool = await get_pool()

    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE audit_log
            SET is_flagged = $1, flag_reason = $2,
                reviewed_by = $3, reviewed_at = NOW()
            WHERE id = $4
            """,
            body.is_flagged,
            body.flag_reason or ("admin_flagged" if body.is_flagged else None),
            user["email"],
            audit_id,
        )

    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Audit entry not found")
    return {"status": "updated"}


@router.put("/admin/audit/{audit_id}/notes")
async def update_audit_notes(request: Request, audit_id: str, body: NotesRequest):
    user = _require_admin(request)
    pool = await get_pool()

    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE audit_log
            SET admin_notes = $1, reviewed_by = $2, reviewed_at = NOW()
            WHERE id = $3
            """,
            body.admin_notes,
            user["email"],
            audit_id,
        )

    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Audit entry not found")
    return {"status": "updated"}


# --- Admin Answer Overrides (FAQ) ---


@router.get("/admin/answers")
async def list_admin_answers(request: Request):
    _require_admin(request)
    pool = await get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, question_pattern, answer, source_audit_id,
                   created_by, updated_by, is_active, created_at, updated_at
            FROM admin_answers
            ORDER BY created_at DESC
            """
        )

    results = []
    for row in rows:
        d = dict(row)
        d["id"] = str(d["id"])
        if d.get("source_audit_id"):
            d["source_audit_id"] = str(d["source_audit_id"])
        results.append(d)

    return {"answers": results}


@router.post("/admin/answers")
async def create_admin_answer(request: Request, body: AdminAnswerCreate):
    user = _require_admin(request)

    from app.knowledge.embeddings import EmbeddingService

    pool = await get_pool()
    embedding_service = EmbeddingService()

    # Generate embedding for the question pattern
    embedding = await embedding_service.generate_embedding(body.question_pattern)

    async with pool.acquire() as conn:
        from pgvector.asyncpg import register_vector
        await register_vector(conn)

        row = await conn.fetchrow(
            """
            INSERT INTO admin_answers (question_pattern, answer, embedding,
                                        source_audit_id, created_by)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, question_pattern, answer, created_by, created_at
            """,
            body.question_pattern,
            body.answer,
            embedding,
            body.source_audit_id,
            user["email"],
        )

    result = dict(row)
    result["id"] = str(result["id"])
    return result


@router.put("/admin/answers/{answer_id}")
async def update_admin_answer(request: Request, answer_id: str, body: AdminAnswerUpdate):
    user = _require_admin(request)

    from app.knowledge.embeddings import EmbeddingService

    pool = await get_pool()

    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM admin_answers WHERE id = $1", answer_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Admin answer not found")

        if body.answer:
            await conn.execute(
                """
                UPDATE admin_answers SET answer = $1, updated_by = $2, updated_at = NOW()
                WHERE id = $3
                """,
                body.answer,
                user["email"],
                answer_id,
            )

        if body.question_pattern:
            # Re-embed the new question pattern
            embedding_service = EmbeddingService()
            embedding = await embedding_service.generate_embedding(body.question_pattern)

            from pgvector.asyncpg import register_vector
            await register_vector(conn)

            await conn.execute(
                """
                UPDATE admin_answers
                SET question_pattern = $1, embedding = $2,
                    updated_by = $3, updated_at = NOW()
                WHERE id = $4
                """,
                body.question_pattern,
                embedding,
                user["email"],
                answer_id,
            )

    return {"status": "updated"}


@router.delete("/admin/answers/{answer_id}")
async def deactivate_admin_answer(request: Request, answer_id: str):
    user = _require_admin(request)
    pool = await get_pool()

    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE admin_answers SET is_active = FALSE, updated_by = $1, updated_at = NOW()
            WHERE id = $2
            """,
            user["email"],
            answer_id,
        )

    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Admin answer not found")
    return {"status": "deactivated"}


# --- Metrics ---


@router.get("/admin/metrics")
async def get_metrics(request: Request, days: int = 30):
    _require_admin(request)
    pool = await get_pool()

    async with pool.acquire() as conn:
        interval = f"{days} days"

        # Total questions
        total_questions = await conn.fetchval(
            "SELECT COUNT(*) FROM audit_log WHERE action = 'question' AND created_at > NOW() - $1::interval",
            interval,
        )

        # Low confidence count
        low_confidence_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM audit_log
            WHERE action = 'question' AND confidence IN ('none', 'low')
              AND created_at > NOW() - $1::interval
            """,
            interval,
        )

        # Disputed answers
        disputed_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM audit_log
            WHERE flag_reason = 'user_disputed'
              AND created_at > NOW() - $1::interval
            """,
            interval,
        )

        # Avg response time
        avg_response_time = await conn.fetchval(
            """
            SELECT ROUND(AVG(response_time_ms))::integer FROM audit_log
            WHERE response_time_ms IS NOT NULL
              AND created_at > NOW() - $1::interval
            """,
            interval,
        )

        # By channel
        channel_rows = await conn.fetch(
            """
            SELECT channel, COUNT(*) as count FROM audit_log
            WHERE action = 'question' AND created_at > NOW() - $1::interval
            GROUP BY channel ORDER BY count DESC
            """,
            interval,
        )

        # FAQ hit rate
        faq_total = await conn.fetchval(
            """
            SELECT COUNT(*) FROM audit_log
            WHERE action = 'question' AND created_at > NOW() - $1::interval
            """,
            interval,
        )
        faq_hits = await conn.fetchval(
            """
            SELECT COUNT(*) FROM audit_log
            WHERE action = 'question'
              AND documents_cited::text LIKE '%FAQ%'
              AND created_at > NOW() - $1::interval
            """,
            interval,
        )
        faq_hit_rate = round((faq_hits / faq_total * 100), 1) if faq_total > 0 else 0

        # Recent low-confidence queries
        low_conf_rows = await conn.fetch(
            """
            SELECT id, query, confidence, created_at FROM audit_log
            WHERE confidence IN ('none', 'low') AND action = 'question'
              AND created_at > NOW() - $1::interval
            ORDER BY created_at DESC LIMIT 20
            """,
            interval,
        )

    return {
        "total_questions": total_questions,
        "low_confidence_count": low_confidence_count,
        "disputed_count": disputed_count,
        "avg_response_time_ms": avg_response_time,
        "faq_hit_rate": faq_hit_rate,
        "by_channel": [{"channel": r["channel"], "count": r["count"]} for r in channel_rows],
        "low_confidence_queries": [
            {"id": str(r["id"]), "query": r["query"], "confidence": r["confidence"], "created_at": r["created_at"].isoformat() if r["created_at"] else None}
            for r in low_conf_rows
        ],
    }
