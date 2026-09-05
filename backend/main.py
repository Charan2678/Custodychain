from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import engine, get_db, Base, SessionLocal
import models
from services.custody_service import process_evidence_pipeline
from services.verifier_service import verify_evidence_integrity
from security.auth import hash_password

# Import v1 routers
from api.v1.auth import router as auth_router
from api.v1.cases import router as cases_router
from api.v1.evidence import router as evidence_router
from api.v1.verification import router as verification_router
from api.v1.reports import router as reports_router
from api.v1.audit import router as audit_router

# Create all tables if they don't already exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CustodyChain Forensic API",
    version="2.0.0",
    description="Enterprise Digital Evidence Custody & Cryptographic Verification Platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Production v1 APIs
app.include_router(auth_router, prefix="/api/v1")
app.include_router(cases_router, prefix="/api/v1")
app.include_router(evidence_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Startup Seeding: Handlers, Default Admin, Default Case
# ---------------------------------------------------------------------------
HANDLER_SEED = [
    {"name": "Collector",    "step_order": 1},
    {"name": "Analyst Tool", "step_order": 2},
    {"name": "Export Tool",  "step_order": 3},
    {"name": "Reviewer",     "step_order": 4},
    {"name": "Archive",      "step_order": 5},
]


@app.on_event("startup")
def seed_database():
    db = SessionLocal()
    try:
        # 1. Seed Handlers
        existing_handlers = db.query(models.Handler).count()
        if existing_handlers == 0:
            for h in HANDLER_SEED:
                db.add(models.Handler(**h))
            db.commit()
            print("[CustodyChain] Handlers seeded.")

        # 2. Seed Default User (Charan)
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
            print("[CustodyChain] Default administrator (Charan) seeded.")

        # 3. Seed Default Case
        case_count = db.query(models.Case).count()
        if case_count == 0:
            initial_case = models.Case(
                case_number="CASE-2026-0912",
                title="Operation Silent Courier",
                description="Forensic investigation into unauthorized data modification across transit handlers.",
                status="OPEN",
                created_by="Charan",
            )
            db.add(initial_case)
            db.commit()
            print("[CustodyChain] Default investigation case seeded.")

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Backward-Compatible Legacy Request Schemas & Routes
# ---------------------------------------------------------------------------
class EvidenceCreateRequest(BaseModel):
    name: str
    content: str
    simulate_tamper: bool = True
    tamper_step: int = 3


@app.post("/evidence", summary="[Legacy] Create evidence and run pipeline")
def create_evidence_legacy(payload: EvidenceCreateRequest, db: Session = Depends(get_db)):
    # Auto-link to default case if available
    default_case = db.query(models.Case).first()
    case_id = default_case.id if default_case else None

    evidence = process_evidence_pipeline(
        db=db,
        evidence_name=payload.name,
        content=payload.content,
        case_id=case_id,
        exhibit_id=f"EX-{evidence_name_slug(payload.name)}",
        simulate_tamper=payload.simulate_tamper,
        tamper_step=payload.tamper_step,
        created_by="Charan",
    )
    return {"evidence_id": evidence.id, "name": evidence.name}


def evidence_name_slug(name: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in name).strip("-")[:16]


@app.get("/evidence", summary="[Legacy] List all evidence items")
def list_evidence_legacy(db: Session = Depends(get_db)):
    items = db.query(models.Evidence).order_by(models.Evidence.id.desc()).all()
    return [
        {
            "id": e.id,
            "name": e.name,
            "original_hash": e.original_hash,
            "created_at": e.created_at,
        }
        for e in items
    ]


@app.get("/history", summary="[Legacy] List all evidence with latest verdicts")
def get_history_legacy(db: Session = Depends(get_db)):
    items = db.query(models.Evidence).order_by(models.Evidence.id.desc()).all()
    results = []
    for e in items:
        verdict = (
            db.query(models.VerificationResult)
            .filter(models.VerificationResult.evidence_id == e.id)
            .order_by(models.VerificationResult.id.desc())
            .first()
        )
        results.append({
            "evidence_id": e.id,
            "name": e.name,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "final_verdict": verdict.final_verdict if verdict else "NOT_VERIFIED",
        })
    return results


@app.get("/evidence/{evidence_id}/custody-log", summary="[Legacy] Get full step-by-step custody log")
def get_custody_log_legacy(evidence_id: int, db: Session = Depends(get_db)):
    logs = (
        db.query(models.CustodyLog, models.Handler)
        .join(models.Handler, models.CustodyLog.handler_id == models.Handler.id)
        .filter(models.CustodyLog.evidence_id == evidence_id)
        .order_by(models.Handler.step_order)
        .all()
    )
    if not logs:
        raise HTTPException(status_code=404, detail="Evidence not found or no log entries")

    return [
        {
            "step_order": h.step_order,
            "handler_name": h.name,
            "hash_before": log.hash_before,
            "hash_after": log.hash_after,
            "status_declared": log.status_declared,
            "timestamp": log.timestamp,
        }
        for log, h in logs
    ]


@app.get("/evidence/{evidence_id}/verify", summary="[Legacy] Run Verifier and get verdict")
def verify_evidence_legacy(evidence_id: int, db: Session = Depends(get_db)):
    evidence = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return verify_evidence_integrity(db, evidence_id)
