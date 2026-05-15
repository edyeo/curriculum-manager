import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from models import User, Subject, SubjectNode, SubjectEdge
import auth as auth_utils
import file_db, gateway_client
import asyncio

router = APIRouter(prefix="/subjects", tags=["subjects"])


class SubjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


def _subject_to_dict(s: Subject, node_count: int = 0) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "status": s.status,
        "owner_id": s.owner_id,
        "created_at": str(s.created_at),
        "nodes_count": node_count,
    }


@router.get("")
def list_subjects(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    subjects = db.query(Subject).all()
    result = []
    for s in subjects:
        node_count = db.query(SubjectNode).filter(SubjectNode.subject_id == s.id).count()
        result.append(_subject_to_dict(s, node_count))
    return {"subjects": result}


@router.post("")
async def create_subject(
    req: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    subject_id = str(uuid.uuid4())
    subject = Subject(id=subject_id, name=req.name, description=req.description, owner_id=current_user.id)
    db.add(subject)
    db.commit()

    # Snapshot node/edge IDs before generation
    before_node_ids = {n["id"] for n in file_db.read_nodes()}
    before_edge_ids = {e["id"] for e in file_db.read_edges()}

    try:
        await gateway_client.generate_curriculum(req.name, req.description or "")
    except Exception:
        # Generation failed — subject still created, just empty
        db.refresh(subject)
        return _subject_to_dict(subject, 0)

    # Register newly created nodes/edges to this subject
    after_node_ids = {n["id"] for n in file_db.read_nodes()}
    after_edge_ids = {e["id"] for e in file_db.read_edges()}

    for nid in (after_node_ids - before_node_ids):
        db.add(SubjectNode(subject_id=subject_id, node_id=nid))
    for eid in (after_edge_ids - before_edge_ids):
        db.add(SubjectEdge(subject_id=subject_id, edge_id=eid))
    db.commit()

    node_count = db.query(SubjectNode).filter(SubjectNode.subject_id == subject_id).count()
    db.refresh(subject)
    return _subject_to_dict(subject, node_count)


@router.get("/{subject_id}")
def get_subject(
    subject_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    node_count = db.query(SubjectNode).filter(SubjectNode.subject_id == subject_id).count()
    return _subject_to_dict(subject, node_count)


@router.delete("/{subject_id}")
def delete_subject(
    subject_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    db.query(SubjectNode).filter(SubjectNode.subject_id == subject_id).delete()
    db.query(SubjectEdge).filter(SubjectEdge.subject_id == subject_id).delete()
    db.delete(subject)
    db.commit()
    return {"status": "deleted"}
