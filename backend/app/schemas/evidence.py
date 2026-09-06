from typing import Optional, List
from pydantic import BaseModel


class CaseCreateRequest(BaseModel):
    case_number: str
    title: str
    description: Optional[str] = None
    evidence_officer_id: Optional[str] = None


class CaseAssignmentRequest(BaseModel):
    assignee_id: str
    stage: str


class EvidenceIntakeRequest(BaseModel):
    case_id: str
    name: str
    content: str
    evidence_number: Optional[str] = None
    description: Optional[str] = None


class CaseEvidenceCreateRequest(BaseModel):
    name: str
    content: str
    evidence_number: Optional[str] = None
    description: Optional[str] = None


class SimulationRequest(BaseModel):
    case_id: str
    name: str
    content: str
    tamper_step: int = 0  # 0 for clean, 3 for Exporter silent corruption
