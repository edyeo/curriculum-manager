"""Simulation routes — 가상 학생 답변 생성 및 결과 저장."""
import json
import os
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import kg_client
import persona_agent
from database import get_db
from models import SimulationResult, SimulationRun, VirtualStudent, VirtualStudentFeatureValue

router = APIRouter(prefix="/api/simulate", tags=["simulate"])

STUDENT_PLATFORM_URL = os.getenv("STUDENT_PLATFORM_URL", "http://localhost:8020")
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:9000")
KG_SERVICE_TOKEN = os.getenv("KG_SERVICE_TOKEN", "kg-service-secret")
KG_API_URL = os.getenv("KG_API_URL", "http://localhost:8010")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
_openai_client: Optional[OpenAI] = None


def _get_openai():
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _openai_client


# ── Pydantic schemas ──────────────────────────────────────────────────────────

# KG question_type → grader type
_TYPE_MAP = {
    "MCQ": "MULTIPLE_CHOICE",
    "OX": "MULTIPLE_CHOICE",
    "short_answer": "SHORT_ANSWER",
    "descriptive": "DESCRIPTIVE",
    "MULTIPLE_CHOICE": "MULTIPLE_CHOICE",
    "SHORT_ANSWER": "SHORT_ANSWER",
    "DESCRIPTIVE": "DESCRIPTIVE",
}


class QuestionInput(BaseModel):
    question_text: str
    question_type: str = "SHORT_ANSWER"   # MULTIPLE_CHOICE | SHORT_ANSWER | DESCRIPTIVE
    question_id: Optional[str] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    options: Optional[list] = None        # MCQ: [{label, text}]


class SimulationRunRequest(BaseModel):
    subject_id: str
    mode: str = Field(pattern="^(simple|interview)$")
    student_ids: list[str] = Field(min_length=1, max_length=20)
    questions: list[QuestionInput] = Field(default_factory=list)


class AnswerOut(BaseModel):
    question_text: str
    answer_text: str
    score: Optional[float] = None
    feedback: Optional[str] = None
    is_correct: Optional[bool] = None


class StudentResultOut(BaseModel):
    student_id: str
    student_name: str
    answers: list[AnswerOut]
    diagnosis: Optional[dict] = None


class SimulationRunOut(BaseModel):
    run_id: str
    mode: str
    subject_id: str
    results: list[StudentResultOut]


class SimulationRunListItem(BaseModel):
    run_id: str
    mode: str
    subject_id: str
    question_count: int
    student_count: int
    created_at: str


# ── 페르소나 프롬프트 빌더 ──────────────────────────────────────────────────────

def _build_persona_prompt(student: VirtualStudent, feature_values: list) -> str:
    lines = [f"Name: {student.name}"]
    if student.description:
        lines.append(f"Description: {student.description}")
    for fv in feature_values:
        lines.append(f"{fv.feature_key}: {fv.value}")
    return "\n".join(lines)


def _get_prior_knowledge_level(feature_values: list) -> float:
    for fv in feature_values:
        if fv.feature_key == "prior_knowledge_level":
            try:
                return float(fv.value)
            except (ValueError, TypeError):
                pass
    return 0.5


# ── Simple Answer (Mode 1) ────────────────────────────────────────────────────

async def _grade(
    question: QuestionInput,
    answer_text: str,
) -> dict:
    """Grader Agent 호출 — correct_answer 없으면 None 반환."""
    if not question.correct_answer:
        return {}
    grader_type = _TYPE_MAP.get(question.question_type, "SHORT_ANSWER")
    payload = {
        "question_type": grader_type,
        "question_text": question.question_text,
        "correct_answer": question.correct_answer,
        "user_answer": answer_text,
        "explanation": question.explanation or "",
        "matrix_cells": [],
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(f"{GATEWAY_URL}/grade", json=payload)
            resp.raise_for_status()
            return resp.json()   # {is_correct, score, feedback, cell_scores}
        except Exception:
            return {}


async def _simple_answer_and_grade(
    question: QuestionInput,
    persona_prompt: str,
    subject_id: str,
) -> AnswerOut:
    answer_text = persona_agent.generate_answer(
        question=question.question_text,
        persona_prompt=persona_prompt,
        subject_name=subject_id,
        question_type=question.question_type,
        options=question.options,
    )
    grade_result = await _grade(question, answer_text)
    return AnswerOut(
        question_text=question.question_text,
        answer_text=answer_text,
        score=grade_result.get("score"),
        feedback=grade_result.get("feedback"),
        is_correct=grade_result.get("is_correct"),
    )


# ── Interview Mode (Mode 2) ───────────────────────────────────────────────────
# 오케스트레이션: virtual-student-api가 주도
#   persona_agent  → 학생 답변 생성 (this service)
#   /service/*     → 면접관·평가자 역할 (student-platform)

_SVC_HEADERS = lambda: {"X-Service-Token": KG_SERVICE_TOKEN}
MAX_INTERVIEW_TURNS = 5


async def _svc_post(client: httpx.AsyncClient, path: str, payload: dict) -> dict:
    resp = await client.post(
        f"{STUDENT_PLATFORM_URL}/interview{path}",
        json=payload,
        headers=_SVC_HEADERS(),
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"interview{path} failed: {resp.text[:200]}")
    return resp.json()


async def _interview_run(
    subject_id: str,
    persona_prompt: str,
    uniform_mastery: Optional[float] = None,
) -> dict:
    nodes = await kg_client.get_nodes(subject_id)
    if not nodes:
        raise HTTPException(status_code=404, detail="Subject has no nodes")

    subjects = await kg_client.get_subjects()
    subject_name = next(
        (s.get("name", subject_id) for s in subjects if s["id"] == subject_id),
        subject_id,
    )

    node_blueprints = await kg_client.get_node_blueprints_bulk(nodes)
    node_map = {n["id"]: n for n in nodes}

    default_mastery = uniform_mastery if uniform_mastery is not None else 0.5
    working_mastery = {n["id"]: default_mastery for n in nodes}

    sorted_nodes = sorted(nodes, key=lambda n: working_mastery[n["id"]])
    current_target_ids = [sorted_nodes[0]["id"]]
    consecutive_followups = 0
    turns = []

    def _get_bps(target_ids):
        seen, result = set(), []
        for nid in target_ids:
            for bp in node_blueprints.get(nid, []):
                if bp["blueprint_id"] not in seen:
                    seen.add(bp["blueprint_id"])
                    result.append(bp)
        return result

    async with httpx.AsyncClient(timeout=120.0) as client:
        for turn_number in range(1, MAX_INTERVIEW_TURNS + 1):
            target_nodes = [node_map[nid] for nid in current_target_ids if nid in node_map]
            target_bps = _get_bps(current_target_ids)
            avg_mastery = sum(working_mastery.get(nid, 0.5) for nid in current_target_ids) / max(len(current_target_ids), 1)
            action = turns[-1]["action"] if turns else "pivot"

            # 1. 면접관: 질문 생성 (student-platform)
            q_resp = await _svc_post(client, "/service/question", {
                "subject_name": subject_name,
                "target_nodes": target_nodes,
                "target_blueprints": target_bps,
                "conversation_history": turns,
                "action": action,
                "mastery_level": avg_mastery,
            })
            question = q_resp["question"]

            # 2. 학생: 답변 생성 (persona_agent — this service)
            answer = persona_agent.generate_answer(
                question=question,
                persona_prompt=persona_prompt,
                subject_name=subject_name,
                conversation_history=turns,
            )

            # 3. 평가자: 채점 (student-platform)
            eval_resp = await _svc_post(client, "/service/evaluate", {
                "question": question,
                "answer": answer,
                "target_nodes": target_nodes,
                "target_blueprints": target_bps,
                "subject_name": subject_name,
            })
            score = float(eval_resp.get("score", 0.5))

            for nid in current_target_ids:
                cur = working_mastery.get(nid, 0.5)
                working_mastery[nid] = round(0.3 * score + 0.7 * cur, 4)

            # 4. 다음 타겟 선택 (student-platform)
            covered = [nid for t in turns for nid in t["target_nodes"]] + current_target_ids
            next_resp = await _svc_post(client, "/service/next-target", {
                "working_mastery": working_mastery,
                "nodes": nodes,
                "covered_node_ids": covered,
                "last_score": score,
                "consecutive_followups": consecutive_followups,
                "current_target_nodes": current_target_ids,
            })
            next_action = next_resp["action"]
            consecutive_followups = (consecutive_followups + 1) if next_action == "follow_up" else 0

            turns.append({
                "turn_number": turn_number,
                "question": question,
                "answer": answer,
                "score": score,
                "feedback": eval_resp.get("feedback", ""),
                "action": next_action,
                "target_nodes": current_target_ids,
            })

            next_target_ids = next_resp["target_ids"]
            if not next_target_ids:
                break
            current_target_ids = next_target_ids

        # 5. 진단 생성 (student-platform)
        assessed = list({nid for t in turns for nid in t["target_nodes"]})
        diagnosis = await _svc_post(client, "/service/diagnose", {
            "subject_name": subject_name,
            "nodes": nodes,
            "turns": turns,
            "final_mastery": working_mastery,
            "assessed_node_ids": assessed,
        })

    return {"turns": turns, "diagnosis": diagnosis}


# ── KG 질문 조회 ──────────────────────────────────────────────────────────────

async def _fetch_kg_questions(subject_id: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                f"{KG_API_URL}/api/question-workbench/questions",
                headers={"X-Service-Token": KG_SERVICE_TOKEN},
                params={"status": "published"},
            )
            resp.raise_for_status()
            return resp.json().get("questions", [])
        except Exception:
            return []


# ── POST /simulate/runs ────────────────────────────────────────────────────────

@router.post("/runs", response_model=SimulationRunOut, status_code=201)
async def create_simulation_run(data: SimulationRunRequest, db: Session = Depends(get_db)):
    # interview 모드는 questions 불필요
    if data.mode == "simple" and not data.questions:
        raise HTTPException(status_code=422, detail="Simple mode requires at least one question")

    students = db.query(VirtualStudent).filter(
        VirtualStudent.id.in_(data.student_ids),
        VirtualStudent.subject_id == data.subject_id,
    ).all()
    if not students:
        raise HTTPException(status_code=404, detail="No matching students found for this subject")

    question_source = "manual" if data.mode == "interview" else (
        "kg" if any(q.question_id for q in data.questions) else "manual"
    )

    run = SimulationRun(
        subject_id=data.subject_id,
        mode=data.mode,
        question_source=question_source,
        questions=[q.model_dump() for q in data.questions],
    )
    db.add(run)
    db.flush()

    results_out = []
    for student in students:
        fvs = db.query(VirtualStudentFeatureValue).filter(
            VirtualStudentFeatureValue.virtual_student_id == student.id
        ).all()
        persona = _build_persona_prompt(student, fvs)
        prior_knowledge = _get_prior_knowledge_level(fvs)

        if data.mode == "simple":
            answer_outs = [
                await _simple_answer_and_grade(q, persona, data.subject_id)
                for q in data.questions
            ]
            answers = [a.model_dump() for a in answer_outs]
            diagnosis = None
        else:
            # interview mode: prior_knowledge_level → 전 노드 uniform initial mastery
            interview_data = await _interview_run(
                subject_id=data.subject_id,
                persona_prompt=persona,
                uniform_mastery=prior_knowledge,
            )
            answers = [
                {
                    "question_text": t["question"],
                    "answer_text": t["answer"],
                    "score": t.get("score"),
                    "feedback": t.get("feedback"),
                    "is_correct": None,
                }
                for t in interview_data.get("turns", [])
            ]
            diagnosis = interview_data.get("diagnosis")

        result = SimulationResult(
            run_id=run.id,
            virtual_student_id=student.id,
            answers=answers,
            diagnosis=diagnosis,
        )
        db.add(result)

        results_out.append(StudentResultOut(
            student_id=student.id,
            student_name=student.name,
            answers=[AnswerOut(
                question_text=a["question_text"],
                answer_text=a["answer_text"],
                score=a.get("score"),
                feedback=a.get("feedback"),
                is_correct=a.get("is_correct"),
            ) for a in answers],
            diagnosis=diagnosis,
        ))

    db.commit()

    return SimulationRunOut(
        run_id=run.id,
        mode=run.mode,
        subject_id=run.subject_id,
        results=results_out,
    )


# ── GET /simulate/runs ────────────────────────────────────────────────────────

@router.get("/runs", response_model=list[SimulationRunListItem])
def list_simulation_runs(
    subject_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(SimulationRun)
    if subject_id:
        q = q.filter(SimulationRun.subject_id == subject_id)
    runs = q.order_by(SimulationRun.created_at.desc()).limit(50).all()

    out = []
    for run in runs:
        student_count = db.query(SimulationResult).filter(
            SimulationResult.run_id == run.id
        ).count()
        out.append(SimulationRunListItem(
            run_id=run.id,
            mode=run.mode,
            subject_id=run.subject_id,
            question_count=len(run.questions) if run.mode == "simple" else 0,
            student_count=student_count,
            created_at=run.created_at.isoformat(),
        ))
    return out


# ── GET /simulate/runs/{run_id} ───────────────────────────────────────────────

@router.get("/runs/{run_id}", response_model=SimulationRunOut)
def get_simulation_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Simulation run not found")

    results = db.query(SimulationResult).filter(SimulationResult.run_id == run_id).all()
    results_out = []
    for r in results:
        student = db.query(VirtualStudent).filter(VirtualStudent.id == r.virtual_student_id).first()
        results_out.append(StudentResultOut(
            student_id=r.virtual_student_id,
            student_name=student.name if student else r.virtual_student_id,
            answers=[AnswerOut(**a) for a in (r.answers or [])],
            diagnosis=r.diagnosis,
        ))

    return SimulationRunOut(
        run_id=run.id,
        mode=run.mode,
        subject_id=run.subject_id,
        results=results_out,
    )


# ── POST /simulate/generate-and-grade ────────────────────────────────────────


class PersonaDict(BaseModel):
    prior_knowledge_level: float = 0.5
    conceptual_depth: str = "보통"
    reasoning_style: str = "단계적"
    verbosity: str = "보통"
    confidence_level: str = "보통"
    learning_pace: str = "보통"


class GenerateAndGradeRequest(BaseModel):
    name: str = "학생"
    persona: PersonaDict
    subject_id: str
    questions: list[QuestionInput]


class AnswerWithId(BaseModel):
    question_id: Optional[str] = None
    answer_text: str
    is_correct: Optional[bool] = None
    score: Optional[float] = None
    feedback: Optional[str] = None


def _build_persona_prompt_from_dict(name: str, persona: dict) -> str:
    lines = [f"Name: {name}"]
    for key, value in persona.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


@router.post("/generate-and-grade", response_model=list[AnswerWithId])
async def generate_and_grade(data: GenerateAndGradeRequest):
    """인라인 페르소나 + 배치 문제 → 배치 답변+채점. DB 레코드 생성 없음 (stateless)."""
    persona_prompt = _build_persona_prompt_from_dict(data.name, data.persona.model_dump())
    results = []
    for q in data.questions:
        answer_text = persona_agent.generate_answer(
            question=q.question_text,
            persona_prompt=persona_prompt,
            subject_name=data.subject_id,
            question_type=q.question_type,
            options=q.options,
        )
        grade_result = await _grade(q, answer_text)
        results.append(AnswerWithId(
            question_id=q.question_id,
            answer_text=answer_text,
            is_correct=grade_result.get("is_correct"),
            score=grade_result.get("score"),
            feedback=grade_result.get("feedback"),
        ))
    return results


# ── GET /simulate/results ────────────────────────────────────────────────────

@router.get("/results")
def list_simulation_results(
    subject_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = (
        db.query(SimulationResult, SimulationRun, VirtualStudent)
        .join(SimulationRun, SimulationResult.run_id == SimulationRun.id)
        .join(VirtualStudent, SimulationResult.virtual_student_id == VirtualStudent.id)
    )
    if subject_id:
        query = query.filter(SimulationRun.subject_id == subject_id)
    rows = query.order_by(SimulationResult.created_at.desc()).limit(200).all()

    out = []
    for result, run, student in rows:
        answers = result.answers or []
        first_q = answers[0]["question_text"] if answers else ""
        scores = [a["score"] for a in answers if a.get("score") is not None]
        avg_score = round(sum(scores) / len(scores), 3) if scores else None
        out.append({
            "result_id": result.id,
            "run_id": result.run_id,
            "student_id": student.id,
            "student_name": student.name,
            "mode": run.mode,
            "first_question": first_q,
            "answer_count": len(answers),
            "avg_score": avg_score,
            "created_at": result.created_at.isoformat(),
        })
    return out


# ── GET /simulate/results/{result_id} ────────────────────────────────────────

@router.get("/results/{result_id}")
def get_simulation_result(result_id: str, db: Session = Depends(get_db)):
    result = db.query(SimulationResult).filter(SimulationResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    run = db.query(SimulationRun).filter(SimulationRun.id == result.run_id).first()
    student = db.query(VirtualStudent).filter(VirtualStudent.id == result.virtual_student_id).first()

    return {
        "result_id": result.id,
        "run_id": result.run_id,
        "student_id": student.id if student else result.virtual_student_id,
        "student_name": student.name if student else result.virtual_student_id,
        "mode": run.mode if run else "unknown",
        "subject_id": run.subject_id if run else "",
        "answers": result.answers or [],
        "diagnosis": result.diagnosis,
        "created_at": result.created_at.isoformat(),
    }


# ── GET /simulate/kg-questions ────────────────────────────────────────────────

@router.get("/kg-questions")
async def get_kg_questions(subject_id: Optional[str] = None):
    questions = await _fetch_kg_questions(subject_id or "")
    return {"questions": questions}


# ── Interview Session (단계별 실행) ────────────────────────────────────────────
# 세션 상태는 서버 메모리에서만 관리. 완료(finish) 시 DB에 저장.

import uuid as _uuid_mod

_virt_sessions: dict[str, dict] = {}

MAX_VIRT_TURNS = 8


class InterviewStartRequest(BaseModel):
    virtual_student_id: str
    subject_id: str


class InterviewStepOut(BaseModel):
    session_id: str
    turn_number: int
    question: str
    answer: str
    score: float
    feedback: str
    next_question: Optional[str] = None
    done: bool = False


class InterviewStartOut(BaseModel):
    session_id: str
    student_name: str
    subject_name: str
    first_question: str
    max_turns: int


# ── POST /simulate/interview/start ───────────────────────────────────────────

@router.post("/interview/start", response_model=InterviewStartOut)
async def interview_start(req: InterviewStartRequest, db: Session = Depends(get_db)):
    student = db.query(VirtualStudent).filter(VirtualStudent.id == req.virtual_student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Virtual student not found")

    fvs = db.query(VirtualStudentFeatureValue).filter(
        VirtualStudentFeatureValue.virtual_student_id == student.id
    ).all()
    persona = _build_persona_prompt(student, fvs)
    prior_knowledge = _get_prior_knowledge_level(fvs)

    nodes = await kg_client.get_nodes(req.subject_id)
    if not nodes:
        raise HTTPException(status_code=404, detail="Subject has no nodes")

    subjects = await kg_client.get_subjects()
    subject_name = next(
        (s.get("name", req.subject_id) for s in subjects if s["id"] == req.subject_id),
        req.subject_id,
    )

    node_blueprints = await kg_client.get_node_blueprints_bulk(nodes)
    node_map = {n["id"]: n for n in nodes}

    default_mastery = prior_knowledge
    working_mastery = {n["id"]: default_mastery for n in nodes}
    sorted_nodes = sorted(nodes, key=lambda n: working_mastery[n["id"]])
    current_target_ids = [sorted_nodes[0]["id"]]

    def _get_bps(target_ids):
        seen, result = set(), []
        for nid in target_ids:
            for bp in node_blueprints.get(nid, []):
                if bp["blueprint_id"] not in seen:
                    seen.add(bp["blueprint_id"])
                    result.append(bp)
        return result

    # 첫 질문 생성
    target_nodes = [node_map[nid] for nid in current_target_ids if nid in node_map]
    async with httpx.AsyncClient(timeout=60.0) as client:
        q_resp = await client.post(
            f"{STUDENT_PLATFORM_URL}/interview/service/question",
            json={
                "subject_name": subject_name,
                "target_nodes": target_nodes,
                "target_blueprints": _get_bps(current_target_ids),
                "conversation_history": [],
                "action": "pivot",
                "mastery_level": default_mastery,
            },
            headers={"X-Service-Token": KG_SERVICE_TOKEN},
        )
        q_resp.raise_for_status()
        first_question = q_resp.json()["question"]

    session_id = str(_uuid_mod.uuid4())
    _virt_sessions[session_id] = {
        "virtual_student_id": student.id,
        "student_name": student.name,
        "subject_id": req.subject_id,
        "subject_name": subject_name,
        "persona": persona,
        "nodes": nodes,
        "node_blueprints": node_blueprints,
        "node_map": node_map,
        "working_mastery": working_mastery,
        "current_target_ids": current_target_ids,
        "consecutive_followups": 0,
        "turns": [],
        "current_question": first_question,
        "done": False,
    }

    return InterviewStartOut(
        session_id=session_id,
        student_name=student.name,
        subject_name=subject_name,
        first_question=first_question,
        max_turns=MAX_VIRT_TURNS,
    )


# ── POST /simulate/interview/{session_id}/step ───────────────────────────────

@router.post("/interview/{session_id}/step", response_model=InterviewStepOut)
async def interview_step(session_id: str):
    state = _virt_sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    if state["done"]:
        raise HTTPException(status_code=400, detail="Session already finished")

    question = state["current_question"]
    target_ids = state["current_target_ids"]
    node_map = state["node_map"]
    nodes = state["nodes"]
    node_blueprints = state["node_blueprints"]
    working_mastery = state["working_mastery"]

    def _get_bps(tids):
        seen, result = set(), []
        for nid in tids:
            for bp in node_blueprints.get(nid, []):
                if bp["blueprint_id"] not in seen:
                    seen.add(bp["blueprint_id"])
                    result.append(bp)
        return result

    target_nodes = [node_map[nid] for nid in target_ids if nid in node_map]
    target_bps = _get_bps(target_ids)
    avg_mastery = sum(working_mastery.get(nid, 0.5) for nid in target_ids) / max(len(target_ids), 1)
    turn_number = len(state["turns"]) + 1

    # 1. 학생 답변
    answer = persona_agent.generate_answer(
        question=question,
        persona_prompt=state["persona"],
        subject_name=state["subject_name"],
        conversation_history=state["turns"],
    )

    # 2. 채점
    async with httpx.AsyncClient(timeout=60.0) as client:
        eval_resp = await client.post(
            f"{STUDENT_PLATFORM_URL}/interview/service/evaluate",
            json={
                "question": question,
                "answer": answer,
                "target_nodes": target_nodes,
                "target_blueprints": target_bps,
                "subject_name": state["subject_name"],
            },
            headers={"X-Service-Token": KG_SERVICE_TOKEN},
        )
        eval_resp.raise_for_status()
        evaluation = eval_resp.json()
        score = float(evaluation.get("score", 0.5))

        # 3. mastery 갱신
        for nid in target_ids:
            cur = working_mastery.get(nid, 0.5)
            working_mastery[nid] = round(0.3 * score + 0.7 * cur, 4)

        # 4. 다음 타겟 선택
        covered = [nid for t in state["turns"] for nid in t["target_nodes"]] + list(target_ids)
        next_resp = await client.post(
            f"{STUDENT_PLATFORM_URL}/interview/service/next-target",
            json={
                "working_mastery": working_mastery,
                "nodes": nodes,
                "covered_node_ids": covered,
                "last_score": score,
                "consecutive_followups": state["consecutive_followups"],
                "current_target_nodes": target_ids,
            },
            headers={"X-Service-Token": KG_SERVICE_TOKEN},
        )
        next_resp.raise_for_status()
        next_data = next_resp.json()
        next_action = next_data["action"]
        next_target_ids = next_data["target_ids"]
        state["consecutive_followups"] = (state["consecutive_followups"] + 1) if next_action == "follow_up" else 0

        turn = {
            "turn_number": turn_number,
            "question": question,
            "answer": answer,
            "score": score,
            "feedback": evaluation.get("feedback", ""),
            "action": next_action,
            "target_nodes": target_ids,
        }
        state["turns"].append(turn)

        done = (turn_number >= MAX_VIRT_TURNS) or (not next_target_ids)
        state["done"] = done

        next_question = None
        if not done:
            next_nodes = [node_map[nid] for nid in next_target_ids if nid in node_map]
            next_bps = _get_bps(next_target_ids)
            next_avg = sum(working_mastery.get(nid, 0.5) for nid in next_target_ids) / max(len(next_target_ids), 1)
            nq_resp = await client.post(
                f"{STUDENT_PLATFORM_URL}/interview/service/question",
                json={
                    "subject_name": state["subject_name"],
                    "target_nodes": next_nodes,
                    "target_blueprints": next_bps,
                    "conversation_history": state["turns"],
                    "action": next_action,
                    "mastery_level": next_avg,
                },
                headers={"X-Service-Token": KG_SERVICE_TOKEN},
            )
            nq_resp.raise_for_status()
            next_question = nq_resp.json()["question"]
            state["current_question"] = next_question
            state["current_target_ids"] = next_target_ids

    return InterviewStepOut(
        session_id=session_id,
        turn_number=turn_number,
        question=question,
        answer=answer,
        score=score,
        feedback=evaluation.get("feedback", ""),
        next_question=next_question,
        done=done,
    )


# ── POST /simulate/interview/{session_id}/finish ─────────────────────────────

@router.post("/interview/{session_id}/finish")
async def interview_finish(session_id: str, db: Session = Depends(get_db)):
    state = _virt_sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    turns = state["turns"]
    if not turns:
        raise HTTPException(status_code=400, detail="No turns to finish")

    assessed = list({nid for t in turns for nid in t["target_nodes"]})

    async with httpx.AsyncClient(timeout=60.0) as client:
        diag_resp = await client.post(
            f"{STUDENT_PLATFORM_URL}/interview/service/diagnose",
            json={
                "subject_name": state["subject_name"],
                "nodes": state["nodes"],
                "turns": turns,
                "final_mastery": state["working_mastery"],
                "assessed_node_ids": assessed,
            },
            headers={"X-Service-Token": KG_SERVICE_TOKEN},
        )
        diag_resp.raise_for_status()
        diagnosis = diag_resp.json()

    # DB 저장
    run = SimulationRun(
        subject_id=state["subject_id"],
        mode="interview",
        question_source="none",
        questions=[],
    )
    db.add(run)
    db.flush()

    answers = [
        {"question_text": t["question"], "answer_text": t["answer"],
         "score": t["score"], "feedback": t["feedback"], "is_correct": None}
        for t in turns
    ]
    result = SimulationResult(
        run_id=run.id,
        virtual_student_id=state["virtual_student_id"],
        answers=answers,
        diagnosis=diagnosis,
    )
    db.add(result)
    db.commit()

    del _virt_sessions[session_id]

    return {
        "run_id": run.id,
        "diagnosis": diagnosis,
        "turns": turns,
    }
