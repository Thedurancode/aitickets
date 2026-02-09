"""PDF ticket generation service using fpdf2."""

import tempfile
from io import BytesIO
from fpdf import FPDF
from app.config import get_settings
from app.services.qrcode import generate_qr_code


def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def generate_ticket_pdf(
    event_name: str,
    event_date: str,
    event_time: str,
    venue_name: str,
    venue_address: str,
    attendee_name: str,
    tier_name: str,
    ticket_id: int,
    qr_token: str,
    doors_open_time: str = None,
) -> bytes:
    """
    Generate a branded PDF ticket.
    Returns PDF as bytes.
    """
    settings = get_settings()
    org_name = settings.org_name
    org_color = settings.org_color
    r, g, b = _hex_to_rgb(org_color)

    # Generate QR code image
    qr_bytes = generate_qr_code(qr_token)

    # Write QR to a temp file for fpdf2
    qr_tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    qr_tmp.write(qr_bytes)
    qr_tmp.flush()

    try:
        pdf = FPDF(orientation="P", unit="mm", format="A5")
        pdf.add_page()
        pdf.set_auto_page_break(auto=False)

        # Header band with org color
        pdf.set_fill_color(r, g, b)
        pdf.rect(0, 0, 148, 28, "F")

        # Org name in header
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(10, 8)
        pdf.cell(128, 10, org_name, align="C")

        # "EVENT TICKET" label
        pdf.set_font("Helvetica", "", 8)
        pdf.set_xy(10, 18)
        pdf.cell(128, 5, "EVENT TICKET", align="C")

        # Event name
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_xy(10, 36)
        pdf.multi_cell(128, 8, event_name, align="C")
        y = pdf.get_y() + 4

        # Event details
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(80, 80, 80)

        pdf.set_xy(10, y)
        pdf.cell(128, 6, f"Date: {event_date}  |  Time: {event_time}", align="C")
        y += 7

        if doors_open_time:
            pdf.set_xy(10, y)
            pdf.cell(128, 6, f"Doors Open: {doors_open_time}", align="C")
            y += 7

        pdf.set_xy(10, y)
        pdf.cell(128, 6, venue_name, align="C")
        y += 6
        pdf.set_font("Helvetica", "", 8)
        pdf.set_xy(10, y)
        pdf.cell(128, 5, venue_address, align="C")
        y += 10

        # Divider line
        pdf.set_draw_color(r, g, b)
        pdf.set_line_width(0.5)
        pdf.line(20, y, 128, y)
        y += 6

        # Attendee + tier info
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_xy(10, y)
        pdf.cell(60, 6, "Attendee:")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(68, 6, attendee_name)
        y += 7

        pdf.set_font("Helvetica", "B", 11)
        pdf.set_xy(10, y)
        pdf.cell(60, 6, "Ticket Type:")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(68, 6, tier_name)
        y += 7

        pdf.set_font("Helvetica", "B", 11)
        pdf.set_xy(10, y)
        pdf.cell(60, 6, "Ticket ID:")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(68, 6, f"#{ticket_id}")
        y += 12

        # QR Code centered
        qr_size = 45
        qr_x = (148 - qr_size) / 2
        pdf.image(qr_tmp.name, x=qr_x, y=y, w=qr_size, h=qr_size)
        y += qr_size + 4

        # Scan instruction
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(120, 120, 120)
        pdf.set_xy(10, y)
        pdf.cell(128, 5, "Scan QR code at the door for entry", align="C")

        # Output
        return pdf.output()

    finally:
        import os
        os.unlink(qr_tmp.name)
