from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=(ROOT/"frontend/app.js").read_text(encoding="utf-8")

def test_frontend_references_declared_backend_route_families():
    refs=set(re.findall(r"/api/v1/[A-Za-z0-9_.?=&/${}-]+", FRONTEND))
    families={"auth","dashboard","cases","evidence","artifacts","verification","audit","reports","provenance"}
    for ref in refs:
        cleaned=ref.split("?")[0].split("/")
        assert len(cleaned) >= 4
        assert cleaned[3] in families, ref

