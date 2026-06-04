"""DB 읽기/쓰기 헬퍼 — student_platform + virtual-student-api 두 DB 사용."""
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# 스크립트 위치 기준으로 상대경로 해석
_BASE = Path(__file__).parent


def get_engine(url: str) -> Engine:
    """상대경로 sqlite URL을 __file__ 기준 절대경로로 변환 후 엔진 생성."""
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        rel = url[len("sqlite:///"):]
        abs_path = (_BASE / rel).resolve()
        url = f"sqlite:///{abs_path}"
    connect_args = {"check_same_thread": False} if "sqlite" in url else {}
    return create_engine(url, connect_args=connect_args)


# ── virtual-student-api DB ────────────────────────────────────────────────────

def fetch_simulation_runs(engine: Engine, mode: str = "simple") -> dict[str, datetime]:
    """mode별 SimulationRun {run_id: created_at} 반환."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, created_at FROM simulation_runs WHERE mode = :mode"),
            {"mode": mode},
        ).fetchall()
    return {row[0]: row[1] for row in rows}


def fetch_persona_features(engine: Engine, vs_api_ids: list[str]) -> dict[str, dict]:
    """{vs_api_id: {feature_key: value}} 반환."""
    if not vs_api_ids:
        return {}
    placeholders = ", ".join(f":id{i}" for i in range(len(vs_api_ids)))
    params: dict[str, Any] = {f"id{i}": vid for i, vid in enumerate(vs_api_ids)}
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                f"SELECT virtual_student_id, feature_key, value "
                f"FROM virtual_student_feature_values "
                f"WHERE virtual_student_id IN ({placeholders})"
            ),
            params,
        ).fetchall()
    result: dict[str, dict] = {}
    for vs_id, key, val in rows:
        result.setdefault(vs_id, {})[key] = val
    return result


# ── student_platform DB ───────────────────────────────────────────────────────

def fetch_virtual_sessions(
    engine: Engine, run_ids: list[str]
) -> list[dict]:
    """
    지정 run_id에 해당하는 virtual_study_sessions 조회.
    virtual_students와 JOIN하여 vs_api_id 포함.
    """
    if not run_ids:
        return []
    placeholders = ", ".join(f":r{i}" for i in range(len(run_ids)))
    params: dict[str, Any] = {f"r{i}": rid for i, rid in enumerate(run_ids)}
    with engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT vss.id        AS session_id,
                       vss.student_id,
                       vs.vs_api_id,
                       vss.node_id,
                       vss.subject_id,
                       vss.run_id,
                       vss.is_correct,
                       vss.score,
                       vss.created_at
                FROM virtual_study_sessions vss
                JOIN virtual_students vs ON vs.id = vss.student_id
                WHERE vss.run_id IN ({placeholders})
                  AND vss.is_correct IS NOT NULL
            """),
            params,
        ).fetchall()
    return [
        {
            "session_id": r[0],
            "student_id": r[1],
            "vs_api_id":  r[2],
            "node_id":    r[3],
            "subject_id": r[4],
            "run_id":     r[5],
            "is_correct": bool(r[6]),
            "score":      r[7],
            "created_at": r[8],
        }
        for r in rows
    ]


def upsert_bkt_params(engine: Engine, params: list[dict]) -> int:
    """bkt_node_params INSERT OR REPLACE."""
    if not params:
        return 0
    with engine.begin() as conn:
        for p in params:
            conn.execute(
                text("""
                    INSERT INTO bkt_node_params
                        (subject_id, node_id, p_l0, p_t, p_g, p_s,
                         n_students, n_responses, trained_at)
                    VALUES
                        (:subject_id, :node_id, :p_l0, :p_t, :p_g, :p_s,
                         :n_students, :n_responses, :trained_at)
                    ON CONFLICT(subject_id, node_id) DO UPDATE SET
                        p_l0        = excluded.p_l0,
                        p_t         = excluded.p_t,
                        p_g         = excluded.p_g,
                        p_s         = excluded.p_s,
                        n_students  = excluded.n_students,
                        n_responses = excluded.n_responses,
                        trained_at  = excluded.trained_at
                """),
                p,
            )
    return len(params)
