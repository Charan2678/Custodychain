import urllib.request
import json

def test_api():
    base = 'http://127.0.0.1:8000'
    print("Testing API v1 endpoints...")

    # 1. Ingest Evidence via v1
    req_data = json.dumps({
        'name': 'API-Automated-Exhibit-01',
        'content': 'EVIDENCE_DATA_PAYLOAD_TEST',
        'case_id': 1,
        'simulate_tamper': True,
        'tamper_step': 3
    }).encode()
    req = urllib.request.Request(f'{base}/api/v1/evidence', data=req_data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as res:
        ev = json.loads(res.read().decode())
        evidence_id = ev['evidence_id']
        print(f"1. Ingestion OK: Evidence ID = {evidence_id}, Exhibit ID = {ev.get('exhibit_id')}")

    # 2. Run Verification via v1
    req = urllib.request.Request(f'{base}/api/v1/verification/{evidence_id}', data=b'', headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as res:
        ver = json.loads(res.read().decode())
        print(f"2. Verification OK: Verdict = {ver['final_verdict']}")
        assert 'STEP_3_EXPORT_TOOL' in ver['final_verdict']
        assert ver['steps'][2]['verified'] is False
        assert ver['steps'][3]['downstream_of_break'] is True

    # 3. Fetch Court PDF
    with urllib.request.urlopen(f'{base}/api/v1/reports/{evidence_id}/pdf') as res:
        pdf_data = res.read()
        print(f"3. Court PDF OK: Size = {len(pdf_data)} bytes; Header = {pdf_data[:4]}")
        assert pdf_data.startswith(b"%PDF")

    # 4. Fetch Audit Trail
    with urllib.request.urlopen(f'{base}/api/v1/audit?limit=5') as res:
        audit = json.loads(res.read().decode())
        print(f"4. Audit Trail OK: Found {len(audit)} events. Latest action = {audit[0]['action']}")

    # 5. Fetch Artifacts
    with urllib.request.urlopen(f'{base}/api/v1/evidence/{evidence_id}/artifacts') as res:
        arts = json.loads(res.read().decode())
        print(f"5. Artifacts OK: Count = {len(arts)} immutable artifacts preserved in storage")

    # 6. Legacy Route Compatibility Check
    with urllib.request.urlopen(f'{base}/history') as res:
        hist = json.loads(res.read().decode())
        print(f"6. Legacy /history OK: {len(hist)} items returned")

    print("\n>>> ALL END-TO-END WORKFLOWS PASSED 100% SUCCESSFULLY! <<<")

if __name__ == "__main__":
    test_api()
