from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    original_content = Column(Text, nullable=False)
    original_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Handler(Base):
    __tablename__ = "handlers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    step_order = Column(Integer, nullable=False)


class CustodyLog(Base):
    __tablename__ = "custody_log"

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False)
    handler_id = Column(Integer, ForeignKey("handlers.id"), nullable=False)
    hash_before = Column(String(64), nullable=False)
    hash_after = Column(String(64), nullable=False)
    actual_content_snapshot = Column(Text, nullable=False)
    status_declared = Column(String(20), default="success")
    timestamp = Column(DateTime, server_default=func.now())


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False)
    final_verdict = Column(String(50), nullable=False)
    broken_step_id = Column(Integer, ForeignKey("handlers.id"), nullable=True)
    checked_at = Column(DateTime, server_default=func.now())
