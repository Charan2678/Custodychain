from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from database import get_db
import models
from services.report_service import generate_forensic_certificate_pdf
from services.audit_service import log_audit_event
from security.auth import get_current_user

router = APIRouter(prefix="/reports", tags=["Forensic Reports"])


@router.get("/{evidence_id}/pdf")
def get_pdf_certificate(
    evidence_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    evidence = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    pdf_bytes = generate_forensic_certificate_pdf(db, evidence_id)

    log_audit_event(
        db,
        user_name=current_user.name,
        action="REPORT_GENERATED_PDF",
        resource_type="EVIDENCE",
        resource_id=str(evidence_id),
        details=f"Court Forensic Certificate generated for exhibit {evidence.exhibit_id}",
    )

    filename = f"CustodyCertificate_{evidence.exhibit_id or evidence.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )
