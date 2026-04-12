import asyncio
import json
import logging
import re

import pdfplumber
import vertexai
from vertexai.generative_models import GenerativeModel, Part

from app.config import settings

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """
Classify this HOA document into one of the following categories and subcategories.
Extract all applicable metadata fields. Return valid JSON only — no markdown, no code fences.

Categories and subcategories:
- Governing: CC&Rs, TIC Agreement, Bylaws, House Rules
- Financial: Budget, Reserve Study, Assessment, Invoice/Receipt, Tax
- Meeting: Minutes, Agenda, Resolution
- Maintenance: Work Order, Inspection, Photo/Evidence, Contractor Bid
- Insurance: Policy, Claim
- Legal: Attorney, Dispute, Lien/Violation
- Ownership: Roster, Deed/Title, Lease
- Vendor: Contract, Warranty
- Correspondence: Newsletter, Notice, Thread

Return format:
{
  "category": "...",
  "subcategory": "...",
  "confidence": 0.0-1.0,
  "title": "descriptive title for this document",
  "metadata": {
    // All applicable fields for this document type
    // e.g. effective_date, parties, amounts, vendor, etc.
  }
}
""".strip()

# Mime types that should be sent to Gemini for OCR
IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/tiff",
}

# Minimum characters to consider a PDF as having extractable text
MIN_TEXT_LENGTH = 50


class DocumentProcessor:
    def __init__(self):
        vertexai.init(
            project=settings.gcp_project_id,
            location=settings.vertex_ai_location,
        )
        self.model = GenerativeModel("gemini-2.0-flash")

    async def extract_text(self, file_path: str, mime_type: str) -> str:
        """Extract text from a file. Uses pdfplumber for text PDFs,
        Gemini multimodal for scanned docs and images."""

        # Images go straight to Gemini OCR
        if mime_type in IMAGE_MIME_TYPES:
            return await self._ocr_with_gemini(file_path, mime_type)

        # PDFs: try pdfplumber first, fall back to Gemini OCR
        if mime_type == "application/pdf":
            text = await asyncio.to_thread(self._extract_pdf_text, file_path)
            if len(text.strip()) >= MIN_TEXT_LENGTH:
                return text
            # Scanned PDF — use Gemini OCR
            logger.info("PDF has minimal text, using Gemini OCR: %s", file_path)
            return await self._ocr_with_gemini(file_path, mime_type)

        # Plain text or other readable formats
        try:
            text = await asyncio.to_thread(self._read_text_file, file_path)
            return text
        except Exception:
            logger.warning("Could not read file as text: %s", file_path)
            return ""

    async def classify_document(
        self, text: str, filename: str = ""
    ) -> dict:
        """Classify a document using Gemini. Returns dict with category,
        subcategory, confidence, title, and metadata."""

        # Truncate very long documents to stay within token limits
        truncated = text[:15000] if len(text) > 15000 else text

        prompt = CLASSIFICATION_PROMPT
        if filename:
            prompt += f"\n\nFilename: {filename}"
        prompt += f"\n\nDocument text:\n{truncated}"

        try:
            response = await asyncio.to_thread(
                self.model.generate_content, prompt
            )
            return self._parse_classification_response(response.text)
        except Exception:
            logger.exception("Classification failed for %s", filename)
            return {
                "category": "Correspondence",
                "subcategory": "Notice",
                "confidence": 0.0,
                "title": filename or "Unknown Document",
                "metadata": {},
            }

    async def process_file(
        self,
        file_path: str,
        mime_type: str,
        source_email_id: str | None = None,
    ) -> dict:
        """Full processing pipeline: extract text, classify, return dict
        ready for database insert."""

        # Extract text
        text = await self.extract_text(file_path, mime_type)

        # Classify
        filename = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path
        classification = await self.classify_document(text, filename)

        confidence = classification.get("confidence", 0.0)

        return {
            "category": classification.get("category", "Correspondence"),
            "subcategory": classification.get("subcategory", "Notice"),
            "title": classification.get("title", filename),
            "content": text,
            "raw_text": text,
            "metadata": json.dumps(classification.get("metadata", {})),
            "source_email_id": source_email_id,
            "source_filename": filename,
            "file_type": mime_type,
            "file_path": file_path,
            "confidence_score": confidence,
            "needs_review": confidence < 0.7,
        }

    async def _ocr_with_gemini(self, file_path: str, mime_type: str) -> str:
        """Use Gemini multimodal to OCR a scanned document or image."""

        def _run():
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            document_part = Part.from_data(data=file_bytes, mime_type=mime_type)
            response = self.model.generate_content(
                [
                    "Extract all text from this document. Return only the "
                    "extracted text, preserving the original structure as much "
                    "as possible. Do not add commentary or formatting.",
                    document_part,
                ]
            )
            return response.text

        try:
            return await asyncio.to_thread(_run)
        except Exception:
            logger.exception("Gemini OCR failed for %s", file_path)
            return ""

    @staticmethod
    def _extract_pdf_text(file_path: str) -> str:
        """Extract text from a PDF using pdfplumber."""
        try:
            with pdfplumber.open(file_path) as pdf:
                pages = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages.append(text)
                return "\n\n".join(pages)
        except Exception:
            logger.exception("pdfplumber failed for %s", file_path)
            return ""

    @staticmethod
    def _read_text_file(file_path: str) -> str:
        """Read a file as plain text."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    @staticmethod
    def _parse_classification_response(response_text: str) -> dict:
        """Parse Gemini's classification response, handling markdown fences."""
        text = response_text.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)

        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse classification JSON: %s", text[:200])
            result = {
                "category": "Correspondence",
                "subcategory": "Notice",
                "confidence": 0.0,
                "title": "Unknown Document",
                "metadata": {},
            }

        # Ensure required fields
        result.setdefault("category", "Correspondence")
        result.setdefault("subcategory", "Notice")
        result.setdefault("confidence", 0.0)
        result.setdefault("title", "Untitled")
        result.setdefault("metadata", {})

        return result
