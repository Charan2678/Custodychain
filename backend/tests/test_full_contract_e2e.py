import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.database.session import Base, engine

def auth(client, email, password="evidence123"):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}

def test_full_role_api_e2e():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as client:
        officer = auth(client, "officer@custodychain.internal")
        analyst = auth(client, "analyst@custodychain.internal")
        auditor = auth(client, "auditor@custodychain.internal")
        admin = auth(client, "charan@custodychain.internal")
        for headers in [officer, analyst, auditor, admin]:
            assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
            assert client.get("/api/v1/dashboard", headers=headers).status_code == 200

        # Officer creates a case; analyst and auditor receive explicit membership.
        case_number = "CASE-E2E-" + uuid.uuid4().hex[:8]
        r = client.post("/api/v1/cases", headers=officer, json={
            "case_number": case_number,
            "title": "E2E Contract Case",
            "description": "API/RBAC integration test",
        })
        assert r.status_code == 200, r.text
        case_id = r.json()["id"]
        for headers in [officer, analyst, auditor, admin]:
            assert client.get(f"/api/v1/cases/{case_id}", headers=headers).status_code == 200

        # Intake only Officer/Admin.
        assert client.post("/api/v1/evidence", headers=auditor, json={"name":"bad","content":"x","case_id":case_id}).status_code == 403
        assert client.post("/api/v1/evidence", headers=analyst, json={"name":"bad","content":"x","case_id":case_id}).status_code == 403

        r = client.post(f"/api/v1/cases/{case_id}/evidence", headers=officer, json={
            "name": "Exhibit-001", "content": "PAYLOAD"
        })
        assert r.status_code == 200, r.text
        evidence_id = r.json()["id"]

        # Review is readable; a non-assigned Officer cannot transfer custody.
        assert client.get(f"/api/v1/evidence/{evidence_id}/review", headers=officer).status_code == 200
        r = client.post(f"/api/v1/evidence/{evidence_id}/transfer", headers=officer, json={"simulate_tamper": False})
        assert r.status_code == 403, r.text
        r = client.post(f"/api/v1/evidence/{evidence_id}/review", headers=officer, json={"decision":"APPROVE","notes":"Initial intake approved"})
        assert r.status_code == 200, r.text
        r = client.post(f"/api/v1/evidence/{evidence_id}/transfer", headers=analyst, json={"simulate_tamper": False})
        assert r.status_code == 200, r.text

        # Independent verification is Analyst/Auditor/Admin only.
        assert client.post(f"/api/v1/verification/{evidence_id}", headers=officer).status_code == 403
        assert client.post(f"/api/v1/verification/{evidence_id}", headers=analyst).status_code == 200
        assert client.post(f"/api/v1/verification/{evidence_id}", headers=auditor).status_code == 200

        # Auditor can read audit; Officer cannot.
        assert client.get("/api/v1/audit", headers=officer).status_code == 403
        assert client.get("/api/v1/audit", headers=auditor).status_code == 200
        assert client.get("/api/v1/audit/verify", headers=auditor).status_code == 200

        # Demo chain: clean and silent tamper.
        clean = client.post("/api/v1/evidence/simulation", headers=analyst, json={
            "case_id": case_id, "name": "Clean-Sim", "content": "ABC", "tamper_step": 0
        })
        assert clean.status_code == 200, clean.text
        assert clean.json()["verdict"] == "CHAIN_INTACT"
        tampered = client.post("/api/v1/evidence/simulation", headers=analyst, json={
            "case_id": case_id, "name": "Tamper-Sim", "content": "ABC", "tamper_step": 3
        })
        assert tampered.status_code == 200, tampered.text
        result = tampered.json()
        assert result["verdict"] == "CHAIN_BROKEN"
        assert result["first_break"]["sequence_number"] == 3
        assert result["first_break"]["affected_downstream_steps"] == [4]

        ai = client.post(f"/api/v1/verification/{result['evidence_id']}/explain", headers=auditor)
        assert ai.status_code == 200, ai.text
        assert ai.json()["first_break_step"] == 3
