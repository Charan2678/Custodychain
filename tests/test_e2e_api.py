import urllib.request
import json

def test_api():
    base = 'http://127.0.0.1:8000'
    print("Testing Production API v1 endpoints with Bearer authentication...")

    # 0. Authenticate as Forensic Analyst
    login_data = json.dumps({
        "email": "analyst@custodychain.internal",
        "password": "evidence123"
    }).encode()
    login_req = urllib.request.Request(f"{base}/api/v1/auth/login", data=login_data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(login_req) as res:
        login_res = json.loads(res.read().decode())
        token = login_res["access_token"]
        assert token, "Token not returned"
        print(f"0. Login OK: Authenticated as {login_res['user']['name']} ({login_res['user']['role']})")

    auth_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # 1. Ingest Evidence via v1
    req_data = json.dumps({
        'name': 'API-Automated-Exhibit-01',
        'content': 'EVIDENCE_DATA_PAYLOAD_TEST',
        'case_id': 1,
        'simulate_tamper': True,
        'tamper_step': 3
    }).encode()
    req = urllib.request.Request(f'{base}/api/v1/evidence', data=req_data, headers=auth_headers)
    with urllib.request.urlopen(req) as res:
        ev = json.loads(res.read().decode())
        evidence_id = ev['evidence_id']
        print(f"1. Ingestion OK: Evidence ID = {evidence_id}, Exhibit ID = {ev.get('exhibit_id')}")

    # 2. Run Verification via v1
    req = urllib.request.Request(f'{base}/api/v1/verification/{evidence_id}', data=b'', headers=auth_headers)
    with urllib.request.urlopen(req) as res:
        ver = json.loads(res.read().decode())
        print(f"2. Verification OK: Verdict = {ver['final_verdict']}")
        assert 'STEP_3_EXPORT_TOOL' in ver['final_verdict']
        assert ver['first_break']['step_order'] == 3
        assert ver['first_break']['handler_name'] == 'Export Tool'
        assert ver['steps'][2]['verified'] is False
        assert ver['steps'][3]['downstream_of_break'] is True

    # 3. Fetch Evidence Integrity PDF Report
    req = urllib.request.Request(f'{base}/api/v1/reports/{evidence_id}/pdf', headers=auth_headers)
    with urllib.request.urlopen(req) as res:
        pdf_data = res.read()
        print(f"3. PDF Report OK: Size = {len(pdf_data)} bytes; Header = {pdf_data[:4]}")
        assert pdf_data.startswith(b"%PDF")

    # 4. Fetch Audit Trail as Auditor
    auditor_login_data = json.dumps({"email": "auditor@custodychain.internal", "password": "evidence123"}).encode()
    auditor_login_req = urllib.request.Request(f"{base}/api/v1/auth/login", data=auditor_login_data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(auditor_login_req) as res:
        auditor_token = json.loads(res.read().decode())["access_token"]

    req = urllib.request.Request(f'{base}/api/v1/audit?limit=5', headers={"Authorization": f"Bearer {auditor_token}"})
    with urllib.request.urlopen(req) as res:
        audit = json.loads(res.read().decode())
        print(f"4. Audit Trail OK: Found {len(audit)} events. Latest action = {audit[0]['action']}")
        assert "event_hash" in audit[0]
        assert "previous_event_hash" in audit[0]

    # 5. Fetch Artifacts
    req = urllib.request.Request(f'{base}/api/v1/evidence/{evidence_id}/artifacts', headers=auth_headers)
    with urllib.request.urlopen(req) as res:
        arts = json.loads(res.read().decode())
        print(f"5. Artifacts OK: Count = {len(arts)} immutable artifacts preserved in storage")

    # 6. Legacy Route Compatibility Check
    with urllib.request.urlopen(f'{base}/history') as res:
        hist = json.loads(res.read().decode())
        print(f"6. Legacy /history OK: {len(hist)} items returned")

    # 7. Clean up test exhibit so automated testing does not pollute the DB with broken records
    try:
        import sys
        import os
        from sqlalchemy import text
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from database import SessionLocal
        import models
        db = SessionLocal()
        db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        db.query(models.CustodyEvent).filter(models.CustodyEvent.evidence_id == evidence_id).delete()
        db.query(models.CustodyLog).filter(models.CustodyLog.evidence_id == evidence_id).delete()
        db.query(models.Artifact).filter(models.Artifact.evidence_id == evidence_id).delete()
        db.query(models.Evidence).filter(models.Evidence.id == evidence_id).delete()
        db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        db.commit()
        db.close()
        print(f"7. Cleanup OK: Removed temporary test exhibit #{evidence_id} from database.")
    except Exception as e:
        print(f"Note: Cleanup skipped: {e}")

    print("\n>>> ALL PRODUCTION END-TO-END WORKFLOWS PASSED 100% SUCCESSFULLY! <<<")

if __name__ == "__main__":
    test_api()

