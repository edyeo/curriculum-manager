"""가상 학생 생성 답변 조회 — student-platform + contents-manager 조합."""
import os
from typing import Optional

import httpx
from fastapi import APIRouter

router = APIRouter(prefix="/api/virtual-answers", tags=["virtual-answers"])

SP_URL = os.getenv("STUDENT_PLATFORM_URL", "http://localhost:8020")
KG_API_URL = os.getenv("KG_API_URL", "http://localhost:8010")
KG_SERVICE_TOKEN = os.getenv("KG_SERVICE_TOKEN", "kg-service-secret")


async def _fetch_sessions(subject_id: Optional[str]) -> list[dict]:
    params = {"subject_id": subject_id} if subject_id else {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{SP_URL}/virtual-students/study-sessions", params=params)
        r.raise_for_status()
        return r.json()


async def _fetch_question_texts(question_ids: list[str]) -> dict[str, str]:
    """question_id → question_text 맵. 없으면 question_id 그대로."""
    if not question_ids:
        return {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{KG_API_URL}/api/question-workbench/questions",
                headers={"X-Service-Token": KG_SERVICE_TOKEN},
                params={"status": "published", "page_size": 500},
            )
            r.raise_for_status()
            questions = r.json().get("questions", [])
            return {q["id"]: q["question_text"] for q in questions if q["id"] in set(question_ids)}
    except Exception:
        return {}


@router.get("")
async def list_virtual_answers(subject_id: Optional[str] = None):
    sessions = await _fetch_sessions(subject_id)
    if not sessions:
        return []

    q_ids = [s["question_id"] for s in sessions]
    text_map = await _fetch_question_texts(q_ids)

    return [
        {**s, "question_text": text_map.get(s["question_id"], s["question_id"])}
        for s in sessions
    ]
