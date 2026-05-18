"""Interview API — 가상 인터뷰 세션 관리 엔드포인트."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import auth as auth_utils
import interview_agent as agent
import kg_client
from database import get_db
from models import (
    InterviewDiagnosis,
    InterviewSession,
    InterviewTurn,
    NodeMastery,
    Student,
)

router = APIRouter(prefix="/interview", tags=["interview"])

MAX_TURNS = agent.MAX_TURNS


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _get_active_session(session_id: int, student_id: int, db: Session) -> InterviewSession:
    s = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.student_id == student_id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Interview session not found")
    if s.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")
    return s


def _load_initial_mastery(student_id: int, subject_id: str, db: Session) -> dict[str, float]:
    records = db.query(NodeMastery).filter(
        NodeMastery.student_id == student_id,
        NodeMastery.subject_id == subject_id,
    ).all()
    return {r.node_id: r.mastery_score for r in records}


def _commit_mastery(
    student_id: int,
    subject_id: str,
    final_mastery: dict[str, float],
    db: Session,
) -> None:
    """세션 종료 시 working_mastery를 node_mastery 테이블에 반영한다."""
    for node_id, score in final_mastery.items():
        record = db.query(NodeMastery).filter(
            NodeMastery.student_id == student_id,
            NodeMastery.node_id == node_id,
        ).first()
        if record:
            record.mastery_score = score
            record.attempt_count += 1
        else:
            db.add(NodeMastery(
                student_id=student_id,
                node_id=node_id,
                subject_id=subject_id,
                mastery_score=score,
                attempt_count=1,
            ))


def _turns_as_history(turns: list[InterviewTurn]) -> list[dict]:
    return [
        {"turn_number": t.turn_number, "question": t.question, "answer": t.answer, "score": t.score}
        for t in turns
    ]


# ── POST /interview/sessions ─────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    subject_id: str


@router.post("/sessions")
async def start_session(
    req: StartSessionRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(auth_utils.get_current_student),
):
    # 이미 active 세션이 있으면 거부
    existing = db.query(InterviewSession).filter(
        InterviewSession.student_id == current_student.id,
        InterviewSession.status == "active",
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Active session {existing.id} already exists. End it before starting a new one.",
        )

    nodes = await kg_client.get_nodes(req.subject_id)
    if not nodes:
        raise HTTPException(status_code=404, detail="Subject not found or has no nodes")

    subjects = await kg_client.get_subjects()
    subject_name = next(
        (s.get("name", req.subject_id) for s in subjects.get("subjects", []) if s["id"] == req.subject_id),
        req.subject_id,
    )

    initial_mastery = _load_initial_mastery(current_student.id, req.subject_id, db)
    # 기록 없는 노드는 기본값 0.5
    for n in nodes:
        initial_mastery.setdefault(n["id"], 0.5)

    # 첫 질문 대상: mastery 가장 낮은 노드
    sorted_nodes = sorted(nodes, key=lambda n: initial_mastery.get(n["id"], 0.5))
    first_target = [sorted_nodes[0]]
    first_target_ids = [sorted_nodes[0]["id"]]
    avg_mastery = initial_mastery.get(first_target_ids[0], 0.5)

    question = agent.generate_question(
        subject_name=subject_name,
        target_nodes=first_target,
        conversation_history=[],
        action="pivot",
        mastery_level=avg_mastery,
    )

    session = InterviewSession(
        student_id=current_student.id,
        subject_id=req.subject_id,
        status="active",
        knowledge_snapshot=dict(initial_mastery),
        working_mastery=dict(initial_mastery),
        current_question=question,
        current_target_nodes=first_target_ids,
        consecutive_followups=0,
        turn_count=0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "subject_id": req.subject_id,
        "subject_name": subject_name,
        "question": question,
        "turn_number": 1,
        "max_turns": MAX_TURNS,
    }


# ── GET /interview/sessions/{id} ─────────────────────────────────────────────

@router.get("/sessions/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(auth_utils.get_current_student),
):
    s = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.student_id == current_student.id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Interview session not found")

    turns = db.query(InterviewTurn).filter(
        InterviewTurn.session_id == session_id,
    ).order_by(InterviewTurn.turn_number).all()

    return {
        "session_id": s.id,
        "subject_id": s.subject_id,
        "status": s.status,
        "turn_count": s.turn_count,
        "max_turns": MAX_TURNS,
        "current_question": s.current_question if s.status == "active" else None,
        "turns": [
            {
                "turn_number": t.turn_number,
                "question": t.question,
                "answer": t.answer,
                "score": t.score,
                "feedback": t.feedback,
                "action": t.action,
            }
            for t in turns
        ],
        "started_at": s.started_at.isoformat(),
        "ended_at": s.ended_at.isoformat() if s.ended_at else None,
    }


# ── POST /interview/sessions/{id}/answer ─────────────────────────────────────

class AnswerRequest(BaseModel):
    answer: str


@router.post("/sessions/{session_id}/answer")
async def submit_answer(
    session_id: int,
    req: AnswerRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(auth_utils.get_current_student),
):
    s = _get_active_session(session_id, current_student.id, db)

    if not s.current_question:
        raise HTTPException(status_code=400, detail="No pending question in this session")

    nodes = await kg_client.get_nodes(s.subject_id)
    subjects = await kg_client.get_subjects()
    subject_name = next(
        (sub.get("name", s.subject_id) for sub in subjects.get("subjects", []) if sub["id"] == s.subject_id),
        s.subject_id,
    )
    node_map = {n["id"]: n for n in nodes}
    target_nodes = [node_map[nid] for nid in (s.current_target_nodes or []) if nid in node_map]

    # 답변 평가
    evaluation = agent.evaluate_answer(
        question=s.current_question,
        answer=req.answer,
        target_nodes=target_nodes,
        subject_name=subject_name,
    )
    score = float(evaluation.get("score", 0.5))
    feedback = evaluation.get("feedback", "")

    # 이전 턴 이력
    past_turns = db.query(InterviewTurn).filter(
        InterviewTurn.session_id == session_id
    ).order_by(InterviewTurn.turn_number).all()

    turn_number = s.turn_count + 1

    # 턴 저장 (현재 대상 노드 기준, 아직 다음 액션 미결정)
    turn = InterviewTurn(
        session_id=session_id,
        turn_number=turn_number,
        question=s.current_question,
        answer=req.answer,
        score=score,
        feedback=feedback,
        action="pending",
        target_nodes=s.current_target_nodes,
    )
    db.add(turn)

    # in-memory working_mastery 갱신
    working = dict(s.working_mastery or {})
    for nid in (s.current_target_nodes or []):
        current = working.get(nid, 0.5)
        working[nid] = agent.apply_ema(current, score)

    s.working_mastery = working
    s.turn_count = turn_number

    # 최대 턴 도달 여부 확인
    if turn_number >= MAX_TURNS:
        s.status = "completed"
        s.ended_at = datetime.utcnow()
        s.current_question = None
        db.flush()
        turn.action = "end"
        db.commit()
        return {
            "turn": _turn_response(turn),
            "next_question": None,
            "session_status": "completed",
            "message": f"최대 턴 수({MAX_TURNS})에 도달했습니다. 세션을 종료합니다.",
        }

    # 다음 타겟 선택
    covered = {t.target_nodes[0] for t in past_turns if t.target_nodes} | set(s.current_target_nodes or [])
    next_target_ids, action = agent.select_target_nodes(
        working_mastery=working,
        nodes=nodes,
        covered_node_ids=covered,
        last_score=score,
        consecutive_followups=s.consecutive_followups,
        current_target_nodes=s.current_target_nodes,
    )
    turn.action = action

    # 연속 follow-up 카운터 갱신
    s.consecutive_followups = (s.consecutive_followups + 1) if action == "follow_up" else 0

    # 다음 질문 생성
    next_target_nodes = [node_map[nid] for nid in next_target_ids if nid in node_map]
    avg_mastery = (
        sum(working.get(nid, 0.5) for nid in next_target_ids) / len(next_target_ids)
        if next_target_ids else 0.5
    )
    history = _turns_as_history(past_turns) + [
        {"turn_number": turn_number, "question": s.current_question, "answer": req.answer, "score": score}
    ]
    next_question = agent.generate_question(
        subject_name=subject_name,
        target_nodes=next_target_nodes,
        conversation_history=history,
        action=action,
        mastery_level=avg_mastery,
    )

    s.current_question = next_question
    s.current_target_nodes = next_target_ids
    db.commit()

    return {
        "turn": _turn_response(turn),
        "next_question": next_question,
        "session_status": "active",
        "turns_remaining": MAX_TURNS - turn_number,
    }


# ── POST /interview/sessions/{id}/end ────────────────────────────────────────

@router.post("/sessions/{session_id}/end")
async def end_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(auth_utils.get_current_student),
):
    s = _get_active_session(session_id, current_student.id, db)

    nodes = await kg_client.get_nodes(s.subject_id)
    subjects = await kg_client.get_subjects()
    subject_name = next(
        (sub.get("name", s.subject_id) for sub in subjects.get("subjects", []) if sub["id"] == s.subject_id),
        s.subject_id,
    )

    turns = db.query(InterviewTurn).filter(
        InterviewTurn.session_id == session_id
    ).order_by(InterviewTurn.turn_number).all()

    if not turns:
        raise HTTPException(status_code=400, detail="Cannot end a session with no completed turns")

    final_mastery = dict(s.working_mastery or s.knowledge_snapshot or {})

    # 실제 질문이 나간 노드 ID 집합
    assessed_node_ids: set[str] = set()
    for t in turns:
        for nid in (t.target_nodes or []):
            assessed_node_ids.add(nid)

    # 진단 생성
    diagnosis_data = agent.generate_diagnosis(
        subject_name=subject_name,
        nodes=nodes,
        turns=_turns_as_history(turns),
        final_mastery=final_mastery,
        assessed_node_ids=assessed_node_ids,
    )

    # DB에 진단 저장
    diagnosis = InterviewDiagnosis(
        session_id=session_id,
        overall_band=diagnosis_data.get("overall_band", "C"),
        strengths=diagnosis_data.get("strengths", []),
        weaknesses=diagnosis_data.get("weaknesses", []),
        not_covered=diagnosis_data.get("not_covered", []),
        recommendations=diagnosis_data.get("recommendations", []),
        node_final_mastery=final_mastery,
    )
    db.add(diagnosis)

    # working_mastery → node_mastery 테이블 반영
    _commit_mastery(current_student.id, s.subject_id, final_mastery, db)

    # 세션 완료 처리
    s.status = "completed"
    s.ended_at = datetime.utcnow()
    s.current_question = None
    db.commit()
    db.refresh(diagnosis)

    return {
        "session_id": session_id,
        "diagnosis_id": diagnosis.id,
        "overall_band": diagnosis.overall_band,
        "strengths": diagnosis.strengths,
        "weaknesses": diagnosis.weaknesses,
        "not_covered": diagnosis.not_covered,
        "recommendations": diagnosis.recommendations,
        "node_final_mastery": final_mastery,
    }


# ── GET /interview/sessions/{id}/diagnosis ───────────────────────────────────

@router.get("/sessions/{session_id}/diagnosis")
def get_diagnosis(
    session_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(auth_utils.get_current_student),
):
    s = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.student_id == current_student.id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Interview session not found")

    diagnosis = db.query(InterviewDiagnosis).filter(
        InterviewDiagnosis.session_id == session_id
    ).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="Diagnosis not available yet. End the session first.")

    return {
        "session_id": session_id,
        "subject_id": s.subject_id,
        "overall_band": diagnosis.overall_band,
        "strengths": diagnosis.strengths,
        "weaknesses": diagnosis.weaknesses,
        "not_covered": diagnosis.not_covered,
        "recommendations": diagnosis.recommendations,
        "node_final_mastery": diagnosis.node_final_mastery,
        "turn_count": s.turn_count,
        "created_at": diagnosis.created_at.isoformat(),
    }


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _turn_response(turn: InterviewTurn) -> dict:
    return {
        "turn_number": turn.turn_number,
        "question": turn.question,
        "answer": turn.answer,
        "score": round(turn.score, 3),
        "feedback": turn.feedback,
        "action": turn.action,
        "target_nodes": turn.target_nodes,
    }
