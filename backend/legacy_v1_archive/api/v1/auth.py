from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
import models
from security.auth import (
    verify_password,
    create_access_token,
    get_current_user,
    require_role,
    hash_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


class LoginRequest(BaseModel):
    email: str
    password: str


class AssignRoleRequest(BaseModel):
    role: str  # EVIDENCE_OFFICER, FORENSIC_ANALYST, AUDITOR, SYSTEM_ADMIN


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": user.email, "role": user.role, "name": user.name})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
        },
    }


@router.get("/me")
def get_me(current_user: models.User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
    }


@router.post("/users/{user_id}/role")
def assign_role(
    user_id: int,
    payload: AssignRoleRequest,
    current_user: models.User = Depends(require_role(["SYSTEM_ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Production-grade role assignment:
    Only authenticated SYSTEM_ADMIN users can modify user roles.
    Self-escalation via /switch-role is prohibited.
    """
    valid_roles = ["EVIDENCE_OFFICER", "FORENSIC_ANALYST", "AUDITOR", "SYSTEM_ADMIN"]
    if payload.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{payload.role}'. Choose from {valid_roles}",
        )

    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

    target_user.role = payload.role
    db.commit()
    db.refresh(target_user)

    return {
        "message": f"Assigned role {payload.role} to user {target_user.email}",
        "user": {
            "id": target_user.id,
            "email": target_user.email,
            "name": target_user.name,
            "role": target_user.role,
        },
    }
