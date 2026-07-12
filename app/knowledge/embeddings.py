import asyncio
import logging
import re

import asyncpg
import vertexai
from vertexai.language_models import TextEmbeddingModel
from pgvector.asyncpg import register_vector

from app.config import settings

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = 2000, overlap_sentences: int = 2) -> list[str]:
    """Split text into overlapping chunks at sentence boundaries.

    Args:
        text: Document text to chunk.
        chunk_size: Target chunk size in characters.
        overlap_sentences: Number of sentences to overlap between chunks.
    """
    if not text or not text.strip():
        return []

    # Split by sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if not sentences:
        return [text.strip()] if text.strip() else []

    chunks = []
    current_sentences: list[str] = []
    current_length = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if current_length + len(sentence) > chunk_size and current_sentences:
            chunks.append(" ".join(current_sentences))
            # Keep last N sentences for overlap
            current_sentences = (
                current_sentences[-overlap_sentences:]
                if len(current_sentences) >= overlap_sentences
                else current_sentences[:]
            )
            current_length = sum(len(s) for s in current_sentences) + max(len(current_sentences) - 1, 0)

        current_sentences.append(sentence)
        current_length += len(sentence) + 1

    if current_sentences:
        last_chunk = " ".join(current_sentences)
        if not chunks or last_chunk != chunks[-1]:
            chunks.append(last_chunk)

    return chunks


class EmbeddingService:
    def __init__(self):
        vertexai.init(
            project=settings.gcp_project_id,
            location=settings.vertex_ai_location,
        )
        self.model = TextEmbeddingModel.from_pretrained(settings.embedding_model)

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
        self, pool: asyncpg.Pool, document_id: str, text: str, hoa_id: str
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
                        (document_id, chunk_text, chunk_index, embedding, hoa_id)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    document_id,
                    chunk,
                    idx,
                    embedding,
                    hoa_id,
                )

        logger.info(
            "Embedded document %s: %d chunks stored", document_id, len(chunks)
        )
        return len(chunks)
