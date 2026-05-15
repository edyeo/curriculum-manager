"""
Mental Model Manager API Routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from agents.mental_model_manager.src.harness import get_manager

router = APIRouter(prefix="/api/mental-models", tags=["mental-models"])


# ========== Request/Response Models ==========

class GenerateRequest(BaseModel):
    entity_id: Optional[str] = None
    mental_model_type: Optional[str] = "conceptual"  # conceptual, analogical, narrative


class GenerateAllRequest(BaseModel):
    entity_id: str


# ========== Routes ==========

@router.post("/generate")
async def generate_mental_model(request: GenerateRequest = None):
    """특정 유형의 mental model 생성"""
    try:
        manager = get_manager()
        # If no request or entity_id provided, use default
        entity_id = request.entity_id if request and request.entity_id else "default"
        mental_model_type = request.mental_model_type if request else "conceptual"

        result = manager.generate_mental_model(
            entity_id=entity_id,
            mental_model_type=mental_model_type
        )
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-all")
async def generate_all_mental_models(request: GenerateAllRequest):
    """모든 유형의 mental model 생성"""
    try:
        manager = get_manager()
        result = manager.generate_all_types(request.entity_id)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entity/{entity_id}")
async def get_mental_models(entity_id: str):
    """Entity의 mental model 조회"""
    try:
        manager = get_manager()
        # 여기서는 DB에서 저장된 mental models를 조회
        # (현재는 생성만 하고 저장하지 않으므로 생성 후 반환)
        result = manager.generate_all_types(entity_id)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
