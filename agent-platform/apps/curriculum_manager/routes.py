"""
Curriculum Manager API Routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from uuid import uuid4

from agents.curriculum_manager.src.harness import PassIterationHarness

router = APIRouter(prefix="/api/curriculum", tags=["curriculum"])


# ========== Request/Response Models ==========

class DraftRequest(BaseModel):
    subject: str
    description: Optional[str] = None


class LinkRequest(BaseModel):
    source_type: str
    target_type: str


class AiLinkRequest(BaseModel):
    source_type: Optional[str] = None
    source_depth: Optional[int] = None
    source_node_id: Optional[str] = None
    target_type: Optional[str] = None
    target_depth: Optional[int] = None
    edge_type: Optional[str] = None


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


@router.post("/generate/link-ai", response_model=GenerateResponse)
async def generate_link_ai(request: AiLinkRequest):
    """AI Link: 사용자 지정 조건(타입·depth·특정 노드)으로 엣지 생성"""
    if not request.source_node_id and not request.source_type:
        raise HTTPException(status_code=400, detail="source_node_id 또는 source_type 중 하나는 필수입니다.")
    try:
        harness = PassIterationHarness()
        new_edges = harness.trigger_link_ai(
            source_type=request.source_type,
            source_depth=request.source_depth,
            target_type=request.target_type,
            target_depth=request.target_depth,
            edge_type=request.edge_type,
            source_node_id=request.source_node_id,
        )
        return GenerateResponse(
            status="success",
            message=f"{len(new_edges)}개 엣지 추가됨",
            data={"edges_added": len(new_edges), "total_edges": len(harness.edges)},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/link-ai/preview")
async def generate_link_ai_preview(request: AiLinkRequest):
    """AI Link 미리보기: 저장 없이 후보 엣지 목록 반환"""
    if not request.source_node_id and not request.source_type:
        raise HTTPException(status_code=400, detail="source_node_id 또는 source_type 중 하나는 필수입니다.")
    try:
        harness = PassIterationHarness()
        new_edges = harness.trigger_link_ai_preview(
            source_type=request.source_type,
            source_depth=request.source_depth,
            target_type=request.target_type,
            target_depth=request.target_depth,
            edge_type=request.edge_type,
            source_node_id=request.source_node_id,
        )
        node_map = {n.id: n for n in harness.nodes}
        edges_out = []
        for e in new_edges:
            src = node_map.get(e.source_id)
            tgt = node_map.get(e.target_id)
            rel = e.relation_type if isinstance(e.relation_type, str) else e.relation_type.value
            edges_out.append({
                "id": str(uuid4()),
                "source_id": e.source_id,
                "source_name": src.name if src else e.source_id,
                "source_type": src.type.value if src else "",
                "source_depth": src.depth if src else 0,
                "target_id": e.target_id,
                "target_name": tgt.name if tgt else e.target_id,
                "target_type": tgt.type.value if tgt else "",
                "target_depth": tgt.depth if tgt else 0,
                "relation_type": rel,
                "logic_basis": e.logic_basis or "",
                "created_by_trigger": "AI_LINK",
            })
        return {"edges": edges_out, "total": len(edges_out)}
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
