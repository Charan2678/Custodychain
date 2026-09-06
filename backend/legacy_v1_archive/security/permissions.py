from fastapi import Depends, HTTPException, status
from security.auth import get_current_user
import models

ROLE_HIERARCHY = {
    "SYSTEM_ADMIN": 4,
    "EVIDENCE_OFFICER": 3,
    "FORENSIC_ANALYST": 2,
    "AUDITOR": 1,
}


def require_role(min_role: str):
    def role_checker(user: models.User = Depends(get_current_user)) -> models.User:
        user_weight = ROLE_HIERARCHY.get(user.role, 0)
        required_weight = ROLE_HIERARCHY.get(min_role, 0)
        if user_weight < required_weight:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires {min_role} privilege level.",
            )
        return user
    return role_checker
