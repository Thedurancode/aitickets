"""Apple Wallet .pkpass generation service."""

import json
import hashlib
import zipfile
import logging
from io import BytesIO
from datetime import datetime

from app.config import get_settings
from app.services.qrcode import generate_qr_code

logger = logging.getLogger(__name__)


def is_wallet_configured() -> bool:
    """Check if Apple Wallet signing certs are configured."""
    settings = get_settings()
    return bool(
        settings.apple_wallet_team_id
        and settings.apple_wallet_pass_type_id
        and settings.apple_wallet_cert_path
        and settings.apple_wallet_key_path
        and settings.apple_wallet_wwdr_cert_path
    )


def _create_icon(color_hex: str, size: int = 87) -> bytes:
    """Generate a simple colored square icon using Pillow."""
    try:
        from PIL import Image, ImageDraw
        hex_color = color_hex.lstrip("#")
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        img = Image.new("RGB", (size, size), (r, g, b))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
    except ImportError:
        # Return a minimal 1x1 PNG if Pillow not available
        import struct
        return b""


def _sign_manifest(manifest_json: bytes) -> bytes:
    """
    Sign the manifest using Apple certificates.
    Returns DER-encoded PKCS#7 signature.
    """
    settings = get_settings()

    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.serialization import pkcs7
        from cryptography.x509 import load_pem_x509_certificate

        with open(settings.apple_wallet_cert_path, "rb") as f:
            cert = load_pem_x509_certificate(f.read())

        with open(settings.apple_wallet_key_path, "rb") as f:
            key = serialization.load_pem_private_key(f.read(), password=None)

        with open(settings.apple_wallet_wwdr_cert_path, "rb") as f:
            wwdr_cert = load_pem_x509_certificate(f.read())

        signature = (
            pkcs7.PKCS7SignatureBuilder()
            .set_data(manifest_json)
            .add_signer(cert, key, hashes.SHA256())
            .add_certificate(wwdr_cert)
            .sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.DetachedSignature])
        )
        return signature

    except Exception as e:
        logger.error(f"Failed to sign wallet pass: {e}")
        raise


def generate_wallet_pass(
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
    Generate an Apple Wallet .pkpass file.
    Returns the .pkpass as bytes (ZIP archive).

    If Apple certs are not configured, returns an unsigned pass
    (useful for development but won't load on real devices).
    """
    settings = get_settings()
    base_url = settings.base_url
    org_name = settings.org_name
    org_color = settings.org_color
    hex_color = org_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)

    # Parse event datetime for relevantDate
    try:
        event_dt = datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M")
        relevant_date = event_dt.strftime("%Y-%m-%dT%H:%M:00-05:00")
    except ValueError:
        relevant_date = f"{event_date}T{event_time}:00-05:00"

    # Build pass.json
    pass_json = {
        "formatVersion": 1,
        "passTypeIdentifier": settings.apple_wallet_pass_type_id,
        "serialNumber": f"ticket-{ticket_id}",
        "teamIdentifier": settings.apple_wallet_team_id or "XXXXXXXXXX",
        "organizationName": org_name,
        "description": f"Ticket for {event_name}",
        "foregroundColor": "rgb(255, 255, 255)",
        "backgroundColor": f"rgb({r}, {g}, {b})",
        "labelColor": "rgb(255, 255, 255)",
        "relevantDate": relevant_date,
        "barcode": {
            "message": f"{base_url}/tickets/validate/{qr_token}",
            "format": "PKBarcodeFormatQR",
            "messageEncoding": "iso-8859-1",
        },
        "barcodes": [
            {
                "message": f"{base_url}/tickets/validate/{qr_token}",
                "format": "PKBarcodeFormatQR",
                "messageEncoding": "iso-8859-1",
            }
        ],
        "eventTicket": {
            "primaryFields": [
                {
                    "key": "event",
                    "label": "EVENT",
                    "value": event_name,
                }
            ],
            "secondaryFields": [
                {
                    "key": "date",
                    "label": "DATE",
                    "value": event_date,
                },
                {
                    "key": "time",
                    "label": "TIME",
                    "value": event_time,
                },
            ],
            "auxiliaryFields": [
                {
                    "key": "venue",
                    "label": "VENUE",
                    "value": venue_name,
                },
                {
                    "key": "tier",
                    "label": "TICKET TYPE",
                    "value": tier_name,
                },
            ],
            "backFields": [
                {
                    "key": "attendee",
                    "label": "Attendee",
                    "value": attendee_name,
                },
                {
                    "key": "ticketId",
                    "label": "Ticket ID",
                    "value": f"#{ticket_id}",
                },
                {
                    "key": "address",
                    "label": "Venue Address",
                    "value": venue_address,
                },
            ],
        },
    }

    if doors_open_time:
        pass_json["eventTicket"]["auxiliaryFields"].append({
            "key": "doors",
            "label": "DOORS OPEN",
            "value": doors_open_time,
        })

    # Create file contents
    pass_json_bytes = json.dumps(pass_json, indent=2).encode("utf-8")
    icon_bytes = _create_icon(org_color, size=29)
    icon_2x_bytes = _create_icon(org_color, size=58)
    icon_3x_bytes = _create_icon(org_color, size=87)
    logo_bytes = _create_icon(org_color, size=160)
    logo_2x_bytes = _create_icon(org_color, size=320)

    files = {
        "pass.json": pass_json_bytes,
        "icon.png": icon_bytes,
        "icon@2x.png": icon_2x_bytes,
        "icon@3x.png": icon_3x_bytes,
        "logo.png": logo_bytes,
        "logo@2x.png": logo_2x_bytes,
    }

    # Build manifest
    manifest = {}
    for name, data in files.items():
        manifest[name] = hashlib.sha1(data).hexdigest()
    manifest_bytes = json.dumps(manifest).encode("utf-8")

    # Build the .pkpass ZIP
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
        zf.writestr("manifest.json", manifest_bytes)

        # Sign if certs are configured
        if is_wallet_configured():
            try:
                signature = _sign_manifest(manifest_bytes)
                zf.writestr("signature", signature)
            except Exception as e:
                logger.warning(f"Could not sign wallet pass: {e}. Pass will be unsigned.")
        else:
            logger.info("Apple Wallet certs not configured. Generating unsigned pass (dev only).")

    return buffer.getvalue()
