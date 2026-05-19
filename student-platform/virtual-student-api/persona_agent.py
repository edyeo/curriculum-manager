"""Persona Agent — 가상 학생 페르소나로 질문에 답변을 생성한다."""
import os
from typing import Optional

from openai import OpenAI

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def generate_answer(
    question: str,
    persona_prompt: str,
    subject_name: str,
    question_type: str = "SHORT_ANSWER",
    options: list | None = None,
    conversation_history: list[dict] | None = None,
) -> str:
    """가상 학생 페르소나로 질문에 답변을 생성한다.

    MCQ의 경우 options에서 하나의 label(A/B/C/D)만 선택해 반환한다.
    """
    is_mcq = question_type in ("MULTIPLE_CHOICE", "MCQ", "OX") and options

    history_lines = []
    for h in (conversation_history or [])[-6:]:
        history_lines.append(f"Q: {h['question']}")
        history_lines.append(f"A: {h['answer']}")
    history_text = "\n".join(history_lines)

    if is_mcq:
        options_text = "\n".join(
            f"{opt['label']}. {opt.get('text', opt.get('label', ''))}"
            for opt in options
        )
        labels = [opt["label"] for opt in options]
        system = (
            f"You are a student with the following characteristics:\n{persona_prompt}\n\n"
            f"You are answering a multiple-choice question. "
            f"Respond with ONLY the single option label ({'/'.join(labels)}) that best matches "
            f"your understanding given your characteristics. No explanation."
        )
        user_parts = [
            f"Subject: {subject_name}",
            f"Question: {question}",
            f"Options:\n{options_text}",
        ]
        max_tokens = 5
    else:
        system = (
            f"You are a student with the following characteristics:\n{persona_prompt}\n\n"
            "Answer the question naturally and consistently with your characteristics. "
            "Respond only with your answer — no meta-commentary."
        )
        user_parts = [f"Subject: {subject_name}", f"Question: {question}"]
        if history_text:
            user_parts.append(f"Conversation so far:\n{history_text}")
        max_tokens = 400

    response = _get_client().chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ],
    )
    answer = response.choices[0].message.content.strip()

    # MCQ: label만 추출 (혹시 설명이 붙어 나올 경우 대비)
    if is_mcq:
        for label in labels:
            if answer.upper().startswith(label.upper()):
                return label
        # fallback: 첫 글자가 유효한 label이면 사용
        first = answer[0].upper() if answer else labels[0]
        return first if first in [l.upper() for l in labels] else labels[0]

    return answer
