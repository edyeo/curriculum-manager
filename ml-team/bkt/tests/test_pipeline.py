"""pipeline.py 기본 기능 테스트 — DB 없이 mock 데이터 사용."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from pipeline import format_for_pyBKT, fit_all
from conftest import NODE_A, NODE_B, SUBJECT_ID


@pytest.fixture(scope="module")
def formatted(mock_sessions, mock_run_map):
    return format_for_pyBKT(mock_sessions, mock_run_map)


# ── format_for_pyBKT ──────────────────────────────────────────────────────────

def test_format_required_columns(formatted):
    df, _ = formatted
    assert {"user_id", "skill_name", "correct", "order_id"}.issubset(df.columns)


def test_format_correct_values_binary(formatted):
    df, _ = formatted
    assert set(df["correct"].unique()).issubset({0, 1})


def test_format_node_counts(formatted):
    _, counts = formatted
    assert counts[NODE_A] == 60  # 5명 × 3 run × 4문제
    assert counts[NODE_B] == 60


def test_format_run_order_ascending(formatted):
    df, _ = formatted
    for (uid, skill), group in df.groupby(["user_id", "skill_name"]):
        assert list(group["order_id"]) == sorted(group["order_id"].tolist())


# ── fit_all ───────────────────────────────────────────────────────────────────

_CFG = {
    "bkt": {
        "min_responses_per_node": 30,
        "num_fits": 2,
        "seed": 42,
        "default_params": {"p_l0": 0.3, "p_t": 0.1, "p_g": 0.2, "p_s": 0.1},
    }
}


@pytest.fixture(scope="module")
def fit_results(formatted):
    df, counts = formatted
    _, results = fit_all(df, counts, _CFG, SUBJECT_ID)
    return results


def test_fit_all_covers_all_nodes(fit_results):
    node_ids = {r["node_id"] for r in fit_results}
    assert NODE_A in node_ids and NODE_B in node_ids


def test_fit_all_params_in_range(fit_results):
    for r in fit_results:
        for k in ("p_l0", "p_t", "p_g", "p_s"):
            assert 0.0 < r[k] < 1.0


def test_fit_all_subject_id(fit_results):
    assert all(r["subject_id"] == SUBJECT_ID for r in fit_results)


# ── save (artifact 구조) ──────────────────────────────────────────────────────

def test_save_artifact_structure(tmp_path, formatted):
    from pipeline import save
    df, counts = formatted
    model, results = fit_all(df, counts, _CFG, SUBJECT_ID)

    cfg = {
        "databases": {"student_platform": "sqlite:///:memory:"},
        "bkt": {"min_responses_per_node": 30},
        "output_dir": str(tmp_path),
    }
    with patch("pipeline.dbmod.upsert_bkt_params", return_value=len(results)):
        run_dir = save(cfg, model, df, results)

    assert (run_dir / "model.pkl").exists()
    assert (run_dir / "params.json").exists()
