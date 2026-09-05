# CustodyChain

**Multi-Handler Evidence Integrity Verification**  
Myonsite Hackathon — Final Round | Built by Charan neerukonda

---

## What It Does

CustodyChain is a simulated digital forensics tool that tracks a piece of evidence through a 5-step handling pipeline and **cryptographically proves** whether the chain of custody was preserved at every step — by independently recomputing hashes rather than trusting any handler's self-reported status.

When a handler silently alters the evidence (while claiming success), the Verifier catches it and pinpoints the exact step where the chain broke.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python + FastAPI |
| Hashing | SHA-256 (`hashlib`) |
| Database | MySQL + SQLAlchemy (PyMySQL) |
| Frontend | HTML + CSS + Vanilla JS |

---

## Project Structure

```
custodychain/
├── backend/
│   ├── requirements.txt
│   ├── .env                    ← set your MySQL password here
│   ├── database.py
│   ├── models.py
│   ├── schema.sql
│   ├── utils/hashing.py
│   ├── services/
│   │   ├── handlers.py         ← tamper injection at Export Tool (Step 3)
│   │   ├── pipeline.py
│   │   └── verifier.py
│   └── main.py
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js
```

---

## Quick Start

### 1. MySQL Setup

```bash
mysql -u root -p < backend/schema.sql
```

### 2. Backend

```bash
cd backend

# Windows
python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

# Edit .env and set your MySQL password
# DB_PASSWORD=your_actual_password

uvicorn main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
python -m http.server 5500
# Then open http://localhost:5500 in your browser
```

---

## Pipeline Handlers

| Step | Handler | Role | Tamper? |
|------|---------|------|---------|
| 1 | Collector | Acquires evidence + baseline hash | ❌ Clean |
| 2 | Analyst Tool | Read-only analysis | ❌ Clean |
| 3 | Export Tool | Repackages evidence | ✅ **TAMPERED** (silently alters line endings, declares success) |
| 4 | Reviewer | Reviews evidence | ❌ Clean |
| 5 | Archive | Long-term storage | ❌ Clean |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/evidence` | Create evidence + run pipeline |
| `GET` | `/evidence` | List all evidence items |
| `GET` | `/evidence/{id}/custody-log` | Step-by-step custody log |
| `GET` | `/evidence/{id}/verify` | Run verifier + get verdict |

---

## Demo Flow

1. Click **Run Demo**
2. Steps 1–2 show ✅ Verified
3. Step 3 (Export Tool) shows ❌ Tamper Detected — despite declaring `status: success`
4. Verdict: `CHAIN_BROKEN_AT_STEP_3 — EXPORT TOOL`
5. Expand any step to see the full hash comparison

---

## Key Insight

> The Verifier **never trusts** self-reported handler status or declared hash values.  
> It independently recomputes the SHA-256 hash from the actual stored content snapshot at each step and compares against the previous step's output.  
> Any unauthorized mutation — no matter how subtle — is detected and pinpointed.
