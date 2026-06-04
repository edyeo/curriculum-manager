"""Neo4j 서브그래프 추출 서비스 — T_STRUCTURE 컨텍스트 주입용."""
import os
from collections import Counter, defaultdict
from typing import Optional

from neo4j import GraphDatabase


def _driver():
    uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "curriculum_password")
    return GraphDatabase.driver(uri, auth=(user, password))


def get_subgraph(
    subject_id: str,
    node_types: Optional[list[str]] = None,
    depth: Optional[int] = None,
    root_node_id: Optional[str] = None,
) -> dict:
    """Neo4j에서 서브그래프 추출.

    root_node_id 지정 시 해당 노드 중심으로 depth 범위 탐색.
    미지정 시 subject 전체 노드·엣지 반환.
    """
    driver = _driver()
    try:
        with driver.session() as session:
            nodes = _fetch_nodes(session, subject_id, node_types, root_node_id, depth)
            node_ids = {n["id"] for n in nodes}
            edges = _fetch_edges(session, subject_id, node_ids)
    finally:
        driver.close()

    return {
        "subject_id": subject_id,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
        "metrics": compute_subgraph_metrics(nodes, edges),
    }


def compute_subgraph_metrics(nodes: list[dict], edges: list[dict]) -> dict:
    """재정의(재구조화) 판단용 파생 지표 계산.

    - node_degrees: 노드별 진입/진출 차수 + 후행 수(out_degree)
    - isolated_nodes: 엣지가 전혀 없는 노드 (구조적 고립)
    - leaf_nodes / root_nodes: 진출/진입 차수 0
    - high_fanout_nodes: 진출 차수 상위 — 개념 과대(split) 후보
    - depth_distribution: depth별 노드 수 (계층 균형 점검)
    - relation_distribution: 관계 타입별 엣지 수
    """
    node_ids = [n["id"] for n in nodes]
    name_by_id = {n["id"]: n.get("name", "") for n in nodes}

    in_deg: dict = defaultdict(int)
    out_deg: dict = defaultdict(int)
    relation_counts: Counter = Counter()
    for e in edges:
        out_deg[e["source_id"]] += 1
        in_deg[e["target_id"]] += 1
        relation_counts[e.get("relation_type", "UNKNOWN")] += 1

    node_degrees = {
        nid: {
            "in": in_deg.get(nid, 0),
            "out": out_deg.get(nid, 0),
            "successors": out_deg.get(nid, 0),
        }
        for nid in node_ids
    }

    isolated = [nid for nid in node_ids if in_deg.get(nid, 0) == 0 and out_deg.get(nid, 0) == 0]
    leaves = [nid for nid in node_ids if out_deg.get(nid, 0) == 0 and in_deg.get(nid, 0) > 0]
    roots = [nid for nid in node_ids if in_deg.get(nid, 0) == 0 and out_deg.get(nid, 0) > 0]

    high_fanout = sorted(
        (
            {"node_id": nid, "name": name_by_id.get(nid, ""), "out_degree": out_deg[nid]}
            for nid in node_ids if out_deg.get(nid, 0) > 0
        ),
        key=lambda x: x["out_degree"],
        reverse=True,
    )[:10]

    depth_dist: Counter = Counter(
        (n.get("depth") if n.get("depth") is not None else "null") for n in nodes
    )

    return {
        "node_degrees": node_degrees,
        "isolated_nodes": isolated,
        "leaf_nodes": leaves,
        "root_nodes": roots,
        "high_fanout_nodes": high_fanout,
        "depth_distribution": {str(k): v for k, v in sorted(depth_dist.items(), key=lambda x: str(x[0]))},
        "relation_distribution": dict(relation_counts),
    }


def _fetch_nodes(
    session,
    subject_id: str,
    node_types: Optional[list[str]],
    root_node_id: Optional[str],
    depth: Optional[int],
) -> list[dict]:
    if root_node_id and depth:
        # 특정 노드 중심 depth 범위 탐색
        type_filter = ""
        params: dict = {"subject_id": subject_id, "root_id": root_node_id, "depth": depth}
        if node_types:
            type_filter = "AND labels(n)[0] IN $types"
            params["types"] = node_types
        result = session.run(
            f"""
            MATCH path = (root {{id: $root_id}})-[*0..{depth}]-(n)
            WHERE n.subject_id = $subject_id {type_filter}
            RETURN DISTINCT n.id AS id, n.name AS name, labels(n)[0] AS type,
                            n.depth AS depth, n.description AS description
            """,
            params,
        )
    else:
        type_filter = ""
        params = {"subject_id": subject_id}
        if node_types:
            type_filter = "AND labels(n)[0] IN $types"
            params["types"] = node_types
        result = session.run(
            f"""
            MATCH (n {{subject_id: $subject_id}})
            WHERE size(labels(n)) > 0 {type_filter}
            RETURN n.id AS id, n.name AS name, labels(n)[0] AS type,
                   n.depth AS depth, n.description AS description
            """,
            params,
        )
    return [dict(r) for r in result]


def _fetch_edges(session, subject_id: str, node_ids: set[str]) -> list[dict]:
    if not node_ids:
        return []
    result = session.run(
        """
        MATCH (s)-[r]->(t)
        WHERE s.subject_id = $subject_id
          AND s.id IN $ids AND t.id IN $ids
        RETURN s.id AS source_id, t.id AS target_id,
               type(r) AS relation_type, r.logic_basis AS logic_basis
        """,
        {"subject_id": subject_id, "ids": list(node_ids)},
    )
    return [dict(r) for r in result]
