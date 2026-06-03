"""
BKT Serving API

학습된 pyBKT artifact를 로드하여 학생별 지식 상태를 추론한다.

Endpoints:
  GET  /health              서비스 상태 + 로드된 모델 정보
  GET  /models/current      현재 로드된 모델 상세 정보
  POST /reload              최신 artifact 재로드
  POST /predict             응답 이력 → P(knows) 시퀀스
  GET  /params/{node_id}    노드별 BKT 파라미터 조회
  GET  /params              전체 노드 파라미터 목록
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import model_store
from schemas import ModelInfo, NodeParams, PredictRequest, PredictResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        info = model_store.load()
        print(f"[BKT Serving] 모델 로드 완료: {info['run_dir']} ({info['n_nodes']}개 노드)")
    except FileNotFoundError as e:
        print(f"[BKT Serving] 경고: {e} — /reload 로 수동 로드 가능")
    yield


app = FastAPI(title="BKT Serving API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    info = model_store.get_model_info()
    return {
        "status": "ok",
        "model_loaded": bool(info),
        "trained_at":   info.get("trained_at"),
        "n_nodes":      info.get("n_nodes"),
    }


# ── Model info ────────────────────────────────────────────────────────────────

@app.get("/models/current", response_model=ModelInfo)
def get_current_model():
    info = model_store.get_model_info()
    if not info:
        raise HTTPException(status_code=503, detail="모델이 로드되지 않았습니다.")
    return ModelInfo(**info)


@app.post("/reload", response_model=ModelInfo)
def reload_model():
    """최신 artifact를 디스크에서 재로드한다."""
    try:
        info = model_store.load()
        return ModelInfo(**info)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Predict ───────────────────────────────────────────────────────────────────

@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    """
    응답 이력을 받아 각 시점의 P(L_t=1) 시퀀스와 현재 마스터리를 반환한다.
    state_predictions[t] = P(L_t=1 | x_1,...,x_t)
    """
    if not req.responses:
        raise HTTPException(status_code=422, detail="responses가 비어있습니다.")
    if any(r not in (0, 1) for r in req.responses):
        raise HTTPException(status_code=422, detail="responses는 0 또는 1만 허용합니다.")

    try:
        m = model_store.get_model()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    df = pd.DataFrame({
        "user_id":    [req.student_id] * len(req.responses),
        "skill_name": [req.node_id]    * len(req.responses),
        "correct":    req.responses,
        "order_id":   list(range(len(req.responses))),
    })

    try:
        result_df = m.predict(data=df)
    except ValueError as e:
        if "no matching skills" in str(e):
            raise HTTPException(
                status_code=404,
                detail=f"node_id '{req.node_id}'는 학습된 모델에 없습니다.",
            )
        raise

    params = model_store.get_params(req.node_id)
    state_preds = [
        round(float(v), 4) if (v == v) else params["p_l0"]  # NaN 방어
        for v in result_df["state_predictions"].tolist()
    ]

    return PredictResponse(
        node_id=req.node_id,
        student_id=req.student_id,
        state_predictions=state_preds,
        current_mastery=state_preds[-1],
        params={k: v for k, v in params.items() if k in ("p_l0", "p_t", "p_g", "p_s")},
    )


# ── Params ────────────────────────────────────────────────────────────────────

@app.get("/params/{node_id}", response_model=NodeParams)
def get_node_params(node_id: str):
    params = model_store.get_params(node_id)
    return NodeParams(node_id=node_id, **params)


@app.get("/params", response_model=list[NodeParams])
def list_params():
    all_params = model_store.get_all_params()
    return [NodeParams(node_id=nid, **p) for nid, p in all_params.items()]


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8007))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
