"""KG 분석 API — kg-refiner 에이전트 tool 전용."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from services.subgraph_service import get_subgraph
from services.node_resolution_service import compute_anomaly_scores

router = APIRouter(prefix="/kg/analytics", tags=["kg-analytics"])


@router.get("/subgraph/{subject_id}")
def subgraph(
    subject_id: str,
    node_types: Optional[str] = Query(None, description="콤마 구분 타입 필터 (예: Seed,Concept)"),
    depth: Optional[int] = Query(None, ge=1, le=5),
    root_node_id: Optional[str] = Query(None),
):
    """T_STRUCTURE용 서브그래프 추출 — Neo4j에서 노드·엣지 일괄 반환."""
    types = [t.strip() for t in node_types.split(",")] if node_types else None
    try:
        result = get_subgraph(
            subject_id=subject_id,
            node_types=types,
            depth=depth,
            root_node_id=root_node_id,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j 연결 오류: {e}")
    return result


@router.get("/node-resolution/{subject_id}")
def node_resolution(
    subject_id: str,
    top_k: int = Query(50, ge=1, le=200),
    min_students: int = Query(10, ge=1),
    min_successors: int = Query(3, ge=2),
):
    """T_STUDENT용 Concept 이상 노드 검출 — weighted_score 상관 기반 TOP-K 반환."""
    try:
        result = compute_anomaly_scores(
            subject_id=subject_id,
            top_k=top_k,
            min_students=min_students,
            min_successors=min_successors,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이상 노드 연산 오류: {e}")

    anomalies = result["anomalies"]
    degenerate = result.get("degenerate_nodes", [])
    diag = result["diagnostics"]
    return {
        "subject_id": subject_id,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "total_node_count": diag.get("subject_node_total", 0),
        "analyzed_concept_count": diag.get("analyzed_concept_count", 0),
        "analyzed_successor_count": diag.get("analyzed_successor_count", 0),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "degenerate_node_count": len(degenerate),
        "degenerate_nodes": degenerate,
        "diagnostics": diag,
    }
