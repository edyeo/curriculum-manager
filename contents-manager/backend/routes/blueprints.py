import uuid, json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from models import User, Blueprint, MatrixCell, IntegrationItem
import auth as auth_utils

router = APIRouter(prefix="/blueprints", tags=["blueprints"])

# EPIC-004 완료 후 ontology.get_entity_names() 호출로 교체 예정
VALID_LAYERS: list[str] = ["System", "Seed", "Concept", "TechStack"]

DEFAULT_LABELS: dict[str, list[str]] = {
    "Seed":       ["인식", "리스크", "통제"],
    "Concept":    ["원리", "매핑", "대안"],
    "TechStack":  ["스펙", "디버깅", "전환"],
}


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_or_404(bp_id: str, db: Session) -> Blueprint:
    bp = db.query(Blueprint).filter(
        Blueprint.id == bp_id, Blueprint.deleted_at.is_(None)
    ).first()
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    return bp


def _seed_matrix(blueprint_id: str, db: Session):
    for layer in VALID_LAYERS:
        for pos, label in enumerate(DEFAULT_LABELS.get(layer, ["기본"])):
            db.add(MatrixCell(
                id=str(uuid.uuid4()),
                blueprint_id=blueprint_id,
                layer=layer,
                label=label,
                position=pos,
            ))


def _build_matrix(blueprint_id: str, db: Session) -> dict:
    cells = (
        db.query(MatrixCell)
        .filter(MatrixCell.blueprint_id == blueprint_id)
        .order_by(MatrixCell.layer, MatrixCell.position)
        .all()
    )
    matrix: dict = {}
    for c in cells:
        matrix.setdefault(c.layer, []).append(
            {"id": c.id, "label": c.label, "position": c.position}
        )
    return matrix


def _build_integrations(blueprint_id: str, db: Session) -> list:
    return [
        {"id": i.id, "name": i.name, "combinations": json.loads(i.combinations)}
        for i in db.query(IntegrationItem).filter(
            IntegrationItem.blueprint_id == blueprint_id
        ).all()
    ]


def _bp_detail(bp: Blueprint, db: Session) -> dict:
    return {
        "id": bp.id,
        "name": bp.name,
        "description": bp.description,
        "created_at": str(bp.created_at),
        "matrix": _build_matrix(bp.id, db),
        "integrations": _build_integrations(bp.id, db),
    }


# ── schemas ───────────────────────────────────────────────────────────────────

class BlueprintCreate(BaseModel):
    name: str
    description: Optional[str] = ""


class BlueprintPatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class CellCreate(BaseModel):
    layer: str
    label: str


class CellPatch(BaseModel):
    label: str


class IntegrationCreate(BaseModel):
    name: str
    combinations: list[dict]


# ── Blueprint CRUD ────────────────────────────────────────────────────────────

@router.get("")
def list_blueprints(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    bps = (
        db.query(Blueprint)
        .filter(Blueprint.deleted_at.is_(None))
        .order_by(Blueprint.created_at.desc())
        .all()
    )
    return {"blueprints": [
        {"id": bp.id, "name": bp.name, "description": bp.description, "created_at": str(bp.created_at)}
        for bp in bps
    ]}


@router.post("", status_code=201)
def create_blueprint(
    req: BlueprintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    bp = Blueprint(
        id=str(uuid.uuid4()),
        name=req.name.strip(),
        description=req.description,
        owner_id=current_user.id,
    )
    db.add(bp)
    _seed_matrix(bp.id, db)
    db.commit()
    db.refresh(bp)
    return _bp_detail(bp, db)


@router.get("/{bp_id}")
def get_blueprint(
    bp_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    return _bp_detail(_get_or_404(bp_id, db), db)


@router.patch("/{bp_id}")
def update_blueprint(
    bp_id: str,
    req: BlueprintPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    bp = _get_or_404(bp_id, db)
    if req.name is not None:
        if not req.name.strip():
            raise HTTPException(status_code=400, detail="Name cannot be empty")
        bp.name = req.name.strip()
    if req.description is not None:
        bp.description = req.description
    db.commit()
    return {"id": bp.id, "name": bp.name, "description": bp.description}


@router.delete("/{bp_id}")
def delete_blueprint(
    bp_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    bp = _get_or_404(bp_id, db)
    bp.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "deleted"}


# ── MatrixCell ────────────────────────────────────────────────────────────────

@router.post("/{bp_id}/cells", status_code=201)
def add_cell(
    bp_id: str,
    req: CellCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_or_404(bp_id, db)
    if req.layer not in VALID_LAYERS:
        raise HTTPException(status_code=400, detail=f"Invalid layer '{req.layer}'. Valid: {VALID_LAYERS}")
    if not req.label.strip():
        raise HTTPException(status_code=400, detail="Label cannot be empty")

    position = db.query(MatrixCell).filter(
        MatrixCell.blueprint_id == bp_id, MatrixCell.layer == req.layer
    ).count()

    cell = MatrixCell(
        id=str(uuid.uuid4()),
        blueprint_id=bp_id,
        layer=req.layer,
        label=req.label.strip(),
        position=position,
    )
    db.add(cell)
    db.commit()
    return {"id": cell.id, "layer": cell.layer, "label": cell.label, "position": cell.position}


@router.patch("/{bp_id}/cells/{cell_id}")
def update_cell(
    bp_id: str,
    cell_id: str,
    req: CellPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_or_404(bp_id, db)
    if not req.label.strip():
        raise HTTPException(status_code=400, detail="Label cannot be empty")
    cell = db.query(MatrixCell).filter(
        MatrixCell.id == cell_id, MatrixCell.blueprint_id == bp_id
    ).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Cell not found")
    cell.label = req.label.strip()
    db.commit()
    return {"id": cell.id, "layer": cell.layer, "label": cell.label, "position": cell.position}


@router.delete("/{bp_id}/cells/{cell_id}")
def delete_cell(
    bp_id: str,
    cell_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_or_404(bp_id, db)
    cell = db.query(MatrixCell).filter(
        MatrixCell.id == cell_id, MatrixCell.blueprint_id == bp_id
    ).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Cell not found")

    layer_count = db.query(MatrixCell).filter(
        MatrixCell.blueprint_id == bp_id, MatrixCell.layer == cell.layer
    ).count()
    if layer_count <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last cell in a layer")

    db.delete(cell)
    db.commit()
    return {"status": "deleted"}


# ── IntegrationItem ───────────────────────────────────────────────────────────

@router.post("/{bp_id}/integrations", status_code=201)
def add_integration(
    bp_id: str,
    req: IntegrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_or_404(bp_id, db)
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    if len(req.combinations) < 2:
        raise HTTPException(status_code=400, detail="At least 2 combinations required")

    item = IntegrationItem(
        id=str(uuid.uuid4()),
        blueprint_id=bp_id,
        name=req.name.strip(),
        combinations=json.dumps(req.combinations, ensure_ascii=False),
    )
    db.add(item)
    db.commit()
    return {"id": item.id, "name": item.name, "combinations": req.combinations}


@router.delete("/{bp_id}/integrations/{item_id}")
def delete_integration(
    bp_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_or_404(bp_id, db)
    item = db.query(IntegrationItem).filter(
        IntegrationItem.id == item_id, IntegrationItem.blueprint_id == bp_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Integration item not found")
    db.delete(item)
    db.commit()
    return {"status": "deleted"}
