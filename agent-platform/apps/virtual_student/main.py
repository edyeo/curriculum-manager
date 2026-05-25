"""Virtual Student Agent — 가상 학생 페르소나 답변 생성 서비스."""
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.virtual_student.src.persona_agent import generate_answer

app = FastAPI(title="Virtual Student Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateAnswerRequest(BaseModel):
    question: str
    persona_prompt: str
    subject_name: str
    question_type: str = "SHORT_ANSWER"
    options: Optional[list] = None
    conversation_history: Optional[list[dict]] = None


class GenerateAnswerResponse(BaseModel):
    answer: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "virtual-student"}


@app.post("/generate-answer", response_model=GenerateAnswerResponse)
def generate(req: GenerateAnswerRequest) -> GenerateAnswerResponse:
    answer = generate_answer(
        question=req.question,
        persona_prompt=req.persona_prompt,
        subject_name=req.subject_name,
        question_type=req.question_type,
        options=req.options,
        conversation_history=req.conversation_history,
    )
    return GenerateAnswerResponse(answer=answer)
