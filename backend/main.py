from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import engine, get_db, Base, SessionLocal
import models
from services.pipeline import run_pipeline
from services.verifier import verify_chain

# Create all tables if they don't already exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CustodyChain API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Startup: Auto-seed the 5 handlers if the table is empty
# This ensures the app is self-contained even if schema.sql was not run manually.
# ---------------------------------------------------------------------------
HANDLER_SEED = [
    {"name": "Collector",    "step_order": 1},
    {"name": "Analyst Tool", "step_order": 2},
    {"name": "Export Tool",  "step_order": 3},
    {"name": "Reviewer",     "step_order": 4},
    {"name": "Archive",      "step_order": 5},
]


@app.on_event("startup")
def seed_handlers():
    db = SessionLocal()
    try:
        existing = db.query(models.Handler).count()
        if existing == 0:
            for h in HANDLER_SEED:
                db.add(models.Handler(**h))
            db.commit()
            print("[CustodyChain] Handlers seeded successfully.")
        else:
            print(f"[CustodyChain] Handlers already present ({existing} rows). Skipping seed.")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class EvidenceCreateRequest(BaseModel):
    name: str
    content: str
    simulate_tamper: bool = True  # when False, Export Tool passes through honestly


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.post("/evidence", summary="Create evidence and run it through the full pipeline")
def create_evidence(payload: EvidenceCreateRequest, db: Session = Depends(get_db)):
    evidence = run_pipeline(db, payload.name, payload.content, payload.simulate_tamper)
    return {"evidence_id": evidence.id, "name": evidence.name}


@app.get("/evidence", summary="List all evidence items")
def list_evidence(db: Session = Depends(get_db)):
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


@app.get("/history", summary="List all evidence items with their latest verification verdict")
def get_history(db: Session = Depends(get_db)):
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
            "created_at": e.created_at.isoformat(),
            "final_verdict": verdict.final_verdict if verdict else "NOT_VERIFIED",
        })
    return results


@app.get("/evidence/{evidence_id}/custody-log", summary="Get full step-by-step custody log")
def get_custody_log(evidence_id: int, db: Session = Depends(get_db)):
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


@app.get("/evidence/{evidence_id}/verify", summary="Run the Verifier and get chain-of-custody verdict")
def verify_evidence(evidence_id: int, db: Session = Depends(get_db)):
    evidence = db.query(models.Evidence).filter(
        models.Evidence.id == evidence_id
    ).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return verify_chain(db, evidence_id)
