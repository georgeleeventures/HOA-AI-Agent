"""Tests for synthetic test data generation."""

import pytest

from scripts.testdata.scenarios import ALL_SCENARIOS, SCENARIO_BY_NAME
from scripts.testdata.generator import generate_attachment, build_mime_message


def test_all_scenarios_count():
    assert len(ALL_SCENARIOS) == 45


def test_scenario_intent_counts():
    intents = {}
    for s in ALL_SCENARIOS:
        intents[s.intent] = intents.get(s.intent, 0) + 1
    assert intents["question"] == 12
    assert intents["document_forward"] == 16
    assert intents["thread_cc"] == 5
    assert intents["correction"] == 4
    assert intents["edge_case"] == 8


def test_all_scenario_names_unique():
    names = [s.name for s in ALL_SCENARIOS]
    assert len(names) == len(set(names))


def test_all_attachments_generate():
    """All 23 attachments should produce non-empty bytes."""
    count = 0
    for s in ALL_SCENARIOS:
        for att in s.attachments:
            fn, mt, data = generate_attachment(att)
            assert len(data) > 0, f"Empty attachment: {fn}"
            assert fn == att.filename
            count += 1
    assert count == 23


def test_pdf_text_extractable():
    """Synthetic PDFs should have extractable text via pdfplumber."""
    try:
        import pdfplumber as _plumber
        if not hasattr(_plumber, "open") or not callable(getattr(_plumber.open, "__call__", None)):
            pytest.skip("pdfplumber is mocked")
    except (ImportError, AttributeError):
        pytest.skip("pdfplumber not available")

    import io

    for s in ALL_SCENARIOS:
        for att in s.attachments:
            if att.file_type == "pdf":
                fn, mt, data = generate_attachment(att)
                with _plumber.open(io.BytesIO(data)) as pdf:
                    text = ""
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            text += t
                    if att.file_type != "empty_pdf":
                        assert len(text) > 10, f"No text extracted from {fn}"


def test_mime_messages_build():
    """MIME messages should build for all 45 scenarios."""
    for s in ALL_SCENARIOS:
        msg = build_mime_message(s, "test@housekeep.click")
        raw = msg.as_bytes()
        assert len(raw) > 0
        assert s.subject in msg["Subject"]


def test_threading_headers():
    """Reply scenarios should get In-Reply-To headers when parent ID is provided."""
    reply_scenarios = [s for s in ALL_SCENARIOS if s.is_reply_to]
    assert len(reply_scenarios) > 0

    for s in reply_scenarios:
        parent_id = f"<{s.is_reply_to}@test.gmail.com>"
        msg = build_mime_message(s, "test@housekeep.click", {s.is_reply_to: parent_id})
        assert msg["In-Reply-To"] == parent_id
        assert msg["References"] == parent_id


def test_doc_forward_scenarios_have_attachments():
    """All document_forward scenarios should have at least one attachment."""
    for s in ALL_SCENARIOS:
        if s.intent == "document_forward":
            assert len(s.attachments) > 0, f"Doc forward {s.name} has no attachments"


def test_doc_forward_scenarios_have_target_category():
    """All document_forward scenarios should specify expected category."""
    for s in ALL_SCENARIOS:
        if s.intent == "document_forward":
            assert s.target_category is not None, f"{s.name} missing target_category"
            assert s.target_subcategory is not None, f"{s.name} missing target_subcategory"
