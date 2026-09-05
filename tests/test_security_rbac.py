import pytest
import urllib.request
import urllib.error
import json

BASE_URL = "http://127.0.0.1:8000"


def http_request(url, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            parsed = json.loads(err_body)
        except Exception:
            parsed = err_body
        return e.code, parsed


def login(email, password="evidence123"):
    status, body = http_request(
        f"{BASE_URL}/api/v1/auth/login",
        method="POST",
        data={"email": email, "password": password},
    )
    assert status == 200, f"Login failed for {email}: {body}"
    return body["access_token"]


def test_auth_rejection_without_token():
    """Missing Bearer token must return HTTP 401 Unauthorized."""
    status, body = http_request(f"{BASE_URL}/api/v1/cases", method="POST", data={"case_number": "CASE-FAIL", "title": "Fail"})
    assert status == 401, f"Expected 401, got {status}: {body}"


def test_auth_rejection_with_invalid_token():
    """Invalid token must return HTTP 401 Unauthorized."""
    status, body = http_request(f"{BASE_URL}/api/v1/cases", method="POST", data={"case_number": "CASE-FAIL", "title": "Fail"}, token="fake.invalid.token")
    assert status == 401, f"Expected 401, got {status}: {body}"


def test_role_enforcement_auditor_denied_case_creation():
    """An Auditor must NOT be permitted to create a case (HTTP 403 Forbidden)."""
    auditor_token = login("auditor@custodychain.internal")
    status, body = http_request(
        f"{BASE_URL}/api/v1/cases",
        method="POST",
        data={"case_number": "CASE-AUDITOR-DENIED", "title": "Auditor Attempt"},
        token=auditor_token,
    )
    assert status == 403, f"Expected 403 Forbidden for auditor, got {status}: {body}"


def test_role_enforcement_analyst_denied_audit_log_access():
    """A Forensic Analyst must NOT be permitted to view security audit logs (HTTP 403 Forbidden)."""
    analyst_token = login("analyst@custodychain.internal")
    status, body = http_request(
        f"{BASE_URL}/api/v1/audit",
        method="GET",
        token=analyst_token,
    )
    assert status == 403, f"Expected 403 Forbidden for analyst on audit trail, got {status}: {body}"


def test_role_permission_officer_allowed_case_creation():
    """An Evidence Officer MUST be permitted to create a case."""
    officer_token = login("officer@custodychain.internal")
    case_num = f"CASE-OFFICER-{hash(officer_token) % 10000}"
    status, body = http_request(
        f"{BASE_URL}/api/v1/cases",
        method="POST",
        data={"case_number": case_num, "title": "Officer Lawful Case"},
        token=officer_token,
    )
    assert status == 200, f"Expected 200, got {status}: {body}"
    assert body["case_number"] == case_num


def test_tamper_evident_audit_ledger_verification():
    """Audit ledger verification endpoint must confirm unbroken SHA-256 hash continuity."""
    admin_token = login("charan@custodychain.internal")
    status, body = http_request(
        f"{BASE_URL}/api/v1/audit/verify",
        method="GET",
        token=admin_token,
    )
    assert status == 200, f"Expected 200, got {status}: {body}"
    assert body["valid"] is True, f"Audit ledger compromised: {body}"
    assert body["status"] == "AUDIT_CHAIN_INTACT"


def test_self_role_escalation_endpoint_removed():
    """Self-role escalation /switch-role must be completely inaccessible."""
    admin_token = login("charan@custodychain.internal")
    status, body = http_request(
        f"{BASE_URL}/api/v1/auth/switch-role",
        method="POST",
        data={"role": "SYSTEM_ADMIN"},
        token=admin_token,
    )
    assert status in (404, 405), f"Expected 404/405 for removed switch-role, got {status}: {body}"


if __name__ == "__main__":
    print("Running security & RBAC tests...")
    test_auth_rejection_without_token()
    print("  [PASS] Missing token returns 401 Unauthorized")
    test_auth_rejection_with_invalid_token()
    print("  [PASS] Invalid token returns 401 Unauthorized")
    test_role_enforcement_auditor_denied_case_creation()
    print("  [PASS] Auditor denied case creation (403 Forbidden)")
    test_role_enforcement_analyst_denied_audit_log_access()
    print("  [PASS] Analyst denied audit log inspection (403 Forbidden)")
    test_role_permission_officer_allowed_case_creation()
    print("  [PASS] Evidence Officer allowed case creation (200 OK)")
    test_tamper_evident_audit_ledger_verification()
    print("  [PASS] Tamper-evident audit ledger mathematically verified")
    test_self_role_escalation_endpoint_removed()
    print("  [PASS] Self-role escalation /switch-role is removed")
    print("All 7 Security & RBAC tests passed successfully!")
