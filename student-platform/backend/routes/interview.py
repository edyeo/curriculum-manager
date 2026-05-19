"""Interview API — 가상 인터뷰 세션 관리.

세션 진행 중 상태(working_mastery, 현재 질문, 턴 이력)는
모두 _sessions dict(서버 메모리)에서만 관리한다.
DB 쓰기는 세션 정상 종료 시 한 번만 수행한다.
중도 이탈 = _sessions에서 소멸 = DB 무변경.
"""
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import auth as auth_utils
import interview_agent as agent
import kg_client
from database import get_db
from models import (
    BlueprintCellMastery, BlueprintItemMastery,
    InterviewDiagnosis, InterviewSession, InterviewTurn, NodeMastery, Student,
)

router = APIRouter(prefix="/interview", tags=["interview"])

# ── 세션 메모리 ───────────────────────────────────────────────────────────────
# key: session_id(int)
# value: {
#   student_id, subject_id, subject_name, nodes,
#   node_blueprints,      ← {node_id: [blueprint_list]}  세션 시작 시 로드, 불변
#   knowledge_snapshot,   ← 시작 시점 mastery (불변)
#   working_mastery,      ← 매 턴 갱신
#   current_question, current_target_nodes, consecutive_followups,
#   turns: [{turn_number, question, answer, score, feedback, action, target_nodes}]
# }
_sessions: dict[int, dict] = {}


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _get_live(session_id: int, student_id: int) -> dict:
    state = _sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Active session not found (ended or timed out)")
    if state["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Not your session")
    return state


def _get_target_blueprints(state: dict, target_node_ids: list[str]) -> list[dict]:
    """현재 타겟 노드들의 blueprint 목록을 중복 없이 반환한다."""
    seen = set()
    result = []
    for nid in target_node_ids:
        for bp in state["node_blueprints"].get(nid, []):
            bp_id = bp["blueprint_id"]
            if bp_id not in seen:
                seen.add(bp_id)
                result.append(bp)
    return result


def _load_initial_mastery(student_id: int, subject_id: str, db: Session) -> dict[str, float]:
    records = db.query(NodeMastery).filter(
        NodeMastery.student_id == student_id,
        NodeMastery.subject_id == subject_id,
    ).all()
    return {r.node_id: r.mastery_score for r in records}


def _commit_mastery(student_id: int, subject_id: str, final_mastery: dict, db: Session):
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


def _commit_blueprint_mastery(
    student_id: int,
    assessed_node_ids: set,
    final_mastery: dict,
    node_blueprints: dict,
    db: Session,
):
    """인터뷰에서 평가된 노드의 최종 mastery를 BlueprintCellMastery / BlueprintItemMastery에 EMA로 반영한다."""
    for node_id in assessed_node_ids:
        score = final_mastery.get(node_id, 0.5)
        for bp in node_blueprints.get(node_id, []):
            bp_id = bp["blueprint_id"]
            for item in bp.get("integration_items", []):
                iid = item.get("item_id")
                cell_scores = []
                for combo in item.get("required_combinations", []):
                    layer, stage = combo["layer"], combo["stage"]
                    record = db.query(BlueprintCellMastery).filter(
                        BlueprintCellMastery.student_id == student_id,
                        BlueprintCellMastery.blueprint_id == bp_id,
                        BlueprintCellMastery.layer == layer,
                        BlueprintCellMastery.stage == stage,
                    ).first()
                    if record:
                        record.mastery_score = round(
                            record.mastery_score + (score - record.mastery_score) * 0.3, 4
                        )
                        record.attempt_count += 1
                    else:
                        db.add(BlueprintCellMastery(
                            student_id=student_id,
                            blueprint_id=bp_id,
                            layer=layer,
                            stage=stage,
                            mastery_score=score,
                            attempt_count=1,
                        ))
                    cell_scores.append(score)

                if iid and cell_scores:
                    item_score = min(cell_scores)
                    item_rec = db.query(BlueprintItemMastery).filter(
                        BlueprintItemMastery.student_id == student_id,
                        BlueprintItemMastery.integration_item_id == iid,
                    ).first()
                    if item_rec:
                        item_rec.mastery_score = round(
                            item_rec.mastery_score + (item_score - item_rec.mastery_score) * 0.3, 4
                        )
                        item_rec.attempt_count += 1
                    else:
                        db.add(BlueprintItemMastery(
                            student_id=student_id,
                            integration_item_id=iid,
                            mastery_score=item_score,
                            attempt_count=1,
                        ))


# ── POST /interview/sessions ─────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    subject_id: str


@router.post("/sessions")
async def start_session(
    req: StartSessionRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(auth_utils.get_current_student),
):
    # 이미 메모리에 active 세션이 있으면 거부
    for sid, state in _sessions.items():
        if state["student_id"] == current_student.id:
            raise HTTPException(
                status_code=409,
                detail=f"Active session {sid} already exists. End it before starting a new one.",
            )

    nodes = await kg_client.get_nodes(req.subject_id)
    if not nodes:
        raise HTTPException(status_code=404, detail="Subject not found or has no nodes")

    subjects = await kg_client.get_subjects()
    subject_name = next(
        (s.get("name", req.subject_id) for s in subjects.get("subjects", []) if s["id"] == req.subject_id),
        req.subject_id,
    )

    # 모든 노드의 blueprint를 병렬로 로드
    blueprint_results = await asyncio.gather(
        *[kg_client.get_node_blueprints(n["id"]) for n in nodes],
        return_exceptions=True,
    )
    node_blueprints = {
        nodes[i]["id"]: (blueprint_results[i] if not isinstance(blueprint_results[i], Exception) else [])
        for i in range(len(nodes))
    }

    # DB에서 초기 mastery 로드
    initial_mastery = _load_initial_mastery(current_student.id, req.subject_id, db)
    for n in nodes:
        initial_mastery.setdefault(n["id"], 0.5)

    # 첫 질문 생성
    sorted_nodes = sorted(nodes, key=lambda n: initial_mastery.get(n["id"], 0.5))
    first_target = [sorted_nodes[0]]
    first_target_ids = [sorted_nodes[0]["id"]]
    first_blueprints = node_blueprints.get(first_target_ids[0], [])

    question = agent.generate_question(
        subject_name=subject_name,
        target_nodes=first_target,
        target_blueprints=first_blueprints,
        conversation_history=[],
        action="pivot",
        mastery_level=initial_mastery.get(first_target_ids[0], 0.5),
    )

    # DB에 세션 레코드 생성 (상태 컬럼 없음 — 메모리에서만 관리)
    session_record = InterviewSession(
        student_id=current_student.id,
        subject_id=req.subject_id,
        status="active",
        knowledge_snapshot=dict(initial_mastery),
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)

    # 메모리에 세션 상태 등록
    _sessions[session_record.id] = {
        "student_id": current_student.id,
        "subject_id": req.subject_id,
        "subject_name": subject_name,
        "nodes": nodes,
        "node_blueprints": node_blueprints,
        "knowledge_snapshot": dict(initial_mastery),
        "working_mastery": dict(initial_mastery),
        "current_question": question,
        "current_target_nodes": first_target_ids,
        "consecutive_followups": 0,
        "turns": [],
    }

    return {
        "session_id": session_record.id,
        "subject_id": req.subject_id,
        "subject_name": subject_name,
        "question": question,
        "turn_number": 1,
        "max_turns": agent.MAX_TURNS,
    }


# ── GET /interview/sessions ──────────────────────────────────────────────────

@router.get("/sessions")
def list_sessions(
    db: Session = Depends(get_db),
    current_student: Student = Depends(auth_utils.get_current_student),
):
    """완료된 인터뷰 세션 목록 + 진단 요약 반환."""
    sessions = (
        db.query(InterviewSession)
        .filter(
            InterviewSession.student_id == current_student.id,
            InterviewSession.status == "completed",
        )
        .order_by(InterviewSession.started_at.desc())
        .all()
    )

    result = []
    for s in sessions:
        diagnosis = db.query(InterviewDiagnosis).filter(
            InterviewDiagnosis.session_id == s.id
        ).first()
        turn_count = db.query(InterviewTurn).filter(
            InterviewTurn.session_id == s.id
        ).count()
        result.append({
            "session_id": s.id,
            "subject_id": s.subject_id,
            "overall_band": diagnosis.overall_band if diagnosis else None,
            "turn_count": turn_count,
            "started_at": s.started_at.isoformat(),
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
        })

    return {"sessions": result}


# ── GET /interview/sessions/{id} ─────────────────────────────────────────────

@router.get("/sessions/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(auth_utils.get_current_student),
):
    # 진행 중 세션은 메모리에서
    if session_id in _sessions:
        state = _get_live(session_id, current_student.id)
        return {
            "session_id": session_id,
            "subject_id": state["subject_id"],
            "status": "active",
            "turn_count": len(state["turns"]),
            "max_turns": agent.MAX_TURNS,
            "current_question": state["current_question"],
            "turns": state["turns"],
        }

    # 완료된 세션은 DB에서
    s = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.student_id == current_student.id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")

    turns = db.query(InterviewTurn).filter(
        InterviewTurn.session_id == session_id,
    ).order_by(InterviewTurn.turn_number).all()

    return {
        "session_id": s.id,
        "subject_id": s.subject_id,
        "status": s.status,
        "turn_count": len(turns),
        "max_turns": agent.MAX_TURNS,
        "current_question": None,
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
    state = _get_live(session_id, current_student.id)

    nodes = state["nodes"]
    node_map = {n["id"]: n for n in nodes}
    target_nodes = [node_map[nid] for nid in state["current_target_nodes"] if nid in node_map]
    target_blueprints = _get_target_blueprints(state, state["current_target_nodes"])

    # 답변 평가
    evaluation = agent.evaluate_answer(
        question=state["current_question"],
        answer=req.answer,
        target_nodes=target_nodes,
        target_blueprints=target_blueprints,
        subject_name=state["subject_name"],
    )
    score = float(evaluation.get("score", 0.5))
    feedback = evaluation.get("feedback", "")
    turn_number = len(state["turns"]) + 1

    # 턴 메모리에 기록
    turn = {
        "turn_number": turn_number,
        "question": state["current_question"],
        "answer": req.answer,
        "score": score,
        "feedback": feedback,
        "action": "pending",
        "target_nodes": state["current_target_nodes"],
    }
    state["turns"].append(turn)

    # working_mastery 갱신 (메모리에서만)
    for nid in state["current_target_nodes"]:
        current = state["working_mastery"].get(nid, 0.5)
        state["working_mastery"][nid] = agent.apply_ema(current, score)

    # 최대 턴 도달 확인
    if turn_number >= agent.MAX_TURNS:
        turn["action"] = "end"
        return {
            "turn": turn,
            "next_question": None,
            "session_status": "max_turns_reached",
            "message": f"최대 턴 수({agent.MAX_TURNS})에 도달했습니다. /end로 세션을 종료하세요.",
        }

    # 다음 타겟 선택
    covered = {nid for t in state["turns"] for nid in t["target_nodes"]}
    next_target_ids, action = agent.select_target_nodes(
        working_mastery=state["working_mastery"],
        nodes=nodes,
        covered_node_ids=covered,
        last_score=score,
        consecutive_followups=state["consecutive_followups"],
        current_target_nodes=state["current_target_nodes"],
    )
    turn["action"] = action
    state["consecutive_followups"] = (state["consecutive_followups"] + 1) if action == "follow_up" else 0

    # 다음 질문 생성
    next_target_nodes = [node_map[nid] for nid in next_target_ids if nid in node_map]
    next_target_blueprints = _get_target_blueprints(state, next_target_ids)
    avg_mastery = (
        sum(state["working_mastery"].get(nid, 0.5) for nid in next_target_ids) / len(next_target_ids)
        if next_target_ids else 0.5
    )
    next_question = agent.generate_question(
        subject_name=state["subject_name"],
        target_nodes=next_target_nodes,
        target_blueprints=next_target_blueprints,
        conversation_history=state["turns"],
        action=action,
        mastery_level=avg_mastery,
    )

    # 상태 업데이트 (메모리에서만)
    state["current_question"] = next_question
    state["current_target_nodes"] = next_target_ids

    return {
        "turn": turn,
        "next_question": next_question,
        "session_status": "active",
        "turns_remaining": agent.MAX_TURNS - turn_number,
    }


# ── POST /interview/sessions/{id}/end ────────────────────────────────────────

@router.post("/sessions/{session_id}/end")
async def end_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(auth_utils.get_current_student),
):
    state = _get_live(session_id, current_student.id)

    if not state["turns"]:
        raise HTTPException(status_code=400, detail="Cannot end a session with no completed turns")

    final_mastery = dict(state["working_mastery"])
    assessed_node_ids = {nid for t in state["turns"] for nid in t["target_nodes"]}

    # 진단 생성
    diagnosis_data = agent.generate_diagnosis(
        subject_name=state["subject_name"],
        nodes=state["nodes"],
        turns=state["turns"],
        final_mastery=final_mastery,
        assessed_node_ids=assessed_node_ids,
    )

    # ── DB에 일괄 저장 ────────────────────────────────────────────────────────
    # 1. 세션 완료 처리
    session_record = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()
    session_record.status = "completed"
    session_record.ended_at = datetime.utcnow()

    # 2. 턴 이력 저장
    for t in state["turns"]:
        db.add(InterviewTurn(
            session_id=session_id,
            turn_number=t["turn_number"],
            question=t["question"],
            answer=t["answer"],
            score=t["score"],
            feedback=t["feedback"],
            action=t["action"],
            target_nodes=t["target_nodes"],
        ))

    # 3. 진단 저장
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

    # 4. node_mastery 갱신
    _commit_mastery(current_student.id, state["subject_id"], final_mastery, db)

    # 5. blueprint cell/item mastery 갱신
    _commit_blueprint_mastery(
        student_id=current_student.id,
        assessed_node_ids=assessed_node_ids,
        final_mastery=final_mastery,
        node_blueprints=state["node_blueprints"],
        db=db,
    )

    db.commit()
    db.refresh(diagnosis)

    # 메모리에서 세션 제거
    del _sessions[session_id]

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
        raise HTTPException(status_code=404, detail="Session not found")

    diagnosis = db.query(InterviewDiagnosis).filter(
        InterviewDiagnosis.session_id == session_id
    ).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="Diagnosis not available. End the session first.")

    turns = db.query(InterviewTurn).filter(
        InterviewTurn.session_id == session_id
    ).count()

    return {
        "session_id": session_id,
        "subject_id": s.subject_id,
        "overall_band": diagnosis.overall_band,
        "strengths": diagnosis.strengths,
        "weaknesses": diagnosis.weaknesses,
        "not_covered": diagnosis.not_covered,
        "recommendations": diagnosis.recommendations,
        "node_final_mastery": diagnosis.node_final_mastery,
        "turn_count": turns,
        "created_at": diagnosis.created_at.isoformat(),
    }
