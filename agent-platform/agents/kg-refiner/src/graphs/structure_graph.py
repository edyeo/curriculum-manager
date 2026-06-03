"""T_STRUCTURE — 서브그래프 컨텍스트 주입 후 구조 검토·개선 제안 LangGraph."""
import json
import os
from pathlib import Path
from typing import TypedDict, Any

import httpx
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field


CONTENTS_MANAGER_URL = os.getenv("CONTENTS_MANAGER_URL", "http://localhost:8010")
SKILL_PATH = Path(__file__).parent.parent.parent / "skills" / "structure_skill.md"


def _load_skill() -> str:
    return SKILL_PATH.read_text()


# ── State ─────────────────────────────────────────────────────────────────────

class StructureState(TypedDict):
    subject_id: str
    node_types: list[str] | None
    depth: int | None
    root_node_id: str | None
    subgraph: dict
    proposals: list[dict]
    validated_proposals: list[dict]
    output_path: str


# ── Structured output ─────────────────────────────────────────────────────────

class NodeSuggestion(BaseModel):
    name: str
    type: str
    depth: int
    description: str = ""


class EdgeSuggestion(BaseModel):
    source_id: str
    target_id: str
    relation_type: str


class Proposal(BaseModel):
    type: str = Field(description="split|merge|relink|reorder|add_edge|remove_edge")
    target_node_id: str
    target_node_name: str = ""
    reason: str
    suggestion: dict[str, Any] = Field(default_factory=dict)
    ontology_valid: bool = True
    confidence: float = Field(ge=0.0, le=1.0)


class ReviewOutput(BaseModel):
    proposals: list[Proposal]


class ValidationOutput(BaseModel):
    validated_proposals: list[Proposal]


# ── Nodes ─────────────────────────────────────────────────────────────────────

def fetch_subgraph(state: StructureState) -> dict:
    params: dict[str, Any] = {}
    if state.get("node_types"):
        params["node_types"] = ",".join(state["node_types"])
    if state.get("depth"):
        params["depth"] = state["depth"]
    if state.get("root_node_id"):
        params["root_node_id"] = state["root_node_id"]

    resp = httpx.get(
        f"{CONTENTS_MANAGER_URL}/kg/analytics/subgraph/{state['subject_id']}",
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    return {"subgraph": resp.json()}


def review(state: StructureState) -> dict:
    subgraph = state["subgraph"]
    llm = ChatOpenAI(model="claude-sonnet-4-6", temperature=0).with_structured_output(ReviewOutput)

    prompt = f"""{_load_skill()}

## Subgraph to Review

Nodes ({subgraph['node_count']}):
{json.dumps(subgraph['nodes'], ensure_ascii=False, indent=2)}

Edges ({subgraph['edge_count']}):
{json.dumps(subgraph['edges'], ensure_ascii=False, indent=2)}

Review the subgraph and propose improvements. Focus on the most impactful changes.
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
    import datetime
    output_dir = Path("logs")
    output_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    path = output_dir / f"structure_proposals_{state['subject_id'][:8]}_{ts}.json"

    payload = {
        "subject_id": state["subject_id"],
        "trigger": "T_STRUCTURE",
        "generated_at": ts,
        "proposal_count": len(state["validated_proposals"]),
        "proposals": state["validated_proposals"],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"[T_STRUCTURE] 제안 저장: {path}  ({len(state['validated_proposals'])}개)")
    return {"output_path": str(path)}


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_structure_graph() -> StateGraph:
    g = StateGraph(StructureState)
    g.add_node("fetch_subgraph", fetch_subgraph)
    g.add_node("review", review)
    g.add_node("validate", validate)
    g.add_node("write", write)

    g.add_edge(START, "fetch_subgraph")
    g.add_edge("fetch_subgraph", "review")
    g.add_edge("review", "validate")
    g.add_edge("validate", "write")
    g.add_edge("write", END)

    return g.compile()
