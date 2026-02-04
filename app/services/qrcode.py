import qrcode
from io import BytesIO
import base64
from app.config import get_settings


def generate_qr_code(token: str) -> bytes:
    """
    Generate a QR code image for ticket validation.
    Returns the image as PNG bytes.
    """
    settings = get_settings()
    validation_url = f"{settings.base_url}/tickets/validate/{token}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(validation_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer.getvalue()


def generate_qr_code_base64(token: str) -> str:
    """
    Generate a QR code and return it as a base64 encoded string.
    Useful for embedding in HTML emails.
    """
    qr_bytes = generate_qr_code(token)
    return base64.b64encode(qr_bytes).decode("utf-8")
