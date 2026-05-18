"""Question Bank routes — browse published questions and submit answers."""
import time
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import Student, StudyAttempt, NodeMastery
import auth as auth_utils
import grader_client
import httpx

router = APIRouter(prefix="/questions", tags=["questions"])

CM_API_URL = os.getenv("KG_API_URL", "http://localhost:8010")
CM_SERVICE_TOKEN = os.getenv("KG_SERVICE_TOKEN", "kg-service-secret")
_CM_HEADERS = {"X-Service-Token": CM_SERVICE_TOKEN}
_TIMEOUT = 15.0


async def _cm_get(path: str, params: dict = None) -> dict:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            r = await client.get(f"{CM_API_URL}{path}", headers=_CM_HEADERS, params=params)
            r.raise_for_status()
            return r.json()
        except httpx.ConnectError:
            raise HTTPException(503, "Curriculum Manager unavailable")
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, f"CM error: {e.response.text}")


def _strip_answer(q: dict) -> dict:
    """학생에게 반환할 때 정답 필드 제거."""
    return {k: v for k, v in q.items() if k != "correct_answer"}


# ── 목록 조회 ──────────────────────────────────────────────────────────────────

@router.get("/published")
async def list_published(
    blueprint_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    question_type: Optional[str] = None,
    current_student: Student = Depends(auth_utils.get_current_student),
):
    """published 문항 목록 (정답 제외)."""
    params = {"status": "published"}
    if blueprint_id:
        params["blueprint_id"] = blueprint_id
    if difficulty:
        params["difficulty"] = difficulty
    if question_type:
        params["question_type"] = question_type

    data = await _cm_get("/api/question-workbench/questions", params=params)
    questions = data.get("questions", [])
    return {"questions": [_strip_answer(q) for q in questions]}


# ── 단건 조회 ──────────────────────────────────────────────────────────────────

@router.get("/{question_id}")
async def get_question(
    question_id: str,
    current_student: Student = Depends(auth_utils.get_current_student),
):
    """문항 상세 (정답 제외)."""
    q = await _cm_get(f"/api/question-workbench/questions/{question_id}")
    if q.get("status") != "published":
        raise HTTPException(404, "Question not found")
    return _strip_answer(q)


# ── 답안 제출 ──────────────────────────────────────────────────────────────────

class SubmitRequest(BaseModel):
    answer: str
    elapsed_ms: Optional[int] = 0
    subject_id: Optional[str] = None


@router.post("/{question_id}/submit")
async def submit_answer(
    question_id: str,
    body: SubmitRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(auth_utils.get_current_student),
):
    """답안 제출 → Grader 채점 → 결과 반환 + 이력 기록."""
    q = await _cm_get(f"/api/question-workbench/questions/{question_id}")
    if q.get("status") != "published":
        raise HTTPException(404, "Question not found")

    _type_map = {"MCQ": "MULTIPLE_CHOICE", "OX": "MULTIPLE_CHOICE", "short_answer": "SHORT_ANSWER"}
    grader_type = _type_map.get(q.get("question_type", "MCQ"), "MULTIPLE_CHOICE")

    result = await grader_client.grade(
        question_type=grader_type,
        question_text=q["question_text"],
        correct_answer=q["correct_answer"],
        user_answer=body.answer,
        explanation=q.get("explanation", ""),
    )

    attempt = StudyAttempt(
        student_id=current_student.id,
        question_id=question_id,
        blueprint_id=q.get("blueprint_id"),
        user_answer=body.answer,
        is_correct=result["is_correct"],
        score=result.get("score"),
        feedback=result.get("feedback"),
        elapsed_ms=body.elapsed_ms or 0,
    )
    db.add(attempt)

    # subject_id가 있을 때만 NodeMastery upsert
    entity_id = q.get("entity_id")
    if entity_id and body.subject_id:
        score = result.get("score", 1.0 if result["is_correct"] else 0.0)
        record = db.query(NodeMastery).filter(
            NodeMastery.student_id == current_student.id,
            NodeMastery.node_id == entity_id,
        ).first()
        if record:
            if result["is_correct"]:
                record.mastery_score = min(1.0, record.mastery_score + (1 - record.mastery_score) * 0.3 * score)
            else:
                record.mastery_score = max(0.0, record.mastery_score - record.mastery_score * 0.2)
            record.attempt_count += 1
        else:
            initial = min(1.0, 0.5 + (1 - 0.5) * 0.3 * score) if result["is_correct"] else max(0.0, 0.5 - 0.5 * 0.2)
            db.add(NodeMastery(
                student_id=current_student.id,
                node_id=entity_id,
                subject_id=body.subject_id,
                mastery_score=initial,
                attempt_count=1,
            ))

    db.commit()

    # 선택 선지 rationale 추출
    selected_rationale = ""
    for opt in q.get("options", []):
        if opt.get("label") == body.answer or opt.get("text") == body.answer:
            selected_rationale = opt.get("rationale", "")
            break

    return {
        "is_correct": result["is_correct"],
        "correct_answer": q["correct_answer"],
        "selected_rationale": selected_rationale,
        "explanation": q.get("explanation", ""),
        "feedback": result.get("feedback", ""),
        "elapsed_ms": body.elapsed_ms or 0,
    }
