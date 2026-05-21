import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from models import User, Subject, KGNode, KGEdge
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


def _node_to_dict(n: KGNode, edge_count: int = 0) -> dict:
    return {
        "id": n.id,
        "type": n.type,
        "depth": n.depth,
        "name": n.name,
        "description": n.description or "",
        "metadata": n.node_metadata or {},
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "created_by_trigger": n.created_by_trigger,
        "edge_count": edge_count,
    }


def _edge_to_dict(e: KGEdge) -> dict:
    return {
        "id": e.id,
        "source_id": e.source_id,
        "target_id": e.target_id,
        "relation_type": e.relation_type,
        "logic_basis": e.logic_basis or "",
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "created_by_trigger": e.created_by_trigger,
    }


def _sync_json_to_db(
    subject_id: str,
    before_node_ids: set,
    before_edge_ids: set,
    db: Session,
) -> tuple[int, int]:
    """트리거 실행 후 JSON 파일에서 신규 노드/엣지를 DB로 싱크."""
    nodes_added = 0
    edges_added = 0

    for n in file_db.read_nodes():
        if n["id"] not in before_node_ids:
            db.merge(KGNode(
                id=n["id"],
                subject_id=subject_id,
                type=n.get("type", "Concept"),
                depth=n.get("depth", 1),
                name=n.get("name", ""),
                description=n.get("description"),
                node_metadata=n.get("metadata", {}),
                created_by_trigger=n.get("created_by_trigger"),
            ))
            nodes_added += 1

    for e in file_db.read_edges():
        eid = e.get("id") or f"{e.get('source_id')}:{e.get('target_id')}:{e.get('relation_type')}"
        if eid not in before_edge_ids:
            db.merge(KGEdge(
                id=eid,
                subject_id=subject_id,
                source_id=e.get("source_id", ""),
                target_id=e.get("target_id", ""),
                relation_type=e.get("relation_type", ""),
                logic_basis=e.get("logic_basis"),
                created_by_trigger=e.get("created_by_trigger"),
            ))
            edges_added += 1

    db.commit()
    return nodes_added, edges_added


# ── Nodes ──────────────────────────────────────────────────────────────────

@router.get("/nodes")
def list_nodes(
    subject_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_subject_or_404(subject_id, db)
    nodes = db.query(KGNode).filter(KGNode.subject_id == subject_id).all()
    node_ids = {n.id for n in nodes}

    edge_counts: dict[str, int] = {}
    for e in db.query(KGEdge).filter(KGEdge.subject_id == subject_id).all():
        if e.source_id in node_ids:
            edge_counts[e.source_id] = edge_counts.get(e.source_id, 0) + 1
        if e.target_id in node_ids:
            edge_counts[e.target_id] = edge_counts.get(e.target_id, 0) + 1

    return {"nodes": [_node_to_dict(n, edge_counts.get(n.id, 0)) for n in nodes]}


@router.post("/nodes")
def create_node(
    subject_id: str,
    req: NodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_subject_or_404(subject_id, db)
    node_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    node = KGNode(
        id=node_id,
        subject_id=subject_id,
        type=req.type,
        depth=req.depth,
        name=req.name,
        description=req.description,
        node_metadata={},
        created_by_trigger="manual",
    )
    db.add(node)
    db.commit()
    db.refresh(node)

    # Write-back to JSON so agents see the new node on next load
    json_nodes = file_db.read_nodes()
    json_nodes.append({
        "id": node_id, "type": req.type, "depth": req.depth,
        "name": req.name, "description": req.description or "",
        "metadata": {}, "created_at": now.isoformat(), "created_by_trigger": "manual",
    })
    file_db.write_nodes(json_nodes)

    return _node_to_dict(node)


@router.patch("/nodes/{node_id}")
def update_node(
    subject_id: str,
    node_id: str,
    req: NodePatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_subject_or_404(subject_id, db)
    node = db.query(KGNode).filter(KGNode.id == node_id, KGNode.subject_id == subject_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found in this subject")

    if req.name is not None:
        node.name = req.name
    if req.description is not None:
        node.description = req.description
    db.commit()
    db.refresh(node)

    # Sync update to JSON
    json_nodes = file_db.read_nodes()
    for n in json_nodes:
        if n["id"] == node_id:
            if req.name is not None:
                n["name"] = req.name
            if req.description is not None:
                n["description"] = req.description
    file_db.write_nodes(json_nodes)

    return _node_to_dict(node)


@router.delete("/nodes/{node_id}")
def delete_node(
    subject_id: str,
    node_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_subject_or_404(subject_id, db)
    node = db.query(KGNode).filter(KGNode.id == node_id, KGNode.subject_id == subject_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found in this subject")

    db.delete(node)
    db.commit()
    file_db.write_nodes([n for n in file_db.read_nodes() if n["id"] != node_id])
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
    edges = db.query(KGEdge).filter(KGEdge.subject_id == subject_id).all()
    return {"edges": [_edge_to_dict(e) for e in edges]}


@router.post("/edges")
def create_edge(
    subject_id: str,
    req: EdgeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_subject_or_404(subject_id, db)
    edge_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    edge = KGEdge(
        id=edge_id,
        subject_id=subject_id,
        source_id=req.source_id,
        target_id=req.target_id,
        relation_type=req.relation_type,
        logic_basis=req.logic_basis,
        created_by_trigger="manual",
    )
    db.add(edge)
    db.commit()
    db.refresh(edge)

    json_edges = file_db.read_edges()
    json_edges.append({
        "id": edge_id, "source_id": req.source_id, "target_id": req.target_id,
        "relation_type": req.relation_type, "logic_basis": req.logic_basis or "",
        "created_at": now.isoformat(), "created_by_trigger": "manual",
    })
    file_db.write_edges(json_edges)

    return _edge_to_dict(edge)


@router.delete("/edges/{edge_id}")
def delete_edge(
    subject_id: str,
    edge_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_subject_or_404(subject_id, db)
    edge = db.query(KGEdge).filter(KGEdge.id == edge_id, KGEdge.subject_id == subject_id).first()
    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found in this subject")

    db.delete(edge)
    db.commit()
    file_db.write_edges([e for e in file_db.read_edges() if e.get("id") != edge_id])
    return {"status": "deleted"}


# ── AI Generate (Draft) ─────────────────────────────────────────────────────

@router.post("/curriculum/generate")
async def generate_draft(
    subject_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    subject = _get_subject_or_404(subject_id, db)
    before_node_ids = {n.id for n in db.query(KGNode).filter(KGNode.subject_id == subject_id).all()}
    before_edge_ids = {e.id for e in db.query(KGEdge).filter(KGEdge.subject_id == subject_id).all()}

    await gateway_client.generate_curriculum(subject.name, subject.description or "")

    nodes_added, edges_added = _sync_json_to_db(subject_id, before_node_ids, before_edge_ids, db)
    return {"status": "generated", "nodes_added": nodes_added, "edges_added": edges_added}


# ── AI Link ─────────────────────────────────────────────────────────────────

class AiLinkRequest(BaseModel):
    source_type: Optional[str] = None
    source_depth: Optional[int] = None
    source_node_id: Optional[str] = None
    target_type: Optional[str] = None
    target_depth: Optional[int] = None
    edge_type: Optional[str] = None


@router.post("/curriculum/link-ai")
async def link_ai(
    subject_id: str,
    req: AiLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_subject_or_404(subject_id, db)
    before_node_ids = {n.id for n in db.query(KGNode).filter(KGNode.subject_id == subject_id).all()}
    before_edge_ids = {e.id for e in db.query(KGEdge).filter(KGEdge.subject_id == subject_id).all()}

    await gateway_client.link_ai_curriculum(req.model_dump(exclude_none=True))

    _, edges_added = _sync_json_to_db(subject_id, before_node_ids, before_edge_ids, db)
    return {"status": "success", "edges_added": edges_added}


@router.post("/curriculum/link-ai/preview")
async def link_ai_preview(
    subject_id: str,
    req: AiLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_subject_or_404(subject_id, db)
    result = await gateway_client.preview_ai_link(req.model_dump(exclude_none=True))
    return result


class AiLinkConfirmRequest(BaseModel):
    edges: list[dict]


@router.post("/curriculum/link-ai/confirm")
async def link_ai_confirm(
    subject_id: str,
    req: AiLinkConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_subject_or_404(subject_id, db)
    existing_ids = {e.id for e in db.query(KGEdge).filter(KGEdge.subject_id == subject_id).all()}
    new_edges = [e for e in req.edges if e.get("id") not in existing_ids]

    json_edges = file_db.read_edges()
    for e in new_edges:
        eid = e.get("id") or f"{e.get('source_id')}:{e.get('target_id')}:{e.get('relation_type')}"
        db.merge(KGEdge(
            id=eid,
            subject_id=subject_id,
            source_id=e.get("source_id", ""),
            target_id=e.get("target_id", ""),
            relation_type=e.get("relation_type", ""),
            logic_basis=e.get("logic_basis"),
            created_by_trigger=e.get("created_by_trigger"),
        ))
        if not any(j.get("id") == eid for j in json_edges):
            json_edges.append({**e, "id": eid})

    if new_edges:
        file_db.write_edges(json_edges)
        db.commit()

    return {"edges_saved": len(new_edges)}


# ── AI Expand ───────────────────────────────────────────────────────────────

@router.post("/curriculum/expand")
async def expand(
    subject_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_subject_or_404(subject_id, db)
    before_node_ids = {n.id for n in db.query(KGNode).filter(KGNode.subject_id == subject_id).all()}
    before_edge_ids = {e.id for e in db.query(KGEdge).filter(KGEdge.subject_id == subject_id).all()}

    result = await gateway_client.expand_curriculum()

    nodes_added, edges_added = _sync_json_to_db(subject_id, before_node_ids, before_edge_ids, db)
    return {**(result or {}), "nodes_added": nodes_added, "edges_added": edges_added}
