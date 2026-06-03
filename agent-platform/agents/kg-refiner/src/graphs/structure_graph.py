"""T_STRUCTURE — 이상 노드 검출 → 검출 노드 중심 서브그래프 도출 →
컨텍스트 주입 후 재정의(수정) 제안 LangGraph.

흐름:
  ① detect_targets : node-resolution tool로 이상/무변별 노드 검출
  ② fetch_subgraphs: 각 검출 노드를 root 로 subgraph tool 호출 (주변 맥락 확보)
  ③ propose        : 검출 정보 + 서브그래프를 컨텍스트로 주입해 수정안 제시
  ④ validate / write

subgraph·node-resolution 은 agent-platform/shared 공통 tool 을 통해 호출한다.
"""
import datetime
import json
import os
from pathlib import Path
from typing import Any, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from shared.kg_analytics_tools import detect_node_anomalies, fetch_subgraph

SKILL_PATH = Path(__file__).parent.parent.parent / "skills" / "structure_skill.md"


def _load_skill() -> str:
    return SKILL_PATH.read_text()


# ── State ─────────────────────────────────────────────────────────────────────

class StructureState(TypedDict):
    subject_id: str
    top_k: int
    min_students: int
    min_successors: int
    depth: int
    detected_nodes: list[dict]
    subgraphs: dict
    proposals: list[dict]
    validated_proposals: list[dict]
    output_path: str


# ── Structured output ─────────────────────────────────────────────────────────

class NodeSuggestion(BaseModel):
    name: str
    type: str
    depth: int
    description: str = ""


class Proposal(BaseModel):
    type: str = Field(description="split|merge|relink|reorder|add_edge|remove_edge|redefine")
    target_node_id: str
    target_node_name: str = ""
    detection: str = Field(default="", description="anomaly|degenerate — 검출 근거 유형")
    reason: str
    suggestion: dict[str, Any] = Field(default_factory=dict)
    ontology_valid: bool = True
    confidence: float = Field(ge=0.0, le=1.0)


class ReviewOutput(BaseModel):
    proposals: list[Proposal]


class ValidationOutput(BaseModel):
    validated_proposals: list[Proposal]


# ── Nodes ─────────────────────────────────────────────────────────────────────

def detect_targets(state: StructureState) -> dict:
    """① node-resolution tool 로 이상/무변별 노드 검출."""
    data = detect_node_anomalies.invoke({
        "subject_id": state["subject_id"],
        "top_k": state.get("top_k", 50),
        "min_students": state.get("min_students", 10),
        "min_successors": state.get("min_successors", 3),
    })

    anomalies = data.get("anomalies", [])
    degenerate = data.get("degenerate_nodes", [])
    detected = [
        {"node_id": a["node_id"], "name": a.get("name", ""), "detection": "anomaly", "info": a}
        for a in anomalies
    ] + [
        {"node_id": d["node_id"], "name": d.get("name", ""), "detection": "degenerate", "info": d}
        for d in degenerate
    ]
    print(
        f"[T_STRUCTURE] 검출 노드 {len(detected)}개 "
        f"(이상 {len(anomalies)} / 무변별 {len(degenerate)}) — subject={state['subject_id']}"
    )
    return {"detected_nodes": detected}


def fetch_subgraphs(state: StructureState) -> dict:
    """② 검출 노드를 root 로 subgraph tool 호출 — 주변 맥락 확보."""
    subgraphs: dict = {}
    depth = state.get("depth") or 1
    for node in state["detected_nodes"]:
        nid = node["node_id"]
        sg = fetch_subgraph.invoke({
            "subject_id": state["subject_id"],
            "root_node_id": nid,
            "depth": depth,
        })
        subgraphs[nid] = sg
    print(f"[T_STRUCTURE] 서브그래프 {len(subgraphs)}개 도출 (depth={depth})")
    return {"subgraphs": subgraphs}


def propose(state: StructureState) -> dict:
    """③ 검출 정보 + 서브그래프를 컨텍스트로 주입해 수정안 제시."""
    detected = state["detected_nodes"]
    if not detected:
        print("[T_STRUCTURE] 검출 노드 없음 — 종료")
        return {"proposals": []}

    subgraphs = state["subgraphs"]
    context_blocks = []
    for node in detected:
        sg = subgraphs.get(node["node_id"], {})
        context_blocks.append({
            "detected_node": {
                "node_id": node["node_id"],
                "name": node["name"],
                "detection": node["detection"],
                "info": node["info"],
            },
            "subgraph": {
                "node_count": sg.get("node_count", 0),
                "edge_count": sg.get("edge_count", 0),
                "nodes": sg.get("nodes", []),
                "edges": sg.get("edges", []),
                "metrics": sg.get("metrics", {}),
            },
        })

    llm = ChatOpenAI(model="claude-sonnet-4-6", temperature=0).with_structured_output(ReviewOutput)
    prompt = f"""{_load_skill()}

## Detected Nodes with Local Subgraph Context

각 항목은 통계적으로 검출된 노드와 그 노드를 중심으로 한 주변 서브그래프다.
- detection=anomaly: 후행 노드 간 숙련도 상관이 낮음 → 개념 범위 과대(split 후보)
- detection=degenerate: 전 학생 정답/오답으로 변별력 없음 → 개념·문제 재정의(redefine) 후보

서브그래프의 metrics(차수·후행 수·고립/리프 노드·depth 분포)를 활용해
각 노드에 대한 구체적 재정의(수정) 방안을 제시하라.

{json.dumps(context_blocks, ensure_ascii=False, indent=2)}
"""
    result: ReviewOutput = llm.invoke(prompt)
    return {"proposals": [p.model_dump() for p in result.proposals]}


def validate(state: StructureState) -> dict:
    proposals = state["proposals"]
    if not proposals:
        return {"validated_proposals": []}

    llm = ChatOpenAI(model="claude-sonnet-4-6", temperature=0).with_structured_output(ValidationOutput)
    prompt = f"""{_load_skill()}

## Validation Task
Review these proposals for ontology rule compliance and filter out invalid ones.
Set `ontology_valid=false` for proposals that violate ontology rules.

Proposals:
{json.dumps(proposals, ensure_ascii=False, indent=2)}
"""
    result: ValidationOutput = llm.invoke(prompt)
    valid = [p.model_dump() for p in result.validated_proposals if p.ontology_valid]
    return {"validated_proposals": valid}


def write(state: StructureState) -> dict:
    output_dir = Path("logs")
    output_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    path = output_dir / f"structure_proposals_{state['subject_id'][:8]}_{ts}.json"

    payload = {
        "subject_id": state["subject_id"],
        "trigger": "T_STRUCTURE",
        "generated_at": ts,
        "detected_count": len(state["detected_nodes"]),
        "proposal_count": len(state["validated_proposals"]),
        "proposals": state["validated_proposals"],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"[T_STRUCTURE] 제안 저장: {path}  ({len(state['validated_proposals'])}개)")
    return {"output_path": str(path)}


# ── Graph ─────────────────────────────────────────────────────────────────────

def _route_entry(state: StructureState) -> str:
    """detected_nodes가 외부에서 주입되면 검출 단계를 건너뛴다."""
    return "fetch_subgraphs" if state.get("detected_nodes") else "detect_targets"


def build_structure_graph() -> StateGraph:
    g = StateGraph(StructureState)
    g.add_node("detect_targets", detect_targets)
    g.add_node("fetch_subgraphs", fetch_subgraphs)
    g.add_node("propose", propose)
    g.add_node("validate", validate)
    g.add_node("write", write)

    # 외부 검출 노드 주입 시 detect_targets 스킵
    g.add_conditional_edges(START, _route_entry, {
        "detect_targets": "detect_targets",
        "fetch_subgraphs": "fetch_subgraphs",
    })
    g.add_edge("detect_targets", "fetch_subgraphs")
    g.add_edge("fetch_subgraphs", "propose")
    g.add_edge("propose", "validate")
    g.add_edge("validate", "write")
    g.add_edge("write", END)

    return g.compile()
