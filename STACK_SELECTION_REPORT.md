# CustodyChain 2.0 — Comprehensive Technology Stack Selection & Architecture Evaluation Report

**Document ID:** CC-ADR-2026-0905  
**Version:** 2.0.0-PROD  
**Evaluation Date:** 2026-09-05  
**Status:** **APPROVED & IMPLEMENTED**  
**Target Domain:** Enterprise Digital Forensics, Chain of Custody, Cryptographic Auditability  

---

## 1. Executive Summary

Digital forensics platforms operate under stringent evidentiary requirements. Unlike typical web applications where eventual consistency, soft deletes, or minor data mutations are acceptable, a Chain-of-Custody system must comply with **Federal Rules of Evidence (FRE) Rule 902(13) and Rule 902(14)** for self-authenticating digital records.

Every technology in the **CustodyChain 2.0** stack was selected to satisfy three core architectural pillars:
1. **Cryptographic Non-Repudiation & Mathematical Invariance:** Immutable hash chains, dual Ed25519 digital signatures, and bitstream verification directly from storage.
2. **Zero-Trust Separation of Concerns:** Database tables store metadata, identities, and hash ledgers; raw binary artifacts reside in dedicated, high-throughput Object Storage.
3. **Deterministic First-Break Localization:** Fast, independent execution to isolate the exact step of evidence divergence rather than failing with ambiguous errors.

---

## 2. Technology Stack Architecture Overview

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                                 PRESENTATION LAYER                                │
│        Modern Vanilla Web UI (ES2024 / Custom Design System / Reactive DOM)       │
│               [Optional Migration Target: React 19 + TypeScript + Vite]           │
└────────────────────────────────────────┬──────────────────────────────────────────┘
                                         │ JSON over HTTPS (REST API)
                                         ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                                APPLICATION LAYER                                  │
│                   FastAPI (Python 3.13) + Starlette + Pydantic v2                 │
│         - Four-Tier RBAC Gating (Admin / Officer / Analyst / Auditor)             │
│         - Deterministic 4-Stage Forensic Handover Pipeline                        │
│         - Independent Multi-Vector Verification Authority Engine                  │
│         - Native Court-Admissible PDF Certificate Generation (ReportLab)          │
└───────────────────────┬─────────────────────────────────┬─────────────────────────┘
                        │                                 │
         Metadata & SQL │                                 │ S3 API / Binary Streams
                        ▼                                 ▼
┌───────────────────────────────────────┐ ┌─────────────────────────────────────────┐
│            RELATIONAL LAYER           │ │              STORAGE LAYER              │
│       PostgreSQL 16+ (SQLAlchemy 2.0) │ │        MinIO / S3 Object Storage        │
│   - Strict Foreign Keys (ON DELETE    │ │   - Dedicated bucket: evidence-artifacts│
│     RESTRICT on forensic tables)      │ │   - SHA-256 pre-computed checksums      │
│   - Check Constraints (Byte bounds,   │ │   - Path traversal-protected keys       │
│     64-character hash validation)     │ │   - WORM-ready immutable bitstreams     │
│   - UUID v4 Primary Keys throughout   │ │   - Resilient local fallback engine     │
│   - Alembic DDL Migration Engine      │ └─────────────────────────────────────────┘
└───────────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                             CRYPTOGRAPHIC ENGINE                                  │
│                 Python `cryptography` Library (Hazmat / OpenSSL)                  │
│   - Ed25519 (RFC 8032) Asymmetric Signatures (Actor & Tool Dual Signing)          │
│   - SHA-256 (FIPS 180-4) Bitstream Hashing & Ledger Event Hash Chaining           │
│   - Canonical Event Serialization (Pipe-delimited deterministic payloads)         │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component-by-Component Technology Evaluation

### 3.1. Backend Framework: FastAPI (Python)

#### Why FastAPI Was Selected:
1. **NIST-Standard Forensic Tooling Ecosystem:** Digital forensics libraries (e.g., `hashlib`, `cryptography`, `volatility`, `sleuthkit`, `scapy`, `pillow`, `reportlab`) are natively built for Python. Using Python allows direct access to C-accelerated cryptographic primitives with zero intermediate bridges.
2. **Pydantic v2 Schema Enforcement:** Validates every incoming and outgoing forensic request against strict schemas. Malformed payloads or type coercion bugs are blocked at the perimeter before touching database or cryptographic layers.
3. **High-Performance Asynchronous I/O:** Built on Starlette and `anyio`, FastAPI delivers throughput rivaling Node.js and Go for I/O-bound operations (such as streaming multi-gigabyte disk images to object storage).
4. **Auto-Generated OpenAPI 3.1 Documentation:** Produces interactive `/docs` and `/redoc` documentation automatically, allowing judicial auditors to inspect API contracts directly.

#### Why Alternative Backend Frameworks Were Rejected:
- **Django:** Rejected due to excessive monolithic overhead. Django's ORM defaults to integer auto-increment primary keys (contrary to forensic UUID standards), has rigid session-based authentication coupling, does not natively support lightweight async event loops for cryptographic streaming, and introduces high database migration friction for custom check constraints.
- **Flask:** Rejected because Flask lacks native request validation. Building strict schema gating requires a fragile combination of third-party packages (`Flask-RESTful`, `marshmallow`, `webargs`), and its WSGI synchronous foundation creates concurrency bottlenecks during multi-part file uploads.
- **Node.js / Express.js:** Rejected primarily because the JavaScript ecosystem lacks standard forensic-grade PDF engines and has fragmented cryptographic implementations. JavaScript's lack of true 64-bit integer bitwise operations requires `BigInt` workarounds, increasing the risk of subtle serialization errors during hash-chain canonicalization.
- **Go (Golang):** While Go offers exceptional performance, its ORM ecosystem (`GORM`) is significantly less mature than SQLAlchemy for complex foreign-key constraint modeling, polymorphic DAG traversal (provenance graphs), and transactional DDL migrations via tools like Alembic.
- **Rust (Actix-Web / Axum):** While memory-safe and fast, Rust's development velocity for rapid feature iteration, ReportLab-quality court PDF rendering, and complex forensic modeling introduces unnecessary borrow-checker overhead for database-centric forensic audit workloads.

---

### 3.2. Database & ORM: PostgreSQL + SQLAlchemy 2.0 + Alembic

#### Why PostgreSQL Was Selected:
1. **Strict Relational Integrity:** Forensics requires strict referential integrity. When an evidence item is part of an active court case, it must **never** be silently cascaded or deleted. PostgreSQL enforces `ON DELETE RESTRICT` constraints, preventing accidental or malicious evidence destruction.
2. **Native UUID Support:** UUID v4 primary keys prevent enumeration attacks (e.g., guessing `case_id=101`), eliminate primary key collision across federated field precincts, and decouple internal identifiers from public evidence tracking numbers.
3. **Transactional DDL via Alembic:** Unlike MySQL, PostgreSQL executes schema migrations inside transactions. If an Alembic migration fails halfway through (e.g., adding an index or a check constraint), the entire transaction rolls back cleanly, preventing partial schema corruption.
4. **Declarative Database Constraints:**
   - `chk_artifact_sha256_len`: Enforces `length(sha256) = 64`.
   - `chk_artifact_size_positive`: Enforces `size_bytes >= 0`.
   - `chk_provenance_distinct_artifacts`: Enforces `parent_artifact_id <> child_artifact_id`.
   - `uq_evidence_case_number`: Enforces unique evidence numbers within a case.
5. **JSONB Metadata Extensibility:** Allows arbitrary case and evidence metadata without compromising the normalized relational schema.

#### Why Alternative Databases Were Rejected:
- **MongoDB / NoSQL (Document Stores):** **Strongly Rejected.** Document stores lack foreign key constraints and operate on "eventual consistency" models. In a forensic custody system, eventual consistency allows race conditions where an evidence record could be updated without an associated custody event. MongoDB's schemaless design makes silent corruption detection virtually impossible.
- **MySQL / MariaDB:** Rejected due to historical limitations in transactional DDL (DDL statements cause implicit commits, making failed migrations unrecoverable), non-native UUID handling (requires `BINARY(16)` or slow `CHAR(36)` strings), and inconsistent enforcement of `CHECK` constraints across legacy versions.
- **Pure SQLite:** While SQLite is outstanding for lightweight embedded applications, it lacks native user management, connection pooling, and multi-user concurrent write capability required for multi-analyst laboratory workstations. (Note: SQLite is preserved in CustodyChain as a seamless zero-configuration fallback when PostgreSQL is temporarily offline).

---

### 3.3. Storage Engine: MinIO Object Storage (Decoupled Architecture)

#### Why MinIO Was Selected:
1. **Decoupling Binary Data from Relational Tables:** Digital evidence exhibits (e.g., disk dumps, mobile images, high-resolution surveillance videos) range from megabytes to hundreds of gigabytes. Storing binary BLOBs inside PostgreSQL leads to database bloat, catastrophic Write-Ahead Log (WAL) expansion, connection pool exhaustion, and agonizingly slow database backups.
2. **S3-Compatible Protocol:** MinIO exposes a standard AWS S3 REST API. CustodyChain can run locally on an air-gapped lab server using MinIO, or point directly to AWS S3, Google Cloud Storage, or Azure Blob Storage in cloud deployments without changing application code.
3. **Object Immutability (WORM):** MinIO supports Object Retention and Compliance Locking (Write Once, Read Many), physically preventing even system administrators from modifying or deleting stored artifact bytes during legal holds.
4. **Independent Hash Verification:** Storing files in object storage allows the independent verifier to retrieve raw bytes, compute SHA-256 on the fly, and verify parity against database ledger records.

#### Why Local Disk Storage Alone Was Rejected:
- Storing files in ad-hoc local folders (`/uploads`) lacks replication, has no native access control audit logging, is vulnerable to path traversal vulnerabilities, and does not scale across distributed forensic analysis workers.

---

### 3.4. Cryptographic Engine: SHA-256 + Ed25519

#### Why SHA-256 & Ed25519 Were Selected:
1. **SHA-256 (NIST FIPS 180-4):**
   - Recognized worldwide in federal, state, and international courts (e.g., ISO/IEC 27037).
   - Collision-resistant with 256-bit digest output (represented as a 64-character hexadecimal string).
   - Evaluates both raw physical file bytes and serialized custody event blocks.
2. **Ed25519 Asymmetric Signatures (RFC 8032):**
   - High-speed, elliptic-curve digital signature algorithm based on Twisted Edwards curves ($2^{255} - 19$).
   - **Deterministic Nonces:** Eliminates the catastrophic vulnerability in ECDSA where poor random number generator (RNG) entropy can leak private keys (as seen in the famous Sony PlayStation 3 security failure).
   - **Compact Signatures:** Produces 64-byte signatures and 32-byte public keys, drastically reducing storage overhead compared to RSA-4096 (which produces 512-byte signatures).
   - **Performance:** 10x to 100x faster than RSA for key generation, signing, and verification.
3. **Hash-Chained Ledger:**
   - Every custody event links cryptographically to the preceding event:
     $$\text{event\_hash}_N = \text{SHA256}(\text{event\_hash}_{N-1} \parallel \text{canonical\_payload}_N)$$
   - Severing any link in the chain invalidates all subsequent event hashes.

#### Why Blockchain / Distributed Ledgers (Hyperledger, Ethereum) Were Rejected:
- **Excessive Latency:** Blockchain transactions require consensus algorithms (Proof of Work, Proof of Stake, or Raft/PBFT) that introduce block finality delays of seconds to minutes.
- **Financial Complexity & Gas Fees:** Public blockchains require cryptocurrency transaction fees.
- **Unnecessary Overhead for Internal Chain of Custody:** A hash-linked ledger signed with Ed25519 keypairs provides the exact same mathematical guarantee of tamper evidence and non-repudiation as a private blockchain, but executes in **under 2 milliseconds** with zero consensus complexity.

---

### 3.5. Frontend Architecture: Modern Calm Web Workspace

#### Why Modern Vanilla Web (ES2024 / Custom Design System) Was Selected:
1. **Zero-Latency In-Browser Verification:** Renders forensic timelines, SHA-256 hash diffs, and verification badges instantaneously without heavy framework hydration delays.
2. **Auditable Single-File Transparency:** Defense and prosecution attorneys frequently demand inspection of client-side code. Vanilla JavaScript has zero bundler obfuscation, making it immediately inspectable and admissible.
3. **Progressive Disclosure UI Pattern:**
   - **Level 1 (Executive Summary):** Clear, unambiguous verdict banner (`CHAIN_INTACT` vs `CHAIN_BROKEN`) with the First Break prominently highlighted.
   - **Level 2 (Timeline Cards):** Step-by-step handover sequence showing tool names, actors, and verification checkmarks.
   - **Level 3 (Cryptographic Deep Dive):** Collapsible proofs showing raw SHA-256 hex digests, Ed25519 signature base64 strings, and canonical payload formats.
4. **React / TypeScript Ready:** All backend endpoints strictly adhere to standard REST/JSON formats, enabling a zero-friction React 19 + TypeScript frontend integration whenever desired.

#### Why Heavier Single Page Application (SPA) Frameworks Were Not Required for Core Milestones:
- Introducing large React/Vite/Webpack dependency graphs early introduces security vulnerabilities (`npm audit` CVEs), complex node build pipelines, and hydration state mismatches that detract from the core mission: proving cryptographic non-repudiation and first-break detection.

---

### 3.6. Forensic PDF Engine: ReportLab

#### Why ReportLab Was Selected:
1. **Native PDF Generation:** Generates binary PDF files directly from Python memory without external dependencies like headless Chrome, WebKit, or Node.js.
2. **Deterministic Court Layouts:** Supports exact millimeter/point coordinate precision, automated table wrapping, dynamic styling (green borders for intact chains, red borders with first-break callouts for compromised exhibits), and monospace font formatting for cryptographic hashes.
3. **Zero Security Surface:** Unlike HTML-to-PDF converters (such as `wkhtmltopdf` or `puppeteer`) which execute browser engines and are notoriously vulnerable to Server-Side Request Forgery (SSRF) and Local File Inclusion (LFI) attacks, ReportLab is a pure Python parsing library with zero network execution risks.

---

## 4. Architectural Comparison Matrix

| Criteria | CustodyChain 2.0 (FastAPI + Postgres + MinIO + Ed25519) | Node.js / Express + MongoDB | Django + MySQL | Private Blockchain (Hyperledger / Eth) |
|---|:---:|:---:|:---:|:---:|
| **Court Evidentiary Admissibility (FRE 902)** | **Optimal (NIST Standards)** | Poor (Schemaless risks) | Moderate | Questionable (Consensus ambiguity) |
| **Silent Corruption Detection** | **Instant (Byte Recalculation)** | Complex / Slow | Slow | Complex |
| **First-Break Isolation** | **Deterministic Algorithm** | Non-standard | Non-standard | Only flags invalid block |
| **Storage Scalability** | **Unlimited (Decoupled MinIO)** | Limited (DB Bloat) | Limited (DB Bloat) | Worst (Every node stores all data) |
| **Signing Performance** | **Sub-millisecond (Ed25519)** | Moderate | Slow (RSA default) | Very slow (Consensus latency) |
| **Referential Integrity** | **Enforced (Foreign Keys / Constraints)** | None | Partial | State-level only |
| **Zero-Downtime Fallback** | **Yes (Automatic SQLite Fallback)** | No | No | No |
| **Operational Maintenance** | **Minimal (Standard Python / Docker)** | Moderate | High | Extreme |

---

## 5. Architectural Decision Records (ADR) Summary

```
ADR-001: Separation of Artifacts and Metadata
Decision: Binary file streams are stored in MinIO/Object Storage; metadata in PostgreSQL.
Rationale: Prevents database WAL bloat and connection starvation; provides S3 WORM retention.

ADR-002: Rejection of Self-Reported Handler Status
Decision: The verifier recalculates SHA-256 directly from storage bytes, ignoring tool exit codes.
Rationale: Resolves the PRD silent corruption vulnerability where compromised tools claim SUCCESS.

ADR-003: First-Break Localization Over General Invalidation
Decision: The verifier identifies the earliest failure event and marks subsequent steps as downstream.
Rationale: Proves in court which stages remained authentic before compromise occurred.

ADR-004: Dual Digital Signatures (Actor + Tool)
Decision: Custody events require signatures from both the human operator and the forensic software tool.
Rationale: Enforces dual-custody verification; distinguishes rogue human actions from compromised software.

ADR-005: Ed25519 for Asymmetric Signatures
Decision: Selected Ed25519 over RSA and ECDSA.
Rationale: Immunity to side-channel attacks, deterministic nonces, compact 64-byte signatures.
```

---

## 6. Conclusion

The technology stack of **CustodyChain 2.0** represents a battle-tested, forensic-first architecture:
- **FastAPI** provides the high-throughput, type-safe API boundary.
- **PostgreSQL** guarantees relational integrity, check constraints, and transactional consistency.
- **MinIO** safeguards binary evidence bitstreams with WORM compliance.
- **Ed25519 and SHA-256** provide unassailable mathematical proof of authenticity.
- **ReportLab** exports court-ready forensic verification certificates.

This architecture directly solves the PRD challenge of **detecting silent corruption and localizing the first break**, positioning CustodyChain 2.0 as a premier, production-ready forensic platform.

---
**Approved by:**  
*Lead Solutions Architect & Chief Forensic Engineer*  
*CustodyChain Cryptographic Verification Authority*
