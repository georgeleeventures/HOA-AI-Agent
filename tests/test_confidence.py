"""Tests for RAG confidence computation and clarification logic."""

from unittest.mock import patch

from app.knowledge.rag import RAGPipeline


class TestComputeConfidence:
    def test_none_with_empty_chunks(self):
        conf, avg = RAGPipeline._compute_confidence([])
        assert conf == "none"
        assert avg == 0.0

    @patch("app.knowledge.rag.settings")
    def test_high_confidence(self, mock_settings):
        mock_settings.confidence_high_threshold = 0.35
        mock_settings.confidence_medium_threshold = 0.55
        chunks = [{"distance": 0.1}, {"distance": 0.2}]
        conf, _ = RAGPipeline._compute_confidence(chunks)
        assert conf == "high"

    @patch("app.knowledge.rag.settings")
    def test_medium_confidence(self, mock_settings):
        mock_settings.confidence_high_threshold = 0.35
        mock_settings.confidence_medium_threshold = 0.55
        chunks = [{"distance": 0.4}, {"distance": 0.6}]
        conf, _ = RAGPipeline._compute_confidence(chunks)
        assert conf == "medium"

    @patch("app.knowledge.rag.settings")
    def test_low_confidence(self, mock_settings):
        mock_settings.confidence_high_threshold = 0.35
        mock_settings.confidence_medium_threshold = 0.55
        chunks = [{"distance": 0.7}, {"distance": 0.9}]
        conf, _ = RAGPipeline._compute_confidence(chunks)
        assert conf == "low"


class TestNeedsClarification:
    def test_none_confidence_short_query(self):
        assert RAGPipeline._needs_clarification("parking", "none") is True

    def test_low_does_not_clarify(self):
        assert RAGPipeline._needs_clarification("satellite dish?", "low") is False

    def test_high_does_not_clarify(self):
        assert RAGPipeline._needs_clarification("parking", "high") is False


class TestContextBudget:
    @patch("app.knowledge.rag.settings")
    def test_context_is_capped(self, mock_settings):
        mock_settings.rag_max_context_chars = 120
        chunks = [
            {
                "category": "Governing",
                "subcategory": "CC&Rs",
                "title": "Rules",
                "chunk_text": "x" * 500,
            },
            {
                "category": "Meeting",
                "subcategory": "Minutes",
                "title": "April",
                "chunk_text": "y" * 500,
            },
        ]

        context = RAGPipeline.__new__(RAGPipeline)._build_context(chunks)

        assert len(context) <= 120
        assert "Rules" in context
        assert "y" not in context

    @patch("app.knowledge.rag.settings")
    def test_context_budget_includes_separators(self, mock_settings):
        mock_settings.rag_max_context_chars = 180
        chunks = [
            {
                "category": "Governing",
                "subcategory": "Rules",
                "title": f"Document {index}",
                "chunk_text": "policy " * 10,
            }
            for index in range(3)
        ]

        context = RAGPipeline.__new__(RAGPipeline)._build_context(chunks)

        assert len(context) <= 180


class TestRetrievalLimit:
    @patch("app.knowledge.rag.settings")
    def test_top_k_is_bounded(self, mock_settings):
        mock_settings.rag_top_k = 4

        assert RAGPipeline._bounded_top_k(None) == 4
        assert RAGPipeline._bounded_top_k(100) == 4
        assert RAGPipeline._bounded_top_k(-1) == 1
