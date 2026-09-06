import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List
try:
    from jose import jwt, JWTError
except ImportError:
    import jwt
    JWTError = jwt.PyJWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.infrastructure.database.session import get_db
from app.models.user import User

security_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """PBKDF2-HMAC-SHA256 password hashing with random salt."""
    if not salt:
        salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${dk.hex()}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        salt, _ = password_hash.split("$", 1)
        expected = hash_password(plain_password, salt)
        return expected == password_hash
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    except (JWTError, Exception):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive")
    return user


def require_role(allowed_roles: List[str]):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied: Requires role in {allowed_roles}, your role is '{current_user.role}'",
            )
        return current_user
    return role_checker


def assert_case_access(db: Session, user: User, case_id):
    """Raise 403 unless the user is the case owner/member or a system admin."""
    from app.models.case import Case, CaseMember
    import uuid
    try:
        case_uuid = case_id if isinstance(case_id, uuid.UUID) else uuid.UUID(str(case_id))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Case UUID")
    case = db.query(Case).filter(Case.id == case_uuid).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    if user.role == "SYSTEM_ADMIN":
        return case
    member = db.query(CaseMember).filter(
        CaseMember.case_id == case_uuid, CaseMember.user_id == user.id
    ).first()
    if not member and case.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: user is not assigned to this case")
    return case


def assert_evidence_access(db: Session, user: User, evidence_id):
    """Raise 403 unless the user can access the evidence's case."""
    from app.models.evidence import Evidence
    import uuid
    try:
        ev_uuid = evidence_id if isinstance(evidence_id, uuid.UUID) else uuid.UUID(str(evidence_id))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Evidence UUID")
    evidence = db.query(Evidence).filter(Evidence.id == ev_uuid).first()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    assert_case_access(db, user, evidence.case_id)
    return evidence


def assert_artifact_access(db: Session, user: User, artifact_id):
    """Raise 403 unless the user can access the artifact's evidence/case."""
    from app.models.artifact import Artifact
    import uuid
    try:
        art_uuid = artifact_id if isinstance(artifact_id, uuid.UUID) else uuid.UUID(str(artifact_id))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Artifact UUID")
    artifact = db.query(Artifact).filter(Artifact.id == art_uuid).first()
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    assert_evidence_access(db, user, artifact.evidence_id)
    return artifact
