from pathlib import Path
import re, sys

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "frontend" / "app.js"
EXPECTED = {"auth","dashboard","cases","evidence","artifacts","verification","audit","reports","provenance"}

def test_frontend_api_families_exist():
    text = APP_JS.read_text(encoding="utf-8")
    refs = set(re.findall(r"/api/v1/[A-Za-z0-9_.?=&/${}-]+", text))
    for ref in refs:
        family = ref.split("/api/v1/", 1)[1].split("/", 1)[0].split("?", 1)[0]
        assert family in EXPECTED, ref
    sys.path.insert(0, str(ROOT / "backend"))
    from app.main import app
    routes = {r.path for r in app.routes if hasattr(r, "path")}
    for family in EXPECTED:
        assert any(path == f"/api/v1/{family}" or path.startswith(f"/api/v1/{family}/") for path in routes), family
