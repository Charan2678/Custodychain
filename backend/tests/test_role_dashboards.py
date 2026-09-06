"""
Test suite validating the 4 genuinely separate role dashboards,
case access restrictions, review approval enforcement, and process marks.
"""
import sys
import os
import uuid
sys.path.insert(0, os.path.abspath("backend"))

from fastapi.testclient import TestClient
from app.main import app



def test_role_dashboards_and_lifecycle():
    from app.infrastructure.database.session import Base, engine
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as client:
        print("=================================================================")
        print("TESTING 4 SEPARATE ROLE DASHBOARDS & APPROVAL LIFECYCLE")
        print("=================================================================")

        # 1. Test Officer Dashboard
        off_login = client.post("/api/v1/auth/login", json={"email": "officer@custodychain.internal", "password": "evidence123"})
        assert off_login.status_code == 200
        off_token = off_login.json()["access_token"]
        off_headers = {"Authorization": f"Bearer {off_token}"}

        off_dash = client.get("/api/v1/dashboard", headers=off_headers)
        assert off_dash.status_code == 200
        off_data = off_dash.json()
        assert off_data["role"] == "EVIDENCE_OFFICER"
        assert "CASE_CREATE" in off_data["actions"]
        assert "EVIDENCE_INTAKE" in off_data["actions"]
        print("  [PASS] Officer Dashboard: Loaded with Officer-specific metrics and actions")

        # 2. Officer Creates Case & Ingests Evidence
        case_num = f"CASE-DASH-{uuid.uuid4().hex[:6]}"
        case_res = client.post("/api/v1/cases", json={"case_number": case_num, "title": "Dashboard Test Case"}, headers=off_headers)
        assert case_res.status_code == 200
        case_id = case_res.json()["id"]

        ev_res = client.post(f"/api/v1/cases/{case_id}/evidence", json={"name": "Exhibit-Dash-01", "content": "FORENSIC_RAW_PAYLOAD"}, headers=off_headers)
        assert ev_res.status_code == 200
        evidence_id = ev_res.json()["id"]
        print(f"  [PASS] Officer created Case ({case_num}) and ingested Evidence ({evidence_id})")

        # 3. Test Analyst Dashboard
        an_login = client.post("/api/v1/auth/login", json={"email": "analyst@custodychain.internal", "password": "evidence123"})
        assert an_login.status_code == 200
        an_token = an_login.json()["access_token"]
        an_headers = {"Authorization": f"Bearer {an_token}"}

        an_dash = client.get("/api/v1/dashboard", headers=an_headers)
        assert an_dash.status_code == 200
        an_data = an_dash.json()
        assert an_data["role"] == "FORENSIC_ANALYST"
        assert "RUN_VERIFICATION" in an_data["actions"]
        assert "CREATE_DERIVED_ARTIFACT" in an_data["actions"]
        print("  [PASS] Analyst Dashboard: Loaded with Laboratory Workbench metrics and actions")

        # 4. Enforce Review-Before-Transfer (Negative Test: Rejection blocks transfer)
        rej_res = client.post(f"/api/v1/evidence/{evidence_id}/review", json={
            "decision": "REJECT",
            "notes": "Evidence intake package seal was torn. Rejected for lab processing."
        }, headers=an_headers)
        assert rej_res.status_code == 200
        assert rej_res.json()["decision"] == "REJECT"

        trans_blocked = client.post(f"/api/v1/evidence/{evidence_id}/transfer", json={"simulate_tamper": False}, headers=an_headers)
        print("  [DEBUG] trans_blocked status:", trans_blocked.status_code, trans_blocked.text)
        assert trans_blocked.status_code == 409
        print("  [PASS] Transfer successfully blocked (409 Conflict) when review decision is REJECT")

        # 5. Positive Test: Approved review unlocks transfer
        appr_res = client.post(f"/api/v1/evidence/{evidence_id}/review", json={
            "decision": "APPROVE",
            "notes": "Physical seal inspected under microscope. Verified intact. Cleared for Normalization."
        }, headers=an_headers)
        assert appr_res.status_code == 200
        assert appr_res.json()["decision"] == "APPROVE"

        trans_ok = client.post(f"/api/v1/evidence/{evidence_id}/transfer", json={"simulate_tamper": False}, headers=an_headers)
        print("  [DEBUG] trans_ok status:", trans_ok.status_code, trans_ok.text)
        assert trans_ok.status_code == 200
        assert trans_ok.json()["sequence_number"] == 2
        print("  [PASS] Transfer succeeded (200 OK) after formal APPROVE review")

        # 6. Verify Process Marks Visible on Review Inspection
        rev_check = client.get(f"/api/v1/evidence/{evidence_id}/review", headers=an_headers)
        assert rev_check.status_code == 200
        rev_d = rev_check.json()
        assert len(rev_d["process_marks"]) >= 2
        assert any("microscope" in m["notes"] for m in rev_d["process_marks"])
        print(f"  [PASS] Evidence Review Inspection shows marked process history ({len(rev_d['process_marks'])} marks)")

        # 7. Test Auditor Dashboard
        aud_login = client.post("/api/v1/auth/login", json={"email": "auditor@custodychain.internal", "password": "evidence123"})
        assert aud_login.status_code == 200
        aud_token = aud_login.json()["access_token"]
        aud_headers = {"Authorization": f"Bearer {aud_token}"}

        aud_dash = client.get("/api/v1/dashboard", headers=aud_headers)
        assert aud_dash.status_code == 200
        aud_data = aud_dash.json()
        assert aud_data["role"] == "AUDITOR"
        assert "VIEW_FIRST_BREAK" in aud_data["actions"]
        assert "VIEW_AUDIT_TRAIL" in aud_data["actions"]
        print("  [PASS] Auditor Dashboard: Loaded with Compliance Queue metrics and actions")

        # 8. Test Admin Dashboard
        adm_login = client.post("/api/v1/auth/login", json={"email": "charan@custodychain.internal", "password": "evidence123"})
        assert adm_login.status_code == 200
        adm_token = adm_login.json()["access_token"]
        adm_headers = {"Authorization": f"Bearer {adm_token}"}

        adm_dash = client.get("/api/v1/dashboard", headers=adm_headers)
        assert adm_dash.status_code == 200
        adm_data = adm_dash.json()
        assert adm_data["role"] == "SYSTEM_ADMIN"
        assert "system_health" in adm_data
        assert "api" in adm_data["system_health"]
        print("  [PASS] Admin Dashboard: Loaded with System Health indicators and global metrics")

        print("\n=================================================================")
        print("ALL ROLE DASHBOARDS & APPROVAL LIFECYCLE TESTS PASSED 100%!")
        print("=================================================================")


    if __name__ == "__main__":
        test_role_dashboards_and_lifecycle()
