"""serving API 기본 기능 테스트 — artifact_dir 픽스처로 실제 모델 사용."""
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "serving"))
from conftest import NODE_A, NODE_B


@pytest.fixture(scope="module")
def client(artifact_dir):
    os.environ["BKT_ARTIFACT_DIR"] = str(artifact_dir)

    import importlib, model_store, main
    importlib.reload(model_store)
    importlib.reload(main)

    with TestClient(main.app) as c:
        yield c


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res.json()["model_loaded"] is True


def test_predict_returns_state_predictions(client):
    res = client.post("/predict", json={
        "node_id": NODE_A, "student_id": "s1", "responses": [0, 1, 1],
    })
    assert res.status_code == 200
    body = res.json()
    assert len(body["state_predictions"]) == 3
    assert 0.0 <= body["current_mastery"] <= 1.0


def test_predict_empty_responses_rejected(client):
    res = client.post("/predict", json={
        "node_id": NODE_A, "student_id": "s1", "responses": [],
    })
    assert res.status_code == 422


def test_get_node_params(client):
    res = client.get(f"/params/{NODE_A}")
    assert res.status_code == 200
    body = res.json()
    for k in ("p_l0", "p_t", "p_g", "p_s"):
        assert 0.0 < body[k] < 1.0


def test_list_params(client):
    res = client.get("/params")
    assert res.status_code == 200
    node_ids = {item["node_id"] for item in res.json()}
    assert NODE_A in node_ids and NODE_B in node_ids


def test_reload(client):
    res = client.post("/reload")
    assert res.status_code == 200
    assert res.json()["n_nodes"] > 0
