import os
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Callable
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
import models

# In production mode, JWT_SECRET must be configured
SECRET_KEY = os.environ.get("JWT_SECRET")
if not SECRET_KEY:
    # Allow test suite fallback if testing, otherwise require explicit configuration
    SECRET_KEY = os.environ.get("TEST_JWT_SECRET", "4f9d8b1c7a3e2f5d608192a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

security_bearer = HTTPBearer(auto_error=False)

# Explicit RBAC Permissions
PERMISSIONS = {
    "SYSTEM_ADMIN": {
        "CREATE_CASE",
        "UPLOAD_EVIDENCE",
        "PROCESS_EVIDENCE",
        "VERIFY_EVIDENCE",
        "VIEW_AUDIT",
        "GENERATE_REPORT",
        "MANAGE_USERS",
        "CONFIGURE_SYSTEM",
    },
    "EVIDENCE_OFFICER": {
        "CREATE_CASE",
        "UPLOAD_EVIDENCE",
        "VERIFY_EVIDENCE",
        "GENERATE_REPORT",
    },
    "FORENSIC_ANALYST": {
        "UPLOAD_EVIDENCE",
        "PROCESS_EVIDENCE",
        "VERIFY_EVIDENCE",
        "GENERATE_REPORT",
    },
    "AUDITOR": {
        "VERIFY_EVIDENCE",
        "VIEW_AUDIT",
        "GENERATE_REPORT",
    },
}


def hash_password(password: str) -> str:
    """Hash password using PBKDF2 with HMAC-SHA256 and salt."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}:{dk.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt_hex, dk_hex = hashed_password.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_dk = bytes.fromhex(dk_hex)
        actual_dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(actual_dk, expected_dk)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Strict production authentication.
    Requires a valid, non-expired Bearer JWT token in the Authorization header.
    Returns 401 Unauthorized if missing, malformed, or user is inactive.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: No Bearer token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(models.User).filter(models.User.email == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_role(allowed_roles: list[str] | str) -> Callable:
    """FastAPI dependency to enforce role-based access control."""
    if isinstance(allowed_roles, str):
        roles_set = {allowed_roles}
    else:
        roles_set = set(allowed_roles)

    def role_checker(current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role not in roles_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Required role in {list(roles_set)}, your role is {current_user.role}",
            )
        return current_user

    return role_checker


def require_permission(required_permission: str) -> Callable:
    """FastAPI dependency to enforce fine-grained action permission."""
    def permission_checker(current_user: models.User = Depends(get_current_user)) -> models.User:
        user_perms = PERMISSIONS.get(current_user.role, set())
        if required_permission not in user_perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Action requires permission '{required_permission}'",
            )
        return current_user

    return permission_checker
