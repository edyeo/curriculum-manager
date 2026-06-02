"""DB 읽기/쓰기 헬퍼 — SQLAlchemy Core (text query)."""
import json
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def get_engine(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


# ── Extract ───────────────────────────────────────────────────────────────────

def fetch_virtual_students(engine: Engine, subject_id: str, max_students: int) -> list[dict]:
    """student_platform.virtual_students 조회 (vs_api_id 포함)."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT id, vs_api_id, name, subject_id FROM virtual_students "
                "WHERE subject_id = :subj LIMIT :lim"
            ),
            {"subj": subject_id, "lim": max_students},
        ).fetchall()
    return [
        {"id": row[0], "vs_api_id": row[1], "name": row[2], "subject_id": row[3]}
        for row in rows
    ]


def fetch_virtual_student_features(vs_engine: Engine, vs_api_id: str) -> dict:
    """virtual-student DB에서 feature values 조회 → persona dict 반환."""
    with vs_engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT feature_key, value FROM virtual_student_feature_values "
                "WHERE virtual_student_id = :vid"
            ),
            {"vid": vs_api_id},
        ).fetchall()
    return {row[0]: row[1] for row in rows}


def fetch_questions(
    engine: Engine,
    subject_id: str,
    question_types: list[str],
    max_questions: int,
) -> list[dict]:
    """contents_manager DB에서 published 문제 목록 조회."""
    placeholders = ", ".join(f":qt{i}" for i in range(len(question_types)))
    params: dict[str, Any] = {"subj": subject_id, "lim": max_questions}
    for i, qt in enumerate(question_types):
        params[f"qt{i}"] = qt

    with engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT qi.id, qi.entity_id, qi.question_text, qi.question_type,
                       qi.options, qi.correct_answer, qi.difficulty
                FROM question_items qi
                JOIN kg_nodes kn ON kn.id = qi.entity_id
                WHERE qi.status = 'published'
                  AND kn.subject_id = :subj
                  AND qi.question_type IN ({placeholders})
                LIMIT :lim
            """),
            params,
        ).fetchall()

    questions = []
    for row in rows:
        options = row[4]
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except (json.JSONDecodeError, TypeError):
                options = []
        questions.append({
            "id": row[0],
            "entity_id": row[1],
            "question_text": row[2],
            "question_type": row[3],
            "options": options or [],
            "correct_answer": row[5] or "",
            "difficulty": row[6] or "medium",
        })
    return questions


def fetch_answered_question_ids(engine: Engine, student_id: int) -> set[str]:
    """가상 학생이 이미 답변한 question_id 집합 반환."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT DISTINCT question_id FROM virtual_study_sessions WHERE student_id = :sid"),
            {"sid": student_id},
        ).fetchall()
    return {row[0] for row in rows}


# ── Load ──────────────────────────────────────────────────────────────────────

def insert_study_sessions(engine: Engine, rows: Sequence[dict]) -> int:
    """virtual_study_sessions 벌크 INSERT."""
    if not rows:
        return 0
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO virtual_study_sessions
                    (student_id, question_id, node_id, subject_id, run_id, user_answer,
                     is_correct, score, feedback, time_taken_seconds, created_at)
                VALUES
                    (:student_id, :question_id, :node_id, :subject_id, :run_id, :user_answer,
                     :is_correct, :score, :feedback, :time_taken_seconds, :created_at)
            """),
            list(rows),
        )
    return len(rows)


def upsert_node_mastery(
    engine: Engine,
    student_id: int,
    node_id: str,
    subject_id: str,
    is_correct: bool,
    score: float,
) -> None:
    """virtual_node_mastery EMA 업데이트."""
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT mastery_score, attempt_count FROM virtual_node_mastery "
                "WHERE student_id = :sid AND node_id = :nid"
            ),
            {"sid": student_id, "nid": node_id},
        ).fetchone()

        now = datetime.utcnow()
        if row:
            current = row[0]
            if is_correct:
                new_mastery = min(1.0, current + (1 - current) * 0.3 * score)
            else:
                new_mastery = max(0.0, current - current * 0.2)
            conn.execute(
                text("""
                    UPDATE virtual_node_mastery
                    SET mastery_score = :ms, attempt_count = :cnt, updated_at = :now
                    WHERE student_id = :sid AND node_id = :nid
                """),
                {"ms": round(new_mastery, 4), "cnt": row[1] + 1,
                 "sid": student_id, "nid": node_id, "now": now},
            )
        else:
            initial = min(1.0, 0.5 + 0.3 * score) if is_correct else max(0.0, 0.5 - 0.1)
            conn.execute(
                text("""
                    INSERT INTO virtual_node_mastery
                        (student_id, node_id, subject_id, mastery_score, attempt_count, updated_at)
                    VALUES (:sid, :nid, :subj, :ms, 1, :now)
                """),
                {"sid": student_id, "nid": node_id, "subj": subject_id,
                 "ms": round(initial, 4), "now": now},
            )
