import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, User, Case
from app.services.custody_service import run_full_pipeline_simulation


def test_custodychain_v2():
    print("=================================================================")
    print("CUSTODYCHAIN 2.0: FULL ARCHITECTURE VERIFICATION TEST")
    print("=================================================================")

    # Use in-memory or SQLite for deterministic test run
    test_db_url = "sqlite:///:memory:"
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    # 1. Seed user and case
    user = User(
        email="analyst@custodychain.internal",
        password_hash="pbkdf2_test_hash",
        display_name="Forensic Analyst Alice",
        role="FORENSIC_ANALYST",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    case = Case(
        case_number="CASE-2026-ALPHA",
        title="Laptop Drive Bitstream Forensics",
        created_by=user.id,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    # -----------------------------------------------------------------
    # TEST 1: Clean Pipeline (No Tamper)
    # -----------------------------------------------------------------
    print("\n[TEST 1] Running Clean Custody Pipeline (4 steps, no tamper)...")
    res1 = run_full_pipeline_simulation(
        db=db,
        case_id=case.id,
        name="DiskImage_Exhibit_001",
        content="RAW_BITSTREAM_AUTHENTIC_EVIDENCE_STREAM_DATA_9921",
        user=user,
        tamper_step=0,
    )
    print(f"  -> Overall Verdict: {res1['verdict']}")
    print(f"  -> Steps count: {len(res1['steps'])}")
    for s in res1["steps"]:
        print(f"     Step {s['sequence_number']} ({s['tool_name']}): {s['status']}")
    
    assert res1["verdict"] == "CHAIN_INTACT", f"Expected CHAIN_INTACT, got {res1['verdict']}"
    assert all(s["verified"] for s in res1["steps"]), "All steps must be verified"
    assert res1["first_break"] is None, "Clean run must have no first break"
    print("  >>> PASS: Clean chain completely verified!")

    # -----------------------------------------------------------------
    # TEST 2: PRD Winning Feature - Secretly Corrupt Handler 3 (Exporter)
    # -----------------------------------------------------------------
    print("\n[TEST 2] Running Tampered Pipeline (Step 3: Exporter silently alters bytes)...")
    res2 = run_full_pipeline_simulation(
        db=db,
        case_id=case.id,
        name="DiskImage_Exhibit_002",
        content="BANK_VAULT_SURVEILLANCE_CAMERA_FOOTAGE_EXHIBIT",
        user=user,
        tamper_step=3,
    )
    print(f"  -> Overall Verdict: {res2['verdict']}")
    fb = res2["first_break"]
    print(f"  -> First Break Identified: Step {fb['sequence_number']} ({fb['tool_name']})")
    print(f"  -> Reason: {fb['reason']}")
    print(f"  -> Expected: {fb['expected_value'][:20]}...")
    print(f"  -> Observed: {fb['observed_value'][:20]}...")
    print(f"  -> Affected Downstream Steps: {fb['affected_downstream_steps']}")

    for s in res2["steps"]:
        print(f"     Step {s['sequence_number']} ({s['tool_name']}): {s['status']} (Downstream: {s['downstream']})")

    assert res2["verdict"] == "CHAIN_BROKEN", f"Expected CHAIN_BROKEN, got {res2['verdict']}"
    assert fb["sequence_number"] == 3, f"Expected first break at Step 3, got {fb['sequence_number']}"
    assert "Exporter" in fb["tool_name"], f"Expected Exporter, got {fb['tool_name']}"
    assert fb["affected_downstream_steps"] == [4], f"Expected Step 4 downstream, got {fb['affected_downstream_steps']}"
    assert res2["steps"][0]["status"] == "VERIFIED", "Step 1 must be VERIFIED"
    assert res2["steps"][1]["status"] == "VERIFIED", "Step 2 must be VERIFIED"
    assert res2["steps"][2]["status"] == "BROKEN", "Step 3 must be BROKEN"
    assert res2["steps"][3]["status"] == "DOWNSTREAM", "Step 4 must be marked DOWNSTREAM"

    print("\n=================================================================")
    print("ALL TESTS PASSED! CUSTODYCHAIN 2.0 CORE FOUNDATION IS ROCK-SOLID!")
    print("=================================================================")


if __name__ == "__main__":
    test_custodychain_v2()
