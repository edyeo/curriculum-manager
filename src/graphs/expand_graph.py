"""
T3 EXPAND Graph
TechStack(depth=3) 노드를 역방향 추론하여 새로운 Seed(depth=3) 노드를 생성하고,
기존 TechStack 노드와 연결한다.
"""
import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from src.schemas import Edge, Entity, EntityType, NodeGenerationOutput, EdgeGenerationOutput
from src.state_manager import load_skill

MAX_NEW_SEEDS = 10


class ExpandState(TypedDict):
    existing_nodes: list[Entity]
    existing_edges: list[Edge]
    new_nodes: list[Entity]
    new_edges: list[Edge]


def analyze_node(state: ExpandState) -> dict:
    """TechStack 노드에서 역방향 Seed 추론 및 새 노드 생성"""
    skill = load_skill("seed_agent_skill.md")
    llm = ChatOpenAI(model="gpt-4o", temperature=0.8)
    structured_llm = llm.with_structured_output(NodeGenerationOutput)

    tech_nodes = [n for n in state["existing_nodes"] if n.type == EntityType.TechStack]
    tech_json = json.dumps(
        [{"id": n.id, "name": n.name, "description": n.description} for n in tech_nodes],
        ensure_ascii=False,
        indent=2,
    )

    messages = [
        SystemMessage(content=skill),
        HumanMessage(
            content=(
                "다음은 현재 그래프에 존재하는 TechStack 노드들입니다.\n\n"
                f"{tech_json}\n\n"
                "이 기술들을 역방향으로 분석하세요: 이 기술들이 존재한다는 사실이 "
                "암시하는 **아직 발견되지 않은 새로운 엔지니어링 난제(Seed)**는 무엇인가요? "
                f"초안에 없던 새로운 Seed를 최대 {MAX_NEW_SEEDS}개 생성하세요."
            )
        ),
    ]

    result: NodeGenerationOutput = structured_llm.invoke(messages)

    new_seeds = [
        Entity(
            type=EntityType.Seed,
            depth=3,  # depth=3: EXPAND 단계에서 발견된 심화 Seed
            name=node.name,
            description=node.description,
            metadata={**node.metadata, "source": "expand"},
        )
        for node in result.nodes[:MAX_NEW_SEEDS]
    ]

    print(f"  [EXPAND] 새 Seed 노드 {len(new_seeds)}개 생성")
    return {"new_nodes": new_seeds}


def connect_node(state: ExpandState) -> dict:
    """새 Seed(D3) ↔ 기존 TechStack(D3) 엣지 생성"""
    skill = load_skill("linking_agent_skill.md")
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    structured_llm = llm.with_structured_output(EdgeGenerationOutput)

    new_seeds = state["new_nodes"]
    tech_nodes = [n for n in state["existing_nodes"] if n.type == EntityType.TechStack]

    if not new_seeds or not tech_nodes:
        return {"new_edges": []}

    seed_json = json.dumps(
        [{"id": n.id, "name": n.name, "description": n.description} for n in new_seeds],
        ensure_ascii=False, indent=2,
    )
    tech_json = json.dumps(
        [{"id": n.id, "name": n.name, "description": n.description} for n in tech_nodes],
        ensure_ascii=False, indent=2,
    )

    messages = [
        SystemMessage(content=skill),
        HumanMessage(
            content=(
                "## Source 노드 (새로운 Seed - depth=3)\n"
                f"{seed_json}\n\n"
                "## Target 노드 (기존 TechStack - depth=3)\n"
                f"{tech_json}\n\n"
                "새로운 Seed가 기존 TechStack과 어떤 논리적 관계를 갖는지 추론하여 Edge를 생성하세요."
            )
        ),
    ]

    result: EdgeGenerationOutput = structured_llm.invoke(messages)

    valid_seed_ids = {n.id for n in new_seeds}
    valid_tech_ids = {n.id for n in tech_nodes}

    edges = [
        Edge(
            source_id=e.source_id,
            target_id=e.target_id,
            relation_type=e.relation_type,
            logic_basis=e.logic_basis,
        )
        for e in result.edges
        if e.source_id in valid_seed_ids and e.target_id in valid_tech_ids
    ]

    print(f"  [EXPAND] 새 엣지 {len(edges)}개 생성")
    return {"new_edges": edges}


def build_expand_graph():
    """T3 EXPAND LangGraph 구성 및 컴파일"""
    graph = StateGraph(ExpandState)

    graph.add_node("analyze", analyze_node)
    graph.add_node("connect", connect_node)

    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "connect")
    graph.add_edge("connect", END)

    return graph.compile()
