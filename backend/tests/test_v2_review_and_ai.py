"""
End-to-end validation for Review, Artifact Preview, Download, and AI Explanation Layer.
"""
import sys
import os
sys.path.insert(0, os.path.abspath("backend"))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_review_and_ai_workflow():
    print("=================================================================")
    print("TESTING REVIEW, INSPECTION, ARTIFACT PREVIEW & AI EXPLANATION")
    print("=================================================================")

    # 1. Login as Officer to create case
    off_login = client.post("/api/v1/auth/login", json={"email": "officer@custodychain.internal", "password": "evidence123"})
    assert off_login.status_code == 200
    off_token = off_login.json()["access_token"]
    import uuid
    c_num = f"CASE-REV-{uuid.uuid4().hex[:6]}"
    off_headers = {"Authorization": f"Bearer {off_token}"}
    case_res = client.post("/api/v1/cases", json={"case_number": c_num, "title": "Review Suite Case"}, headers=off_headers)
    assert case_res.status_code == 200
    case_id = case_res.json()["id"]
    print("  [PASS] Evidence Officer created Case")

    # Login as Forensic Analyst
    login_res = client.post("/api/v1/auth/login", json={"email": "analyst@custodychain.internal", "password": "evidence123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  [PASS] Logged in as Forensic Analyst")

    # 2. Ingest Evidence with Step 3 Tamper Simulation
    sim_res = client.post("/api/v1/evidence/simulation", json={
        "case_id": case_id,
        "name": "DiskImage-Tamper-Test",
        "content": "FORENSIC_EVIDENCE_SECTOR_0",
        "tamper_step": 3
    }, headers=headers)
    assert sim_res.status_code == 200
    ev_data = sim_res.json()
    evidence_id = ev_data["evidence_id"]
    assert ev_data["verdict"] == "CHAIN_BROKEN"
    print(f"  [PASS] Ingested tampered evidence: {evidence_id} (Verdict: {ev_data['verdict']})")

    # 3. GET /review
    rev_res = client.get(f"/api/v1/evidence/{evidence_id}/review", headers=headers)
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    assert rev_data["evidence_id"] == evidence_id
    assert "artifact" in rev_data
    assert "recomputed_sha256" in rev_data["artifact"]
    assert rev_data["artifact"]["content"] is not None
    artifact_id = rev_data["artifact"]["id"]
    print(f"  [PASS] GET /review succeeded: Artifact size={rev_data['artifact']['size_bytes']}B, Hash={rev_data['artifact']['sha256'][:16]}...")

    # 4. POST /review-note
    note_res = client.post(f"/api/v1/evidence/{evidence_id}/review-note", json={
        "note": "Forensic Analyst examination confirmed byte mutation at exporter stage.",
        "finding": "FLAGGED_FOR_CORRUPTION",
        "advance_handover": False
    }, headers=headers)
    assert note_res.status_code == 200
    assert note_res.json()["status"] == "NOTE_RECORDED"
    print("  [PASS] POST /review-note successfully committed to audit trail")

    # 5. GET /artifacts/{id}/preview
    preview_res = client.get(f"/api/v1/artifacts/{artifact_id}/preview", headers=headers)
    assert preview_res.status_code == 200
    p_data = preview_res.json()
    assert p_data["artifact_id"] == artifact_id
    assert len(p_data["preview"]) > 0
    print(f"  [PASS] GET /artifacts/{artifact_id[:8]}/preview returned safe preview ({len(p_data['preview'])} chars)")

    # 6. GET /artifacts/{id}/download
    dl_res = client.get(f"/api/v1/artifacts/{artifact_id}/download", headers=headers)
    assert dl_res.status_code == 200
    assert "X-SHA256-Checksum" in dl_res.headers
    print(f"  [PASS] GET /artifacts/{artifact_id[:8]}/download returned bitstream with checksum header")

    # 7. POST /verification/{id}/explain (AI Explanation Layer)
    ai_res = client.post(f"/api/v1/verification/{evidence_id}/explain", headers=headers)
    assert ai_res.status_code == 200
    ai_data = ai_res.json()
    assert ai_data["verdict"] == "CHAIN_BROKEN"
    assert ai_data["first_break_step"] == 3
    assert "court_admissibility" in ai_data
    print("  [PASS] POST /verification/{id}/explain generated judicial narrative:")
    print(f"         Title: {ai_data['title']}")
    print(f"         Directive: {ai_data['court_admissibility'][:80]}...")

    # 8. GET /audit and /audit/verify
    aud_res = client.get("/api/v1/audit?limit=10", headers=headers)
    assert aud_res.status_code == 403  # Analyst lacks AUDIT clearance!
    print("  [PASS] Analyst blocked from viewing audit trail (403 Forbidden)")

    # Login as Auditor
    aud_login = client.post("/api/v1/auth/login", json={"email": "auditor@custodychain.internal", "password": "evidence123"})
    aud_token = aud_login.json()["access_token"]
    aud_headers = {"Authorization": f"Bearer {aud_token}"}
    aud_list_res = client.get("/api/v1/audit?limit=10", headers=aud_headers)
    assert aud_list_res.status_code == 200
    assert len(aud_list_res.json()) >= 1

    aud_verify_res = client.get("/api/v1/audit/verify", headers=aud_headers)
    assert aud_verify_res.status_code == 200
    assert aud_verify_res.json()["valid"] is True
    print(f"  [PASS] Auditor verified audit ledger continuity (Records: {aud_verify_res.json()['count']})")

    print("\n=================================================================")
    print("ALL 8 NEW WORKFLOW & AI INTEGRATION TESTS PASSED 100%!")
    print("=================================================================")


if __name__ == "__main__":
    test_review_and_ai_workflow()
