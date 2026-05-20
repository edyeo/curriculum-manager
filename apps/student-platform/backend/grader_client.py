"""Grader client — proxies grading requests through API Gateway."""
import os
import httpx
from fastapi import HTTPException

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:9000")
TIMEOUT = 30.0


async def grade(
    question_type: str,
    question_text: str,
    correct_answer: str,
    user_answer: str,
    explanation: str = "",
    matrix_cells: list = None,
) -> dict:
    payload = {
        "question_type": question_type,
        "question_text": question_text,
        "correct_answer": correct_answer,
        "user_answer": user_answer,
        "explanation": explanation,
        "matrix_cells": matrix_cells or [],
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.post(f"{GATEWAY_URL}/grade", json=payload)
            r.raise_for_status()
            return r.json()  # { is_correct, score, feedback }
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Grader service unavailable")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Grader error: {e.response.text}")
