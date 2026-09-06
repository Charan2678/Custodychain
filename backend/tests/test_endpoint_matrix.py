import io
import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.infrastructure.database.session import Base, engine
from app.models.verification_run import VerificationRun


def login(client, email):
    r = client.post('/api/v1/auth/login', json={
        'email': email,
        'password': 'evidence123',
    })
    assert r.status_code == 200, r.text
    return {'Authorization': f"Bearer {r.json()['access_token']}"}


def test_runtime_endpoint_matrix_and_read_only_gets():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as client:
        officer = login(client, 'officer@custodychain.internal')
        analyst = login(client, 'analyst@custodychain.internal')
        auditor = login(client, 'auditor@custodychain.internal')
        admin = login(client, 'charan@custodychain.internal')

        # Core discovery endpoints.
        assert client.get('/health').status_code == 200
        assert client.get('/').status_code == 200
        assert client.get('/docs').status_code == 200

        # Case creation and membership/access.
        case = client.post('/api/v1/cases', headers=officer, json={
            'case_number': 'CASE-MATRIX-' + uuid.uuid4().hex[:10],
            'title': 'Endpoint Matrix Case',
            'description': 'Runtime integration test',
        })
        assert case.status_code == 200, case.text
        case_id = case.json()['id']

        for h in (officer, analyst, auditor, admin):
            assert client.get(f'/api/v1/cases/{case_id}', headers=h).status_code == 200

        # Upload multipart endpoint.
        upload = client.post(
            '/api/v1/evidence/upload',
            headers=officer,
            files={'file': ('matrix.txt', io.BytesIO(b'MATRIX_UPLOAD_BYTES'), 'text/plain')},
            data={'case_id': case_id, 'name': 'Matrix Upload', 'description': 'upload test'},
        )
        assert upload.status_code == 200, upload.text
        evidence_id = upload.json()['evidence_id']

        # Evidence discovery/details/review/artifacts.
        assert client.get('/api/v1/evidence', headers=analyst).status_code == 200
        detail = client.get(f'/api/v1/evidence/{evidence_id}', headers=auditor)
        assert detail.status_code == 200, detail.text
        review = client.get(f'/api/v1/evidence/{evidence_id}/review', headers=auditor)
        assert review.status_code == 200, review.text
        artifact_id = review.json()['artifact']['id']

        art = client.get(f'/api/v1/artifacts/{artifact_id}', headers=auditor)
        assert art.status_code == 200, art.text
        preview = client.get(f'/api/v1/artifacts/{artifact_id}/preview', headers=auditor)
        assert preview.status_code == 200, preview.text
        download = client.get(f'/api/v1/artifacts/{artifact_id}/download', headers=auditor)
        assert download.status_code == 200, download.text
        assert download.content == b'MATRIX_UPLOAD_BYTES'
        assert download.headers.get('X-SHA256-Checksum')

        # Provenance is available to case members.
        prov = client.get(f'/api/v1/provenance/{evidence_id}', headers=analyst)
        assert prov.status_code == 200, prov.text
        assert 'nodes' in prov.json() and 'edges' in prov.json()

        # Review -> approval -> transfer. Auditor remains read-only.
        assert client.post(f'/api/v1/evidence/{evidence_id}/review', headers=auditor,
                           json={'decision': 'APPROVE', 'notes': 'auditor read-only check'}).status_code == 403
        assert client.post(f'/api/v1/evidence/{evidence_id}/transfer', headers=analyst,
                           json={'simulate_tamper': False}).status_code == 409
        approved = client.post(f'/api/v1/evidence/{evidence_id}/review', headers=officer,
                               json={'decision': 'APPROVE', 'notes': 'approved for laboratory handover'})
        assert approved.status_code == 200, approved.text
        transferred = client.post(f'/api/v1/evidence/{evidence_id}/transfer', headers=analyst,
                                  json={'simulate_tamper': False})
        assert transferred.status_code == 200, transferred.text

        # File intake performs an initial verification; an explicit Verify action creates another authoritative run.
        from app.infrastructure.database.session import SessionLocal
        db = SessionLocal()
        try:
            count_before_post = db.query(VerificationRun).filter(VerificationRun.evidence_id == uuid.UUID(evidence_id)).count()
        finally:
            db.close()
        assert count_before_post == 1

        ver = client.post(f'/api/v1/verification/{evidence_id}', headers=auditor)
        assert ver.status_code == 200, ver.text
        ver_data = ver.json()
        run_id = ver_data['verification_id']
        assert ver_data['status'] == 'COMPLETED'

        # GET is read-only and returns the same persisted snapshot.
        get_ver = client.get(f'/api/v1/verification/{evidence_id}', headers=analyst)
        assert get_ver.status_code == 200, get_ver.text
        assert get_ver.json()['verification_id'] == run_id

        # Confirm GET didn't create another run.
        db = SessionLocal()
        try:
            count_before_ai = db.query(VerificationRun).filter(VerificationRun.evidence_id == uuid.UUID(evidence_id)).count()
        finally:
            db.close()
        assert count_before_ai == 2

        # AI explain endpoint is connected; deterministic fallback is acceptable without key.
        ai = client.post(f'/api/v1/verification/{evidence_id}/explain', headers=auditor)
        assert ai.status_code == 200, ai.text
        assert ai.json()['evidence_id'] == evidence_id

        db = SessionLocal()
        try:
            count_after_ai = db.query(VerificationRun).filter(VerificationRun.evidence_id == uuid.UUID(evidence_id)).count()
        finally:
            db.close()
        assert count_after_ai == count_before_ai

        # PDF report is connected to the persisted verification snapshot.
        pdf = client.get(f'/api/v1/reports/{evidence_id}/pdf', headers=auditor)
        assert pdf.status_code == 200, pdf.text
        assert pdf.headers['content-type'].startswith('application/pdf')
        assert pdf.content[:4] == b'%PDF'

        # Audit endpoints and RBAC.
        assert client.get('/api/v1/audit', headers=officer).status_code == 403
        assert client.get('/api/v1/audit/verify', headers=analyst).status_code == 403
        audit_list = client.get('/api/v1/audit?limit=100', headers=auditor)
        assert audit_list.status_code == 200, audit_list.text
        audit_verify = client.get('/api/v1/audit/verify', headers=auditor)
        assert audit_verify.status_code == 200, audit_verify.text
        assert audit_verify.json()['valid'] is True, audit_verify.text
