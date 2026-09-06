import os
from pathlib import Path

TEST_DB = Path(__file__).resolve().parents[1] / "storage" / "custodychain_test_suite.db"
try:
    TEST_DB.unlink()
except FileNotFoundError:
    pass
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB.as_posix()}")
os.environ.setdefault("STORAGE_PROVIDER", "local")
os.environ.setdefault("JWT_SECRET", "test-secret-for-custodychain-suite-2026")
