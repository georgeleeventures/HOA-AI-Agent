import json
import logging

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from app.database import get_pool
from app.web.routes import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    question: str


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

    from app.knowledge.embeddings import EmbeddingService
    from app.knowledge.rag import RAGPipeline

    pool = await get_pool()
    embedding_service = EmbeddingService()
    rag = RAGPipeline(pool, embedding_service)

    result = await rag.query(
        question=body.question,
        user_role=user.get("role", "resident"),
    )

    # Log to audit
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_log (user_email, channel, action, query,
                                       response_summary, documents_cited)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                user["email"],
                "web_chat",
                "question",
                body.question,
                result["answer"][:500],
                json.dumps([
                    {"title": s["document_title"], "category": s["category"]}
                    for s in result.get("sources", [])
                ]),
            )
    except Exception:
        logger.exception("Failed to write audit log")

    return result


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


@router.get("/admin/audit")
async def get_audit_log(
    request: Request,
    limit: int = 50,
    offset: int = 0,
):
    _require_admin(request)
    pool = await get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, user_email, channel, action, query,
                   response_summary, documents_cited, created_at
            FROM audit_log
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
        if isinstance(d.get("documents_cited"), str):
            d["documents_cited"] = json.loads(d["documents_cited"])
        results.append(d)

    return {"audit_log": results}
