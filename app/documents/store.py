import json
import logging

import asyncpg

logger = logging.getLogger(__name__)


class DocumentStore:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def store_document(self, doc: dict) -> str:
        """Insert a document into the database. Returns the document UUID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO documents (
                    category, subcategory, title, content, raw_text,
                    metadata, source_email_id, source_filename, file_type,
                    file_path, confidence_score, needs_review
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING id
                """,
                doc.get("category"),
                doc.get("subcategory"),
                doc.get("title"),
                doc.get("content"),
                doc.get("raw_text"),
                doc.get("metadata", "{}"),
                doc.get("source_email_id"),
                doc.get("source_filename"),
                doc.get("file_type"),
                doc.get("file_path"),
                doc.get("confidence_score"),
                doc.get("needs_review", False),
            )
            doc_id = str(row["id"])
            logger.info(
                "Stored document %s: %s > %s (%s)",
                doc_id,
                doc.get("category"),
                doc.get("subcategory"),
                doc.get("title"),
            )
            return doc_id

    async def get_document(self, doc_id: str) -> dict | None:
        """Fetch a single document by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM documents WHERE id = $1", doc_id
            )
        if row is None:
            return None
        result = dict(row)
        result["id"] = str(result["id"])
        if isinstance(result.get("metadata"), str):
            try:
                result["metadata"] = json.loads(result["metadata"])
            except json.JSONDecodeError:
                result["metadata"] = {}
        return result

    async def list_documents(
        self,
        category: str | None = None,
        subcategory: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """List documents with optional filters."""
        conditions = []
        params: list = []
        param_idx = 1

        if category:
            conditions.append(f"category = ${param_idx}")
            params.append(category)
            param_idx += 1

        if subcategory:
            conditions.append(f"subcategory = ${param_idx}")
            params.append(subcategory)
            param_idx += 1

        if search:
            conditions.append(
                f"to_tsvector('english', content) @@ plainto_tsquery('english', ${param_idx})"
            )
            params.append(search)
            param_idx += 1

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        params.append(limit)
        params.append(offset)

        query = f"""
            SELECT id, category, subcategory, title, source_filename,
                   file_type, confidence_score, needs_review, created_at
            FROM documents
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        results = []
        for row in rows:
            d = dict(row)
            d["id"] = str(d["id"])
            results.append(d)
        return results

    async def get_documents_needing_review(self) -> list[dict]:
        """Return all documents flagged for admin review."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, category, subcategory, title, source_filename,
                       confidence_score, created_at
                FROM documents
                WHERE needs_review = TRUE
                ORDER BY created_at DESC
                """
            )

        results = []
        for row in rows:
            d = dict(row)
            d["id"] = str(d["id"])
            results.append(d)
        return results

    async def update_classification(
        self, doc_id: str, category: str, subcategory: str
    ) -> None:
        """Admin reclassification of a document. Clears the review flag."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE documents
                SET category = $1, subcategory = $2, needs_review = FALSE,
                    updated_at = NOW()
                WHERE id = $3
                """,
                category,
                subcategory,
                doc_id,
            )
        logger.info(
            "Reclassified document %s to %s > %s", doc_id, category, subcategory
        )
