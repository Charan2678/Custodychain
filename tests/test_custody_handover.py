import json
import urllib.request
import urllib.error
import pytest

BASE = "http://127.0.0.1:8000"


def get_auth_headers(email: str, password: str = "evidence123") -> dict:
    login_data = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(f"{BASE}/api/v1/auth/login", data=login_data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode())
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {data['access_token']}"
        }


def test_step_by_step_custody_handover_and_role_hierarchy():
    officer_headers = get_auth_headers("officer@custodychain.internal")
    analyst_headers = get_auth_headers("analyst@custodychain.internal")
    auditor_headers = get_auth_headers("auditor@custodychain.internal")

    # 1. Evidence Officer registers new exhibit (Step 1 Intake)
    ingest_payload = json.dumps({
        "name": "Exhibit-iPhone14-Forensic-Extraction",
        "content": "RAW_PHYSICAL_EXTRACTION_FORENSIC_STREAM_001",
        "case_id": 1,
        "step_by_step": True,
        "simulate_tamper": False
    }).encode()
    req = urllib.request.Request(f"{BASE}/api/v1/evidence", data=ingest_payload, headers=officer_headers)
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode())
        assert res.status == 200
        ev_id = data["evidence_id"]
        assert data["final_verdict"] == "CHAIN_INTACT", "Exhibit intake must start clean and INTACT, not broken"
        assert len(data["steps"]) == 1, "Initial intake must be Step 1 (Collector) only"
        assert data["steps"][0]["handler_name"] == "Collector"

    # 2. Evidence Officer transfers custody to Forensic Analyst (Step 1 -> 2)
    transfer1_payload = json.dumps({"simulate_tamper": False}).encode()
    req = urllib.request.Request(f"{BASE}/api/v1/evidence/{ev_id}/transfer", data=transfer1_payload, headers=officer_headers)
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode())
        assert res.status == 200
        assert data["final_verdict"] == "CHAIN_INTACT"
        assert len(data["steps"]) == 2
        assert data["steps"][1]["handler_name"] == "Analyst Tool"

    # 3. Evidence Officer tries to execute Step 3 (Lab analysis) -> Must be blocked with 403
    transfer2_payload = json.dumps({"simulate_tamper": False}).encode()
    req = urllib.request.Request(f"{BASE}/api/v1/evidence/{ev_id}/transfer", data=transfer2_payload, headers=officer_headers)
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req)
    assert exc_info.value.code == 403
    err_body = json.loads(exc_info.value.read().decode())
    assert "Forensic Analysts" in err_body["detail"]

    # 4. Auditor tries to execute Step 3 -> Must be blocked with 403 (Read-only clearance)
    req = urllib.request.Request(f"{BASE}/api/v1/evidence/{ev_id}/transfer", data=transfer2_payload, headers=auditor_headers)
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req)
    assert exc_info.value.code == 403
    err_body = json.loads(exc_info.value.read().decode())
    assert "Auditor" in err_body["detail"] or "compliance" in err_body["detail"]

    # 5. Forensic Analyst executes Step 3 (Laboratory processing & export)
    req = urllib.request.Request(f"{BASE}/api/v1/evidence/{ev_id}/transfer", data=transfer2_payload, headers=analyst_headers)
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode())
        assert res.status == 200
        assert data["final_verdict"] == "CHAIN_INTACT"
        assert len(data["steps"]) == 3
        assert data["steps"][2]["handler_name"] == "Export Tool"

    # 6. Forensic Analyst transfers to Legal Review (Step 3 -> 4)
    transfer3_payload = json.dumps({"simulate_tamper": False}).encode()
    req = urllib.request.Request(f"{BASE}/api/v1/evidence/{ev_id}/transfer", data=transfer3_payload, headers=analyst_headers)
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode())
        assert res.status == 200
        assert data["final_verdict"] == "CHAIN_INTACT"
        assert len(data["steps"]) == 4
        assert data["steps"][3]["handler_name"] == "Reviewer"

    # 7. Forensic Analyst seals into Archive Vault (Step 4 -> 5)
    transfer4_payload = json.dumps({"simulate_tamper": False}).encode()
    req = urllib.request.Request(f"{BASE}/api/v1/evidence/{ev_id}/transfer", data=transfer4_payload, headers=analyst_headers)
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode())
        assert res.status == 200
        assert data["final_verdict"] == "CHAIN_INTACT"
        assert len(data["steps"]) == 5
        assert data["steps"][4]["handler_name"] == "Archive"

    # 8. Exhibit has reached final archive custody; further transfers must return 400
    req = urllib.request.Request(f"{BASE}/api/v1/evidence/{ev_id}/transfer", data=transfer4_payload, headers=analyst_headers)
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req)
    assert exc_info.value.code == 400
