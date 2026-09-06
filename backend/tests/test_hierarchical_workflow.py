import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.infrastructure.database.session import Base, engine


def auth(client, email):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "evidence123"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_admin_officer_analyst_auditor_hierarchy():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as client:
        admin = auth(client, "charan@custodychain.internal")
        officer = auth(client, "officer@custodychain.internal")
        analyst = auth(client, "analyst@custodychain.internal")
        auditor = auth(client, "auditor@custodychain.internal")

        officer_user = client.get("/api/v1/auth/me", headers=officer).json()
        analyst_user = client.get("/api/v1/auth/me", headers=analyst).json()
        auditor_user = client.get("/api/v1/auth/me", headers=auditor).json()

        case = client.post(
            "/api/v1/cases",
            headers=admin,
            json={
                "case_number": f"CASE-HIER-{uuid.uuid4().hex[:8]}",
                "title": "Hierarchical Workflow Case",
                "evidence_officer_id": officer_user["id"],
            },
        )
        assert case.status_code == 200, case.text
        case_id = case.json()["id"]

        assignments = client.get(f"/api/v1/cases/{case_id}/assignments", headers=admin)
        assert assignments.status_code == 200
        assert any(a["stage"] == "EVIDENCE_OFFICER" and a["status"] == "ACTIVE" for a in assignments.json())

        evidence = client.post(
            f"/api/v1/cases/{case_id}/evidence",
            headers=officer,
            json={"name": "Hierarchy Exhibit", "content": "ORIGINAL"},
        )
        assert evidence.status_code == 200, evidence.text
        evidence_id = evidence.json()["id"]

        assert client.post(
            f"/api/v1/evidence/{evidence_id}/transfer",
            headers=officer,
            json={"simulate_tamper": False},
        ).status_code == 403

        review = client.post(
            f"/api/v1/evidence/{evidence_id}/review",
            headers=officer,
            json={"decision": "APPROVE", "notes": "Intake approved"},
        )
        assert review.status_code == 200, review.text

        transfer = client.post(
            f"/api/v1/evidence/{evidence_id}/transfer",
            headers=analyst,
            json={"simulate_tamper": False},
        )
        assert transfer.status_code == 200, transfer.text

        edit_attempt = client.post(
            f"/api/v1/evidence/{evidence_id}/edit",
            headers=analyst,
            json={"new_content": "ALTERED", "edit_reason": "unauthorized test edit"},
        )
        assert edit_attempt.status_code == 409

        copy_attempt = client.post(f"/api/v1/evidence/{evidence_id}/copy-attempt", headers=analyst)
        assert copy_attempt.status_code == 200, copy_attempt.text

        admin_dashboard = client.get("/api/v1/dashboard", headers=admin)
        assert admin_dashboard.status_code == 200
        alerts = admin_dashboard.json()["security_alerts"]
        assert any(alert["action"] == "UNAUTHORIZED_EDIT_ATTEMPT" and alert["evidence_id"] == evidence_id for alert in alerts)
        assert any(alert["action"] == "EVIDENCE_COPY_ATTEMPT" and alert["evidence_id"] == evidence_id for alert in alerts)

        assignments = client.get(f"/api/v1/cases/{case_id}/assignments", headers=auditor)
        assert assignments.status_code == 200
        assert any(a["stage"] == "FORENSIC_ANALYST" and a["status"] == "ACTIVE" for a in assignments.json())
        assert auditor_user["role"] == "AUDITOR"
        assert analyst_user["role"] == "FORENSIC_ANALYST"
