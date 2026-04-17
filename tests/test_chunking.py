"""Tests for sentence-aware text chunking."""

from app.knowledge.embeddings import chunk_text


def test_chunk_empty_text():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_single_sentence():
    text = "The pet weight limit is 25 pounds."
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_short_document():
    text = "Rule one. Rule two. Rule three."
    chunks = chunk_text(text, chunk_size=2000)
    assert len(chunks) == 1


def test_chunk_splits_at_sentence_boundaries():
    sentences = [f"Sentence number {i} with enough words." for i in range(20)]
    text = " ".join(sentences)
    chunks = chunk_text(text, chunk_size=200, overlap_sentences=1)
    assert len(chunks) > 1


def test_chunk_overlap():
    text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
    chunks = chunk_text(text, chunk_size=60, overlap_sentences=1)
    assert len(chunks) >= 2
    for i in range(len(chunks) - 1):
        current_sentences = chunks[i].split(". ")
        last_sent = current_sentences[-1].rstrip(".")
        assert last_sent in chunks[i + 1]


def test_chunk_preserves_all_content():
    sentences = ["Sentence A.", "Sentence B.", "Sentence C.", "Sentence D.", "Sentence E."]
    text = " ".join(sentences)
    chunks = chunk_text(text, chunk_size=50, overlap_sentences=1)
    all_text = " ".join(chunks)
    for s in sentences:
        assert s.rstrip(".") in all_text


def test_chunk_large_document():
    sentences = [f"Section {i}: This is a detailed rule about topic {i}." for i in range(100)]
    text = " ".join(sentences)
    chunks = chunk_text(text, chunk_size=500, overlap_sentences=2)
    assert len(chunks) > 5
