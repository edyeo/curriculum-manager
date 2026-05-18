"""Grader Agent — LLM-based answer grading service.

MULTIPLE_CHOICE: exact string comparison, no LLM. cell_scores are binary (1.0/0.0).
SHORT_ANSWER / DESCRIPTIVE: OpenAI ChatCompletion with per-cell decomposition.
"""
import json
import os
from typing import Literal, List, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, field_validator

app = FastAPI(title="Grader Agent", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = """당신은 공학 커리큘럼의 문제 채점 전문가입니다.
학생 답안을 모범 답안과 비교해 객관적으로 채점하고, JSON으로만 응답합니다.
다른 텍스트는 절대 포함하지 마세요."""


class GradeRequest(BaseModel):
    question_type: Literal["MULTIPLE_CHOICE", "SHORT_ANSWER", "DESCRIPTIVE"]
    question_text: str
    correct_answer: str
    user_answer: str
    explanation: str = ""
    matrix_cells: List[Dict[str, str]] = []  # [{"layer": "Concept", "stage": "원리"}, ...]

    @field_validator("user_answer")
    @classmethod
    def user_answer_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("user_answer must not be empty")
        return v


class GradeResponse(BaseModel):
    is_correct: bool
    score: float
    feedback: str
    cell_scores: Dict[str, float] = {}  # {"Concept/원리": 0.9, ...}


def _make_cell_scores(matrix_cells: list, score: float) -> dict:
    """MCQ용: 모든 셀에 동일한 binary 점수 적용."""
    return {f"{c['layer']}/{c['stage']}": score for c in matrix_cells}


def _grade_multiple_choice(correct: str, user: str, matrix_cells: list) -> GradeResponse:
    is_correct = correct.strip().upper() == user.strip().upper()
    score = 1.0 if is_correct else 0.0
    return GradeResponse(
        is_correct=is_correct,
        score=score,
        feedback="정답입니다." if is_correct else f"오답입니다. 정답: {correct}",
        cell_scores=_make_cell_scores(matrix_cells, score),
    )


async def _grade_with_llm(req: GradeRequest) -> GradeResponse:
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        temperature=0.0,
    )

    cell_section = ""
    if req.matrix_cells:
        cell_list = "\n".join(f"  - {c['layer']}/{c['stage']}" for c in req.matrix_cells)
        cell_keys = ", ".join(f'"{c["layer"]}/{c["stage"]}": 0.0~1.0' for c in req.matrix_cells)
        cell_section = f"""
평가 항목 (matrix 셀):
{cell_list}

cell_scores에 각 항목별 점수를 포함하세요:
  {{{cell_keys}}}
"""

    user_message = f"""다음 문제의 학생 답안을 채점하세요.

문제: {req.question_text}
모범 답안: {req.correct_answer}
참고 해설: {req.explanation}
학생 답안: {req.user_answer}
{cell_section}
아래 JSON 형식으로만 응답하세요:
{{"is_correct": true/false, "score": 0.0~1.0, "feedback": "채점 근거 1~2문장", "cell_scores": {{...}}}}

채점 기준:
- score 1.0: 완전 정답
- score 0.5~0.9: 부분 정답 (핵심 개념은 맞으나 설명 불완전)
- score 0.0~0.4: 오답 또는 핵심 개념 누락
- cell_scores: 각 matrix 셀의 역량을 답안이 얼마나 충족했는지 독립적으로 평가"""

    try:
        response = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ])
        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)
        score = max(0.0, min(1.0, float(result["score"])))
        raw_cells = result.get("cell_scores", {})
        cell_scores = {k: max(0.0, min(1.0, float(v))) for k, v in raw_cells.items()}
        # 응답에 없는 셀은 전체 점수로 fallback
        for c in req.matrix_cells:
            key = f"{c['layer']}/{c['stage']}"
            if key not in cell_scores:
                cell_scores[key] = score
        return GradeResponse(
            is_correct=bool(result["is_correct"]),
            score=score,
            feedback=str(result.get("feedback", "")),
            cell_scores=cell_scores,
        )
    except Exception as e:
        fallback = 0.0
        return GradeResponse(
            is_correct=False,
            score=fallback,
            feedback=f"채점 오류: {e}",
            cell_scores=_make_cell_scores(req.matrix_cells, fallback),
        )


@app.get("/health")
def health():
    return {"status": "ok", "service": "grader"}


@app.post("/grade", response_model=GradeResponse)
async def grade(req: GradeRequest) -> GradeResponse:
    if req.question_type == "MULTIPLE_CHOICE":
        return _grade_multiple_choice(req.correct_answer, req.user_answer, req.matrix_cells)
    return await _grade_with_llm(req)
