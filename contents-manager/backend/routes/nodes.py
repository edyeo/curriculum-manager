import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from models import User, Subject, SubjectNode, SubjectEdge
import auth as auth_utils, file_db, gateway_client

router = APIRouter(prefix="/subjects/{subject_id}", tags=["nodes"])


class NodeCreate(BaseModel):
    name: str
    type: str  # Seed | Concept | TechStack
    depth: int
    description: Optional[str] = ""


class NodePatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


def _get_subject_or_404(subject_id: str, db: Session) -> Subject:
    s = db.query(Subject).filter(Subject.id == subject_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Subject not found")
    return s


def _owned_node_ids(subject_id: str, db: Session) -> set[str]:
    return {r.node_id for r in db.query(SubjectNode).filter(SubjectNode.subject_id == subject_id).all()}


def _owned_edge_ids(subject_id: str, db: Session) -> set[str]:
    return {r.edge_id for r in db.query(SubjectEdge).filter(SubjectEdge.subject_id == subject_id).all()}


# ── Nodes ──────────────────────────────────────────────────────────────────

@router.get("/nodes")
def list_nodes(
    subject_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_subject_or_404(subject_id, db)
    owned = _owned_node_ids(subject_id, db)
    nodes = [n for n in file_db.read_nodes() if n["id"] in owned]

    # Attach edge/question counts (edges only for now)
    all_edges = file_db.read_edges()
    owned_edges = _owned_edge_ids(subject_id, db)

    def edge_count(node_id: str) -> int:
        return sum(1 for e in all_edges if e["id"] in owned_edges and
                   (e.get("source_id") == node_id or e.get("target_id") == node_id))

    return {"nodes": [{**n, "edge_count": edge_count(n["id"])} for n in nodes]}


@router.post("/nodes")
def create_node(
    subject_id: str,
    req: NodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_subject_or_404(subject_id, db)
    node_id = str(uuid.uuid4())
    node = {
        "id": node_id,
        "type": req.type,
        "name": req.name,
        "description": req.description,
        "depth": req.depth,
        "metadata": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by_trigger": "manual",
    }
    nodes = file_db.read_nodes()
    nodes.append(node)
    file_db.write_nodes(nodes)
    db.add(SubjectNode(subject_id=subject_id, node_id=node_id))
    db.commit()
    return node


@router.patch("/nodes/{node_id}")
def update_node(
    subject_id: str,
    node_id: str,
    req: NodePatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_subject_or_404(subject_id, db)
    owned = _owned_node_ids(subject_id, db)
    if node_id not in owned:
        raise HTTPException(status_code=404, detail="Node not found in this subject")

    nodes = file_db.read_nodes()
    for n in nodes:
        if n["id"] == node_id:
            if req.name is not None:
                n["name"] = req.name
            if req.description is not None:
                n["description"] = req.description
            file_db.write_nodes(nodes)
            return n
    raise HTTPException(status_code=404, detail="Node not found")


@router.delete("/nodes/{node_id}")
def delete_node(
    subject_id: str,
    node_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_subject_or_404(subject_id, db)
    owned = _owned_node_ids(subject_id, db)
    if node_id not in owned:
        raise HTTPException(status_code=404, detail="Node not found in this subject")

    nodes = file_db.read_nodes()
    file_db.write_nodes([n for n in nodes if n["id"] != node_id])
    db.query(SubjectNode).filter(
        SubjectNode.subject_id == subject_id, SubjectNode.node_id == node_id
    ).delete()
    db.commit()
    return {"status": "deleted"}


# ── Edges ──────────────────────────────────────────────────────────────────

class EdgeCreate(BaseModel):
    source_id: str
    target_id: str
    relation_type: str
    logic_basis: Optional[str] = ""


@router.get("/edges")
def list_edges(
    subject_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_subject_or_404(subject_id, db)
    owned = _owned_edge_ids(subject_id, db)
    edges = [e for e in file_db.read_edges() if e["id"] in owned]
    return {"edges": edges}


@router.post("/edges")
def create_edge(
    subject_id: str,
    req: EdgeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_subject_or_404(subject_id, db)
    edge_id = str(uuid.uuid4())
    edge = {
        "id": edge_id,
        "source_id": req.source_id,
        "target_id": req.target_id,
        "relation_type": req.relation_type,
        "logic_basis": req.logic_basis,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by_trigger": "manual",
    }
    edges = file_db.read_edges()
    edges.append(edge)
    file_db.write_edges(edges)
    db.add(SubjectEdge(subject_id=subject_id, edge_id=edge_id))
    db.commit()
    return edge


@router.delete("/edges/{edge_id}")
def delete_edge(
    subject_id: str,
    edge_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_subject_or_404(subject_id, db)
    owned = _owned_edge_ids(subject_id, db)
    if edge_id not in owned:
        raise HTTPException(status_code=404, detail="Edge not found in this subject")

    edges = file_db.read_edges()
    file_db.write_edges([e for e in edges if e["id"] != edge_id])
    db.query(SubjectEdge).filter(
        SubjectEdge.subject_id == subject_id, SubjectEdge.edge_id == edge_id
    ).delete()
    db.commit()
    return {"status": "deleted"}


# ── AI Expand ───────────────────────────────────────────────────────────────

@router.post("/curriculum/expand")
async def expand(
    subject_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_subject_or_404(subject_id, db)
    before_node_ids = {n["id"] for n in file_db.read_nodes()}
    before_edge_ids = {e["id"] for e in file_db.read_edges()}

    result = await gateway_client.expand_curriculum()

    for nid in ({n["id"] for n in file_db.read_nodes()} - before_node_ids):
        db.add(SubjectNode(subject_id=subject_id, node_id=nid))
    for eid in ({e["id"] for e in file_db.read_edges()} - before_edge_ids):
        db.add(SubjectEdge(subject_id=subject_id, edge_id=eid))
    db.commit()
    return result
