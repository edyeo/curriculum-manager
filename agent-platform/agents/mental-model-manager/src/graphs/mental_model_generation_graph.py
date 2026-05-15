"""
Mental Model Generation Graph
Entity에 대한 Junior/Senior/Staff 수준별 평가 기준(Rubric)을 생성한다.
"""
import os
import json
from typing import Optional
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from shared.schemas import Entity
from shared.state_manager import load_nodes, load_edges, load_skill
from shared.db_client import get_db_client


class MentalModelRubric(TypedDict):
    """생성된 평가 기준"""
    junior_rubric: list[str]
    senior_rubric: list[str]
    staff_rubric: list[str]


class MentalModelGenerationState(TypedDict):
    entity_id: str
    entity: Optional[Entity]
    entity_context: str
    rubric: dict
    saved_result: Optional[dict]


def _load_entity_and_context_node(state: MentalModelGenerationState) -> dict:
    """Entity와 관련 정보 로드"""
    entity_id = state["entity_id"]
    nodes = load_nodes()
    edges = load_edges()

    # Entity 로드
    entity = next((n for n in nodes if n.id == entity_id), None)
    if not entity:
        raise ValueError(f"Entity {entity_id} not found in knowledge graph")

    print(f"\n📚 Entity 로드: {entity.name} ({entity.type.value})")

    # 관련 context 생성
    related_ids = set()
    for edge in edges:
        if edge.source_id == entity_id:
            related_ids.add(edge.target_id)
        elif edge.target_id == entity_id:
            related_ids.add(edge.source_id)

    related_entities = [n for n in nodes if n.id in related_ids]
    related_context = f"관련 개념: {', '.join(e.name for e in related_entities[:5])}"
    if not related_entities:
        related_context = ""

    return {
        "entity": entity,
        "entity_context": related_context
    }


def _generate_rubric_node(state: MentalModelGenerationState) -> dict:
    """LLM으로 Junior/Senior/Staff 평가 기준 생성"""
    entity = state["entity"]
    entity_context = state["entity_context"]

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        temperature=0.7
    )

    skill = load_skill("mental_model_generator_skill.md")

    user_message = f"""Entity 분석:
- 이름: {entity.name}
- 설명: {entity.description}
- 타입: {entity.type.value}
- Depth: {entity.depth}
{f"- {entity_context}" if entity_context else ""}

이 Entity에 대해 Junior/Senior/Staff 수준별 평가 기준(Rubric)을 생성하세요.
각 수준은 5-7개의 명확한 평가 항목으로 구성되어야 합니다.

JSON 형식으로 반환:
{{
  "entity": "{entity.name}",
  "junior_rubric": ["항목1", "항목2", ...],
  "senior_rubric": ["항목1", "항목2", ...],
  "staff_rubric": ["항목1", "항목2", ...]
}}"""

    try:
        response = llm.invoke([
            SystemMessage(content=skill),
            HumanMessage(content=user_message)
        ])

        # JSON 추출
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        rubric = json.loads(content.strip())

        print(f"✅ 평가 기준 생성 완료")
        print(f"  Junior: {len(rubric.get('junior_rubric', []))}개 항목")
        print(f"  Senior: {len(rubric.get('senior_rubric', []))}개 항목")
        print(f"  Staff: {len(rubric.get('staff_rubric', []))}개 항목")

        return {"rubric": rubric}

    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 실패: {e}")
        return {
            "rubric": {
                "entity": entity.name,
                "junior_rubric": [],
                "senior_rubric": [],
                "staff_rubric": []
            }
        }
    except Exception as e:
        print(f"❌ 평가 기준 생성 실패: {e}")
        return {
            "rubric": {
                "entity": entity.name,
                "junior_rubric": [],
                "senior_rubric": [],
                "staff_rubric": []
            }
        }


def _save_mental_model_node(state: MentalModelGenerationState) -> dict:
    """생성된 Mental Model을 DB에 저장"""
    _, _, _ = get_db_client()

    entity_id = state["entity_id"]
    entity = state["entity"]
    rubric = state["rubric"]

    mental_model = {
        "id": entity_id,
        "entity_name": entity.name,
        "entity_type": entity.type.value,
        "entity_depth": entity.depth,
        "junior_rubric": rubric.get("junior_rubric", []),
        "senior_rubric": rubric.get("senior_rubric", []),
        "staff_rubric": rubric.get("staff_rubric", []),
        "created_at": datetime.now().isoformat()
    }

    # TODO: Mental Model DB에 저장 (현재는 메모리에만 유지)
    # mm_db.create_mental_model(mental_model)

    print(f"💾 Mental Model 저장: {entity.name}")
    return {"saved_result": mental_model}


def build_mental_model_generation_graph():
    """Mental Model Generation Graph 구성"""
    graph = StateGraph(MentalModelGenerationState)

    graph.add_node("load_entity_and_context", _load_entity_and_context_node)
    graph.add_node("generate_rubric", _generate_rubric_node)
    graph.add_node("save_mental_model", _save_mental_model_node)

    graph.add_edge(START, "load_entity_and_context")
    graph.add_edge("load_entity_and_context", "generate_rubric")
    graph.add_edge("generate_rubric", "save_mental_model")
    graph.add_edge("save_mental_model", END)

    return graph.compile()
