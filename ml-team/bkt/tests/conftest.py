"""
공유 fixtures.

- mock_sessions / mock_run_map: DB 없이 format_for_pyBKT 테스트용
- artifact_dir: 실제 pyBKT 모델을 tmp 디렉토리에 학습·저장 (serving 테스트용)
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# ml-team/bkt/ 와 ml-team/bkt/serving/ 모두 import 가능하게
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "serving"))

import bkt_model

# ── Mock 학습 데이터 ──────────────────────────────────────────────────────────

SUBJECT_ID = "subj-test-0001"
NODE_A = "node_concept_A"
NODE_B = "node_concept_B"

RUN_IDS = ["run-001", "run-002", "run-003"]
MOCK_RUN_MAP = {
    "run-001": datetime(2026, 1, 1, 9, 0),
    "run-002": datetime(2026, 1, 2, 9, 0),
    "run-003": datetime(2026, 1, 3, 9, 0),
}

# 5명 학생 × 3 run × 노드 2개 × run당 4문제
def _make_mock_sessions() -> list[dict]:
    rng = np.random.default_rng(42)
    sessions = []
    sid = 1
    for student_idx in range(5):
        vs_api_id = f"vs-{student_idx:03d}"
        p_init = 0.2 + student_idx * 0.12   # 학생마다 초기 지식 다름

        for run_order, run_id in enumerate(RUN_IDS):
            p_now = min(0.95, p_init + run_order * 0.15)  # run 반복할수록 향상
            run_dt = MOCK_RUN_MAP[run_id]

            for node_id in [NODE_A, NODE_B]:
                for q_idx in range(4):
                    sessions.append({
                        "session_id": sid,
                        "student_id": student_idx + 1,
                        "vs_api_id":  vs_api_id,
                        "node_id":    node_id,
                        "subject_id": SUBJECT_ID,
                        "run_id":     run_id,
                        "is_correct": bool(rng.random() < p_now),
                        "score":      float(rng.random() < p_now),
                        "created_at": run_dt.replace(second=q_idx),
                    })
                    sid += 1
    return sessions


MOCK_SESSIONS = _make_mock_sessions()


@pytest.fixture(scope="session")
def mock_sessions():
    return MOCK_SESSIONS


@pytest.fixture(scope="session")
def mock_run_map():
    return MOCK_RUN_MAP


# ── Artifact fixture ───────────────────────────────────────────────────────────

def _build_artifact(run_dir: Path) -> None:
    """실제 pyBKT 모델을 학습해 run_dir에 저장."""
    rng = np.random.default_rng(0)
    rows = []
    for student in range(20):
        p = 0.2 + student * 0.03
        for node in [NODE_A, NODE_B]:
            for t in range(10):
                p_t = min(0.95, p + t * 0.04)
                rows.append({
                    "user_id":    f"s{student}",
                    "skill_name": node,
                    "correct":    int(rng.random() < p_t),
                    "order_id":   t,
                })

    df = pd.DataFrame(rows)
    model = bkt_model.fit(df, num_fits=3, seed=42)

    run_dir.mkdir(parents=True, exist_ok=True)
    bkt_model.save_model(model, run_dir / "model.pkl")

    node_params = bkt_model.params_to_dict(model)
    params_list = [
        {
            "node_id":     nid,
            "subject_id":  SUBJECT_ID,
            **p,
            "n_students":  20,
            "n_responses": 200,
        }
        for nid, p in node_params.items()
    ]
    (run_dir / "params.json").write_text(
        json.dumps({
            "trained_at": "20260101T000000",
            "run_dir":    str(run_dir),
            "params":     params_list,
        }, ensure_ascii=False, indent=2)
    )


@pytest.fixture(scope="session")
def artifact_dir(tmp_path_factory):
    """session 범위 — 한 번만 학습하고 모든 테스트가 공유."""
    base = tmp_path_factory.mktemp("bkt_artifacts")
    run_dir = base / "bkt_20260101T000000"
    _build_artifact(run_dir)
    return base
