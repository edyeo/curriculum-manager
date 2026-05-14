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
    entity_id: str
    keywords: Optional[List[str]] = None
    sources: Optional[List[str]] = None  # blog, linkedin, github, paper


class QueryRequest(BaseModel):
    entity_id: Optional[str] = None
    keyword: Optional[str] = None
    source: Optional[str] = None


# ========== Routes ==========

@router.post("/start")
async def start_research(request: ResearchRequest):
    """주어진 entity에 대해 조사 시작"""
    try:
        researcher = get_researcher()
        result = researcher.research(
            entity_id=request.entity_id,
            keywords=request.keywords,
            sources=request.sources
        )
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
