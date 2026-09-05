import os
import sys
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from database import SessionLocal, Base, engine
import models
from services.custody_service import process_evidence_pipeline
from services.verifier_service import verify_evidence_integrity
from services.report_service import generate_forensic_certificate_pdf


def run_all_tests():
    print("==================================================")
    print("CustodyChain: Cryptographic Verification Test Suite")
    print("==================================================")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    passed = 0
    total = 0

    try:
        # TEST 1: Clean Chain (Intact)
        total += 1
        print("\n[TEST 1] Clean Chain (tamper_step=0)...")
        ev1 = process_evidence_pipeline(
            db,
            evidence_name="Test-Clean-Artifact-01",
            content="INTEGRITY_BASELINE_AUTHENTIC_STREAM",
            simulate_tamper=False,
            tamper_step=0,
        )
        res1 = verify_evidence_integrity(db, ev1.id)
        assert res1["final_verdict"] == "CHAIN_INTACT", f"Expected CHAIN_INTACT, got {res1['final_verdict']}"
        assert all(s["verified"] for s in res1["steps"]), "All steps should be verified"
        assert all(s["signature_valid"] for s in res1["steps"]), "All signatures should be valid"
        assert all(s["ledger_link_valid"] for s in res1["steps"]), "All ledger links should be valid"
        print(f"  [PASS]: Verdict=CHAIN_INTACT, all 5 Ed25519 signatures & ledger links valid.")
        passed += 1

        # TEST 2: Step 3 Export Tool Tamper
        total += 1
        print("\n[TEST 2] Step 3 Export Tool Tamper (tamper_step=3)...")
        ev2 = process_evidence_pipeline(
            db,
            evidence_name="Test-Export-Tamper-02",
            content="CASE_EVIDENCE_PACKET_9921",
            simulate_tamper=True,
            tamper_step=3,
        )
        res2 = verify_evidence_integrity(db, ev2.id)
        assert "STEP_3_EXPORT_TOOL" in res2["final_verdict"], f"Expected break at step 3, got {res2['final_verdict']}"
        assert res2["steps"][2]["verified"] is False, "Step 3 should not be verified"
        assert res2["steps"][3]["downstream_of_break"] is True, "Step 4 should be downstream of break"
        assert res2["steps"][4]["downstream_of_break"] is True, "Step 5 should be downstream of break"
        print(f"  [PASS]: Correctly caught break: {res2['final_verdict']}")
        passed += 1

        # TEST 3: Step 2 Analyst Tool Tamper
        total += 1
        print("\n[TEST 3] Step 2 Analyst Tool Tamper (tamper_step=2)...")
        ev3 = process_evidence_pipeline(
            db,
            evidence_name="Test-Analyst-Tamper-03",
            content="FORENSIC_PHONE_DUMP_STREAM",
            simulate_tamper=True,
            tamper_step=2,
        )
        res3 = verify_evidence_integrity(db, ev3.id)
        assert "STEP_2_ANALYST_TOOL" in res3["final_verdict"], f"Expected break at step 2, got {res3['final_verdict']}"
        print(f"  [PASS]: Correctly caught break: {res3['final_verdict']}")
        passed += 1

        # TEST 4: Step 5 Archive Tamper
        total += 1
        print("\n[TEST 4] Step 5 Archive Storage Bit-Rot (tamper_step=5)...")
        ev4 = process_evidence_pipeline(
            db,
            evidence_name="Test-Archive-Tamper-04",
            content="VAULT_ARCHIVE_FINAL_SNAPSHOT",
            simulate_tamper=True,
            tamper_step=5,
        )
        res4 = verify_evidence_integrity(db, ev4.id)
        assert "STEP_5_ARCHIVE" in res4["final_verdict"], f"Expected break at step 5, got {res4['final_verdict']}"
        print(f"  [PASS]: Correctly caught break: {res4['final_verdict']}")
        passed += 1

        # TEST 5: Forged Signature Detection
        total += 1
        print("\n[TEST 5] Forged / Altered Signature Detection...")
        ev5 = process_evidence_pipeline(
            db,
            evidence_name="Test-Forged-Sig-05",
            content="HIGH_SECURITY_MEMO",
            simulate_tamper=False,
            tamper_step=0,
        )
        # Corrupt the signature of event 2 directly in DB
        event_to_corrupt = (
            db.query(models.CustodyEvent)
            .filter(models.CustodyEvent.evidence_id == ev5.id, models.CustodyEvent.sequence_number == 2)
            .first()
        )
        event_to_corrupt.signature = "A" * 88  # Invalid base64 Ed25519 signature
        db.commit()

        res5 = verify_evidence_integrity(db, ev5.id)
        assert "SIGNATURE_INVALID" in res5["final_verdict"], f"Expected SIGNATURE_INVALID, got {res5['final_verdict']}"
        print(f"  [PASS]: Forgery caught: {res5['final_verdict']}")
        passed += 1

        # TEST 6: Tampered Ledger Chain (Hash Link Break)
        total += 1
        print("\n[TEST 6] Tampered Previous Event Hash Link...")
        ev6 = process_evidence_pipeline(
            db,
            evidence_name="Test-Ledger-Break-06",
            content="BANK_TRANSACTION_LEDGER_DATA",
            simulate_tamper=False,
            tamper_step=0,
        )
        # Tamper with previous_event_hash of step 3
        event_ledger_corrupt = (
            db.query(models.CustodyEvent)
            .filter(models.CustodyEvent.evidence_id == ev6.id, models.CustodyEvent.sequence_number == 3)
            .first()
        )
        event_ledger_corrupt.previous_event_hash = "deadbeef" * 8
        db.commit()

        res6 = verify_evidence_integrity(db, ev6.id)
        assert ("LEDGER_BROKEN" in res6["final_verdict"] or "SIGNATURE_INVALID" in res6["final_verdict"]), (
            f"Expected ledger or signature break, got {res6['final_verdict']}"
        )
        print(f"  [PASS]: Ledger corruption caught: {res6['final_verdict']}")
        passed += 1

        # TEST 7: Court PDF Certificate Generation
        total += 1
        print("\n[TEST 7] Court PDF Certificate Generation...")
        pdf_bytes = generate_forensic_certificate_pdf(db, ev1.id)
        assert pdf_bytes.startswith(b"%PDF"), "Generated file is not a valid PDF"
        assert len(pdf_bytes) > 1000, "PDF size is unexpectedly small"
        print(f"  [PASS]: PDF certificate successfully generated ({len(pdf_bytes)} bytes)")
        passed += 1

    finally:
        db.close()

    print("\n==================================================")
    print(f"TEST RESULTS: {passed}/{total} Passed ({100 * passed / total:.1f}%)")
    print("==================================================")


if __name__ == "__main__":
    run_all_tests()
