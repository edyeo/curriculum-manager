"""KG Read API — service-to-service read-only endpoints for the Knowledge Graph.

Authenticated via X-Service-Token header (not editor JWT).
Consumed by student-platform and any future KG consumers.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Subject, SubjectNode, SubjectEdge
import auth as auth_utils
import file_db
import gateway_client

router = APIRouter(prefix="/kg", tags=["kg"])


def _owned_node_ids(subject_id: str, db: Session) -> set[str]:
    return {r.node_id for r in db.query(SubjectNode).filter(SubjectNode.subject_id == subject_id).all()}


def _owned_edge_ids(subject_id: str, db: Session) -> set[str]:
    return {r.edge_id for r in db.query(SubjectEdge).filter(SubjectEdge.subject_id == subject_id).all()}


# ── Subjects ──────────────────────────────────────────────────────────────────

@router.get("/subjects")
def kg_subjects(
    db: Session = Depends(get_db),
    _=Depends(auth_utils.verify_service_token),
):
    subjects = db.query(Subject).all()
    return {
        "subjects": [
            {"id": s.id, "name": s.name, "description": s.description, "status": s.status}
            for s in subjects
        ]
    }


# ── Nodes ─────────────────────────────────────────────────────────────────────

@router.get("/subjects/{subject_id}/nodes")
def kg_nodes(
    subject_id: str,
    db: Session = Depends(get_db),
    _=Depends(auth_utils.verify_service_token),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    owned = _owned_node_ids(subject_id, db)
    nodes = [
        {
            "id": n["id"],
            "type": n.get("type", ""),
            "name": n.get("name", ""),
            "depth": n.get("depth", 1),
            "description": n.get("description", ""),
        }
        for n in file_db.read_nodes()
        if n["id"] in owned
    ]
    return {"nodes": nodes}


# ── Edges ─────────────────────────────────────────────────────────────────────

@router.get("/subjects/{subject_id}/edges")
def kg_edges(
    subject_id: str,
    db: Session = Depends(get_db),
    _=Depends(auth_utils.verify_service_token),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    owned = _owned_edge_ids(subject_id, db)
    edges = [
        {
            "id": e["id"],
            "source_id": e.get("source_id", ""),
            "target_id": e.get("target_id", ""),
            "relation": e.get("relation_type", ""),
        }
        for e in file_db.read_edges()
        if e["id"] in owned
    ]
    return {"edges": edges}


# ── Questions ─────────────────────────────────────────────────────────────────

@router.get("/nodes/{node_id}/questions")
async def kg_questions(
    node_id: str,
    _=Depends(auth_utils.verify_service_token),
):
    try:
        return await gateway_client.get_questions(node_id)
    except Exception:
        return {"questions": []}
