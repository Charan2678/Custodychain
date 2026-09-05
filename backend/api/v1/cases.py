from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
import models
from security.auth import get_current_user
from services.audit_service import log_audit_event

router = APIRouter(prefix="/cases", tags=["Forensic Cases"])


class CaseCreateRequest(BaseModel):
    case_number: str
    title: str
    description: str | None = None


@router.get("")
def list_cases(db: Session = Depends(get_db)):
    cases = db.query(models.Case).order_by(models.Case.id.desc()).all()
    results = []
    for c in cases:
        ev_count = db.query(models.Evidence).filter(models.Evidence.case_id == c.id).count()
        results.append({
            "id": c.id,
            "case_number": c.case_number,
            "title": c.title,
            "description": c.description,
            "status": c.status,
            "created_by": c.created_by,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "evidence_count": ev_count,
        })
    return results


@router.post("")
def create_case(
    payload: CaseCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(models.Case).filter(models.Case.case_number == payload.case_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Case number already exists")

    new_case = models.Case(
        case_number=payload.case_number,
        title=payload.title,
        description=payload.description,
        created_by=current_user.name,
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    log_audit_event(
        db,
        user_name=current_user.name,
        action="CASE_CREATED",
        resource_type="CASE",
        resource_id=str(new_case.id),
        details=f"Case {new_case.case_number}: {new_case.title}",
    )

    return new_case


@router.get("/{case_id}")
def get_case(case_id: int, db: Session = Depends(get_db)):
    c = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Case not found")

    evidence_items = (
        db.query(models.Evidence)
        .filter(models.Evidence.case_id == case_id)
        .order_by(models.Evidence.id.desc())
        .all()
    )

    return {
        "id": c.id,
        "case_number": c.case_number,
        "title": c.title,
        "description": c.description,
        "status": c.status,
        "created_by": c.created_by,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "evidence": [
            {
                "id": e.id,
                "exhibit_id": e.exhibit_id,
                "name": e.name,
                "original_hash": e.original_hash,
                "status": e.status,
                "size_bytes": e.size_bytes,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in evidence_items
        ],
    }
