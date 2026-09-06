import os
import socket
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

logger = logging.getLogger("custodychain.database")

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Base(DeclarativeBase):
    pass


def _is_pg_available(host: str = "localhost", port: int = 5432, timeout: float = 1.0) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except Exception:
        return False


def get_engine():
    db_url = settings.database_url
    connect_args = {}

    if db_url.startswith("postgresql"):
        # Check if local postgres port is accessible
        if "localhost" in db_url or "127.0.0.1" in db_url:
            if not _is_pg_available("127.0.0.1", 5432):
                fallback_db_path = os.path.join(BACKEND_ROOT, "storage", "custodychain.db")
                os.makedirs(os.path.dirname(fallback_db_path), exist_ok=True)
                db_url = f"sqlite:///{fallback_db_path}"
                logger.warning(
                    f"PostgreSQL at localhost:5432 is not running. Resiliently falling back to: {db_url}"
                )

    if db_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    return create_engine(
        db_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


engine = get_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
