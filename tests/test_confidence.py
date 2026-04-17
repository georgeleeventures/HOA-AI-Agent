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
