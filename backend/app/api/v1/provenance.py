import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.models.evidence import Evidence
from app.models.artifact import Artifact
from app.models.custody_event import CustodyEvent
from app.models.provenance import ProvenanceRelation
from app.models.tool import Tool
from app.models.actor import Actor
from app.models.user import User
from app.core.security import get_current_user, assert_evidence_access

router = APIRouter(prefix="/provenance", tags=["Artifact Provenance & Lineage Graph"])


@router.get("/{evidence_id}")
def get_provenance_graph(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        ev_uuid = uuid.UUID(evidence_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Evidence UUID")

    ev = assert_evidence_access(db, current_user, ev_uuid)

    artifacts = db.query(Artifact).filter(Artifact.evidence_id == ev.id).all()
    events = db.query(CustodyEvent).filter(CustodyEvent.evidence_id == ev.id).all()
    relations = (
        db.query(ProvenanceRelation)
        .join(CustodyEvent, ProvenanceRelation.custody_event_id == CustodyEvent.id)
        .filter(CustodyEvent.evidence_id == ev.id)
        .all()
    )

    event_map = {e.id: e for e in events}
    tool_ids = [e.tool_id for e in events if e.tool_id]
    tools = {t.id: t for t in db.query(Tool).filter(Tool.id.in_(tool_ids)).all()} if tool_ids else {}

    nodes = []
    for a in artifacts:
        nodes.append({
            "id": str(a.id),
            "type": "artifact",
            "data": {
                "label": a.artifact_type,
                "sha256": a.sha256,
                "size_bytes": a.size_bytes,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            },
        })

    edges = []
    for rel in relations:
        ev_item = event_map.get(rel.custody_event_id)
        tool_item = tools.get(ev_item.tool_id) if (ev_item and ev_item.tool_id) else None
        edges.append({
            "id": str(rel.id),
            "source": str(rel.parent_artifact_id),
            "target": str(rel.child_artifact_id),
            "label": tool_item.name if tool_item else rel.relationship_type,
            "data": {
                "operation": ev_item.operation if ev_item else None,
                "sequence_number": ev_item.sequence_number if ev_item else None,
            },
        })

    return {
        "evidence_id": str(ev.id),
        "evidence_name": ev.name,
        "nodes": nodes,
        "edges": edges,
    }
