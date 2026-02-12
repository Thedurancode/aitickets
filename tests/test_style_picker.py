"""Tests for the SMS-based flyer style picker feature."""

import secrets
from datetime import datetime, timedelta

from app.models import FlyerStyle, StylePickerSession, StylePickerStatus


# ============== Helpers ==============


def _create_style(db, name="Neon Night", description="Bold neon colors on dark background"):
    style = FlyerStyle(name=name, description=description)
    db.add(style)
    db.commit()
    db.refresh(style)
    return style


def _create_session(db, event_id, phone="+15551234567", hours_until_expiry=24):
    token = secrets.token_urlsafe(32)
    session = StylePickerSession(
        token=token,
        event_id=event_id,
        phone=phone,
        status=StylePickerStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(hours=hours_until_expiry),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


# ============== Page Rendering ==============


def test_style_picker_page_renders(client, db, create_event):
    """GET /pick-style/{token} renders the style picker page with styles."""
    event = create_event()
    style = _create_style(db)
    session = _create_session(db, event["id"])

    r = client.get(f"/pick-style/{session.token}")
    assert r.status_code == 200
    assert "Pick a Flyer Style" in r.text
    assert style.name in r.text
    assert event["name"] in r.text


def test_style_picker_page_invalid_token(client):
    """GET /pick-style/{bad_token} returns 404."""
    r = client.get("/pick-style/nonexistent-token-abc123")
    assert r.status_code == 404


def test_style_picker_page_expired(client, db, create_event):
    """GET /pick-style/{token} shows expired state when session is expired."""
    event = create_event()
    session = _create_session(db, event["id"], hours_until_expiry=-1)

    r = client.get(f"/pick-style/{session.token}")
    assert r.status_code == 200
    assert "Expired" in r.text or "expired" in r.text


def test_style_picker_page_already_selected(client, db, create_event):
    """GET /pick-style/{token} shows selected state when already picked."""
    event = create_event()
    style = _create_style(db)
    session = _create_session(db, event["id"])
    session.status = StylePickerStatus.SELECTED
    session.selected_style_id = style.id
    session.selected_at = datetime.utcnow()
    db.commit()

    r = client.get(f"/pick-style/{session.token}")
    assert r.status_code == 200
    assert "Style Selected" in r.text
    assert style.name in r.text


# ============== Style Selection ==============


def test_select_style_success(client, db, create_event):
    """POST /pick-style/{token}/select records the selection."""
    event = create_event()
    style = _create_style(db)
    session = _create_session(db, event["id"])

    r = client.post(
        f"/pick-style/{session.token}/select",
        json={"style_id": style.id},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["style_id"] == style.id
    assert data["style_name"] == style.name

    # Verify DB was updated
    db.refresh(session)
    assert session.status == StylePickerStatus.SELECTED
    assert session.selected_style_id == style.id
    assert session.selected_at is not None


def test_select_style_invalid_token(client):
    """POST /pick-style/{bad_token}/select returns 404."""
    r = client.post(
        "/pick-style/bad-token/select",
        json={"style_id": 1},
    )
    assert r.status_code == 404


def test_select_style_missing_style_id(client, db, create_event):
    """POST /pick-style/{token}/select without style_id returns 400."""
    event = create_event()
    session = _create_session(db, event["id"])

    r = client.post(
        f"/pick-style/{session.token}/select",
        json={},
    )
    assert r.status_code == 400


def test_select_style_nonexistent_style(client, db, create_event):
    """POST /pick-style/{token}/select with nonexistent style_id returns 404."""
    event = create_event()
    session = _create_session(db, event["id"])

    r = client.post(
        f"/pick-style/{session.token}/select",
        json={"style_id": 9999},
    )
    assert r.status_code == 404


def test_select_style_already_selected(client, db, create_event):
    """POST /pick-style/{token}/select when already selected returns error."""
    event = create_event()
    style = _create_style(db)
    session = _create_session(db, event["id"])
    session.status = StylePickerStatus.SELECTED
    session.selected_style_id = style.id
    db.commit()

    style2 = _create_style(db, name="Classic Elegant", description="Clean white with gold accents")
    r = client.post(
        f"/pick-style/{session.token}/select",
        json={"style_id": style2.id},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is False
    assert "already" in data["error"].lower()


def test_select_style_expired_session(client, db, create_event):
    """POST /pick-style/{token}/select on expired session returns error."""
    event = create_event()
    style = _create_style(db)
    session = _create_session(db, event["id"], hours_until_expiry=-1)

    r = client.post(
        f"/pick-style/{session.token}/select",
        json={"style_id": style.id},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is False
    assert "expired" in data["error"].lower()


# ============== SMS Helper ==============


def test_send_style_picker_sms_builds_message():
    """send_style_picker_sms constructs the right message."""
    from unittest.mock import patch

    with patch("app.services.sms.send_sms") as mock_send:
        mock_send.return_value = {"success": True, "sid": "SM123", "error": None}

        from app.services.sms import send_style_picker_sms
        result = send_style_picker_sms("+15551234567", "Winter Fest", "https://example.com/pick-style/abc123")

        assert result["success"] is True
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][1]
        assert "Winter Fest" in msg
        assert "https://example.com/pick-style/abc123" in msg
        assert "24 hours" in msg
