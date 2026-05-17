from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Literal
from database import get_db
from models import Student, NodeMastery, StudySession
import auth as auth_utils
import grader_client
import kg_client

router = APIRouter(prefix="/study", tags=["study"])


# ── Mastery 업데이트 (EMA) ────────────────────────────────────────────────────

def _update_mastery(current: float, score: float) -> float:
    is_correct = score >= 0.5
    if is_correct:
        return min(1.0, current + (1 - current) * 0.3 * score)
    return max(0.0, current - current * 0.2)


def _upsert_mastery(db: Session, student_id: int, node_id: str, subject_id: str, score: float) -> tuple[float, float]:
    record = db.query(NodeMastery).filter(
        NodeMastery.student_id == student_id,
        NodeMastery.node_id == node_id,
    ).first()

    before = record.mastery_score if record else 0.5

    if record:
        record.mastery_score = _update_mastery(record.mastery_score, score)
        record.attempt_count += 1
    else:
        record = NodeMastery(
            student_id=student_id,
            node_id=node_id,
            subject_id=subject_id,
            mastery_score=_update_mastery(0.5, score),
            attempt_count=1,
        )
        db.add(record)

    db.flush()
    return before, record.mastery_score


# ── Submit ────────────────────────────────────────────────────────────────────

class SubmitRequest(BaseModel):
    question_id: str
    node_id: str
    subject_id: str
    question_type: Literal["MULTIPLE_CHOICE", "SHORT_ANSWER", "DESCRIPTIVE"]
    question_text: str
    correct_answer: str
    user_answer: str
    explanation: str = ""
    time_taken_seconds: int = 0


@router.post("/submit")
async def submit(
    req: SubmitRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(auth_utils.get_current_student),
):
    result = await grader_client.grade(
        question_type=req.question_type,
        question_text=req.question_text,
        correct_answer=req.correct_answer,
        user_answer=req.user_answer,
        explanation=req.explanation,
    )

    mastery_before, mastery_after = _upsert_mastery(
        db, current_student.id, req.node_id, req.subject_id, result["score"]
    )

    session = StudySession(
        student_id=current_student.id,
        question_id=req.question_id,
        node_id=req.node_id,
        subject_id=req.subject_id,
        user_answer=req.user_answer,
        is_correct=result["is_correct"],
        score=result["score"],
        feedback=result["feedback"],
        time_taken_seconds=req.time_taken_seconds,
    )
    db.add(session)
    db.commit()

    return {
        "is_correct": result["is_correct"],
        "score": result["score"],
        "feedback": result["feedback"],
        "mastery_before": round(mastery_before, 3),
        "mastery_after": round(mastery_after, 3),
    }


# ── Mastery 조회 ──────────────────────────────────────────────────────────────

@router.get("/mastery")
def get_mastery(
    subject_id: str | None = None,
    db: Session = Depends(get_db),
    current_student: Student = Depends(auth_utils.get_current_student),
):
    query = db.query(NodeMastery).filter(NodeMastery.student_id == current_student.id)
    if subject_id:
        query = query.filter(NodeMastery.subject_id == subject_id)
    records = query.all()

    return {
        "mastery": [
            {
                "node_id": r.node_id,
                "subject_id": r.subject_id,
                "mastery_score": round(r.mastery_score, 3),
                "attempt_count": r.attempt_count,
            }
            for r in records
        ]
    }


# ── Recommend ─────────────────────────────────────────────────────────────────

@router.get("/recommend")
async def recommend(
    subject_id: str,
    current_node_id: str | None = None,
    db: Session = Depends(get_db),
    current_student: Student = Depends(auth_utils.get_current_student),
):
    nodes = await kg_client.get_nodes(subject_id)
    edges = await kg_client.get_edges(subject_id)

    mastery_records = db.query(NodeMastery).filter(
        NodeMastery.student_id == current_student.id,
        NodeMastery.subject_id == subject_id,
    ).all()
    mastery_map = {m.node_id: m.mastery_score for m in mastery_records}

    # 노드에 mastery 점수 첨부
    for node in nodes:
        node["mastery_score"] = mastery_map.get(node["id"], None)

    # 전략 결정
    unlearned = [n for n in nodes if n["mastery_score"] is None]
    weak = [n for n in nodes if n["mastery_score"] is not None and n["mastery_score"] < 0.4]
    mid = [n for n in nodes if n["mastery_score"] is not None and 0.4 <= n["mastery_score"] < 0.7]

    if weak:
        strategy = "REMEDIATION"
        reason_prefix = "mastery가 낮은"
        candidates = sorted(weak, key=lambda n: n["mastery_score"])
    elif unlearned:
        strategy = "EXPLORATION"
        reason_prefix = "아직 학습하지 않은"
        candidates = sorted(unlearned, key=lambda n: n.get("depth", 1))
    elif mid:
        strategy = "CONSOLIDATION"
        reason_prefix = "심화 학습이 필요한"
        candidates = sorted(mid, key=lambda n: n["mastery_score"])
    else:
        strategy = "CHALLENGE"
        reason_prefix = "숙달 후 다음 단계인"
        candidates = sorted(nodes, key=lambda n: n.get("mastery_score", 1.0))

    if not candidates:
        return {"strategy": strategy, "reason": "추천할 노드가 없습니다.", "recommended_node": None, "recommended_question": None}

    target_node = candidates[0]
    questions = await kg_client.get_questions(target_node["id"])

    # 이미 풀었던 문제 제외
    solved_ids = {
        s.question_id for s in db.query(StudySession.question_id).filter(
            StudySession.student_id == current_student.id,
            StudySession.node_id == target_node["id"],
        ).all()
    }
    unsolved = [q for q in questions if q.get("id") not in solved_ids]
    recommended_question = unsolved[0] if unsolved else (questions[0] if questions else None)

    return {
        "strategy": strategy,
        "reason": f"{reason_prefix} '{target_node['name']}' 노드 학습을 권장합니다.",
        "recommended_node": target_node,
        "recommended_question": recommended_question,
    }
