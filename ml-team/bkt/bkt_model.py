"""
pyBKT 기반 BKT (Bayesian Knowledge Tracing) 래퍼.

fit / save / load / predict / evaluate 모두 pyBKT library를 그대로 사용한다.
"""
import math
from pathlib import Path

import pandas as pd
from pyBKT.models import Model

DEFAULT_PARAMS: dict = {"p_l0": 0.3, "p_t": 0.1, "p_g": 0.2, "p_s": 0.1}

_PARAM_MAP = {
    "prior":   "p_l0",
    "learns":  "p_t",
    "guesses": "p_g",
    "slips":   "p_s",
}


# ── fit / save / load ─────────────────────────────────────────────────────────

def fit(df: pd.DataFrame, num_fits: int = 5, seed: int = 42) -> Model:
    """
    pyBKT Model 학습.

    df 필수 컬럼: user_id, skill_name, correct, order_id
    defaults를 EM 초기값으로 주입해 prior=NaN 수렴 방지.
    """
    model = Model(seed=seed, num_fits=num_fits)
    model.fit(
        data=df,
        defaults={
            "prior":   DEFAULT_PARAMS["p_l0"],
            "learns":  DEFAULT_PARAMS["p_t"],
            "guesses": DEFAULT_PARAMS["p_g"],
            "slips":   DEFAULT_PARAMS["p_s"],
        },
    )
    return model


def save_model(model: Model, path: str | Path) -> None:
    """Model artifact를 pickle로 저장. save()는 인스턴스 메서드."""
    model.save(str(path))


def load_model(path: str | Path) -> Model:
    """저장된 Model artifact 로드. load()는 인스턴스 메서드."""
    m = Model()
    m.load(str(path))
    return m


# ── 파라미터 추출 ─────────────────────────────────────────────────────────────

def params_to_dict(
    model: Model,
    default: dict | None = None,
) -> dict[str, dict]:
    """
    model.params() DataFrame → {node_id: {p_l0, p_t, p_g, p_s}}.
    NaN / 범위 초과는 default로 대체.
    """
    fallback = default or DEFAULT_PARAMS
    raw = model.params()
    result: dict[str, dict] = {}

    for skill in raw.index.get_level_values(0).unique():
        extracted: dict[str, float] = {}
        valid = True
        for pybkt_key, our_key in _PARAM_MAP.items():
            try:
                val = float(raw.loc[(skill, pybkt_key, "default"), "value"])
            except KeyError:
                val = float("nan")
            if math.isnan(val) or not (0.0 < val < 1.0):
                valid = False
                break
            extracted[our_key] = round(val, 4)

        result[skill] = extracted if valid else {k: float(v) for k, v in fallback.items()}

    return result


# ── predict / evaluate ────────────────────────────────────────────────────────

def predict(model: Model, df: pd.DataFrame) -> pd.DataFrame:
    """
    pyBKT model.predict() 그대로 호출.
    반환 DataFrame에는 correct_predictions 컬럼이 포함된다.
    """
    return model.predict(data=df)


def evaluate(model: Model, df: pd.DataFrame) -> dict:
    """
    pyBKT model.evaluate()로 AUC / RMSE 계산.
    skill별 결과를 받으면 매크로 평균으로 집계.
    """
    try:
        raw = model.evaluate(data=df, metric=["auc", "rmse"])
        # 단일 dict 반환
        if isinstance(raw, dict) and "auc" in raw:
            return {
                "auc":  round(float(raw["auc"]), 4),
                "rmse": round(float(raw["rmse"]), 4),
                "n":    len(df),
            }
        # skill별 dict 반환 → 매크로 평균
        aucs, rmses = [], []
        for v in raw.values():
            if isinstance(v, dict):
                if "auc" in v and not math.isnan(float(v["auc"])):
                    aucs.append(float(v["auc"]))
                if "rmse" in v and not math.isnan(float(v["rmse"])):
                    rmses.append(float(v["rmse"]))
        return {
            "auc":  round(sum(aucs) / len(aucs), 4) if aucs else None,
            "rmse": round(sum(rmses) / len(rmses), 4) if rmses else None,
            "n":    len(df),
        }
    except Exception as e:
        return {"auc": None, "rmse": None, "n": len(df), "error": str(e)}
