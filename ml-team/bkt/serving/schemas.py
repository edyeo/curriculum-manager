from typing import Optional
from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    node_id: str
    student_id: str
    responses: list[int] = Field(..., description="시간 순 응답 이력 (0=오답, 1=정답)")


class PredictResponse(BaseModel):
    node_id: str
    student_id: str
    state_predictions: list[float] = Field(..., description="각 시점의 P(L_t=1 | x_1..x_t)")
    current_mastery: float          = Field(..., description="최신 지식 상태 추정값")
    params: dict                    = Field(..., description="해당 노드의 BKT 파라미터")


class NodeParams(BaseModel):
    node_id: str
    p_l0: float
    p_t: float
    p_g: float
    p_s: float
    n_students:  Optional[int] = None
    n_responses: Optional[int] = None


class ModelInfo(BaseModel):
    run_dir:    str
    trained_at: str
    n_nodes:    int
    artifact:   str  # model.pkl 절대 경로
