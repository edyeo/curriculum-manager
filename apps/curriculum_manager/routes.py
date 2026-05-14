"""
Curriculum Manager API Routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from agents.curriculum_manager.src.harness import PassIterationHarness

router = APIRouter(prefix="/api/curriculum", tags=["curriculum"])


# ========== Request/Response Models ==========

class DraftRequest(BaseModel):
    subject: str
    description: Optional[str] = None


class LinkRequest(BaseModel):
    source_type: str
    target_type: str


class GenerateResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None


# ========== Routes ==========

@router.post("/generate/draft", response_model=GenerateResponse)
async def generate_draft(request: DraftRequest):
    """DRAFT: 주제를 기반으로 초기 노드 생성"""
    try:
        harness = PassIterationHarness()
        harness.trigger_draft(request.subject)
        return GenerateResponse(
            status="success",
            message=f"Draft generated for subject: {request.subject}",
            data={"nodes_count": len(harness.nodes)}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/link", response_model=GenerateResponse)
async def generate_link(request: LinkRequest):
    """LINK: 두 엔티티 타입 간의 엣지 생성"""
    try:
        harness = PassIterationHarness()
        harness.trigger_link(request.source_type, request.target_type)
        return GenerateResponse(
            status="success",
            message=f"Edges created between {request.source_type} and {request.target_type}",
            data={"edges_count": len(harness.edges)}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/expand", response_model=GenerateResponse)
async def generate_expand():
    """EXPAND: 그래프 확장 및 새 노드 추가"""
    try:
        harness = PassIterationHarness()
        harness.trigger_expand()
        return GenerateResponse(
            status="success",
            message="Graph expanded successfully",
            data={"nodes_count": len(harness.nodes), "edges_count": len(harness.edges)}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """현재 커리큘럼 상태 조회"""
    try:
        harness = PassIterationHarness()
        return {
            "status": "ready",
            "nodes_count": len(harness.nodes),
            "edges_count": len(harness.edges)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
