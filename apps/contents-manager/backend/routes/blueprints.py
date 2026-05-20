import uuid, json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from sqlalchemy.orm import Session

from database import get_db
from models import User, Blueprint, BlueprintIntegrationItem
import auth as auth_utils

router = APIRouter(prefix="/blueprints", tags=["blueprints"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class MatrixLayer(BaseModel):
    layer: str
    stages: List[str]
    stage_descriptions: Optional[Dict[str, str]] = {}

class BlueprintCreate(BaseModel):
    name: str
    description: Optional[str] = None
    matrix: Optional[List[MatrixLayer]] = None

class BlueprintUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    matrix: Optional[List[MatrixLayer]] = None
    weight: Optional[float] = None
    required: Optional[bool] = None

class IntegrationItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    required_combinations: Optional[List[dict]] = None  # [{layer, stage}]

class IntegrationItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    required_combinations: Optional[List[dict]] = None


def _bp_to_dict(bp: Blueprint) -> dict:
    return {
        "id": bp.id,
        "name": bp.name,
        "description": bp.description,
        "matrix": json.loads(bp.matrix) if bp.matrix else [],
        "weight": bp.weight if bp.weight is not None else 1.0,
        "required": bp.required if bp.required is not None else False,
        "owner_id": bp.owner_id,
        "created_at": bp.created_at.isoformat() if bp.created_at else None,
        "updated_at": bp.updated_at.isoformat() if bp.updated_at else None,
    }


def _item_to_dict(item: BlueprintIntegrationItem) -> dict:
    return {
        "id": item.id,
        "blueprint_id": item.blueprint_id,
        "name": item.name,
        "description": item.description,
        "required_combinations": json.loads(item.required_combinations) if item.required_combinations else [],
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


# ── Blueprint CRUD ─────────────────────────────────────────────────────────────

@router.get("")
def list_blueprints(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    bps = db.query(Blueprint).order_by(Blueprint.created_at.desc()).all()
    return {"blueprints": [_bp_to_dict(b) for b in bps]}


@router.post("", status_code=201)
def create_blueprint(
    body: BlueprintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    bp = Blueprint(
        id=str(uuid.uuid4()),
        name=body.name,
        description=body.description,
        matrix=json.dumps([m.dict() for m in body.matrix] if body.matrix else []),
        owner_id=current_user.id,
    )
    db.add(bp)
    db.commit()
    db.refresh(bp)
    return _bp_to_dict(bp)


@router.get("/{blueprint_id}")
def get_blueprint(
    blueprint_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    bp = db.query(Blueprint).filter(Blueprint.id == blueprint_id).first()
    if not bp:
        raise HTTPException(404, "Blueprint not found")
    items = db.query(BlueprintIntegrationItem).filter(
        BlueprintIntegrationItem.blueprint_id == blueprint_id
    ).all()
    result = _bp_to_dict(bp)
    result["integration_items"] = [_item_to_dict(i) for i in items]
    return result


@router.patch("/{blueprint_id}")
def update_blueprint(
    blueprint_id: str,
    body: BlueprintUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    bp = db.query(Blueprint).filter(Blueprint.id == blueprint_id).first()
    if not bp:
        raise HTTPException(404, "Blueprint not found")
    if body.name is not None:
        bp.name = body.name
    if body.description is not None:
        bp.description = body.description
    if body.matrix is not None:
        bp.matrix = json.dumps([m.dict() for m in body.matrix])
    if body.weight is not None:
        bp.weight = body.weight
    if body.required is not None:
        bp.required = body.required
    db.commit()
    db.refresh(bp)
    return _bp_to_dict(bp)


@router.delete("/{blueprint_id}", status_code=204)
def delete_blueprint(
    blueprint_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    bp = db.query(Blueprint).filter(Blueprint.id == blueprint_id).first()
    if not bp:
        raise HTTPException(404, "Blueprint not found")
    db.delete(bp)
    db.commit()


# ── Integration Items ──────────────────────────────────────────────────────────

@router.get("/{blueprint_id}/integration-items")
def list_integration_items(
    blueprint_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    items = db.query(BlueprintIntegrationItem).filter(
        BlueprintIntegrationItem.blueprint_id == blueprint_id
    ).all()
    return {"items": [_item_to_dict(i) for i in items]}


@router.post("/{blueprint_id}/integration-items", status_code=201)
def create_integration_item(
    blueprint_id: str,
    body: IntegrationItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    if not db.query(Blueprint).filter(Blueprint.id == blueprint_id).first():
        raise HTTPException(404, "Blueprint not found")
    item = BlueprintIntegrationItem(
        id=str(uuid.uuid4()),
        blueprint_id=blueprint_id,
        name=body.name,
        description=body.description,
        required_combinations=json.dumps(body.required_combinations or []),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _item_to_dict(item)


@router.patch("/{blueprint_id}/integration-items/{item_id}")
def update_integration_item(
    blueprint_id: str,
    item_id: str,
    body: IntegrationItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    item = db.query(BlueprintIntegrationItem).filter(
        BlueprintIntegrationItem.id == item_id,
        BlueprintIntegrationItem.blueprint_id == blueprint_id,
    ).first()
    if not item:
        raise HTTPException(404, "Integration item not found")
    if body.name is not None:
        item.name = body.name
    if body.description is not None:
        item.description = body.description
    if body.required_combinations is not None:
        item.required_combinations = json.dumps(body.required_combinations)
    db.commit()
    db.refresh(item)
    return _item_to_dict(item)


@router.delete("/{blueprint_id}/integration-items/{item_id}", status_code=204)
def delete_integration_item(
    blueprint_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    item = db.query(BlueprintIntegrationItem).filter(
        BlueprintIntegrationItem.id == item_id,
        BlueprintIntegrationItem.blueprint_id == blueprint_id,
    ).first()
    if not item:
        raise HTTPException(404, "Integration item not found")
    db.delete(item)
    db.commit()
