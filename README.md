# CustodyChain: Digital Evidence Custody & Cryptographic Verification Platform

> **Forensic Chain-of-Custody Ledger with Independent Mathematical Verification, Ed25519 PKI Signatures, and 4-Tier RBAC Clearance.**

## Reviewer Quick Start

This is a FastAPI backend with a vanilla HTML/CSS/JavaScript frontend. No Node build step is required.

### Prerequisites

- Python 3.10+
- A browser
- Node.js is optional and is only needed for JavaScript syntax checks
- PostgreSQL is optional for local evaluation; when PostgreSQL is unavailable, the backend automatically uses `backend/storage/custodychain.db` (SQLite)

### Windows startup

Open PowerShell in the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open a second PowerShell terminal in the repository root:

```powershell
python -m http.server 5500 -d frontend
```

Open:

- Frontend: http://127.0.0.1:5500
- API health: http://127.0.0.1:8000/health
- Swagger: http://127.0.0.1:8000/docs

The backend creates the local tables on startup and seeds the four demo accounts. All demo passwords are `evidence123`.

### Demo evaluation flow

1. Open **Use demo account** and select **System Administrator**.
2. Register or open a case and confirm the active custody assignment.
3. Use **Simulate Step 3 Silent Tamper**.
4. Confirm `CHAIN_BROKEN`, first break at Step 3, and `Evidence Exporter` as the handler.
5. Confirm the Admin security alert `CHAIN_BROKEN_DETECTED`.
6. Open an evidence item and select **Explain finding with AI**.
7. Confirm a Gemini explanation when `backend/.env` contains a valid key.
8. Open **Download PDF** from the Reports view and confirm the PDF opens and downloads.

The intended handoff hierarchy is **System Admin -> Evidence Officer -> Forensic Analyst -> Independent Auditor**. Unauthorized custody actions return `403`; direct evidence edits remain immutable and are audited as edit attempts.

### Gemini configuration (optional)

Create `backend/.env` locally. This file is ignored by Git and must never be committed:

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-3.6-flash
```

Gemini explains deterministic verification facts. It does not decide hashes, signatures, lineage, or the first break.

---

## Table of Contents
1. [Core Concept & Architectural Principles](#core-concept--architectural-principles)
2. [Cryptographic Verification Engine](#cryptographic-verification-engine)
3. [4-Tier RBAC Clearance Hierarchy](#4-tier-rbac-clearance-hierarchy)
4. [Technology Stack](#technology-stack)
5. [Project Architecture](#project-architecture)
6. [Prerequisites & Environment Setup](#prerequisites--environment-setup)
7. [Running the Application](#running-the-application)
8. [Automated Test Suites](#automated-test-suites)
9. [API Reference](#api-reference)
10. [Default Security Credentials](#default-security-credentials)

---

## Core Concept & Architectural Principles

In criminal and civil proceedings, the legal admissibility of digital evidence hinges on proving an unbroken, untampered **Chain of Custody** (CoC). Traditional evidence management tools rely on *self-declared database logs* (e.g., an export tool writing `status: success` into a record). If a tool encounters silent CRLF newline alterations, storage bit-rot, or malicious tampering, the database still declares success, contaminating the judicial record.

**CustodyChain** eliminates trust in self-reported statuses through **Independent Verification**:
- It pulls raw artifact byte streams directly from disk storage.
- It recomputes SHA-256 cryptographic hashes from the bare bytes.
- It validates asymmetric Ed25519 digital signatures attached to each custody transition.
- It validates the previous-event cryptographic hash chain linking each step back to intake.
- It pinpoints the exact transition where a chain broke, localizing tampering in seconds.

```
       [01: Collector]                [02: Analyst Tool]               [03: Export Tool]
    Acquires baseline raw           Read-only laboratory             Repackages evidence
        SHA-256 Hash                    SHA-256 Valid                  CRLF Alteration!
      Ed25519 Signature               Ed25519 Signature             Stored Byte Mismatch
              │                               │                               │
              ▼                               ▼                               ▼
       [✓ VERIFIED]                    [✓ VERIFIED]                     [✕ BROKEN]
                                                              (First Verifiable Break)
                                                                              │
                                                                              ▼
                                                                  [04: Reviewer: TAINTED]
                                                                  [05: Archive:  TAINTED]
```

---

## Cryptographic Verification Engine: How Change & Tampering Are Calculated

When an investigator asks **"How does CustodyChain calculate whether digital evidence has changed?"**, the platform relies on **four deterministic cryptographic vectors** calculated in real time:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       MULTI-VECTOR VERIFICATION ENGINE                      │
├──────────────────────────────┬──────────────────────────────┬───────────────┤
│ Vector 1: Storage Byte Hash  │ Vector 2: Ed25519 PKI        │ Vector 3: Merkle Chain        │
│ Recomputed from raw disk     │ Validates custodian identity │ Links each step to previous   │
│ SHA-256(Raw Bytes) == Genesis│ Verify_Sig(PubKey, Event)    │ Hash_N = SHA256(Prev || Event)│
└──────────────────────────────┴──────────────────────────────┴───────────────┘
```

### 1. Independent Mathematical Recomputation (Bare Byte Stream)
CustodyChain **never** trusts database status columns or self-declared strings.
- When an artifact is ingested at Step 1, its raw byte stream is stored in the immutable WORM (Write-Once-Read-Many) storage repository, and its genesis **SHA-256 digest** ($H_0$) is committed to the database.
- At every subsequent handler or verification check, the verifier reads the raw binary file directly off disk:
  $$\text{LiveHash} = \text{SHA-256}(\text{disk\_stream})$$
- If an unauthorized process, bad disk sector, or silent CRLF translation modifies even a single bit in the file, $\text{LiveHash} \neq H_0$, immediately raising a `STORAGE_HASH_MISMATCH` verdict.

### 2. Ed25519 Asymmetric Digital Signatures
Every handler transition (Collector, Analyst Tool, Export Tool, Reviewer, Archive) is backed by an Ed25519 cryptographic key pair:
- The handler signs a strictly ordered canonical string:
  $$\text{Payload} = \text{EvidenceID} \parallel \text{Sequence} \parallel \text{Handler} \parallel \text{HashBefore} \parallel \text{HashAfter} \parallel \text{Timestamp} \parallel \text{PrevEventHash}$$
  $$\text{Signature} = \text{Ed25519\_Sign}(\text{PrivateKey}_{\text{handler}}, \text{Payload})$$
- The verifier loads the handler's published public key and executes cryptographic signature verification. If an adversary tampers with the record or attempts to forge an event without the handler's private key, verification returns `SIGNATURE_INVALID`.

### 3. Previous-Event Hash Continuity (Merkle Blockchain Ledger)
Each custody event incorporates the SHA-256 hash of the immediate preceding event in its payload:
$$\text{EventHash}_i = \text{SHA-256}(\text{EventHash}_{i-1} \parallel \text{CanonicalPayload}_i)$$
- Genesis event references a fixed root hash (`0000000000000000000000000000000000000000000000000000000000000000`).
- If an attacker retroactively deletes, reorders, or injects an event, the subsequent `previous_event_hash` pointers fail continuity checks, returning `CHAIN_HASH_MISMATCH`.

### 4. Step-by-Step Handover & Forensic Inspection Review
Rather than jumping directly to the end of the pipeline, CustodyChain supports a **progressive custody workflow**:
- **Step 1 (Intake)**: Registered intact by the Evidence Officer.
- **Review & Inspection**: Authorized custodians can click **Review & Inspect** to view the raw byte stream, inspect the genesis vs. live recomputed SHA-256 hashes, verify the preceding Ed25519 signature, log official inspection notes, and approve handover to the next handler.
- **Stage Progression**: Step 1 (Collector) $\rightarrow$ Step 2 (Analyst Tool) $\rightarrow$ Step 3 (Export Tool) $\rightarrow$ Step 4 (Legal Reviewer) $\rightarrow$ Step 5 (Archive Vault Sealed).


---

## 4-Tier RBAC Clearance Hierarchy

CustodyChain implements a strict four-tier Role-Based Access Control (RBAC) model. Each role has specific legal boundaries to prevent evidence contamination and preserve investigator neutrality:

| Tier | Role | Clearance Description | Permissions | Restrictions |
|---|---|---|---|---|
| **Level 4** | **System Admin** (`SYSTEM_ADMIN`) | Full administrative authority across ledger, custody records, and audit logs. | Case Registry, Evidence Intake, Verification Engine, Audit Trail, Simulation, User Admin | *None (Full Clearance)* |
| **Level 3** | **Evidence Officer** (`EVIDENCE_OFFICER`) | Physical evidence intake, chain registration, and legal case creation. | `+ New Case`, Evidence Intake, Quick Ingestion, Tamper Simulation | 🔒 **Audit Trail** (Auditor/Admin only)<br>🔒 **Verification** (Cannot self-verify intake)<br>🔒 **Report Generation** |
| **Level 2** | **Forensic Analyst** (`FORENSIC_ANALYST`) | Scientific lab analysis, Ed25519 signature checks, and integrity verification. | Lab Ingestion, Verification Engine, Court PDF Export, Tamper Simulation | 🔒 **New Case Registration** (Officer/Admin only)<br>🔒 **Audit Trail** (Auditor/Admin only) |
| **Level 1** | **Independent Auditor** (`AUDITOR`) | Regulatory oversight and legal compliance (Read-Only Independent Observer). | Immutable Audit Trail inspection, Audit Ledger Hash Verification, Independent Verification, PDF Export | 🔒 **Evidence Ingestion** (Cannot contaminate evidence)<br>🔒 **Case Creation**<br>🔒 **Tamper Scenarios** |

In the web interface, restricted actions dynamically transition to locked states (`🔒 Locked`) with security clearance badges, tooltips, and security alert toasts explaining policy restrictions.

---

## Technology Stack

### Backend
- **Language**: Python 3.10+
- **API Framework**: FastAPI (High-performance async REST API, auto-generated OpenAPI/Swagger)
- **ASGI Server**: Uvicorn
- **ORM & Database Abstraction**: SQLAlchemy 2.0
- **Database Driver**: psycopg (PostgreSQL) with SQLite fallback
- **Cryptographic Primitives**: Python `cryptography` (Ed25519 PKI signatures), `hashlib` (SHA-256)
- **Authentication**: `PyJWT` (Strict Bearer JWT authentication, PBKDF2-HMAC-SHA256 password hashing)
- **Forensic PDF Reports**: `ReportLab` (Vector-quality, court-admissible forensic certificates)

### Database
- **Engine**: PostgreSQL when configured; SQLite fallback for local/demo execution
- **Storage**: Relational tables with foreign key constraints, indexed SHA-256 hash digests, and WORM (Write-Once-Read-Many) disk storage directory for binary evidence artifacts.

### Frontend
- **Structure**: Vanilla HTML5 (Accessible, semantic layout, ARIA attributes)
- **Styling**: Vanilla CSS3 (Custom design token architecture, modern dark/light themes, glassmorphism, responsive sidebar toggle)
- **Logic**: Vanilla JavaScript (ES6 Modules, async/await, Bearer JWT session management, progressive disclosure)

---

## Project Architecture

```
Custodychain/
├── backend/
│   ├── api/
│   │   └── v1/
│   │       ├── audit.py            # Audit trail & SHA-256 ledger verification
│   │       ├── auth.py             # User login, role assignment, JWT tokens
│   │       ├── cases.py            # Legal case registry & management
│   │       ├── evidence.py         # Evidence intake & pipeline processing
│   │       ├── reports.py          # Court Evidence Integrity PDF generator
│   │       └── verification.py     # Independent verification engine endpoints
│   ├── database.py                 # SQLAlchemy session factory & connection pool
│   ├── main.py                     # FastAPI application factory & middleware
│   ├── models.py                   # SQLAlchemy schema (Cases, Evidence, Events, Audit)
│   ├── alembic/                    # Database migration scripts
│   ├── security/
│   │   └── auth.py                 # Bearer JWT auth, PBKDF2 hashing, RBAC dependencies
│   ├── services/
│   │   ├── audit_service.py        # Hash-chained audit event logger & verifier
│   │   ├── crypto_service.py       # Ed25519 PKI key generation & signature verification
│   │   ├── custody_service.py      # 4-step custody pipeline & artifact storage
│   │   ├── report_service.py       # ReportLab PDF certificate generation
│   │   ├── storage_service.py      # WORM physical artifact storage on disk
│   │   └── verifier_service.py     # Multi-vector mathematical verification engine
│   ├── storage/
│   │   └── artifacts/              # Raw stored evidence artifacts (WORM)
│   ├── requirements.txt            # Python dependencies
│   └── .env.example                # Template for environment configuration
│
├── frontend/
│   ├── app.js                      # Workspace controller, API fetcher, RBAC UI guards
│   ├── index.html                  # Two-pane workspace layout, clearance card, modals
│   └── style.css                   # Calm forensic design tokens, themes, locked states
│
├── tests/
│   ├── test_full_contract_e2e.py   # Full role and custody contract test
│   ├── test_hierarchical_workflow.py # Assignment and edit/copy alert test
│   ├── test_endpoint_matrix.py     # Endpoint lifecycle matrix
│   └── test_v2_engine.py            # Clean and tampered chain engine test
│
├── .gitignore                      # Git exclusion rules
└── README.md                       # Comprehensive platform documentation
```

---

## Prerequisites & Environment Setup

### 1. Prerequisites
- **Python**: Version 3.10 or higher
- **PostgreSQL** *(optional)*: The default local configuration falls back to SQLite when PostgreSQL is unavailable
- **Node.js** *(optional)*: For checking JavaScript syntax

---

### 2. Database Creation
No manual database creation is required for the default local/demo setup. The backend creates tables at startup. To use PostgreSQL, set `DATABASE_URL` in `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/custodychain
```

---

### 3. Environment Configuration
Navigate to the `backend/` directory and copy the environment template:

```bash
cd backend
cp .env.example .env
```

Edit `backend/.env` with your database URL and a secure secret:
```env
DATABASE_URL=postgresql+psycopg://postgres:your_actual_password@localhost:5432/custodychain
JWT_SECRET=4f9d8b1c7a3e2f5d608192a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3
CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.6-flash
```

---

### 4. Install Python Dependencies

```bash
# Create and activate virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate

# macOS / Linux:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

---

## Running the Application

### 1. Start the Backend API Server
With the virtual environment activated inside `backend/`:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
- **Backend URL**: `http://127.0.0.1:8000`
- **Interactive API Docs (Swagger)**: `http://127.0.0.1:8000/docs`
- **Alternative Docs (ReDoc)**: `http://127.0.0.1:8000/redoc`

---

### 2. Start the Frontend Workspace
In a second terminal window, navigate to `frontend/` and serve static files:

```bash
cd frontend
python -m http.server 5500
```
- **Workspace UI**: Open **`http://127.0.0.1:5500`** in your browser.

---

## Automated Test Suites

CustodyChain includes complete automated test coverage for cryptographic verification, RBAC security, and end-to-end API flows.

### 1. Run Cryptographic Verification Suite (7/7 Checks)
Tests clean chains, multi-step tamper injection, Ed25519 signature forgery detection, hash link corruption, and PDF generation:

```bash
python tests/test_verification_engine.py
```
**Expected Output:**
```text
CustodyChain: Cryptographic Verification Test Suite
[TEST 1] Clean Chain (tamper_step=0)...                    [PASS]
[TEST 2] Step 3 Export Tool Tamper (tamper_step=3)...      [PASS]
[TEST 3] Step 2 Analyst Tool Tamper (tamper_step=2)...     [PASS]
[TEST 4] Step 5 Archive Storage Bit-Rot (tamper_step=5)... [PASS]
[TEST 5] Forged / Altered Signature Detection...           [PASS]
[TEST 6] Tampered Previous Event Hash Link...              [PASS]
[TEST 7] Court PDF Certificate Generation...               [PASS]
TEST RESULTS: 7/7 Passed (100.0%)
```

### 2. Run Security, RBAC & API Tests (pytest)
Tests strict Bearer token authentication, 401 Unauthorized rejection, 403 Forbidden role enforcement across all tiers, and audit ledger hash verification:

```bash
pytest tests/ -v -p no:cacheprovider
```
**Expected Output:**
```text
tests/test_e2e_api.py::test_api PASSED
tests/test_security_rbac.py::test_auth_rejection_without_token PASSED
tests/test_security_rbac.py::test_auth_rejection_with_invalid_token PASSED
tests/test_security_rbac.py::test_role_enforcement_auditor_denied_case_creation PASSED
tests/test_security_rbac.py::test_role_enforcement_analyst_denied_audit_log_access PASSED
tests/test_security_rbac.py::test_role_permission_officer_allowed_case_creation PASSED
tests/test_security_rbac.py::test_tamper_evident_audit_ledger_verification PASSED
tests/test_security_rbac.py::test_self_role_escalation_endpoint_removed PASSED
8 passed in 2.33s
```

---

## API Reference

All protected endpoints require an `Authorization: Bearer <token>` header obtained from `/api/v1/auth/login`.

### Authentication (`/api/v1/auth`)
- `POST /api/v1/auth/login` — Authenticate with email/password; returns JWT access token and user role.
- `GET /api/v1/auth/me` — Returns the current authenticated user's profile and permissions.
- `POST /api/v1/auth/users/{user_id}/role` — *(System Admin only)* Reassigns user roles.

### Case Management (`/api/v1/cases`)
- `GET /api/v1/cases` — List all registered forensic cases and evidence counts.
- `POST /api/v1/cases` — *(Evidence Officer / System Admin)* Register a new official legal case (`case_number`, `title`, `description`).

### Digital Evidence & Custody Handover (`/api/v1/evidence`)
- `GET /api/v1/evidence` — List evidence exhibits (`?case_id=` filter supported, includes `pending_action_role`).
- `POST /api/v1/evidence` — *(Assigned Evidence Officer)* Ingest evidence at Step 1.
- `GET /api/v1/evidence/{id}` — Get detailed exhibit metadata, SHA-256 hash, and custody status.
- `POST /api/v1/evidence/{id}/transfer` — *(Assigned Forensic Analyst)* Progress custody handover to the next handler with Ed25519 digital signature.
- `POST /api/v1/evidence/{id}/copy-attempt` — Record monitored copying from the protected preview for Admin audit alerts.
- `POST /api/v1/evidence/{id}/edit` — Direct edits are rejected and recorded as immutable edit attempts.
- `GET /api/v1/evidence/{id}/review` — *(Authorized Role)* Inspect raw bitstream, compare baseline vs recomputed SHA-256 hashes, view preceding signature, and check transfer clearance.
- `POST /api/v1/evidence/{id}/review-note` — *(Authorized Role)* Record formal forensic inspector remarks and optionally sign and authorize handover to next custodian.
- `GET /api/v1/evidence/{id}/events` — List all Ed25519 signed custody events and hash linkages.
- `GET /api/v1/evidence/{id}/artifacts` — List physical artifact snapshots stored in WORM storage.


### Independent Verification (`/api/v1/verification`)
- `POST /api/v1/verification/{evidence_id}` — *(Analyst / Auditor / Admin)* Execute multi-vector verification (recompute disk hashes, check Ed25519 signatures, check previous hash continuity).
- `GET /api/v1/verification/{evidence_id}` — Get the latest authoritative verification verdict and typed `first_break` details.

### Security Audit Trail (`/api/v1/audit`)
- `GET /api/v1/audit` — *(Auditor / System Admin)* Retrieve immutable security audit events.
- `GET /api/v1/audit/verify` — *(Auditor / System Admin)* Verify the unbroken SHA-256 hash chain continuity of the audit log.

### Forensic Reports (`/api/v1/reports`)
- `GET /api/v1/reports/{evidence_id}/pdf` — *(Analyst / Auditor / Admin)* Generate and download an "Evidence Integrity Report — Chain of Custody Verification" PDF certificate.

---

## Default Security Credentials

The platform seeds four production-ready test accounts representing each tier of the clearance hierarchy (password for all: `evidence123`):

| Persona | Email | Password | Role | Clearance Level |
|---|---|---|---|---|
| **Charan (Root Admin)** | `charan@custodychain.internal` | `evidence123` | `SYSTEM_ADMIN` | **Level 4** (Full Clearance) |
| **Officer John Vance** | `officer@custodychain.internal` | `evidence123` | `EVIDENCE_OFFICER` | **Level 3** (Intake & Case Registry) |
| **Dr. Elena Rostova** | `analyst@custodychain.internal` | `evidence123` | `FORENSIC_ANALYST` | **Level 2** (Laboratory Analysis) |
| **Sarah Chen (Auditor)** | `auditor@custodychain.internal` | `evidence123` | `AUDITOR` | **Level 1** (Regulatory Oversight) |

You can toggle between these personas directly in the top-right user menu of the web application to observe real-time RBAC enforcement and UI permission locks.

---

## License & Attribution

Built for digital forensics, evidentiary integrity assurance, and chain-of-custody compliance.  
Developed by **Charan Neerukonda**.

## Verified local run (September 2026)

The current source was validated with an in-process FastAPI TestClient endpoint matrix and a clean Uvicorn startup check.

Test command:

```bash
PYTHONPATH=backend pytest -q
```

Expected result: all tests pass. The exact count can change as focused regression tests are added.

Frontend JavaScript syntax was also checked with:

```bash
node --check frontend/app.js
```

### Local startup

Backend:

```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate        # Windows
# source .venv/bin/activate      # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend (from the project root in another terminal):

```bash
python -m http.server 5500 -d frontend
```

Open `http://127.0.0.1:5500`.

### Gemini configuration

Create `backend/.env` locally (never commit this file) and add:

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-3.6-flash
```

Gemini is an explanation layer only. Deterministic SHA-256, signature, event-chain, and lineage verification remains authoritative.
