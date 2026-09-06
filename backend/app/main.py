import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.infrastructure.database.session import Base, engine, SessionLocal
from app.models.user import User
from app.core.security import hash_password

from app.api.v1.auth import router as auth_router
from app.api.v1.cases import router as cases_router
from app.api.v1.evidence import router as evidence_router, artifacts_router
from app.api.v1.verification import router as verification_router
from app.api.v1.provenance import router as provenance_router
from app.api.v1.reports import router as reports_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables exist (auto-bootstrap on startup)
    Base.metadata.create_all(bind=engine)

    # Seed demo users if not present
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "analyst@custodychain.internal").first():
            demo_users = [
                User(
                    email="analyst@custodychain.internal",
                    password_hash=hash_password("evidence123"),
                    display_name="Forensic Analyst Alice",
                    role="FORENSIC_ANALYST",
                ),
                User(
                    email="officer@custodychain.internal",
                    password_hash=hash_password("evidence123"),
                    display_name="Evidence Officer Bob",
                    role="EVIDENCE_OFFICER",
                ),
                User(
                    email="auditor@custodychain.internal",
                    password_hash=hash_password("evidence123"),
                    display_name="Legal Auditor Carol",
                    role="AUDITOR",
                ),
                User(
                    email="charan@custodychain.internal",
                    password_hash=hash_password("evidence123"),
                    display_name="Admin Charan",
                    role="SYSTEM_ADMIN",
                ),
            ]
            db.add_all(demo_users)
            db.commit()

        from app.models.user import Role, UserRole
        from app.models.case import Case

        # Seed roles
        role_names = ["SYSTEM_ADMIN", "EVIDENCE_OFFICER", "FORENSIC_ANALYST", "AUDITOR"]
        for r_name in role_names:
            if not db.query(Role).filter(Role.name == r_name).first():
                db.add(Role(name=r_name, description=f"Clearance for {r_name}"))
        db.commit()

        # Seed default investigation case
        if not db.query(Case).first():
            admin_user = db.query(User).filter(User.email == "charan@custodychain.internal").first()
            if admin_user:
                default_case = Case(
                    case_number="CASE-2026-0912",
                    title="Operation Silent Courier",
                    description="Investigation into unauthorized exfiltration and evidence tampering",
                    created_by=admin_user.id,
                )
                db.add(default_case)
                db.commit()
                db.refresh(default_case)

        # Ensure demo users are assigned as CaseMembers to all cases for demo workspace continuity
        from app.models.case import CaseMember
        all_cases = db.query(Case).all()
        all_users = db.query(User).filter(User.is_active.is_(True)).all()
        for c in all_cases:
            existing_member_user_ids = {cm.user_id for cm in db.query(CaseMember).filter(CaseMember.case_id == c.id).all()}
            for u in all_users:
                if u.id not in existing_member_user_ids:
                    access = "OWNER" if u.id == c.created_by else ("AUDITOR" if u.role == "AUDITOR" else "EDITOR")
                    db.add(CaseMember(case_id=c.id, user_id=u.id, access_level=access))
        db.commit()
    finally:
        db.close()

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register v1 Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(cases_router, prefix=settings.API_V1_STR)
app.include_router(evidence_router, prefix=settings.API_V1_STR)
app.include_router(artifacts_router, prefix=settings.API_V1_STR)
app.include_router(verification_router, prefix=settings.API_V1_STR)
app.include_router(provenance_router, prefix=settings.API_V1_STR)
app.include_router(reports_router, prefix=settings.API_V1_STR)
from app.api.v1.audit import router as audit_router
app.include_router(audit_router, prefix=settings.API_V1_STR)
from app.api.v1.dashboard import router as dashboard_router
app.include_router(dashboard_router, prefix=settings.API_V1_STR)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "storage_provider": settings.STORAGE_PROVIDER,
    }


@app.get("/")
def root():
    return {
        "message": "CustodyChain Cryptographic Evidence Verification API v2",
        "docs": "/docs",
        "health": "/health",
    }
