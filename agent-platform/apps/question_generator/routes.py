"""
Question Generator API Routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from agents.question_generator.src.harness import get_generator

router = APIRouter(prefix="/api/questions", tags=["questions"])


# ── EPIC-003 Workbench schemas ─────────────────────────────────────────────────

class WorkbenchGenerateRequest(BaseModel):
    entity_id: str
    blueprint_id: Optional[str] = None
    integration_item_id: Optional[str] = None
    blueprint_context: Optional[str] = ""
    question_type: Optional[str] = "MCQ"
    count: Optional[int] = 3


class SubgraphSearchRequest(BaseModel):
    integration_item_id: str
    item_name: str
    item_description: str
    required_combinations: Optional[List[dict]] = None


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


# ── EPIC-003 Workbench endpoints ───────────────────────────────────────────────

@router.post("/generate-workbench")
async def generate_workbench(request: WorkbenchGenerateRequest):
    """Blueprint context + sibling/antipattern 기반 MCQ 생성 (Feature 2.3)"""
    try:
        from agents.question_generator.src.graphs.workbench_question_graph import (
            build_workbench_question_graph
        )
        graph = build_workbench_question_graph()
        result = graph.invoke({
            "entity_id": request.entity_id,
            "blueprint_id": request.blueprint_id,
            "integration_item_id": request.integration_item_id,
            "blueprint_context": request.blueprint_context or "",
            "question_type": request.question_type or "MCQ",
            "count": request.count or 3,
            "entity": None,
            "siblings": [],
            "antipatterns": [],
            "related_context": "",
            "questions": [],
            "saved_questions": [],
        })
        questions = result.get("questions", [])
        return {"status": "success", "data": questions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subgraph-search")
async def subgraph_search(request: SubgraphSearchRequest):
    """통합항목 기반 서브그래프 후보 탐색 (Feature 2.2)"""
    try:
        from agents.question_generator.src.graphs.subgraph_search_graph import (
            build_subgraph_search_graph
        )
        graph = build_subgraph_search_graph()
        result = graph.invoke({
            "integration_item_id": request.integration_item_id,
            "item_name": request.item_name,
            "item_description": request.item_description,
            "required_combinations": request.required_combinations or [],
            "all_nodes": [],
            "all_edges": [],
            "candidate_roots": [],
            "candidates": [],
        })
        return {
            "status": "success",
            "candidates": result.get("candidates", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
