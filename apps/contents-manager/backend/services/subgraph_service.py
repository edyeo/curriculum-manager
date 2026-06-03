"""Neo4j 서브그래프 추출 서비스 — T_STRUCTURE 컨텍스트 주입용."""
import os
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
            type_filter = "AND n.type IN $types"
            params["types"] = node_types
        result = session.run(
            f"""
            MATCH path = (root {{id: $root_id}})-[*0..{depth}]-(n)
            WHERE n.subject_id = $subject_id {type_filter}
            RETURN DISTINCT n.id AS id, n.name AS name, n.type AS type,
                            n.depth AS depth, n.description AS description
            """,
            params,
        )
    else:
        type_filter = ""
        params = {"subject_id": subject_id}
        if node_types:
            type_filter = "AND n.type IN $types"
            params["types"] = node_types
        result = session.run(
            f"""
            MATCH (n {{subject_id: $subject_id}})
            WHERE n.type IS NOT NULL {type_filter}
            RETURN n.id AS id, n.name AS name, n.type AS type,
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
