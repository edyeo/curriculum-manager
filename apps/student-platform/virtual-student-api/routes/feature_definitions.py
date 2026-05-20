from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import VirtualStudentFeatureDefinition, VirtualStudentFeatureValue
from schemas import FeatureDefinitionCreate, FeatureDefinitionUpdate, FeatureDefinitionResponse

router = APIRouter(prefix="/api/virtual-students/feature-definitions", tags=["feature-definitions"])


@router.get("", response_model=List[FeatureDefinitionResponse])
def list_feature_definitions(db: Session = Depends(get_db)):
    return db.query(VirtualStudentFeatureDefinition).all()


@router.post("", response_model=FeatureDefinitionResponse, status_code=201)
def create_feature_definition(data: FeatureDefinitionCreate, db: Session = Depends(get_db)):
    if db.query(VirtualStudentFeatureDefinition).filter_by(key=data.key).first():
        raise HTTPException(409, f"Feature key '{data.key}' already exists")
    if data.value_type == "categorical" and not data.value_options:
        raise HTTPException(422, "value_options required for categorical features")
    fd = VirtualStudentFeatureDefinition(
        **data.model_dump(),
        is_builtin=False,
        created_at=datetime.utcnow(),
    )
    db.add(fd)
    db.commit()
    db.refresh(fd)
    return fd


@router.put("/{key}", response_model=FeatureDefinitionResponse)
def update_feature_definition(key: str, data: FeatureDefinitionUpdate, db: Session = Depends(get_db)):
    fd = db.query(VirtualStudentFeatureDefinition).filter_by(key=key).first()
    if not fd:
        raise HTTPException(404, "Feature definition not found")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(fd, field, val)
    db.commit()
    db.refresh(fd)
    return fd


@router.delete("/{key}", status_code=204)
def delete_feature_definition(key: str, db: Session = Depends(get_db)):
    fd = db.query(VirtualStudentFeatureDefinition).filter_by(key=key).first()
    if not fd:
        raise HTTPException(404, "Feature definition not found")
    if fd.is_builtin:
        raise HTTPException(403, "Cannot delete builtin feature definitions")
    ref_count = db.query(VirtualStudentFeatureValue).filter_by(feature_key=key).count()
    if ref_count > 0:
        raise HTTPException(409, f"Feature '{key}' is referenced by {ref_count} student value(s)")
    db.delete(fd)
    db.commit()
