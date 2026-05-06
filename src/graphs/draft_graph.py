"""
T1 DRAFT Graph
세 에이전트(Seed / Concept / TechStack)가 병렬로 실행되어
각자 최대 10개의 노드를 생성하고 state.json에 저장한다.
"""
import operator
from typing import Annotated

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from src.schemas import Entity, EntityType, NodeGenerationOutput
from src.state_manager import load_skill

MAX_NODES_PER_TYPE = 10


class DraftState(TypedDict):
    subject: str
    nodes: Annotated[list[Entity], operator.add]  # 병렬 에이전트 결과 자동 병합


def _make_agent_node(entity_type: EntityType, depth: int, skill_file: str):
    """에이전트 노드 팩토리"""

    def agent_node(state: DraftState) -> dict:
        skill = load_skill(skill_file)
        llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        structured_llm = llm.with_structured_output(NodeGenerationOutput)

        messages = [
            SystemMessage(content=skill),
            HumanMessage(
                content=(
                    f"주제: {state['subject']}\n\n"
                    f"위 주제에 대해 {entity_type.value} 타입의 노드를 "
                    f"최대 {MAX_NODES_PER_TYPE}개 생성하세요."
                )
            ),
        ]

        result: NodeGenerationOutput = structured_llm.invoke(messages)

        entities = [
            Entity(
                type=entity_type,
                depth=depth,
                name=node.name,
                description=node.description,
                metadata=node.metadata,
            )
            for node in result.nodes[:MAX_NODES_PER_TYPE]
        ]

        print(f"  [{entity_type.value}] {len(entities)}개 노드 생성")
        return {"nodes": entities}

    agent_node.__name__ = f"{entity_type.value.lower()}_agent"
    return agent_node


def build_draft_graph():
    """T1 DRAFT LangGraph 구성 및 컴파일"""
    graph = StateGraph(DraftState)

    # 세 에이전트 노드 등록
    graph.add_node(
        "seed_agent",
        _make_agent_node(EntityType.Seed, 1, "seed_agent_skill.md"),
    )
    graph.add_node(
        "concept_agent",
        _make_agent_node(EntityType.Concept, 2, "concept_agent_skill.md"),
    )
    graph.add_node(
        "tech_agent",
        _make_agent_node(EntityType.TechStack, 3, "tech_agent_skill.md"),
    )

    # START → 세 에이전트 병렬 팬아웃
    graph.add_edge(START, "seed_agent")
    graph.add_edge(START, "concept_agent")
    graph.add_edge(START, "tech_agent")

    # 세 에이전트 → END (Annotated reducer로 nodes 자동 병합)
    graph.add_edge("seed_agent", END)
    graph.add_edge("concept_agent", END)
    graph.add_edge("tech_agent", END)

    return graph.compile()
