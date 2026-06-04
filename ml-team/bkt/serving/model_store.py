"""
BKT Model artifact 로딩 및 캐싱.

startup 시 최신 artifact를 자동 로드한다.
BKT_ARTIFACT_DIR 환경변수로 경로를 오버라이드할 수 있다.
"""
import json
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))  # ml-team/bkt/
import bkt_model
from pyBKT.models import Model

_DEFAULT_ARTIFACT_DIR = Path(__file__).parent.parent.parent.parent / ".data" / "ml_artifact" / "bkt"

_model: Model | None = None
_params: dict[str, dict] = {}   # {node_id: {p_l0, p_t, p_g, p_s, ...}}
_model_info: dict = {}


def _artifact_dir() -> Path:
    return Path(os.getenv("BKT_ARTIFACT_DIR", str(_DEFAULT_ARTIFACT_DIR)))


def _latest_run_dir() -> Path | None:
    """bkt_{ts}/ 폴더 중 가장 최신 항목 반환."""
    base = _artifact_dir()
    if not base.exists():
        return None
    runs = sorted(
        [d for d in base.iterdir() if d.is_dir() and d.name.startswith("bkt_")],
        key=lambda d: d.name,
    )
    return runs[-1] if runs else None


def load(run_dir: Path | None = None) -> dict:
    """
    artifact 로드. run_dir 미지정 시 최신 항목 자동 선택.
    반환: model_info dict
    """
    global _model, _params, _model_info

    target = run_dir or _latest_run_dir()
    if target is None:
        raise FileNotFoundError(
            f"BKT artifact 없음 — {_artifact_dir()} 에 학습 결과가 없습니다."
        )

    pkl_path    = target / "model.pkl"
    params_path = target / "params.json"

    if not pkl_path.exists():
        raise FileNotFoundError(f"model.pkl 없음: {pkl_path}")

    _model = bkt_model.load_model(pkl_path)

    # params.json 에서 노드별 파라미터 로드
    _params = {}
    if params_path.exists():
        data = json.loads(params_path.read_text())
        for entry in data.get("params", []):
            node_id = entry["node_id"]
            _params[node_id] = {
                "p_l0":        entry.get("p_l0"),
                "p_t":         entry.get("p_t"),
                "p_g":         entry.get("p_g"),
                "p_s":         entry.get("p_s"),
                "n_students":  entry.get("n_students"),
                "n_responses": entry.get("n_responses"),
            }

    _model_info = {
        "run_dir":    str(target),
        "trained_at": target.name[len("bkt_"):],
        "n_nodes":    len(_params),
        "artifact":   str(pkl_path),
    }
    return _model_info


def get_model() -> Model:
    if _model is None:
        raise RuntimeError("모델이 로드되지 않았습니다. /reload를 호출하세요.")
    return _model


def get_params(node_id: str) -> dict:
    """노드 파라미터 반환. 없으면 default 사용."""
    return _params.get(node_id, dict(bkt_model.DEFAULT_PARAMS))


def get_all_params() -> dict[str, dict]:
    return _params


def get_model_info() -> dict:
    return _model_info
