import uuid
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.models.evidence import Evidence
from app.models.user import User
from app.core.security import get_current_user, require_role, assert_evidence_access
from app.services.report_service import generate_forensic_certificate_pdf

router = APIRouter(prefix="/reports", tags=["Forensic Reports"])


@router.get("/{evidence_id}/pdf")
def download_pdf_report(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        ev_uuid = uuid.UUID(evidence_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Evidence UUID")

    ev = assert_evidence_access(db, current_user, ev_uuid)

    pdf_bytes = generate_forensic_certificate_pdf(db, ev.id, system_user_id=current_user.id)
    filename = f"CustodyChain_Report_{ev.evidence_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )
