"""KG 분석 공통 tool — contents-manager `/kg/analytics/*` API 래퍼.

subgraph 추출 / 이상 노드 검출 API를 LangChain `@tool`로 노출한다.
kg-refiner 외 다른 에이전트도 import 하여 동일 도구를 재사용할 수 있다.

- 결정론적 파이프라인: `fetch_subgraph.invoke({...})` 형태로 호출
- 에이전틱(LLM tool-calling): `llm.bind_tools([fetch_subgraph, detect_node_anomalies])`

API 호스트는 환경변수 `CONTENTS_MANAGER_URL` (기본 http://localhost:8010).
"""
import os
from typing import Optional

import httpx
from langchain_core.tools import tool

CONTENTS_MANAGER_URL = os.getenv("CONTENTS_MANAGER_URL", "http://localhost:8010")
DEFAULT_TIMEOUT = float(os.getenv("KG_ANALYTICS_TIMEOUT", "60"))


# ── 내부 HTTP 호출 (순수 함수) ────────────────────────────────────────────────

def _get_subgraph(
    subject_id: str,
    root_node_id: Optional[str] = None,
    depth: Optional[int] = None,
    node_types: Optional[list[str]] = None,
    base_url: Optional[str] = None,
    timeout: Optional[float] = None,
) -> dict:
    params: dict = {}
    if node_types:
        params["node_types"] = ",".join(node_types)
    if depth is not None:
        params["depth"] = depth
    if root_node_id:
        params["root_node_id"] = root_node_id

    resp = httpx.get(
        f"{base_url or CONTENTS_MANAGER_URL}/kg/analytics/subgraph/{subject_id}",
        params=params,
        timeout=timeout or DEFAULT_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def _get_node_anomalies(
    subject_id: str,
    top_k: int = 50,
    min_students: int = 10,
    min_successors: int = 3,
    base_url: Optional[str] = None,
    timeout: Optional[float] = None,
) -> dict:
    resp = httpx.get(
        f"{base_url or CONTENTS_MANAGER_URL}/kg/analytics/node-resolution/{subject_id}",
        params={
            "top_k": top_k,
            "min_students": min_students,
            "min_successors": min_successors,
        },
        timeout=timeout or DEFAULT_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


# ── LangChain tools ───────────────────────────────────────────────────────────

@tool
def fetch_subgraph(
    subject_id: str,
    root_node_id: Optional[str] = None,
    depth: Optional[int] = None,
    node_types: Optional[list[str]] = None,
) -> dict:
    """지식 그래프 서브그래프를 추출한다.

    root_node_id 와 depth 를 주면 해당 노드를 중심으로 depth 범위의 이웃만
    추출하고, 생략하면 subject 전체 그래프를 반환한다. 재정의(재구조화) 제안 시
    대상 노드 주변 맥락을 좁혀 보기 위해 사용한다.

    Args:
        subject_id: 대상 Subject ID
        root_node_id: 중심 노드 ID (지정 시 이 노드 기준 이웃 탐색)
        depth: root_node_id 기준 탐색 깊이 (1~5)
        node_types: 필터링할 노드 타입 목록 (예: ["Seed", "Concept"])

    Returns:
        {subject_id, node_count, edge_count, nodes, edges,
         metrics(노드별 차수·후행 수·고립 노드·depth 분포)}
    """
    return _get_subgraph(subject_id, root_node_id, depth, node_types)


@tool
def detect_node_anomalies(
    subject_id: str,
    top_k: int = 50,
    min_students: int = 10,
    min_successors: int = 3,
) -> dict:
    """학생 학습 데이터 기반으로 이상 Concept 노드를 검출한다.

    후행 노드 간 숙련도 상관이 낮은 노드(개념 범위 과대 → split 후보)와,
    전 학생이 정답/오답인 무변별 노드(개념·문제 이상 → degenerate)를 함께
    반환한다. 응답은 재정의 제안에 바로 활용할 수 있는 값을 포함한다.

    Args:
        subject_id: 대상 Subject ID
        top_k: 이상 노드 상위 K개
        min_students: 분석에 필요한 최소 공통 학생 수
        min_successors: 분석 대상 Concept의 최소 후행 노드 수

    Returns:
        {total_node_count, analyzed_concept_count, analyzed_successor_count,
         anomaly_count, anomalies, degenerate_node_count, degenerate_nodes,
         diagnostics(process, evaluated, excluded_summary)}
    """
    return _get_node_anomalies(subject_id, top_k, min_students, min_successors)


KG_ANALYTICS_TOOLS = [fetch_subgraph, detect_node_anomalies]
