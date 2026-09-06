import os
import sys
import uuid

# Set test database before app import
os.environ["DATABASE_URL"] = "sqlite:///./test_api.db"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.database.session import Base, engine


def test_e2e_api_suite():
    print("=================================================================")
    print("CUSTODYCHAIN 2.0: END-TO-END REST API & RBAC TEST SUITE")
    print("=================================================================")

    # Clean old db if exists
    if os.path.exists("test_api.db"):
        try:
            os.remove("test_api.db")
        except Exception:
            pass

    with TestClient(app) as client:
        # 1. Health check
        res = client.get("/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print("  [PASS] GET /health -> 200 OK")

        # 2. Login as Forensic Analyst
        res = client.post("/api/v1/auth/login", json={
            "email": "analyst@custodychain.internal",
            "password": "evidence123",
        })
        assert res.status_code == 200, f"Analyst login failed: {res.text}"
        analyst_token = res.json()["access_token"]
        analyst_headers = {"Authorization": f"Bearer {analyst_token}"}
        print("  [PASS] POST /api/v1/auth/login (Analyst) -> 200 OK (JWT acquired)")

        # 3. Login as Evidence Officer
        res = client.post("/api/v1/auth/login", json={
            "email": "officer@custodychain.internal",
            "password": "evidence123",
        })
        assert res.status_code == 200, f"Officer login failed: {res.text}"
        officer_token = res.json()["access_token"]
        officer_headers = {"Authorization": f"Bearer {officer_token}"}
        print("  [PASS] POST /api/v1/auth/login (Officer) -> 200 OK (JWT acquired)")

        # 4. Officer creates Case
        case_num = f"CASE-CRIME-SCENE-{uuid.uuid4().hex[:6]}"
        res = client.post("/api/v1/cases", json={
            "case_number": case_num,
            "title": "Suspect Server Storage Extraction",
            "description": "Evidence collected pursuant to lawful judicial search warrant",
        }, headers=officer_headers)
        assert res.status_code == 200, f"Case creation failed: {res.text}"
        case_id = res.json()["id"]
        print(f"  [PASS] POST /api/v1/cases -> Case created: {case_id}")

        # 4b. Test Step 10: POST /cases/{case_id}/evidence & GET /cases/{case_id}/evidence
        res = client.post(f"/api/v1/cases/{case_id}/evidence", json={
            "name": "DirectIntakeEvidence",
            "content": "TEST_DIRECT_INTAKE_PAYLOAD",
        }, headers=officer_headers)
        assert res.status_code == 200, f"Case evidence intake failed: {res.text}"
        print(f"  [PASS] POST /api/v1/cases/{case_id}/evidence -> Evidence created: {res.json()['id']}")

        res = client.get(f"/api/v1/cases/{case_id}/evidence", headers=officer_headers)
        assert res.status_code == 200
        assert len(res.json()) >= 1
        print(f"  [PASS] GET /api/v1/cases/{case_id}/evidence -> Listed {len(res.json())} exhibits")

        # 5. Run Clean Simulation (tamper_step=0)
        res = client.post("/api/v1/evidence/simulation", json={
            "case_id": case_id,
            "name": "ServerImage_Clean",
            "content": "CONFIDENTIAL_FINANCIAL_LOGS_AUTHENTIC_2026",
            "tamper_step": 0,
        }, headers=analyst_headers)
        assert res.status_code == 200, f"Clean simulation failed: {res.text}"
        clean_data = res.json()
        assert clean_data["verdict"] == "CHAIN_INTACT"
        assert all(s["status"] == "VERIFIED" for s in clean_data["steps"])
        clean_ev_id = clean_data["evidence_id"]
        print(f"  [PASS] POST /api/v1/evidence/simulation (Clean) -> Verdict: {clean_data['verdict']}")

        # 6. Run Tampered Simulation (tamper_step=3 at Evidence Exporter)
        res = client.post("/api/v1/evidence/simulation", json={
            "case_id": case_id,
            "name": "ServerImage_Tampered",
            "content": "GOVERNMENT_CLASSIFIED_COMMUNICATION_CABLE",
            "tamper_step": 3,
        }, headers=analyst_headers)
        assert res.status_code == 200, f"Tamper simulation failed: {res.text}"
        tampered_data = res.json()
        assert tampered_data["verdict"] == "CHAIN_BROKEN"
        fb = tampered_data["first_break"]
        assert fb["sequence_number"] == 3
        assert "Exporter" in fb["tool_name"]
        assert fb["affected_downstream_steps"] == [4]
        tampered_ev_id = tampered_data["evidence_id"]
        print(f"  [PASS] POST /api/v1/evidence/simulation (Tampered) -> Caught break at Step {fb['sequence_number']} ({fb['tool_name']}): {fb['reason']}")

        # 7. Query Provenance Lineage Graph
        res = client.get(f"/api/v1/provenance/{clean_ev_id}", headers=analyst_headers)
        assert res.status_code == 200, f"Provenance query failed: {res.text}"
        prov_data = res.json()
        assert len(prov_data["nodes"]) >= 4
        assert len(prov_data["edges"]) >= 3
        print(f"  [PASS] GET /api/v1/provenance/{clean_ev_id} -> Graph nodes: {len(prov_data['nodes'])}, edges: {len(prov_data['edges'])}")

        # 7b. Test Step 12: GET /evidence/{id}/artifacts & GET /artifacts/{id}
        res = client.get(f"/api/v1/evidence/{clean_ev_id}/artifacts", headers=analyst_headers)
        assert res.status_code == 200
        artifacts_list = res.json()
        assert len(artifacts_list) >= 1
        first_art_id = artifacts_list[0]["id"]
        print(f"  [PASS] GET /api/v1/evidence/{clean_ev_id}/artifacts -> Found {len(artifacts_list)} artifacts")

        res = client.get(f"/api/v1/artifacts/{first_art_id}", headers=analyst_headers)
        assert res.status_code == 200
        assert res.json()["id"] == first_art_id
        print(f"  [PASS] GET /api/v1/artifacts/{first_art_id} -> Successfully retrieved artifact metadata")

        # 8. Download Court Forensic PDF Certificate
        res = client.get(f"/api/v1/reports/{tampered_ev_id}/pdf", headers=analyst_headers)
        assert res.status_code == 200, f"PDF report failed: {res.text}"
        assert res.content.startswith(b"%PDF")
        print(f"  [PASS] GET /api/v1/reports/{tampered_ev_id}/pdf -> Generated valid PDF ({len(res.content)} bytes)")

        print("\n=================================================================")
        print("ALL 8 END-TO-END API TESTS PASSED PERFECTLY!")
        print("=================================================================")

    # Clean up test db file
    if os.path.exists("test_api.db"):
        try:
            os.remove("test_api.db")
        except Exception:
            pass


if __name__ == "__main__":
    test_e2e_api_suite()
