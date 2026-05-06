"""
Authentication routes for user registration, login, and profile management.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EventGoer
from app.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    authenticate_user,
    get_current_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Request / Response Schemas ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=1)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class GoogleAuthRequest(BaseModel):
    token: str  # Google OAuth token


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    auth_provider: Optional[str] = None
    is_admin: bool = False
    email_opt_in: bool = True
    sms_opt_in: bool = False
    marketing_opt_in: bool = False
    created_at: Optional[str] = None


# ── Helpers ─────────────────────────────────────────────────────────────────

def _user_dict(user: EventGoer) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "auth_provider": user.auth_provider or "email",
        "is_admin": bool(user.is_admin),
        "email_opt_in": bool(user.email_opt_in),
        "sms_opt_in": bool(user.sms_opt_in),
        "marketing_opt_in": bool(user.marketing_opt_in),
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _build_tokens(user: EventGoer) -> dict:
    token_data = {"sub": user.id, "email": user.email}
    return {
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
        "token_type": "bearer",
        "user": _user_dict(user),
    }


# ── Routes ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user with email and password."""
    existing = db.query(EventGoer).filter(EventGoer.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = EventGoer(
        email=body.email,
        name=body.name,
        password_hash=get_password_hash(body.password),
        auth_provider="email",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("New user registered: %s", user.id)
    return _build_tokens(user)


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email and password."""
    user = authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    logger.info("User logged in: %s", user.id)
    return _build_tokens(user)


@router.post("/refresh")
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a refresh token for a new access token."""
    payload = decode_token(body.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.query(EventGoer).filter(EventGoer.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    token_data = {"sub": user.id, "email": user.email}
    return {
        "access_token": create_access_token(token_data),
        "token_type": "bearer",
    }


@router.get("/me")
def get_me(current_user: EventGoer = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    return _user_dict(current_user)


@router.put("/me")
def update_me(
    body: ProfileUpdateRequest,
    current_user: EventGoer = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the current user's profile."""
    if body.name is not None:
        current_user.name = body.name
    if body.phone is not None:
        current_user.phone = body.phone
    if body.avatar_url is not None:
        current_user.avatar_url = body.avatar_url

    db.commit()
    db.refresh(current_user)
    return _user_dict(current_user)


@router.post("/google")
def google_auth(body: GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Authenticate or register via Google OAuth.
    Expects a Google ID token, verifies it, and returns JWT tokens.
    """
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        idinfo = id_token.verify_oauth2_token(
            body.token, google_requests.Request()
        )

        google_id = idinfo["sub"]
        email = idinfo.get("email")
        name = idinfo.get("name", "")
        avatar = idinfo.get("picture")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google account has no email",
            )

    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google auth is not configured on this server",
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        )

    # Look up by google_id first, then by email
    user = db.query(EventGoer).filter(EventGoer.google_id == google_id).first()
    if not user:
        user = db.query(EventGoer).filter(EventGoer.email == email).first()

    if user:
        # Link Google account if not yet linked
        if not user.google_id:
            user.google_id = google_id
            user.auth_provider = "google"
        if avatar and not user.avatar_url:
            user.avatar_url = avatar
        db.commit()
        db.refresh(user)
    else:
        # Create new user
        user = EventGoer(
            email=email,
            name=name,
            google_id=google_id,
            avatar_url=avatar,
            auth_provider="google",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    logger.info("Google auth for user: %s", user.id)
    return _build_tokens(user)
