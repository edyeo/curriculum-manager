import os
from datetime import datetime
from typing import Optional, List

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import VirtualStudent, VirtualStudentFeatureDefinition, VirtualStudentFeatureValue
from schemas import (
    VirtualStudentCreate,
    VirtualStudentUpdate,
    VirtualStudentDetail,
    VirtualStudentList,
    VirtualStudentListItem,
    FeatureValueResponse,
)

router = APIRouter(prefix="/api/virtual-students", tags=["virtual-students"])

KG_API_URL = os.getenv("KG_API_URL", "")
SP_URL = os.getenv("STUDENT_PLATFORM_URL", "")


def _sync_to_student_platform(vs_api_id: str, name: str, subject_id: str) -> None:
    """virtual student 생성 시 student_platform에 동기화. 실패해도 생성은 계속."""
    if not SP_URL:
        return
    try:
        httpx.post(
            f"{SP_URL}/virtual-students",
            json={"vs_api_id": vs_api_id, "name": name, "subject_id": subject_id},
            timeout=5.0,
        )
    except Exception:
        pass


def _validate_subject(subject_id: str):
    if not KG_API_URL:
        return
    try:
        resp = httpx.get(f"{KG_API_URL}/api/subjects/{subject_id}", timeout=3.0)
        if resp.status_code == 404:
            raise HTTPException(422, f"Subject '{subject_id}' not found")
    except httpx.RequestError:
        pass  # KG API unavailable — skip validation


def _build_feature_values(student: VirtualStudent, db: Session) -> List[FeatureValueResponse]:
    result = []
    for fv in student.feature_values:
        fd = db.query(VirtualStudentFeatureDefinition).filter_by(key=fv.feature_key).first()
        result.append(FeatureValueResponse(
            feature_key=fv.feature_key,
            display_name=fd.display_name if fd else fv.feature_key,
            description=fd.description if fd else "",
            category=fd.category if fd else "",
            value=fv.value,
        ))
    return result


@router.get("", response_model=VirtualStudentList)
def list_virtual_students(
    subject_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(VirtualStudent)
    if subject_id:
        q = q.filter(VirtualStudent.subject_id == subject_id)
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return VirtualStudentList(total=total, page=page, page_size=page_size, items=items)


@router.get("/{student_id}", response_model=VirtualStudentDetail)
def get_virtual_student(student_id: str, db: Session = Depends(get_db)):
    student = db.query(VirtualStudent).filter_by(id=student_id).first()
    if not student:
        raise HTTPException(404, "Virtual student not found")
    return VirtualStudentDetail(
        id=student.id,
        name=student.name,
        description=student.description,
        subject_id=student.subject_id,
        created_at=student.created_at,
        updated_at=student.updated_at,
        feature_values=_build_feature_values(student, db),
    )


@router.post("", response_model=VirtualStudentDetail, status_code=201)
def create_virtual_student(data: VirtualStudentCreate, db: Session = Depends(get_db)):
    _validate_subject(data.subject_id)

    provided = {fv.feature_key: fv.value for fv in (data.feature_values or [])}
    all_defs = {fd.key: fd for fd in db.query(VirtualStudentFeatureDefinition).all()}

    for key in provided:
        if key not in all_defs:
            raise HTTPException(422, f"Unknown feature key: '{key}'")

    student = VirtualStudent(
        name=data.name,
        description=data.description,
        subject_id=data.subject_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(student)
    db.flush()

    for key, fd in all_defs.items():
        value = provided.get(key, fd.default_value)
        if value is not None:
            db.add(VirtualStudentFeatureValue(
                virtual_student_id=student.id,
                feature_key=key,
                value=value,
            ))

    db.commit()
    db.refresh(student)
    _sync_to_student_platform(student.id, student.name, student.subject_id)
    return VirtualStudentDetail(
        id=student.id,
        name=student.name,
        description=student.description,
        subject_id=student.subject_id,
        created_at=student.created_at,
        updated_at=student.updated_at,
        feature_values=_build_feature_values(student, db),
    )


@router.put("/{student_id}", response_model=VirtualStudentDetail)
def update_virtual_student(student_id: str, data: VirtualStudentUpdate, db: Session = Depends(get_db)):
    student = db.query(VirtualStudent).filter_by(id=student_id).first()
    if not student:
        raise HTTPException(404, "Virtual student not found")

    if data.name is not None:
        student.name = data.name
    if data.description is not None:
        student.description = data.description
    if data.subject_id is not None:
        _validate_subject(data.subject_id)
        student.subject_id = data.subject_id

    if data.feature_values is not None:
        all_defs = {fd.key: fd for fd in db.query(VirtualStudentFeatureDefinition).all()}
        for fv_input in data.feature_values:
            if fv_input.feature_key not in all_defs:
                raise HTTPException(422, f"Unknown feature key: '{fv_input.feature_key}'")
            existing = db.query(VirtualStudentFeatureValue).filter_by(
                virtual_student_id=student_id,
                feature_key=fv_input.feature_key,
            ).first()
            if existing:
                existing.value = fv_input.value
            else:
                db.add(VirtualStudentFeatureValue(
                    virtual_student_id=student_id,
                    feature_key=fv_input.feature_key,
                    value=fv_input.value,
                ))

    student.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(student)
    return VirtualStudentDetail(
        id=student.id,
        name=student.name,
        description=student.description,
        subject_id=student.subject_id,
        created_at=student.created_at,
        updated_at=student.updated_at,
        feature_values=_build_feature_values(student, db),
    )


@router.delete("/{student_id}", status_code=204)
def delete_virtual_student(student_id: str, db: Session = Depends(get_db)):
    student = db.query(VirtualStudent).filter_by(id=student_id).first()
    if not student:
        raise HTTPException(404, "Virtual student not found")
    db.delete(student)
    db.commit()
