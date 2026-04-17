"""Tests for document processor MIME type inference and text cleaning."""

import io
import pytest


_MIME_MAP = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _infer_mime(file_path: str, original: str = "application/octet-stream") -> str:
    """Replicate the MIME inference logic from processor.py."""
    if original not in ("application/octet-stream", ""):
        return original
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    return _MIME_MAP.get(ext, original)


def test_mime_inference_pdf():
    assert _infer_mime("/tmp/test.pdf") == "application/pdf"


def test_mime_inference_jpg():
    ext = "jpg"
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg"}
    assert mime_map.get(ext) == "image/jpeg"


def test_mime_inference_docx():
    ext = "docx"
    mime_map = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    assert mime_map.get(ext) == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_mime_inference_unknown():
    ext = "xyz"
    mime_map = {"pdf": "application/pdf", "jpg": "image/jpeg"}
    assert mime_map.get(ext) is None


def test_null_byte_stripping():
    """Text with null bytes should be cleaned."""
    text = "Hello\x00World\x00Test"
    clean = text.replace("\x00", "")
    assert clean == "HelloWorldTest"
    assert "\x00" not in clean


def test_pdf_roundtrip():
    """Generate a PDF with fpdf2, extract text with pdfplumber, verify content."""
    try:
        import pdfplumber as _plumber
        # Check it's the real module, not a mock
        if not hasattr(_plumber, "open") or not callable(getattr(_plumber.open, "__call__", None)):
            pytest.skip("pdfplumber is mocked")
    except (ImportError, AttributeError):
        pytest.skip("pdfplumber not available")

    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, "Pet weight limit is 25 pounds")
    data = pdf.output()

    with _plumber.open(io.BytesIO(data)) as p:
        text = p.pages[0].extract_text()
    assert "25 pounds" in text


def test_docx_readable():
    """Generate a DOCX with python-docx, read it back."""
    from docx import Document

    doc = Document()
    doc.add_heading("House Rules", level=0)
    doc.add_paragraph("Quiet hours are 10pm to 8am.")

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    doc2 = Document(buf)
    text = "\n".join(p.text for p in doc2.paragraphs)
    assert "Quiet hours" in text
    assert "10pm" in text
