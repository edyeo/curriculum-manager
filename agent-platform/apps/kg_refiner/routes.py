"""
KG Refiner API Routes

REFINE 트리거를 HTTP 엔드포인트로 노출한다.
응답은 재정의 제안(validated proposals)을 포함한 JSON.

- POST /api/kg-refiner/refine       : 자체 검출 + 검출 노드 서브그래프 → 재정의 제안
- POST /api/kg-refiner/refine-node  : 외부 pipeline 검출 노드를 하나씩 받아 재정의 제안
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.kg_refiner.src.harness import KGRefinerHarness

router = APIRouter(prefix="/api/kg-refiner", tags=["kg-refiner"])

_harness: Optional[KGRefinerHarness] = None


def get_harness() -> KGRefinerHarness:
    global _harness
    if _harness is None:
        _harness = KGRefinerHarness()
    return _harness


# ── Request models ────────────────────────────────────────────────────────────

class RefineRequest(BaseModel):
    subject_id: str
    top_k: int = 50
    min_students: int = 10
    min_successors: int = 3
    depth: int = 1


class RefineNodeRequest(BaseModel):
    subject_id: str
    node_id: str
    name: str = ""
    detection: str = "external"   # anomaly | degenerate | external
    info: dict = {}               # 외부 검출 메트릭 (점수·사유 등)
    depth: int = 1


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/refine")
async def refine(request: RefineRequest):
    """자체 검출 → 검출 노드 중심 서브그래프 → 재정의 제안."""
    try:
        result = get_harness().trigger_refine(
            subject_id=request.subject_id,
            top_k=request.top_k,
            min_students=request.min_students,
            min_successors=request.min_successors,
            depth=request.depth,
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refine-node")
async def refine_node(request: RefineNodeRequest):
    """단일 노드 재정의: 외부 pipeline이 검출한 노드 하나를 받아 처리.

    검출 단계를 건너뛰고, 받은 노드를 root 로 서브그래프를 도출한 뒤
    재정의(수정) 제안을 생성한다. 검출과 재정의를 분리하려는 경우 사용.
    """
    try:
        result = get_harness().trigger_refine_node(
            subject_id=request.subject_id,
            node_id=request.node_id,
            name=request.name,
            detection=request.detection,
            info=request.info,
            depth=request.depth,
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
