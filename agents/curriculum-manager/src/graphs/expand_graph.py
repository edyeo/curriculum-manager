"""
T3 EXPAND Graph — Debate-based Gap Analysis
토론 파이프라인: Critic → Devil's Advocate → Synthesizer(노드) → Linker(엣지)

1. Critic       : 기존 그래프의 빈틈과 구조적 결함 진단
2. Devil's Adv. : Critic에 도전 + Critic이 놓친 맹점 추가 발굴
3. Synthesizer  : 두 분석을 종합하여 새 노드 생성 (type/depth LLM 결정)
4. Linker       : 새 노드 ↔ 기존/새 노드 간 엣지 연결
"""
import json
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from shared.schemas import (
    Edge, Entity, EntityType,
    DebateNodeGenerationOutput,
    EdgeGenerationOutput,
)
from shared.state_manager import load_skill

MAX_NEW_NODES = 10


class ExpandState(TypedDict):
    existing_nodes: list[Entity]
    existing_edges: list[Edge]
    critic_analysis: str        # Critic의 텍스트 분석
    devils_analysis: str        # Devil's Advocate의 텍스트 분석
    new_nodes: list[Entity]     # Synthesizer가 생성한 새 노드
    new_edges: list[Edge]       # Linker가 생성한 새 엣지
    log_file_path: str          # 토론 로그가 저장될 파일 경로


def _format_graph_summary(nodes: list[Entity], edges: list[Edge]) -> str:
    """그래프를 LLM이 이해하기 쉬운 텍스트로 포맷"""
    node_id_map = {n.id: n.name for n in nodes}
    lines = []

    # 노드 요약 (타입 + depth별)
    lines.append("### 노드 목록")
    for node in nodes:
        lines.append(
            f"- [{node.type.value}|D{node.depth}] {node.name} (id: {node.id[:8]}...)\n"
            f"  → {node.description[:100]}..."
        )

    # 엣지 요약
    lines.append("\n### 엣지 목록")
    if edges:
        for edge in edges:
            src_name = node_id_map.get(edge.source_id, edge.source_id[:8])
            tgt_name = node_id_map.get(edge.target_id, edge.target_id[:8])
            lines.append(f"- {src_name} --[{edge.relation_type}]--> {tgt_name}")
    else:
        lines.append("- (없음)")

    return "\n".join(lines)


# ── Node 1: Critic ────────────────────────────────────────────

def critic_node(state: ExpandState) -> dict:
    """기존 그래프의 빈틈·결함 진단"""
    skill = load_skill("critic_agent_skill.md")
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o"), temperature=0.4)

    graph_summary = _format_graph_summary(state["existing_nodes"], state["existing_edges"])

    messages = [
        SystemMessage(content=skill),
        HumanMessage(
            content=(
                "## 현재 지식 그래프\n\n"
                f"{graph_summary}\n\n"
                "위 그래프를 분석하여 빈틈과 문제점을 도출하세요."
            )
        ),
    ]

    response = llm.invoke(messages)
    print("  [Critic] 분석 완료")
    
    log_path = state.get("log_file_path")
    if log_path:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*20} [Critic] {'='*20}\n")
            f.write(response.content + "\n")
            
    return {"critic_analysis": response.content}


# ── Node 2: Devil's Advocate ──────────────────────────────────

def devils_advocate_node(state: ExpandState) -> dict:
    """Critic 분석에 도전 + 추가 맹점 발굴"""
    skill = load_skill("devils_advocate_skill.md")
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o"), temperature=0.7)

    graph_summary = _format_graph_summary(state["existing_nodes"], state["existing_edges"])

    messages = [
        SystemMessage(content=skill),
        HumanMessage(
            content=(
                "## 현재 지식 그래프\n\n"
                f"{graph_summary}\n\n"
                "## Critic의 분석\n\n"
                f"{state['critic_analysis']}\n\n"
                "Critic의 분석에 도전하고, Critic이 놓친 추가 맹점을 발굴하세요."
            )
        ),
    ]

    response = llm.invoke(messages)
    print("  [Devil's Advocate] 반론 및 추가 맹점 완료")
    
    log_path = state.get("log_file_path")
    if log_path:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*20} [Devil's Advocate] {'='*20}\n")
            f.write(response.content + "\n")
            
    return {"devils_analysis": response.content}


# ── Node 3: Synthesizer (노드 생성) ───────────────────────────

def synthesize_nodes_node(state: ExpandState) -> dict:
    """두 분석을 종합하여 새 노드 생성"""
    skill = load_skill("synthesizer_skill.md")
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o"), temperature=0.5)
    structured_llm = llm.with_structured_output(
        DebateNodeGenerationOutput, method="function_calling"
    )

    existing_names = [f"[{n.type.value}|D{n.depth}] {n.name}" for n in state["existing_nodes"]]

    messages = [
        SystemMessage(content=skill),
        HumanMessage(
            content=(
                "## 기존 노드 목록\n"
                + "\n".join(existing_names)
                + "\n\n## Critic 분석\n"
                + state["critic_analysis"]
                + "\n\n## Devil's Advocate 분석\n"
                + state["devils_analysis"]
                + f"\n\n토론 결과를 종합하여 기존에 없는 새 노드를 최대 {MAX_NEW_NODES}개 생성하세요."
            )
        ),
    ]

    result: DebateNodeGenerationOutput = structured_llm.invoke(messages)

    new_nodes = [
        Entity(
            type=EntityType(node.type),
            depth=node.depth,
            name=node.name,
            description=node.description,
            metadata={**node.metadata, "source": "expand_debate"},
            created_by_trigger="T3_EXPAND_SYNTHESIZER",
        )
        for node in result.nodes[:MAX_NEW_NODES]
    ]

    type_summary = {}
    for n in new_nodes:
        key = f"{n.type.value}(D{n.depth})"
        type_summary[key] = type_summary.get(key, 0) + 1
    summary_str = ", ".join(f"{k}={v}" for k, v in type_summary.items())

    print(f"  [Synthesizer] 새 노드 {len(new_nodes)}개 생성: {summary_str}")
    print(f"  [Rationale] {result.synthesis_rationale[:100]}...")
    
    log_path = state.get("log_file_path")
    if log_path:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*20} [Synthesizer] {'='*20}\n")
            f.write(f"Rationale:\n{result.synthesis_rationale}\n\n")
            f.write("Generated Nodes:\n")
            for n in new_nodes:
                f.write(f"- [{n.type.value}|D{n.depth}] {n.name}: {n.description}\n")
            f.write("\n")
            
    return {"new_nodes": new_nodes}


# ── Node 4: Linker (엣지 연결) ────────────────────────────────

def synthesize_edges_node(state: ExpandState) -> dict:
    """새 노드 ↔ 기존·새 노드 간 엣지 연결"""
    skill = load_skill("linking_agent_skill.md")
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o"), temperature=0.3)
    structured_llm = llm.with_structured_output(EdgeGenerationOutput, method="function_calling")

    new_nodes = state["new_nodes"]
    if not new_nodes:
        return {"new_edges": []}

    all_nodes = state["existing_nodes"] + new_nodes

    # 새 노드를 Source, 전체 노드를 Target으로
    new_json = json.dumps(
        [{"id": n.id, "name": n.name, "type": n.type, "depth": n.depth, "description": n.description}
         for n in new_nodes],
        ensure_ascii=False, indent=2,
    )
    all_json = json.dumps(
        [{"id": n.id, "name": n.name, "type": n.type, "depth": n.depth, "description": n.description}
         for n in all_nodes],
        ensure_ascii=False, indent=2,
    )

    messages = [
        SystemMessage(content=skill),
        HumanMessage(
            content=(
                "## Source 노드 (토론으로 새로 생성된 노드)\n"
                f"{new_json}\n\n"
                "## Target 노드 (기존 + 새 노드 전체)\n"
                f"{all_json}\n\n"
                "새로 생성된 노드들이 기존 또는 다른 새 노드와 어떤 논리적 관계를 갖는지 추론하여 Edge를 생성하세요."
            )
        ),
    ]

    result: EdgeGenerationOutput = structured_llm.invoke(messages)

    valid_ids = {n.id for n in all_nodes}
    new_node_ids = {n.id for n in new_nodes}
    existing_edge_pairs = {(e.source_id, e.target_id) for e in state["existing_edges"]}

    edges = [
        Edge(
            source_id=e.source_id,
            target_id=e.target_id,
            relation_type=e.relation_type,
            logic_basis=e.logic_basis,
            created_by_trigger="T3_EXPAND_LINKER",
        )
        for e in result.edges
        if (e.source_id in valid_ids and e.target_id in valid_ids)
        and (e.source_id, e.target_id) not in existing_edge_pairs   # 중복 방지
        and e.source_id in new_node_ids                              # 최소 하나는 새 노드
    ]

    print(f"  [Linker] 새 엣지 {len(edges)}개 생성")
    
    log_path = state.get("log_file_path")
    if log_path:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*20} [Linker] {'='*20}\n")
            f.write("Generated Edges:\n")
            node_names = {n.id: n.name for n in all_nodes}
            for e in edges:
                src_name = node_names.get(e.source_id, e.source_id[:8])
                tgt_name = node_names.get(e.target_id, e.target_id[:8])
                f.write(f"- {src_name} --[{e.relation_type}]--> {tgt_name}\n  Logic: {e.logic_basis}\n")
            f.write("\n")
            
    return {"new_edges": edges}


# ── Graph 조립 ────────────────────────────────────────────────

def build_expand_graph():
    """T3 EXPAND: Debate Pipeline LangGraph"""
    graph = StateGraph(ExpandState)

    graph.add_node("critic", critic_node)
    graph.add_node("devils_advocate", devils_advocate_node)
    graph.add_node("synthesize_nodes", synthesize_nodes_node)
    graph.add_node("synthesize_edges", synthesize_edges_node)

    graph.add_edge(START, "critic")
    graph.add_edge("critic", "devils_advocate")
    graph.add_edge("devils_advocate", "synthesize_nodes")
    graph.add_edge("synthesize_nodes", "synthesize_edges")
    graph.add_edge("synthesize_edges", END)

    return graph.compile()
