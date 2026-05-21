"""SQLite Extract 헬퍼 — contents_manager DB에서 KG 데이터 읽기."""
import json
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def get_engine(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


def fetch_subjects(engine: Engine, subject_id: str | None = None) -> list[dict]:
    """subjects 테이블에서 Subject 목록 조회. 없으면 kg_nodes.subject_id로 유추."""
    params: dict[str, Any] = {}
    where = ""
    if subject_id:
        where = "WHERE id = :subj"
        params["subj"] = subject_id

    with engine.connect() as conn:
        # subjects 테이블이 있는 경우 직접 조회
        try:
            rows = conn.execute(
                text(f"SELECT id, name FROM subjects {where}"), params
            ).fetchall()
            return [{"id": row[0], "name": row[1]} for row in rows]
        except Exception:
            pass

        # subjects 테이블 없음 → kg_nodes.subject_id로 유추 (id=subject_id, name=subject_id)
        extra = "AND subject_id = :subj" if subject_id else ""
        if subject_id:
            params["subj"] = subject_id
        rows = conn.execute(
            text(f"SELECT DISTINCT subject_id FROM kg_nodes WHERE subject_id IS NOT NULL {extra}"),
            params,
        ).fetchall()
        return [{"id": row[0], "name": row[0]} for row in rows]


def fetch_nodes(
    engine: Engine,
    subject_id: str | None = None,
    node_types: list[str] | None = None,
) -> list[dict]:
    """kg_nodes에서 KG 노드 목록 조회."""
    conditions = []
    params: dict[str, Any] = {}

    if subject_id:
        conditions.append("subject_id = :subj")
        params["subj"] = subject_id

    if node_types:
        placeholders = ", ".join(f":nt{i}" for i in range(len(node_types)))
        conditions.append(f"type IN ({placeholders})")
        for i, nt in enumerate(node_types):
            params[f"nt{i}"] = nt

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT id, subject_id, type, depth, name, description, metadata
                FROM kg_nodes {where}
            """),
            params,
        ).fetchall()

    nodes = []
    for row in rows:
        metadata = row[6]
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        nodes.append({
            "id": row[0],
            "subject_id": row[1],
            "type": row[2],
            "depth": row[3],
            "name": row[4],
            "description": row[5] or "",
            "metadata": json.dumps(metadata or {}, ensure_ascii=False),
        })
    return nodes


def fetch_edges(engine: Engine, subject_id: str | None = None) -> list[dict]:
    """kg_edges에서 KG 엣지 목록 조회."""
    params: dict[str, Any] = {}
    where = ""
    if subject_id:
        where = "WHERE subject_id = :subj"
        params["subj"] = subject_id

    with engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT id, subject_id, source_id, target_id, relation_type, logic_basis
                FROM kg_edges {where}
            """),
            params,
        ).fetchall()

    return [
        {
            "id": row[0],
            "subject_id": row[1],
            "source_id": row[2],
            "target_id": row[3],
            "relation_type": row[4],
            "logic_basis": row[5] or "",
        }
        for row in rows
    ]


def fetch_questions(
    engine: Engine,
    subject_id: str | None = None,
    status: str = "published",
) -> list[dict]:
    """question_items에서 주요 property만 조회 (content 제외)."""
    params: dict[str, Any] = {"status": status}
    extra = ""
    if subject_id:
        extra = "AND kn.subject_id = :subj"
        params["subj"] = subject_id

    with engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT qi.id, qi.entity_id, qi.question_type, qi.difficulty, qi.status
                FROM question_items qi
                JOIN kg_nodes kn ON kn.id = qi.entity_id
                WHERE qi.status = :status {extra}
            """),
            params,
        ).fetchall()

    return [
        {
            "id": row[0],
            "entity_id": row[1],
            "question_type": row[2],
            "difficulty": row[3] or "medium",
            "status": row[4],
        }
        for row in rows
    ]
