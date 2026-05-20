from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from generator import GeneratorParams, get_generator
from models import VirtualStudent, VirtualStudentFeatureDefinition, VirtualStudentFeatureValue
from schemas import VirtualStudentListItem

router = APIRouter(prefix="/api/virtual-students/generate", tags=["generate"])


class GenerateRequest(BaseModel):
    subject_id: str
    count: int = Field(ge=1, le=200)
    # 향후 확장: strategy, distribution_config, seed 등


@router.post("", response_model=List[VirtualStudentListItem], status_code=201)
def generate_virtual_students(data: GenerateRequest, db: Session = Depends(get_db)):
    feature_defs = db.query(VirtualStudentFeatureDefinition).all()
    if not feature_defs:
        raise HTTPException(422, "Feature definitions not found. Run seed first.")

    params = GeneratorParams(subject_id=data.subject_id, count=data.count)
    generator = get_generator()  # strategy 확장 시: get_generator(data.strategy)
    templates = generator.generate(params, feature_defs)

    created = []
    for tmpl in templates:
        student = VirtualStudent(
            name=tmpl["name"],
            description=tmpl.get("description"),
            subject_id=tmpl["subject_id"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(student)
        db.flush()

        for key, value in tmpl["feature_values"].items():
            if value:
                db.add(VirtualStudentFeatureValue(
                    virtual_student_id=student.id,
                    feature_key=key,
                    value=value,
                ))
        created.append(student)

    db.commit()
    return created
