import os
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
import models

SECRET_KEY = os.environ.get("JWT_SECRET", "custodychain-production-secret-key-2026-secure")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

security_bearer = HTTPBearer(auto_error=False)


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
    Returns authenticated user. If no auth header is present,
    returns the default forensic analyst / admin (Charan) to guarantee
    flawless hackathon/demo operation without mandatory login blocks.
    """
    if credentials and credentials.credentials:
        payload = decode_access_token(credentials.credentials)
        if payload and "sub" in payload:
            user = db.query(models.User).filter(models.User.email == payload["sub"]).first()
            if user:
                return user

    # Default fallback user for seamless demo / local execution
    default_user = db.query(models.User).filter(models.User.email == "charan@custodychain.internal").first()
    if not default_user:
        default_user = models.User(
            email="charan@custodychain.internal",
            password_hash=hash_password("evidence123"),
            name="Charan",
            role="SYSTEM_ADMIN",
            is_active=True,
        )
        db.add(default_user)
        db.commit()
        db.refresh(default_user)
    return default_user
