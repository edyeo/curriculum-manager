"""Simulation routes — 가상 학생 답변 생성 및 결과 저장."""
import json
import os
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import SimulationResult, SimulationRun, VirtualStudent, VirtualStudentFeatureValue

router = APIRouter(prefix="/simulate", tags=["simulate"])

STUDENT_PLATFORM_URL = os.getenv("STUDENT_PLATFORM_URL", "http://localhost:8020")
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

class QuestionInput(BaseModel):
    question_text: str
    question_id: Optional[str] = None
    correct_answer: Optional[str] = None


class SimulationRunRequest(BaseModel):
    subject_id: str
    mode: str = Field(pattern="^(simple|interview)$")
    student_ids: list[str] = Field(min_length=1, max_length=20)
    questions: list[QuestionInput] = Field(default_factory=list)


class AnswerOut(BaseModel):
    question_text: str
    answer_text: str


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

def _simple_answer(question_text: str, persona_prompt: str, subject_id: str) -> str:
    client = _get_openai()
    system = (
        f"You are a student with the following characteristics:\n{persona_prompt}\n\n"
        "Answer the question naturally, consistent with your characteristics. "
        "Respond only with your answer text."
    )
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=400,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Subject: {subject_id}\n\nQuestion: {question_text}"},
        ],
    )
    return response.choices[0].message.content.strip()


# ── Interview Mode (Mode 2) ───────────────────────────────────────────────────

async def _interview_run(
    subject_id: str,
    persona_prompt: str,
    initial_mastery: Optional[dict] = None,
    uniform_mastery: Optional[float] = None,
) -> dict:
    payload = {
        "subject_id": subject_id,
        "initial_mastery": initial_mastery or {},
        "persona_prompt": persona_prompt,
        "max_turns": 5,
    }
    if uniform_mastery is not None:
        payload["uniform_mastery"] = uniform_mastery
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{STUDENT_PLATFORM_URL}/interview/virtual-run",
            json=payload,
            headers={"X-Service-Token": KG_SERVICE_TOKEN},
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Interview virtual-run failed: {resp.text[:200]}",
            )
        return resp.json()


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
            answers = []
            for q in data.questions:
                answer_text = _simple_answer(q.question_text, persona, data.subject_id)
                answers.append({"question_text": q.question_text, "answer_text": answer_text})
            diagnosis = None
        else:
            # interview mode: prior_knowledge_level → 전 노드 uniform initial mastery
            # (feature → node 타입별 mastery 파생은 backlog)
            interview_data = await _interview_run(
                subject_id=data.subject_id,
                uniform_mastery=prior_knowledge,
                persona_prompt=persona,
            )
            answers = [
                {"question_text": t["question"], "answer_text": t["answer"]}
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
            answers=[AnswerOut(**a) for a in answers],
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


# ── GET /simulate/kg-questions ────────────────────────────────────────────────

@router.get("/kg-questions")
async def get_kg_questions(subject_id: Optional[str] = None):
    questions = await _fetch_kg_questions(subject_id or "")
    return {"questions": questions}
