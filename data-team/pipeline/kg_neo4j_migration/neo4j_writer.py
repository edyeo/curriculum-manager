"""Neo4j Load 헬퍼 — MERGE 기반 idempotent 쓰기."""
from typing import Any

from neo4j import Driver

# relation_type (SQLite) → Neo4j relationship type 매핑
RELATION_TYPE_MAP = {
    "relied_on": "RELIED_ON",
    "has_subtopic": "HAS_SUBTOPIC",
    "requires": "REQUIRES",
    "implemented_by": "IMPLEMENTED_BY",
}


def _batches(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def merge_subjects(driver: Driver, subjects: list[dict]) -> int:
    query = """
    UNWIND $rows AS row
    MERGE (n:Subject {id: row.id})
    SET n.name        = row.name,
        n.description = row.description,
        n.status      = row.status
    """
    with driver.session() as session:
        session.run(query, rows=subjects)
    return len(subjects)


def merge_nodes(driver: Driver, nodes: list[dict], batch_size: int = 500) -> int:
    """
    KG 노드 MERGE. 동적 label(type)은 APOC 없이 Cypher의 label() 함수 대신
    type별로 분리하여 처리.
    """
    from collections import defaultdict
    by_type: dict[str, list[dict]] = defaultdict(list)
    for n in nodes:
        by_type[n["type"]].append(n)

    total = 0
    with driver.session() as session:
        for node_type, group in by_type.items():
            # Cypher는 동적 label을 직접 지원하지 않으므로 type별 개별 쿼리 사용
            query = f"""
            UNWIND $rows AS row
            MERGE (n:{node_type} {{id: row.id}})
            SET n.name        = row.name,
                n.description = row.description,
                n.depth       = row.depth,
                n.metadata    = row.metadata,
                n.subject_id  = row.subject_id
            """
            for batch in _batches(group, batch_size):
                session.run(query, rows=batch)
                total += len(batch)
    return total


def merge_contains(driver: Driver, nodes: list[dict], batch_size: int = 500) -> int:
    """Subject -[:CONTAINS]-> KGNode 관계 MERGE."""
    query = """
    UNWIND $rows AS row
    MATCH (subj:Subject {id: row.subject_id})
    MATCH (n {id: row.id})
    MERGE (subj)-[:CONTAINS]->(n)
    """
    total = 0
    with driver.session() as session:
        for batch in _batches(nodes, batch_size):
            session.run(query, rows=batch)
            total += len(batch)
    return total


def merge_edges(driver: Driver, edges: list[dict], batch_size: int = 500) -> int:
    """kg_edges → Neo4j 관계 MERGE. relation_type별로 분리 실행."""
    from collections import defaultdict
    by_rel: dict[str, list[dict]] = defaultdict(list)
    for e in edges:
        rel = RELATION_TYPE_MAP.get(e["relation_type"], e["relation_type"].upper())
        by_rel[rel].append(e)

    total = 0
    with driver.session() as session:
        for rel_type, group in by_rel.items():
            query = f"""
            UNWIND $rows AS row
            MATCH (s {{id: row.source_id}})
            MATCH (t {{id: row.target_id}})
            MERGE (s)-[r:{rel_type}]->(t)
            SET r.logic_basis = row.logic_basis
            """
            for batch in _batches(group, batch_size):
                session.run(query, rows=batch)
                total += len(batch)
    return total


def merge_questions(driver: Driver, questions: list[dict], batch_size: int = 500) -> int:
    """Question 노드 MERGE + ABOUT 관계 연결."""
    query = """
    UNWIND $rows AS row
    MERGE (q:Question {id: row.id})
    SET q.question_type = row.question_type,
        q.difficulty    = row.difficulty,
        q.status        = row.status
    WITH q, row
    MATCH (n {id: row.entity_id})
    MERGE (q)-[:ABOUT]->(n)
    """
    total = 0
    with driver.session() as session:
        for batch in _batches(questions, batch_size):
            session.run(query, rows=batch)
            total += len(batch)
    return total


def reset_graph(driver: Driver) -> None:
    """Neo4j 전체 노드·관계 삭제 (--reset 전용)."""
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
