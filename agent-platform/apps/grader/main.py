"""Grader Agent — LLM-based answer grading service.

MULTIPLE_CHOICE: exact string comparison, no LLM.
SHORT_ANSWER / DESCRIPTIVE: Claude API call.
"""
import json
import os
from typing import Literal

import anthropic
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

app = FastAPI(title="Grader Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


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
    prompt = f"""다음 문제의 학생 답안을 채점하세요.

문제: {req.question_text}
모범 답안: {req.correct_answer}
참고 해설: {req.explanation}
학생 답안: {req.user_answer}

JSON으로만 응답하세요 (다른 텍스트 없이):
{{"is_correct": true/false, "score": 0.0~1.0, "feedback": "채점 근거 1~2문장"}}

채점 기준:
- score 1.0: 완전 정답
- score 0.5~0.9: 부분 정답 (핵심 개념은 맞으나 설명이 불완전)
- score 0.0~0.4: 오답 또는 핵심 개념 누락"""

    try:
        client = _get_client()
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        # strip markdown code fences if present
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
