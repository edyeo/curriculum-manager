"""
Question Generator API Routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from agents.question_generator.src.harness import get_generator

router = APIRouter(prefix="/api/questions", tags=["questions"])


# ========== Request/Response Models ==========

class GenerateRequest(BaseModel):
    entity_id: str
    count: Optional[int] = 5
    difficulty_levels: Optional[List[str]] = None


class RecordResponseRequest(BaseModel):
    question_id: str
    response: str
    is_correct: bool
    user_id: Optional[str] = None


# ========== Routes ==========

@router.post("/generate")
async def generate_questions(request: GenerateRequest):
    """Entity를 기반으로 문제 생성"""
    try:
        generator = get_generator()
        result = generator.generate_questions(
            entity_id=request.entity_id,
            count=request.count,
            difficulty_levels=request.difficulty_levels
        )
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entity/{entity_id}")
async def get_questions(entity_id: str):
    """Entity의 문제 조회"""
    try:
        generator = get_generator()
        # DB에서 직접 조회 (구현 필요)
        stats = generator.get_statistics(entity_id)
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/{entity_id}")
async def get_statistics(entity_id: str):
    """Entity의 문제 통계"""
    try:
        generator = get_generator()
        stats = generator.get_statistics(entity_id)
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/response")
async def record_response(request: RecordResponseRequest):
    """사용자의 답변 기록"""
    try:
        generator = get_generator()
        result = generator.record_response(
            question_id=request.question_id,
            response=request.response,
            is_correct=request.is_correct,
            user_id=request.user_id
        )
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/performance")
async def get_user_performance(user_id: str, entity_id: Optional[str] = None):
    """사용자의 성과 조회"""
    try:
        generator = get_generator()
        result = generator.get_user_performance(user_id, entity_id)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview")
async def get_overview():
    """전체 entity 문제 통계 조회 (1회 쿼리로 모든 현황 조회)"""
    try:
        generator = get_generator()
        result = generator.get_all_stats()
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
