"""
Authentication and Authorization Module

Implements JWT-based authentication with proper security measures.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EventGoer

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Security scheme
security = HTTPBearer()


class AuthenticationError(Exception):
    """Custom authentication error."""
    pass


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Token payload data
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: Token payload data

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> EventGoer:
    """
    Dependency to extract and validate current authenticated user from JWT token.

    Args:
        credentials: HTTP authorization credentials containing JWT
        db: Database session

    Returns:
        Authenticated EventGoer object

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials

    try:
        payload = decode_token(token)

        # Validate token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        # Extract user ID
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        # Fetch user from database
        user = db.query(EventGoer).filter(EventGoer.id == user_id).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        return user

    except JWTError as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: EventGoer = Depends(get_current_user)
) -> EventGoer:
    """
    Dependency to get current active (non-disabled) user.

    Args:
        current_user: Current authenticated user

    Returns:
        Active EventGoer object

    Raises:
        HTTPException: If user account is inactive
    """
    # Add check for user active status if you have that field
    # For now, just return the user
    return current_user


async def get_current_admin_user(
    current_user: EventGoer = Depends(get_current_user)
) -> EventGoer:
    """
    Dependency to ensure current user has admin privileges.

    Args:
        current_user: Current authenticated user

    Returns:
        Admin EventGoer object

    Raises:
        HTTPException: If user is not an admin
    """
    # Check if user has admin role
    # This assumes you have an is_admin field or role system
    if not getattr(current_user, 'is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )

    return current_user


def authenticate_user(db: Session, email: str, password: str) -> Optional[EventGoer]:
    """
    Authenticate a user by email and password.

    Args:
        db: Database session
        email: User email
        password: Plain text password

    Returns:
        EventGoer object if authentication succeeds, None otherwise
    """
    user = db.query(EventGoer).filter(EventGoer.email == email).first()

    if not user:
        logger.warning(f"Authentication failed: User not found for email {email}")
        return None

    # Check if user has password_hash field
    if not hasattr(user, 'password_hash') or not user.password_hash:
        logger.warning(f"Authentication failed: No password set for user {user.id}")
        return None

    if not verify_password(password, user.password_hash):
        logger.warning(f"Authentication failed: Invalid password for user {user.id}")
        return None

    logger.info(f"User authenticated successfully: {user.id}")
    return user


class OptionalAuth:
    """
    Dependency for optional authentication.
    Returns user if authenticated, None if not.
    """

    async def __call__(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
        db: Session = Depends(get_db)
    ) -> Optional[EventGoer]:
        """Get current user if authenticated, None otherwise."""
        if not credentials:
            return None

        try:
            token = credentials.credentials
            payload = decode_token(token)
            user_id = payload.get("sub")

            if user_id:
                return db.query(EventGoer).filter(EventGoer.id == user_id).first()
        except HTTPException:
            pass

        return None


# Singleton instance for optional auth
optional_auth = OptionalAuth()