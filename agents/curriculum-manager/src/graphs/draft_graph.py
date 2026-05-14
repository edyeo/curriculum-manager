"""
T1 DRAFT Graph
세 에이전트(Seed / Concept / TechStack)가 병렬로 실행되어
각자 최대 10개의 노드를 생성하고 state.json에 저장한다.
"""
import operator
import os
from typing import Annotated

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from shared.schemas import Entity, EntityType, NodeGenerationOutput
from shared.state_manager import load_skill
from shared.ontology_loader import get_ontology

MAX_NODES_PER_TYPE = 10


class DraftState(TypedDict):
    subject: str
    nodes: Annotated[list[Entity], operator.add]  # 병렬 에이전트 결과 자동 병합


def _make_agent_node(entity_type: EntityType, skill_file: str):
    """에이전트 노드 팩토리"""

    def agent_node(state: DraftState) -> dict:
        skill = load_skill(skill_file)
        llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o"), temperature=0.7)
        structured_llm = llm.with_structured_output(NodeGenerationOutput, method="function_calling")

        # Seed 에이전트에만 ontology constraint 블록 추가 주입
        ontology_block = ""
        if entity_type == EntityType.Seed:
            ontology_block = "\n\n" + get_ontology().get_entity_prompt_block("Seed")

        messages = [
            SystemMessage(content=skill + ontology_block),
            HumanMessage(
                content=(
                    f"주제: {state['subject']}\n\n"
                    f"위 주제에 대해 {entity_type.value} 타입의 노드를 최대 {MAX_NODES_PER_TYPE}개 생성하세요.\n"
                    "각 노드의 depth는 추상화 수준에 따라 직접 결정하세요:\n"
                    "  depth=1: 고수준/범주적 개념 (예: '메시지 큐')\n"
                    "  depth=2: 중간 수준 (예: '분산 로그 기반 브로커')\n"
                    "  depth=3: 구체적/특정 (예: 'Apache Kafka')"
                )
            ),
        ]

        result: NodeGenerationOutput = structured_llm.invoke(messages)

        entities = [
            Entity(
                type=entity_type,
                depth=node.depth,
                name=node.name,
                description=node.description,
                metadata=node.metadata,
                created_by_trigger="T1_DRAFT",
            )
            for node in result.nodes[:MAX_NODES_PER_TYPE]
        ]

        depth_summary = {}
        for e in entities:
            depth_summary[e.depth] = depth_summary.get(e.depth, 0) + 1
        depth_str = ", ".join(f"D{d}={c}" for d, c in sorted(depth_summary.items()))
        print(f"  [{entity_type.value}] {len(entities)}개 노드 생성 ({depth_str})")
        return {"nodes": entities}

    agent_node.__name__ = f"{entity_type.value.lower()}_agent"
    return agent_node


def build_draft_graph():
    """T1 DRAFT LangGraph 구성 및 컴파일"""
    graph = StateGraph(DraftState)

    # 세 에이전트 노드 등록
    graph.add_node(
        "seed_agent",
        _make_agent_node(EntityType.Seed, "seed_agent_skill.md"),
    )
    graph.add_node(
        "concept_agent",
        _make_agent_node(EntityType.Concept, "concept_agent_skill.md"),
    )
    graph.add_node(
        "tech_agent",
        _make_agent_node(EntityType.TechStack, "tech_agent_skill.md"),
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
