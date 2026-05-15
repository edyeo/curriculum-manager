"""
Researcher API Routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from agents.researcher.src.harness import get_researcher

router = APIRouter(prefix="/api/research", tags=["research"])


# ========== Request/Response Models ==========

class ResearchRequest(BaseModel):
    text: Optional[str] = None  # 키워드 도출 시 추가 컨텍스트로 활용


class QueryRequest(BaseModel):
    entity_id: Optional[str] = None
    keyword: Optional[str] = None
    source: Optional[str] = None


# ========== Routes ==========

@router.post("/start")
async def start_research(request: Optional[ResearchRequest] = None):
    """
    Curriculum의 노드/링크 정보를 분석하여 추가될만한 키워드를 도출하고 조사 수행

    Optional:
    - text: 키워드 도출 시 추가 컨텍스트로 활용할 텍스트
    """
    try:
        researcher = get_researcher()
        additional_text = request.text if request else None
        result = researcher.research(text=additional_text)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def query_results(request: QueryRequest):
    """조사 결과 조회"""
    try:
        researcher = get_researcher()
        result = researcher.query_results(
            entity_id=request.entity_id,
            keyword=request.keyword,
            source=request.source
        )
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/{entity_id}")
async def get_summary(entity_id: str):
    """Entity의 조사 요약"""
    try:
        researcher = get_researcher()
        result = researcher.get_summary(entity_id)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
