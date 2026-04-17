"""Generate synthetic attachments (PDF, DOCX, XLSX, images) and build MIME messages."""

from __future__ import annotations

import base64
import io
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .scenarios import (
    DOCUMENT_CONTENT,
    TEST_RESIDENTS,
    AttachmentSpec,
    EmailScenario,
)


# ---------------------------------------------------------------------------
# PDF generation (fpdf2)
# ---------------------------------------------------------------------------

def _sanitize_latin1(text: str) -> str:
    """Replace non-latin-1 characters for fpdf2 core fonts."""
    replacements = {
        "\u2014": "--",   # em dash
        "\u2013": "-",    # en dash
        "\u2018": "'",    # left single quote
        "\u2019": "'",    # right single quote
        "\u201c": '"',    # left double quote
        "\u201d": '"',    # right double quote
        "\u2026": "...",  # ellipsis
        "\u2022": "*",    # bullet
        "\u00a0": " ",    # non-breaking space
        "\u2264": "<=",   # less-than-or-equal
        "\u2265": ">=",   # greater-than-or-equal
        "\u00d7": "x",    # multiplication sign
        "\U0001f3e0": "",  # house emoji
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    # Strip any remaining non-latin-1 characters
    return text.encode("latin-1", errors="replace").decode("latin-1")


def generate_pdf(title: str, body: str) -> bytes:
    """Generate a simple PDF with title and body text."""
    from fpdf import FPDF

    title = _sanitize_latin1(title)
    body = _sanitize_latin1(body)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(w=0, h=8, text=title, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Body
    pdf.set_font("Helvetica", "", 10)
    for line in body.split("\n"):
        stripped = line.strip()
        if not stripped:
            pdf.ln(3)
        elif stripped.isupper() and len(stripped) > 3:
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(w=0, h=6, text=stripped, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
        else:
            pdf.multi_cell(w=0, h=5, text=stripped, new_x="LMARGIN", new_y="NEXT")

    return pdf.output()


# ---------------------------------------------------------------------------
# DOCX generation (python-docx)
# ---------------------------------------------------------------------------

def generate_docx(title: str, sections: list[tuple[str, str]]) -> bytes:
    """Generate a DOCX with title and named sections."""
    from docx import Document

    doc = Document()
    doc.add_heading(title, level=0)

    for heading, content in sections:
        doc.add_heading(heading, level=1)
        doc.add_paragraph(content)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# XLSX generation (openpyxl)
# ---------------------------------------------------------------------------

def generate_xlsx(title: str, rows: list[list[str]], summary: str = "") -> bytes:
    """Generate an XLSX with a data table and optional summary text."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Reserve Study"

    # Title row
    ws.append([title])
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(rows[0]) if rows else 5)
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([])

    # Data rows
    for i, row in enumerate(rows):
        ws.append(row)
        if i == 0:
            for cell in ws[ws.max_row]:
                cell.font = Font(bold=True)

    # Summary
    if summary:
        ws.append([])
        ws.append([])
        for line in summary.strip().split("\n"):
            ws.append([line.strip()])

    # Auto-width columns (skip merged cells)
    for col in ws.columns:
        widths = []
        for cell in col:
            try:
                widths.append(len(str(cell.value or "")))
            except AttributeError:
                pass
        if widths:
            letter = col[0].column_letter if hasattr(col[0], "column_letter") else None
            if letter:
                ws.column_dimensions[letter].width = min(max(widths) + 2, 50)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Image generation (Pillow)
# ---------------------------------------------------------------------------

def generate_jpg(description: str) -> bytes:
    """Generate a JPEG image with text overlay (simulates a maintenance photo)."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (800, 600), color=(180, 160, 140))
    draw = ImageDraw.Draw(img)

    # Try to use a system font, fall back to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except (OSError, IOError):
        font = ImageFont.load_default()
        font_small = font

    # Add some visual noise to look more photo-like
    import random
    random.seed(42)
    for _ in range(200):
        x, y = random.randint(0, 799), random.randint(0, 599)
        shade = random.randint(150, 200)
        draw.point((x, y), fill=(shade, shade - 20, shade - 30))

    # Draw text
    y_offset = 40
    for line in description.split("\n"):
        line = line.strip()
        if not line:
            y_offset += 10
            continue
        if y_offset < 100:
            draw.text((40, y_offset), line, fill=(30, 30, 30), font=font)
        else:
            draw.text((40, y_offset), line, fill=(50, 50, 50), font=font_small)
        y_offset += 30

    # Add timestamp overlay
    draw.text((500, 550), "2026-01-20 09:45:12", fill=(200, 200, 200), font=font_small)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def generate_png(description: str) -> bytes:
    """Generate a PNG image (simulates a scanned document)."""
    from PIL import Image, ImageDraw, ImageFont

    # White background like a scanned page
    img = Image.new("RGB", (850, 1100), color=(252, 252, 248))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Courier.dfont", 18)
    except (OSError, IOError):
        font = ImageFont.load_default()

    # Simulate slight scan artifacts
    import random
    random.seed(99)
    for _ in range(50):
        x, y = random.randint(0, 849), random.randint(0, 1099)
        draw.point((x, y), fill=(220, 220, 220))

    y_offset = 60
    for line in description.split("\n"):
        line = line.strip()
        if not line:
            y_offset += 15
            continue
        draw.text((60, y_offset), line, fill=(20, 20, 20), font=font)
        y_offset += 28

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Empty / corrupted PDF
# ---------------------------------------------------------------------------

def generate_empty_pdf() -> bytes:
    """Generate a minimal valid PDF with no readable text (simulates corruption)."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    # Just a blank page
    return pdf.output()


# ---------------------------------------------------------------------------
# Attachment dispatcher
# ---------------------------------------------------------------------------

def generate_attachment(spec: AttachmentSpec) -> tuple[str, str, bytes]:
    """Generate an attachment from a spec. Returns (filename, mime_type, data)."""
    content = DOCUMENT_CONTENT.get(spec.generator_key, {})

    if spec.file_type == "pdf":
        title = content.get("title", "Document")
        body = content.get("body", "No content available.")
        data = generate_pdf(title, body)

    elif spec.file_type == "docx":
        title = content.get("title", "Document")
        sections = content.get("sections", [("Content", "No content available.")])
        data = generate_docx(title, sections)

    elif spec.file_type == "xlsx":
        title = content.get("title", "Spreadsheet")
        rows = content.get("rows", [["No data"]])
        summary = content.get("summary", "")
        data = generate_xlsx(title, rows, summary)

    elif spec.file_type == "jpg":
        desc = content.get("description", "Test Image")
        data = generate_jpg(desc)

    elif spec.file_type == "png":
        desc = content.get("description", "Scanned Document")
        data = generate_png(desc)

    elif spec.file_type == "empty_pdf":
        data = generate_empty_pdf()

    else:
        data = b"Unsupported file type"

    return spec.filename, spec.mime_type, data


# ---------------------------------------------------------------------------
# MIME message builder
# ---------------------------------------------------------------------------

def build_mime_message(
    scenario: EmailScenario,
    hoa_email: str,
    message_id_map: dict[str, str] | None = None,
) -> MIMEMultipart:
    """Build a complete MIME message from an EmailScenario.

    Args:
        scenario: The email scenario to build.
        hoa_email: The HOA inbox email address (goes in To: or CC:).
        message_id_map: Mapping of scenario.name -> Message-ID for threading.

    Returns:
        A MIMEMultipart message ready to be sent or inserted.
    """
    sender = TEST_RESIDENTS[scenario.sender_key]

    has_attachments = bool(scenario.attachments)

    if has_attachments:
        msg = MIMEMultipart("mixed")
    else:
        msg = MIMEMultipart("alternative") if scenario.html_only else MIMEMultipart()

    # Headers
    msg["From"] = f"{sender.name} <{sender.email}>"
    msg["Subject"] = scenario.subject

    # Determine To/CC based on intent
    if scenario.intent == "thread_cc":
        # HOA address is in CC, primary recipients are other residents
        cc_residents = [TEST_RESIDENTS[k] for k in scenario.cc_list if k in TEST_RESIDENTS]
        to_addrs = [r.email for r in cc_residents if r.email != sender.email]
        msg["To"] = ", ".join(to_addrs) if to_addrs else hoa_email
        msg["Cc"] = hoa_email
    else:
        msg["To"] = hoa_email
        if scenario.cc_list:
            cc_emails = [TEST_RESIDENTS[k].email for k in scenario.cc_list if k in TEST_RESIDENTS]
            if cc_emails:
                msg["Cc"] = ", ".join(cc_emails)

    # Threading headers
    if scenario.is_reply_to and message_id_map:
        parent_id = message_id_map.get(scenario.is_reply_to)
        if parent_id:
            msg["In-Reply-To"] = parent_id
            msg["References"] = parent_id

    # Body
    if has_attachments:
        # Wrap body in a multipart/alternative inside the mixed container
        body_part = MIMEMultipart("alternative")
        if scenario.html_only:
            body_part.attach(MIMEText(scenario.body, "html"))
        else:
            body_part.attach(MIMEText(scenario.body or "(no message body)", "plain"))
        msg.attach(body_part)

        # Attachments
        for spec in scenario.attachments:
            filename, mime_type, data = generate_attachment(spec)
            if mime_type.startswith("image/"):
                subtype = mime_type.split("/")[1]
                att = MIMEImage(data, _subtype=subtype)
            else:
                att = MIMEApplication(data)
                att["Content-Type"] = mime_type
            att.add_header("Content-Disposition", "attachment", filename=filename)
            msg.attach(att)
    else:
        if scenario.html_only:
            msg.attach(MIMEText(scenario.body, "html"))
        elif scenario.body:
            msg.attach(MIMEText(scenario.body, "plain"))
        else:
            msg.attach(MIMEText("", "plain"))

    return msg


def mime_to_raw_base64(msg: MIMEMultipart) -> str:
    """Convert a MIME message to the base64url-encoded string Gmail API expects."""
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
