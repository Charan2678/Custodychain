from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
import models
from security.auth import (
    verify_password,
    create_access_token,
    get_current_user,
    hash_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


class LoginRequest(BaseModel):
    email: str
    password: str


class SwitchRoleRequest(BaseModel):
    role: str  # EVIDENCE_OFFICER, FORENSIC_ANALYST, AUDITOR, SYSTEM_ADMIN


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
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


@router.post("/switch-role")
def switch_role(
    payload: SwitchRoleRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    valid_roles = ["EVIDENCE_OFFICER", "FORENSIC_ANALYST", "AUDITOR", "SYSTEM_ADMIN"]
    if payload.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Choose from {valid_roles}")

    current_user.role = payload.role
    db.commit()
    return {"message": f"Active role switched to {payload.role}", "user": {"name": current_user.name, "role": current_user.role}}
