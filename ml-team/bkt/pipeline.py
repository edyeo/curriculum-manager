"""
BKT 학습 파이프라인

Usage:
  python pipeline.py                    # 전체 실행 (config.yaml의 subject_id 사용)
  python pipeline.py --evaluate         # 학습 후 AUC/RMSE 출력
  python pipeline.py --min-responses 50 # 최소 관측 수 오버라이드
"""
import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

import bkt_model
import db as dbmod


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


# ── Step 1: Extract ────────────────────────────────────────────────────────────

def extract(cfg: dict) -> tuple[list[dict], dict[str, datetime], dict[str, dict]]:
    sp_engine = dbmod.get_engine(cfg["databases"]["student_platform"])
    vs_engine = dbmod.get_engine(cfg["databases"]["virtual_student"])
    subject_id = cfg["subject_id"]

    print("[1/4] 세션 데이터 추출 중...")

    run_map = dbmod.fetch_simulation_runs(vs_engine, mode="simple")
    if not run_map:
        print("  → simple mode SimulationRun 없음 — 종료")
        return [], {}, {}
    print(f"  → simple run {len(run_map)}개")

    sessions = dbmod.fetch_virtual_sessions(sp_engine, list(run_map.keys()))
    if subject_id:
        sessions = [s for s in sessions if s["subject_id"] == subject_id]
    if not sessions:
        print("  → 해당 subject의 세션 없음 — 종료")
        return [], {}, {}

    vs_api_ids = list({s["vs_api_id"] for s in sessions})
    personas = dbmod.fetch_persona_features(vs_engine, vs_api_ids)

    students = len({s["student_id"] for s in sessions})
    nodes    = len({s["node_id"] for s in sessions})
    print(f"  → {len(sessions)}개 응답 ({students}명 학생, {nodes}개 노드)")

    return sessions, run_map, personas


# ── Step 2: Format ─────────────────────────────────────────────────────────────

def format_for_pyBKT(
    sessions: list[dict],
    run_map: dict[str, datetime],
) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    pyBKT 입력 DataFrame 구성 + 노드별 응답 수 집계.

    반환:
      df           — user_id, skill_name, correct, order_id
      node_counts  — {node_id: n_responses} (min_responses 필터용)
    """
    print("[2/4] run 순서 정렬 및 DataFrame 구성 중...")

    def _to_dt(v) -> datetime:
        if isinstance(v, datetime):
            return v
        return datetime.fromisoformat(str(v))

    sorted_run_ids = sorted(run_map.keys(), key=lambda r: _to_dt(run_map[r]))

    # (student_id, node_id) → {run_id: [(created_at, is_correct), ...]}
    bucket: dict[tuple, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for s in sessions:
        key = (s["student_id"], s["node_id"])
        bucket[key][s["run_id"]].append((s["created_at"], int(s["is_correct"])))

    rows: list[dict] = []
    node_counts: dict[str, int] = defaultdict(int)

    for (student_id, node_id), run_data in bucket.items():
        order = 0
        for run_id in sorted_run_ids:
            if run_id not in run_data:
                continue
            responses = sorted(run_data[run_id], key=lambda x: x[0] or "")
            for _, correct in responses:
                rows.append({
                    "user_id":    str(student_id),
                    "skill_name": node_id,
                    "correct":    correct,
                    "order_id":   order,
                })
                order += 1
                node_counts[node_id] += 1

    df = pd.DataFrame(rows)
    total_seqs = len({(r["user_id"], r["skill_name"]) for r in rows})
    print(f"  → {len(node_counts)}개 노드, {total_seqs}개 학생-노드 시퀀스, {len(rows)}개 응답")
    return df, dict(node_counts)


# ── Step 3: Fit ────────────────────────────────────────────────────────────────

def fit_all(
    df: pd.DataFrame,
    node_counts: dict[str, int],
    cfg: dict,
    subject_id: str,
) -> tuple[object, list[dict]]:
    """
    pyBKT 모델 학습 후 파라미터 dict 반환.

    min_responses 미달 노드는 default_params 적용하고 학습 DataFrame에서 제외.
    반환: (fitted_model, results_list)
    """
    bkt_cfg   = cfg["bkt"]
    min_resp  = bkt_cfg["min_responses_per_node"]
    default   = bkt_cfg["default_params"]
    num_fits  = bkt_cfg.get("num_fits", 5)
    seed      = bkt_cfg.get("seed", 42)

    print(f"[3/4] pyBKT 학습 중... (min_responses={min_resp}, num_fits={num_fits})")

    fit_nodes     = {n for n, c in node_counts.items() if c >= min_resp}
    default_nodes = {n for n in node_counts if n not in fit_nodes}

    fitted_model = None
    fitted_params: dict[str, dict] = {}

    if fit_nodes:
        fit_df = df[df["skill_name"].isin(fit_nodes)].copy()
        fitted_model = bkt_model.fit(fit_df, num_fits=num_fits, seed=seed)
        fitted_params = bkt_model.params_to_dict(fitted_model, default=default)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    results: list[dict] = []

    for node_id, n_resp in node_counts.items():
        if node_id in fit_nodes and node_id in fitted_params:
            params = fitted_params[node_id]
            tag = "EM"
        else:
            params = {k: float(v) for k, v in default.items()}
            tag = "default"

        # node별 student 수
        n_students = df[df["skill_name"] == node_id]["user_id"].nunique()
        results.append({
            "subject_id":  subject_id,
            "node_id":     node_id,
            **params,
            "n_students":  n_students,
            "n_responses": n_resp,
            "trained_at":  now,
        })
        print(f"  [{tag:7s}] {node_id[:50]}  p_l0={params['p_l0']:.3f} p_t={params['p_t']:.3f}  n={n_resp}")

    print(f"  → EM {len(fit_nodes)}개 / 기본값 {len(default_nodes)}개")
    return fitted_model, results


# ── Step 4: Save ───────────────────────────────────────────────────────────────

def save(
    cfg: dict,
    model: object,
    fit_df: pd.DataFrame,
    results: list[dict],
) -> Path:
    sp_engine = dbmod.get_engine(cfg["databases"]["student_platform"])
    base_dir  = (Path(__file__).parent / cfg.get("output_dir", "../../.data/ml_artifact/bkt")).resolve()

    ts         = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_dir    = base_dir / f"bkt_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    print("[4/4] 저장 중...")

    # Model artifact
    if model is not None:
        pkl_path = run_dir / "model.pkl"
        bkt_model.save_model(model, pkl_path)
        print(f"  → model.pkl: {pkl_path}")

    # 파라미터 요약 JSON
    def _serialize(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Not serializable: {type(obj)}")

    json_path = run_dir / "params.json"
    json_path.write_text(
        json.dumps(
            {"trained_at": ts, "run_dir": str(run_dir), "params": results},
            default=_serialize, ensure_ascii=False, indent=2,
        )
    )
    print(f"  → params.json: {json_path}")

    # DB upsert
    upserted = dbmod.upsert_bkt_params(sp_engine, results)
    print(f"  → DB: bkt_node_params {upserted}개 upsert")

    return run_dir


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BKT 학습 파이프라인")
    parser.add_argument("--config", default=str(Path(__file__).parent / "config.yaml"))
    parser.add_argument("--evaluate", action="store_true", help="학습 후 AUC/RMSE 출력")
    parser.add_argument("--min-responses", type=int, help="최소 관측 수 오버라이드")
    args = parser.parse_args()

    cfg = load_config(args.config)

    if not cfg.get("subject_id"):
        print("ERROR: config.yaml의 subject_id를 설정하세요.")
        return

    if args.min_responses:
        cfg["bkt"]["min_responses_per_node"] = args.min_responses

    subject_id = cfg["subject_id"]

    sessions, run_map, personas = extract(cfg)
    if not sessions:
        return

    df, node_counts = format_for_pyBKT(sessions, run_map)
    if df.empty:
        print("DataFrame 비어있음 — 종료")
        return

    fitted_model, results = fit_all(df, node_counts, cfg, subject_id)

    fit_nodes = {r["node_id"] for r in results if r["n_responses"] >= cfg["bkt"]["min_responses_per_node"]}
    fit_df    = df[df["skill_name"].isin(fit_nodes)] if fit_nodes else df

    run_dir = save(cfg, fitted_model, fit_df, results)

    if args.evaluate and fitted_model is not None:
        print("\n[평가] pyBKT AUC / RMSE 계산 중...")
        eval_df = df[df["skill_name"].isin(fit_nodes)] if fit_nodes else pd.DataFrame()
        if not eval_df.empty:
            metrics = bkt_model.evaluate(fitted_model, eval_df)
            print(f"  AUC : {metrics['auc']}")
            print(f"  RMSE: {metrics['rmse']}")
            print(f"  N   : {metrics['n']}개 응답")
        else:
            print("  평가 가능한 노드 없음")

    print()
    print("=" * 50)
    print(f"완료: {len(results)}개 노드 → {run_dir}")


if __name__ == "__main__":
    main()
