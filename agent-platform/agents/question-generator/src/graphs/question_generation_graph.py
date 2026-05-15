"""
Question Generation Graph
Entity를 분석하여 다양한 난이도의 문제를 생성하고 저장한다.
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


class QuestionOutput(TypedDict):
    """LLM이 생성하는 문제 객체"""
    question_text: str
    options: list[dict]
    correct_answer: str
    explanation: str
    difficulty_level: str
    rationale: str


class QuestionGenerationState(TypedDict):
    entity_id: str
    entity: Optional[Entity]
    related_context: str
    difficulty_distribution: dict
    questions: list[dict]
    saved_questions: list[dict]


def _load_entity_and_context_node(state: QuestionGenerationState) -> dict:
    """Knowledge Graph에서 entity와 관련 정보 로드"""
    entity_id = state["entity_id"]
    nodes = load_nodes()
    edges = load_edges()

    # Entity 로드
    entity = next((n for n in nodes if n.id == entity_id), None)
    if not entity:
        raise ValueError(f"Entity {entity_id} not found in knowledge graph")

    print(f"\n📚 Entity 로드: {entity.name} ({entity.type.value})")

    # 관련 entity 찾기 (직접 연결된 모든 노드)
    related_ids = set()
    for edge in edges:
        if edge.source_id == entity_id:
            related_ids.add(edge.target_id)
        elif edge.target_id == entity_id:
            related_ids.add(edge.source_id)

    related_entities = [n for n in nodes if n.id in related_ids]

    # 관련 context 생성
    related_context = f"관련 개념: {', '.join(e.name for e in related_entities)}"
    if not related_entities:
        related_context = "관련 개념 없음"

    print(f"  관련 entity: {len(related_entities)}개")

    return {
        "entity": entity,
        "related_context": related_context
    }


def _analyze_difficulty_distribution_node(state: QuestionGenerationState) -> dict:
    """난이도 분포 분석 (entity 깊이에 따라)"""
    entity = state["entity"]

    # Entity depth에 따른 난이도 분포
    depth_distribution = {
        1: {"easy": 4, "medium": 2, "hard": 0},      # 기초 개념: 쉬운 문제 중심
        2: {"easy": 2, "medium": 3, "hard": 1},      # 중간: 다양한 난이도
        3: {"easy": 1, "medium": 2, "hard": 3}       # 구체적: 어려운 문제 중심
    }

    distribution = depth_distribution.get(entity.depth, {"easy": 2, "medium": 2, "hard": 2})

    print(f"  난이도 분포: {distribution}")
    return {"difficulty_distribution": distribution}


def _generate_questions_node(state: QuestionGenerationState) -> dict:
    """LLM으로 문제 생성"""
    entity = state["entity"]
    related_context = state["related_context"]
    difficulty_dist = state["difficulty_distribution"]

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        temperature=0.7
    )

    skill = load_skill("question_generator_skill.md")

    # 난이도별 요청
    difficulty_prompt = ", ".join(
        [f"{level} {count}개" for level, count in difficulty_dist.items()]
    )

    user_message = f"""Entity 분석:
- 이름: {entity.name}
- 설명: {entity.description}
- 타입: {entity.type.value}
- Depth: {entity.depth}
- {related_context}

생성 요청:
- 총 {sum(difficulty_dist.values())}개 문제
- 난이도 분포: {difficulty_prompt}

각 문제는 JSON 형식으로 question_text, options, correct_answer, explanation, difficulty_level, rationale를 포함해야 합니다.
응답은 JSON array로 시작하세요: [ {{ ... }} ]"""

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

        # JSON 파싱
        questions = json.loads(content.strip())
        if not isinstance(questions, list):
            questions = [questions]

        print(f"🎯 생성된 문제: {len(questions)}개")
        return {"questions": questions}

    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 실패: {e}")
        return {"questions": []}
    except Exception as e:
        print(f"❌ 문제 생성 실패: {e}")
        return {"questions": []}


def _save_questions_node(state: QuestionGenerationState) -> dict:
    """생성된 문제를 Question Bank DB에 저장"""
    _, qb_db, _ = get_db_client()

    entity_id = state["entity_id"]
    questions = state["questions"]
    saved = []

    for q in questions:
        try:
            saved_question = qb_db.create_question(
                entity_id=entity_id,
                question_text=q.get("question_text"),
                options=q.get("options", []),
                correct_answer=q.get("correct_answer"),
                difficulty_level=q.get("difficulty_level", "medium"),
                explanation=q.get("explanation"),
                metadata={
                    "type": q.get("type", "multiple_choice"),
                    "rationale": q.get("rationale", ""),
                    "generated_at": datetime.now().isoformat()
                }
            )
            saved.append(saved_question)
            print(f"  ✓ 저장: {q.get('difficulty_level', 'medium')}")
        except Exception as e:
            print(f"  ✗ 저장 실패: {e}")

    print(f"✅ 총 {len(saved)}개 문제 저장 완료")
    return {"saved_questions": saved}


def build_question_generation_graph():
    """Question Generation Graph 구성"""
    graph = StateGraph(QuestionGenerationState)

    graph.add_node("load_entity_and_context", _load_entity_and_context_node)
    graph.add_node("analyze_difficulty", _analyze_difficulty_distribution_node)
    graph.add_node("generate_questions", _generate_questions_node)
    graph.add_node("save_questions", _save_questions_node)

    graph.add_edge(START, "load_entity_and_context")
    graph.add_edge("load_entity_and_context", "analyze_difficulty")
    graph.add_edge("analyze_difficulty", "generate_questions")
    graph.add_edge("generate_questions", "save_questions")
    graph.add_edge("save_questions", END)

    return graph.compile()
