import json
import logging

import asyncpg

logger = logging.getLogger(__name__)


class DocumentStore:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def store_document(self, doc: dict, hoa_id: str) -> str:
        """Insert a document into the database. Returns the document UUID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO documents (
                    hoa_id, category, subcategory, title, content, raw_text,
                    metadata, source_email_id, source_filename, file_type,
                    file_path, confidence_score, needs_review
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING id
                """,
                hoa_id,
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

    async def get_document(self, doc_id: str, hoa_id: str) -> dict | None:
        """Fetch a single document by ID, scoped to HOA."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM documents WHERE id = $1 AND hoa_id = $2",
                doc_id,
                hoa_id,
            )
        if row is None:
            return None
        result = dict(row)
        result["id"] = str(result["id"])
        result["hoa_id"] = str(result["hoa_id"])
        if isinstance(result.get("metadata"), str):
            try:
                result["metadata"] = json.loads(result["metadata"])
            except json.JSONDecodeError:
                result["metadata"] = {}
        return result

    async def list_documents(
        self,
        hoa_id: str,
        category: str | None = None,
        subcategory: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """List documents with optional filters, scoped to HOA."""
        conditions = ["hoa_id = $1"]
        params: list = [hoa_id]
        param_idx = 2

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

    async def get_documents_needing_review(self, hoa_id: str) -> list[dict]:
        """Return all documents flagged for admin review, scoped to HOA."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, category, subcategory, title, source_filename,
                       confidence_score, created_at
                FROM documents
                WHERE hoa_id = $1 AND needs_review = TRUE
                ORDER BY created_at DESC
                """,
                hoa_id,
            )

        results = []
        for row in rows:
            d = dict(row)
            d["id"] = str(d["id"])
            results.append(d)
        return results

    async def update_classification(
        self, doc_id: str, hoa_id: str, category: str, subcategory: str
    ) -> None:
        """Admin reclassification of a document. Clears the review flag."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE documents
                SET category = $1, subcategory = $2, needs_review = FALSE,
                    updated_at = NOW()
                WHERE id = $3 AND hoa_id = $4
                """,
                category,
                subcategory,
                doc_id,
                hoa_id,
            )
        logger.info(
            "Reclassified document %s to %s > %s", doc_id, category, subcategory
        )

    async def store_new_version(
        self, doc: dict, hoa_id: str, supersedes_id: str
    ) -> str:
        """Store a new version of a document, marking the old one as not current."""
        async with self.pool.acquire() as conn:
            old = await conn.fetchrow(
                "SELECT version, lineage_group FROM documents WHERE id = $1 AND hoa_id = $2",
                supersedes_id,
                hoa_id,
            )
            if not old:
                return await self.store_document(doc, hoa_id)

            new_version = (old["version"] or 1) + 1
            lineage_group = old["lineage_group"] or supersedes_id

            await conn.execute(
                "UPDATE documents SET is_current = FALSE, updated_at = NOW() WHERE id = $1 AND hoa_id = $2",
                supersedes_id,
                hoa_id,
            )

            row = await conn.fetchrow(
                """
                INSERT INTO documents (
                    hoa_id, category, subcategory, title, content, raw_text,
                    metadata, source_email_id, source_filename, file_type,
                    file_path, confidence_score, needs_review,
                    version, supersedes_id, lineage_group, is_current,
                    effective_date
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,TRUE,$17)
                RETURNING id
                """,
                hoa_id,
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
                new_version,
                supersedes_id,
                str(lineage_group),
                doc.get("effective_date"),
            )
            doc_id = str(row["id"])
            logger.info(
                "Stored document v%d %s (supersedes %s)",
                new_version,
                doc_id,
                supersedes_id,
            )
            return doc_id
