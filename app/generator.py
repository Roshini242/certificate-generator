import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)  # about 842 x 595 points

GOLD = colors.HexColor("#B8860B")
DARK = colors.HexColor("#1F2937")
GREY = colors.HexColor("#6B7280")


def _fit_font_size(text: str, font_name: str, start_size: int, max_width: float) -> int:
    """Shrink the font until the text fits inside max_width (so long names don't overflow)."""
    size = start_size
    while size > 10 and stringWidth(text, font_name, size) > max_width:
        size -= 1
    return size


def generate_certificate(
    recipient_name: str,
    course_name: str,
    issue_date: date,
    output_path: str,
) -> str:
    """
    Draws one certificate PDF using the single predefined template.
    Returns the path of the file that was created.
    """
    # Make sure the output folder exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    c = canvas.Canvas(output_path, pagesize=landscape(A4))
    center_x = PAGE_WIDTH / 2
    max_text_width = PAGE_WIDTH - 160  # leave margins on both sides

    # --- Double border ---
    c.setStrokeColor(GOLD)
    c.setLineWidth(6)
    c.rect(25, 25, PAGE_WIDTH - 50, PAGE_HEIGHT - 50)
    c.setLineWidth(1.5)
    c.rect(40, 40, PAGE_WIDTH - 80, PAGE_HEIGHT - 80)

    # --- Title ---
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 44)
    c.drawCentredString(center_x, PAGE_HEIGHT - 130, "CERTIFICATE")

    c.setFillColor(DARK)
    c.setFont("Helvetica", 20)
    c.drawCentredString(center_x, PAGE_HEIGHT - 165, "OF COMPLETION")

    # --- "This is to certify that" ---
    c.setFillColor(GREY)
    c.setFont("Helvetica-Oblique", 16)
    c.drawCentredString(center_x, PAGE_HEIGHT - 225, "This is to certify that")

    # --- Recipient name (auto-sized) ---
    name_size = _fit_font_size(recipient_name, "Helvetica-Bold", 38, max_text_width)
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", name_size)
    c.drawCentredString(center_x, PAGE_HEIGHT - 280, recipient_name)

    # Line under the name
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.line(center_x - 200, PAGE_HEIGHT - 292, center_x + 200, PAGE_HEIGHT - 292)

    # --- Course text ---
    c.setFillColor(GREY)
    c.setFont("Helvetica-Oblique", 16)
    c.drawCentredString(center_x, PAGE_HEIGHT - 330, "has successfully completed")

    course_size = _fit_font_size(course_name, "Helvetica-Bold", 26, max_text_width)
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", course_size)
    c.drawCentredString(center_x, PAGE_HEIGHT - 370, course_name)

    # --- Date ---
    c.setFillColor(GREY)
    c.setFont("Helvetica", 14)
    c.drawCentredString(
        center_x, 90, f"Issued on {issue_date.strftime('%d %B %Y')}"
    )

    c.showPage()
    c.save()
    return output_path