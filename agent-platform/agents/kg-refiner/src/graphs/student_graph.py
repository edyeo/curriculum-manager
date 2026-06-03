"""T_STUDENT — 이상 노드 탐지 후 원인 조사·재설계 제안 LangGraph."""
import json
import os
from pathlib import Path
from typing import TypedDict, Any

import httpx
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field


CONTENTS_MANAGER_URL = os.getenv("CONTENTS_MANAGER_URL", "http://localhost:8010")
SKILL_PATH = Path(__file__).parent.parent.parent / "skills" / "student_skill.md"


def _load_skill() -> str:
    return SKILL_PATH.read_text()


# ── State ─────────────────────────────────────────────────────────────────────

class StudentState(TypedDict):
    subject_id: str
    top_k: int
    min_students: int
    min_successors: int
    anomalies: list[dict]
    proposals: list[dict]
    validated_proposals: list[dict]
    output_path: str


# ── Structured output ─────────────────────────────────────────────────────────

class NewNode(BaseModel):
    name: str
    type: str = "Concept"
    depth: int
    description: str = ""


class EdgeRedistribution(BaseModel):
    successor_node_id: str
    assign_to_new_node_index: int = Field(description="0-based index into new_nodes list")


class SplitSuggestion(BaseModel):
    new_nodes: list[NewNode]
    edges_to_redistribute: list[EdgeRedistribution] = Field(default_factory=list)
    edges_to_remove: list[str] = Field(default_factory=list)


class AnomalyProposal(BaseModel):
    type: str = "split"
    target_node_id: str
    target_node_name: str
    anomaly_score: float
    sample_students: int
    reason: str
    suggestion: SplitSuggestion
    ontology_valid: bool = True
    confidence: float = Field(ge=0.0, le=1.0)


class InvestigationOutput(BaseModel):
    proposals: list[AnomalyProposal]


class ValidationOutput(BaseModel):
    validated_proposals: list[AnomalyProposal]


# ── Nodes ─────────────────────────────────────────────────────────────────────

def fetch_anomalies(state: StudentState) -> dict:
    resp = httpx.get(
        f"{CONTENTS_MANAGER_URL}/kg/analytics/node-resolution/{state['subject_id']}",
        params={
            "top_k": state.get("top_k", 50),
            "min_students": state.get("min_students", 10),
            "min_successors": state.get("min_successors", 3),
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    anomalies = data.get("anomalies", [])
    diag = data.get("diagnostics", {})
    print(f"[T_STUDENT] 이상 노드 {len(anomalies)}개 수신 (subject={state['subject_id']})")
    if diag:
        for line in diag.get("process", []):
            print(f"  · {line}")
        excluded = [e for e in diag.get("evaluated", []) if e.get("status") == "excluded"]
        if excluded:
            print(f"  제외된 후보 {len(excluded)}개:")
            for e in excluded:
                print(f"    - {e.get('name') or e['node_id'][:8]}: {e.get('reason')}")

    degenerate = data.get("degenerate_nodes", [])
    if degenerate:
        print(f"  ⚠ 무변별(개념 이상) 노드 {len(degenerate)}개:")
        for d in degenerate:
            print(f"    - {d.get('name') or d['node_id'][:8]}: {d.get('reason')}")
    return {"anomalies": anomalies}


def investigate(state: StudentState) -> dict:
    anomalies = state["anomalies"]
    if not anomalies:
        print("[T_STUDENT] 이상 노드 없음 — 종료")
        return {"proposals": []}

    llm = ChatOpenAI(model="claude-sonnet-4-6", temperature=0).with_structured_output(InvestigationOutput)

    prompt = f"""{_load_skill()}

## Anomalous Concept Nodes Detected

The following Concept nodes show statistically divergent successor mastery patterns,
indicating their concept scope is too broad and should be split.

Anomalies (sorted by anomaly_score desc):
{json.dumps(anomalies, ensure_ascii=False, indent=2)}

For each node, investigate why the concept is too broad and propose a concrete Split.
"""
    result: InvestigationOutput = llm.invoke(prompt)
    return {"proposals": [p.model_dump() for p in result.proposals]}


def validate(state: StudentState) -> dict:
    proposals = state["proposals"]
    if not proposals:
        return {"validated_proposals": []}

    llm = ChatOpenAI(model="claude-sonnet-4-6", temperature=0).with_structured_output(ValidationOutput)

    prompt = f"""{_load_skill()}

## Validation Task
Review these Split proposals for ontology compliance.
- New nodes must be type=Concept with valid depth
- All successor edges must be accounted for in edges_to_redistribute
- Set ontology_valid=false for proposals with structural errors

Proposals:
{json.dumps(proposals, ensure_ascii=False, indent=2)}
"""
    result: ValidationOutput = llm.invoke(prompt)
    valid = [p.model_dump() for p in result.validated_proposals if p.ontology_valid]
    return {"validated_proposals": valid}


def write(state: StudentState) -> dict:
    import datetime
    output_dir = Path("logs")
    output_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    path = output_dir / f"student_proposals_{state['subject_id'][:8]}_{ts}.json"

    payload = {
        "subject_id": state["subject_id"],
        "trigger": "T_STUDENT",
        "generated_at": ts,
        "proposal_count": len(state["validated_proposals"]),
        "proposals": state["validated_proposals"],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"[T_STUDENT] 제안 저장: {path}  ({len(state['validated_proposals'])}개)")
    return {"output_path": str(path)}


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_student_graph() -> StateGraph:
    g = StateGraph(StudentState)
    g.add_node("fetch_anomalies", fetch_anomalies)
    g.add_node("investigate", investigate)
    g.add_node("validate", validate)
    g.add_node("write", write)

    g.add_edge(START, "fetch_anomalies")
    g.add_edge("fetch_anomalies", "investigate")
    g.add_edge("investigate", "validate")
    g.add_edge("validate", "write")
    g.add_edge("write", END)

    return g.compile()
