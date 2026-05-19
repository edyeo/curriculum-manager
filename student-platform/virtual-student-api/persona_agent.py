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
    conversation_history: list[dict] | None = None,
) -> str:
    """가상 학생 페르소나로 질문에 답변을 생성한다."""
    history_lines = []
    for h in (conversation_history or [])[-6:]:
        history_lines.append(f"Q: {h['question']}")
        history_lines.append(f"A: {h['answer']}")
    history_text = "\n".join(history_lines)

    system = (
        f"You are a student with the following characteristics:\n{persona_prompt}\n\n"
        "Answer the question naturally and consistently with your characteristics. "
        "Respond only with your answer — no meta-commentary."
    )
    user_parts = [f"Subject: {subject_name}", f"Question: {question}"]
    if history_text:
        user_parts.append(f"Conversation so far:\n{history_text}")

    response = _get_client().chat.completions.create(
        model=MODEL,
        max_tokens=400,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ],
    )
    return response.choices[0].message.content.strip()
