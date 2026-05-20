import os
from datetime import datetime
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import VirtualStudent, VirtualStudentFeatureDefinition, VirtualStudentFeatureValue
from schemas import SeedRequest, VirtualStudentListItem

router = APIRouter(prefix="/api/virtual-students/seed", tags=["seed"])

KG_API_URL = os.getenv("KG_API_URL", "")


@router.post("", response_model=List[VirtualStudentListItem], status_code=201)
def seed_virtual_students(data: SeedRequest, db: Session = Depends(get_db)):
    if KG_API_URL:
        try:
            resp = httpx.get(f"{KG_API_URL}/api/subjects/{data.subject_id}", timeout=3.0)
            if resp.status_code == 404:
                raise HTTPException(422, f"Subject '{data.subject_id}' not found")
        except httpx.RequestError:
            pass

    all_defs = {fd.key: fd for fd in db.query(VirtualStudentFeatureDefinition).all()}
    created = []

    for tmpl in data.templates:
        student = VirtualStudent(
            name=tmpl.name,
            description=tmpl.description,
            subject_id=data.subject_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(student)
        db.flush()

        provided = tmpl.feature_values or {}
        for key, fd in all_defs.items():
            value = provided.get(key, fd.default_value)
            if value is not None:
                db.add(VirtualStudentFeatureValue(
                    virtual_student_id=student.id,
                    feature_key=key,
                    value=str(value),
                ))

        created.append(student)

    db.commit()
    return created
