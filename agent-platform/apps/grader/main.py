"""Grader Agent — LLM-based answer grading service.

MULTIPLE_CHOICE: exact string comparison, no LLM.
SHORT_ANSWER / DESCRIPTIVE: OpenAI ChatCompletion (same model as other agents).
"""
import json
import os
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, field_validator

app = FastAPI(title="Grader Agent", version="0.1.0")

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


def _grade_multiple_choice(correct: str, user: str) -> GradeResponse:
    is_correct = correct.strip().upper() == user.strip().upper()
    return GradeResponse(
        is_correct=is_correct,
        score=1.0 if is_correct else 0.0,
        feedback="정답입니다." if is_correct else f"오답입니다. 정답: {correct}",
    )


async def _grade_with_llm(req: GradeRequest) -> GradeResponse:
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        temperature=0.0,
    )

    user_message = f"""다음 문제의 학생 답안을 채점하세요.

문제: {req.question_text}
모범 답안: {req.correct_answer}
참고 해설: {req.explanation}
학생 답안: {req.user_answer}

아래 JSON 형식으로만 응답하세요:
{{"is_correct": true/false, "score": 0.0~1.0, "feedback": "채점 근거 1~2문장"}}

채점 기준:
- score 1.0: 완전 정답
- score 0.5~0.9: 부분 정답 (핵심 개념은 맞으나 설명 불완전)
- score 0.0~0.4: 오답 또는 핵심 개념 누락"""

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
        return GradeResponse(
            is_correct=bool(result["is_correct"]),
            score=score,
            feedback=str(result.get("feedback", "")),
        )
    except Exception as e:
        return GradeResponse(is_correct=False, score=0.0, feedback=f"채점 오류: {e}")


@app.get("/health")
def health():
    return {"status": "ok", "service": "grader"}


@app.post("/grade", response_model=GradeResponse)
async def grade(req: GradeRequest) -> GradeResponse:
    if req.question_type == "MULTIPLE_CHOICE":
        return _grade_multiple_choice(req.correct_answer, req.user_answer)
    return await _grade_with_llm(req)
