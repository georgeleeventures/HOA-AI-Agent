import asyncio
import logging

import asyncpg
import vertexai
from vertexai.language_models import TextEmbeddingModel
from pgvector.asyncpg import register_vector

from app.config import settings

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap
        # Avoid tiny trailing chunks
        if start >= len(words):
            break

    return chunks


class EmbeddingService:
    def __init__(self):
        vertexai.init(
            project=settings.gcp_project_id,
            location=settings.vertex_ai_location,
        )
        self.model = TextEmbeddingModel.from_pretrained("text-embedding-004")

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate a 768-dimensional embedding for a single text."""
        embeddings = await asyncio.to_thread(
            self.model.get_embeddings, [text]
        )
        return embeddings[0].values

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Batch-embed multiple texts. Processes in batches of 250
        (Vertex AI limit)."""
        all_embeddings = []
        batch_size = 250

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings = await asyncio.to_thread(
                self.model.get_embeddings, batch
            )
            all_embeddings.extend([e.values for e in embeddings])

        return all_embeddings

    async def embed_document(
        self, pool: asyncpg.Pool, document_id: str, text: str
    ) -> int:
        """Chunk text, embed each chunk, and store in document_chunks.
        Returns the number of chunks created."""
        chunks = chunk_text(text)
        if not chunks:
            logger.warning("No chunks generated for document %s", document_id)
            return 0

        # Generate embeddings for all chunks
        embeddings = await self.generate_embeddings(chunks)

        # Store in database
        async with pool.acquire() as conn:
            await register_vector(conn)

            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                await conn.execute(
                    """
                    INSERT INTO document_chunks
                        (document_id, chunk_text, chunk_index, embedding)
                    VALUES ($1, $2, $3, $4)
                    """,
                    document_id,
                    chunk,
                    idx,
                    embedding,
                )

        logger.info(
            "Embedded document %s: %d chunks stored", document_id, len(chunks)
        )
        return len(chunks)
