"""가상 학생 동기화 엔드포인트 — virtual-student-api 생성 시 호출."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import VirtualStudent, VirtualStudySession

router = APIRouter(prefix="/virtual-students", tags=["virtual-students"])


class VirtualStudentSync(BaseModel):
    vs_api_id: str
    name: str
    subject_id: str


@router.post("", status_code=201)
def sync_virtual_student(data: VirtualStudentSync, db: Session = Depends(get_db)):
    existing = db.query(VirtualStudent).filter_by(vs_api_id=data.vs_api_id).first()
    if existing:
        return {"id": existing.id, "vs_api_id": existing.vs_api_id, "synced": False}

    vs = VirtualStudent(
        vs_api_id=data.vs_api_id,
        name=data.name,
        subject_id=data.subject_id,
        created_at=datetime.utcnow(),
    )
    db.add(vs)
    db.commit()
    db.refresh(vs)
    return {"id": vs.id, "vs_api_id": vs.vs_api_id, "synced": True}


@router.get("/study-sessions")
def list_virtual_study_sessions(subject_id: str | None = None, db: Session = Depends(get_db)):
    q = (
        db.query(VirtualStudySession, VirtualStudent)
        .join(VirtualStudent, VirtualStudySession.student_id == VirtualStudent.id)
    )
    if subject_id:
        q = q.filter(VirtualStudySession.subject_id == subject_id)
    rows = q.order_by(VirtualStudySession.created_at.desc()).limit(500).all()
    return [
        {
            "id": sess.id,
            "student_id": vs.vs_api_id,
            "student_name": vs.name,
            "question_id": sess.question_id,
            "node_id": sess.node_id,
            "subject_id": sess.subject_id,
            "user_answer": sess.user_answer,
            "is_correct": sess.is_correct,
            "score": sess.score,
            "feedback": sess.feedback,
            "created_at": sess.created_at.isoformat() if sess.created_at else None,
        }
        for sess, vs in rows
    ]


@router.get("")
def list_virtual_students(subject_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(VirtualStudent)
    if subject_id:
        q = q.filter(VirtualStudent.subject_id == subject_id)
    return [{"id": vs.id, "vs_api_id": vs.vs_api_id, "name": vs.name, "subject_id": vs.subject_id} for vs in q.all()]
