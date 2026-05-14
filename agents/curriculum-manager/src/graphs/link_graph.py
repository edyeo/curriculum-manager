"""
T2 LINK Graph
지정된 두 타입의 노드 간 Pairwise 엣지를 생성한다.
가드레일: source.depth != target.depth 이면 엣지 제거.
"""
import json
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from src.schemas import Edge, Entity, EdgeGenerationOutput
from src.state_manager import load_skill


class LinkState(TypedDict):
    source_type: str
    target_type: str
    source_nodes: list[Entity]
    target_nodes: list[Entity]
    new_edges: list[Edge]


def link_node(state: LinkState) -> dict:
    """링킹 에이전트로 엣지 생성"""
    skill = load_skill("linking_agent_skill.md")
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o"), temperature=0.3)
    structured_llm = llm.with_structured_output(EdgeGenerationOutput, method="function_calling")

    source_nodes = state["source_nodes"]
    target_nodes = state["target_nodes"]

    source_json = json.dumps(
        [
            {"id": n.id, "name": n.name, "type": n.type, "depth": n.depth, "description": n.description}
            for n in source_nodes
        ],
        ensure_ascii=False,
        indent=2,
    )
    target_json = json.dumps(
        [
            {"id": n.id, "name": n.name, "type": n.type, "depth": n.depth, "description": n.description}
            for n in target_nodes
        ],
        ensure_ascii=False,
        indent=2,
    )

    messages = [
        SystemMessage(content=skill),
        HumanMessage(
            content=(
                f"## Source 노드 ({state['source_type']})\n{source_json}\n\n"
                f"## Target 노드 ({state['target_type']})\n{target_json}\n\n"
                "위 두 그룹 간의 논리적 관계를 추론하여 Edge 목록을 생성하세요."
            )
        ),
    ]

    result: EdgeGenerationOutput = structured_llm.invoke(messages)

    # ID 유효성 검사
    valid_source_ids = {n.id for n in source_nodes}
    valid_target_ids = {n.id for n in target_nodes}

    edges = [
        Edge(
            source_id=e.source_id,
            target_id=e.target_id,
            relation_type=e.relation_type,
            logic_basis=e.logic_basis,
            created_by_trigger="T2_LINK",
        )
        for e in result.edges
        if e.source_id in valid_source_ids and e.target_id in valid_target_ids
    ]

    print(f"  [LINK] LLM 제안 {len(result.edges)}개 → ID 유효 {len(edges)}개")
    return {"new_edges": edges}


def guard_node(state: LinkState) -> dict:
    """가드레일: depth가 동일한 엣지만 통과"""
    source_depth_map = {n.id: n.depth for n in state["source_nodes"]}
    target_depth_map = {n.id: n.depth for n in state["target_nodes"]}

    before = len(state["new_edges"])
    valid_edges = [
        e
        for e in state["new_edges"]
        if source_depth_map.get(e.source_id) == target_depth_map.get(e.target_id)
    ]
    removed = before - len(valid_edges)

    if removed:
        print(f"  [GUARD] depth 불일치 엣지 {removed}개 제거 → 통과 {len(valid_edges)}개")
    else:
        print(f"  [GUARD] 모든 엣지 통과 ({len(valid_edges)}개)")

    return {"new_edges": valid_edges}


def build_link_graph():
    """T2 LINK LangGraph 구성 및 컴파일"""
    graph = StateGraph(LinkState)

    graph.add_node("link", link_node)
    graph.add_node("guard", guard_node)

    graph.add_edge(START, "link")
    graph.add_edge("link", "guard")
    graph.add_edge("guard", END)

    return graph.compile()
