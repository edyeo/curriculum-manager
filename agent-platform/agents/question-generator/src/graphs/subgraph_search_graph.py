"""
Subgraph Search Graph (EPIC-003 Feature 2.2)

Blueprint 통합항목의 컨텍스트를 해석하여 Knowledge Graph에서
Seed-Concept-Tech 클러스터를 탐색하고 서브그래프 후보 3개 이상 반환.
"""
import os
import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from shared.state_manager import load_nodes, load_edges


class SubgraphCandidate(TypedDict):
    nodes: list[dict]   # [{id, name, type, description}]
    edges: list[dict]   # [{source_id, target_id, relation_type}]
    score: float
    rationale: str


class SubgraphSearchState(TypedDict):
    integration_item_id: str
    item_name: str
    item_description: str
    required_combinations: list  # [{layer, stage}]
    all_nodes: list
    all_edges: list
    candidate_roots: list        # LLM이 선택한 진입점 노드 id 목록
    candidates: list[SubgraphCandidate]


def _load_graph_node(state: SubgraphSearchState) -> dict:
    nodes = load_nodes()
    edges = load_edges()
    return {"all_nodes": [n.__dict__ for n in nodes], "all_edges": [e.__dict__ for e in edges]}


def _find_candidate_roots_node(state: SubgraphSearchState) -> dict:
    """LLM으로 통합항목에 맞는 Seed 노드 진입점 선택"""
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o"), temperature=0.3)

    seeds = [n for n in state["all_nodes"] if n.get("type") == "Seed"]
    seed_summary = "\n".join(
        f"  [{n['id']}] {n['name']}: {(n.get('description') or '')[:80]}"
        for n in seeds[:50]
    )

    combos_text = ", ".join(
        f"{c.get('layer')}/{c.get('stage')}" for c in state["required_combinations"]
    ) or "없음"

    user_message = f"""통합항목 정보:
- 이름: {state['item_name']}
- 설명: {state['item_description']}
- 요구 인지 조합: {combos_text}

Knowledge Graph Seed 노드 목록:
{seed_summary}

위 통합항목을 문제 출제의 핵심 맥락으로 삼을 때, 가장 적합한 Seed 노드 ID 3~5개를 선택하세요.
응답은 JSON array of strings만 출력: ["id1", "id2", ...]"""

    try:
        resp = llm.invoke([
            SystemMessage(content="당신은 Knowledge Graph 전문가입니다."),
            HumanMessage(content=user_message),
        ])
        content = resp.content.strip()
        if "```" in content:
            content = content.split("```")[1].split("```")[0]
            if content.startswith("json"):
                content = content[4:]
        roots = json.loads(content.strip())
        print(f"🔍 진입점 Seed 노드: {roots}")
        return {"candidate_roots": roots}
    except Exception as e:
        print(f"❌ 진입점 탐색 실패: {e}")
        return {"candidate_roots": []}


def _build_subgraph_candidates_node(state: SubgraphSearchState) -> dict:
    """각 Seed 진입점에서 BFS로 Seed-Concept-Tech 클러스터 구성"""
    node_map = {n["id"]: n for n in state["all_nodes"]}
    edge_list = state["all_edges"]

    def bfs_cluster(root_id: str, max_depth: int = 2) -> tuple[list, list]:
        visited = {root_id}
        queue = [(root_id, 0)]
        cluster_nodes = [root_id]
        cluster_edges = []
        while queue:
            nid, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            for edge in edge_list:
                neighbor = None
                if edge["source_id"] == nid:
                    neighbor = edge["target_id"]
                elif edge["target_id"] == nid:
                    neighbor = edge["source_id"]
                if neighbor and neighbor not in visited and neighbor in node_map:
                    visited.add(neighbor)
                    cluster_nodes.append(neighbor)
                    cluster_edges.append(edge)
                    queue.append((neighbor, depth + 1))
        return cluster_nodes, cluster_edges

    candidates = []
    for root_id in state["candidate_roots"]:
        if root_id not in node_map:
            continue
        node_ids, edges = bfs_cluster(root_id)
        nodes_data = [
            {
                "id": node_map[nid]["id"],
                "name": node_map[nid].get("name", ""),
                "type": str(node_map[nid].get("type", "")),
                "description": (node_map[nid].get("description") or "")[:120],
            }
            for nid in node_ids if nid in node_map
        ]
        edges_data = [
            {
                "source_id": e["source_id"],
                "target_id": e["target_id"],
                "relation_type": str(e.get("relation_type", "")),
            }
            for e in edges
        ]
        # 타입 다양성 점수: Seed/Concept/TechStack 혼합일수록 높음
        types = {node_map[nid].get("type") for nid in node_ids if nid in node_map}
        score = len(types) / 3.0
        candidates.append({
            "nodes": nodes_data,
            "edges": edges_data,
            "score": round(score, 2),
            "rationale": f"진입점: {node_map[root_id].get('name', root_id)}, 클러스터 크기: {len(node_ids)}개 노드",
        })

    # score 내림차순, 최소 3개
    candidates.sort(key=lambda c: c["score"], reverse=True)
    print(f"📊 서브그래프 후보: {len(candidates)}개")
    return {"candidates": candidates}


def build_subgraph_search_graph():
    graph = StateGraph(SubgraphSearchState)
    graph.add_node("load_graph", _load_graph_node)
    graph.add_node("find_roots", _find_candidate_roots_node)
    graph.add_node("build_candidates", _build_subgraph_candidates_node)

    graph.add_edge(START, "load_graph")
    graph.add_edge("load_graph", "find_roots")
    graph.add_edge("find_roots", "build_candidates")
    graph.add_edge("build_candidates", END)
    return graph.compile()
