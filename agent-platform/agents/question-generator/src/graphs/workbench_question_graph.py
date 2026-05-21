"""
Workbench Question Generation Graph (EPIC-003 Feature 2.3)

기존 question_generation_graph.py 대비 강화 사항:
- Blueprint/통합항목 컨텍스트 주입
- Sibling/antipattern 노드를 추적하여 오답지 3개 생성
- 선지별 rationale (KG 제약조건 충족/위배 근거) 포함
"""
import os
import json
from typing import Optional
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from pathlib import Path

from shared.schemas import Entity
from shared.state_manager import load_nodes, load_edges

_SKILL_FILE = Path(__file__).parent.parent / "skills" / "question_generator_skill.md"


def _load_skill() -> str:
    if _SKILL_FILE.exists():
        return _SKILL_FILE.read_text(encoding="utf-8")
    return "You are an expert educational question generator."


class WorkbenchQuestion(TypedDict):
    question_text: str
    options: list[dict]   # [{label, text, rationale, is_correct}]
    correct_answer: str
    explanation: str
    difficulty_level: str
    node_snapshot: dict   # entity + distractor 노드 메타데이터 스냅샷


class WorkbenchState(TypedDict):
    entity_id: str
    blueprint_id: Optional[str]
    integration_item_id: Optional[str]
    blueprint_context: str
    question_type: str    # MCQ | OX | short_answer
    count: int            # 생성할 문제 수
    entity: Optional[Entity]
    siblings: list        # 같은 부모를 가진 형제 노드
    antipatterns: list    # 안티패턴 노드
    related_context: str
    questions: list[WorkbenchQuestion]
    saved_questions: list[dict]


def _load_entity_and_graph_node(state: WorkbenchState) -> dict:
    """Entity + 형제/안티패턴 노드 로드"""
    entity_id = state["entity_id"]
    nodes = load_nodes()
    edges = load_edges()

    entity = next((n for n in nodes if n.id == entity_id), None)
    if not entity:
        raise ValueError(f"Entity {entity_id} not found")

    node_map = {n.id: n for n in nodes}

    # 직접 연결 이웃
    neighbor_ids = set()
    parent_ids = set()
    for edge in edges:
        if edge.source_id == entity_id:
            neighbor_ids.add(edge.target_id)
        elif edge.target_id == entity_id:
            neighbor_ids.add(edge.source_id)
            if edge.relation_type == "has_subtopic":
                parent_ids.add(edge.source_id)

    # 형제: 같은 부모의 다른 자식
    sibling_ids = set()
    for parent_id in parent_ids:
        for edge in edges:
            if edge.source_id == parent_id and edge.relation_type == "has_subtopic":
                if edge.target_id != entity_id:
                    sibling_ids.add(edge.target_id)

    # 안티패턴: entity와 같은 타입이면서 직접 연결되지 않은 노드 (depth 동일)
    antipattern_ids = set()
    for n in nodes:
        if (n.id != entity_id
                and n.type == entity.type
                and n.id not in neighbor_ids
                and n.id not in sibling_ids
                and n.depth == entity.depth):
            antipattern_ids.add(n.id)

    siblings = [node_map[nid] for nid in sibling_ids if nid in node_map][:4]
    antipatterns = [node_map[nid] for nid in antipattern_ids if nid in node_map][:4]

    neighbors = [node_map[nid] for nid in neighbor_ids if nid in node_map]
    related_context = (
        f"직접 연결 개념: {', '.join(n.name for n in neighbors)}"
        if neighbors else "관련 개념 없음"
    )

    print(f"📚 Entity: {entity.name} | siblings={len(siblings)} | antipatterns={len(antipatterns)}")
    return {
        "entity": entity,
        "siblings": [s.__dict__ for s in siblings],
        "antipatterns": [a.__dict__ for a in antipatterns],
        "related_context": related_context,
    }


def _build_blueprint_context_node(state: WorkbenchState) -> dict:
    """Blueprint/통합항목 컨텍스트 — 이미 주입된 경우 그대로 사용"""
    if state.get("blueprint_context"):
        return {}  # 백엔드에서 이미 resolve됨
    return {"blueprint_context": ""}


def _generate_workbench_questions_node(state: WorkbenchState) -> dict:
    """문제 생성: question_type에 따라 MCQ / OX / 단답형"""
    entity = state["entity"]
    siblings = state["siblings"]
    antipatterns = state["antipatterns"]
    related_context = state["related_context"]
    blueprint_context = state.get("blueprint_context", "")
    question_type = state.get("question_type", "MCQ")
    count = state.get("count", 3)

    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o"), temperature=0.7)

    skill = _load_skill()

    distractor_pool = siblings[:3] + antipatterns[:3]
    distractor_info = "\n".join(
        f"  - {d.get('name', d.get('id', ''))}: {d.get('description', '')[:80]}"
        for d in distractor_pool
    ) or "  (없음)"

    bp_section = f"\n\n[Blueprint 컨텍스트]\n{blueprint_context}" if blueprint_context else ""

    if question_type == "OX":
        format_instruction = f"""생성 요청:
- 총 {count}개 OX 문제 (다양한 난이도: easy/medium/hard)
- 각 문제는 2개 선지: O(참) / X(거짓)
- 각 선지에 rationale 포함

응답 형식 (JSON array):
[
  {{
    "question_text": "...",
    "difficulty_level": "easy|medium|hard",
    "options": [
      {{"label": "O", "text": "참", "is_correct": true, "rationale": "정답 근거: ..."}},
      {{"label": "X", "text": "거짓", "is_correct": false, "rationale": "오답 근거: ..."}}
    ],
    "correct_answer": "O",
    "explanation": "종합 해설..."
  }}
]"""
    elif question_type == "short_answer":
        format_instruction = f"""생성 요청:
- 총 {count}개 단답형 문제 (다양한 난이도: easy/medium/hard)
- options는 빈 배열 [], correct_answer에 정답 키워드

응답 형식 (JSON array):
[
  {{
    "question_text": "...",
    "difficulty_level": "easy|medium|hard",
    "options": [],
    "correct_answer": "정답 키워드 (1-3단어)",
    "explanation": "해설..."
  }}
]"""
    else:  # MCQ (default)
        format_instruction = f"""생성 요청:
- 총 {count}개 MCQ (다양한 난이도: easy/medium/hard)
- 각 문제는 4개 선지 (정답 1개 + 오답 3개)
- 오답은 반드시 위 오답 후보 노드를 참조하여 생성할 것
- 각 선지에 rationale 포함: "왜 정답인지" 또는 "왜 오답인지" (KG 제약조건 관점)

응답 형식 (JSON array):
[
  {{
    "question_text": "...",
    "difficulty_level": "easy|medium|hard",
    "options": [
      {{"label": "A", "text": "...", "is_correct": true, "rationale": "정답 근거: ..."}},
      {{"label": "B", "text": "...", "is_correct": false, "rationale": "오답 근거: ..."}},
      {{"label": "C", "text": "...", "is_correct": false, "rationale": "오답 근거: ..."}},
      {{"label": "D", "text": "...", "is_correct": false, "rationale": "오답 근거: ..."}}
    ],
    "correct_answer": "A",
    "explanation": "종합 해설 (트레이드오프 포함)..."
  }}
]"""

    user_message = f"""Entity 분석:
- 이름: {entity.name}
- 설명: {entity.description}
- 타입: {entity.type.value}
- Depth: {entity.depth}
- {related_context}
{bp_section}

오답 후보 노드 (형제/안티패턴):
{distractor_info}

{format_instruction}"""

    try:
        response = llm.invoke([SystemMessage(content=skill), HumanMessage(content=user_message)])
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        questions = json.loads(content.strip())
        if not isinstance(questions, list):
            questions = [questions]
        print(f"🎯 생성된 MCQ: {len(questions)}개")
        return {"questions": questions}
    except Exception as e:
        print(f"❌ MCQ 생성 실패: {e}")
        return {"questions": []}


def _attach_node_snapshot_node(state: WorkbenchState) -> dict:
    """문항에 node_snapshot 첨부 (De-normalization, 데이터 무결성)"""
    entity = state["entity"]
    snapshot = {
        "id": entity.id,
        "name": entity.name,
        "type": entity.type.value,
        "description": entity.description,
        "depth": entity.depth,
        "siblings": [
            {"id": s.get("id"), "name": s.get("name")} for s in state["siblings"]
        ],
        "antipatterns": [
            {"id": a.get("id"), "name": a.get("name")} for a in state["antipatterns"]
        ],
        "captured_at": datetime.now().isoformat(),
    }
    enriched = [{**q, "node_snapshot": snapshot} for q in state["questions"]]
    return {"questions": enriched}


def _save_questions_node(state: WorkbenchState) -> dict:
    """저장은 UI에서 사용자 승인 후 backend가 처리 — 에이전트는 생성만 담당"""
    print(f"✅ {len(state['questions'])}개 생성 완료 (저장은 UI 승인 후)")
    return {"saved_questions": []}


def build_workbench_question_graph():
    graph = StateGraph(WorkbenchState)
    graph.add_node("load_entity_and_graph", _load_entity_and_graph_node)
    graph.add_node("build_blueprint_context", _build_blueprint_context_node)
    graph.add_node("generate_questions", _generate_workbench_questions_node)
    graph.add_node("attach_snapshot", _attach_node_snapshot_node)
    graph.add_node("save_questions", _save_questions_node)

    graph.add_edge(START, "load_entity_and_graph")
    graph.add_edge("load_entity_and_graph", "build_blueprint_context")
    graph.add_edge("build_blueprint_context", "generate_questions")
    graph.add_edge("generate_questions", "attach_snapshot")
    graph.add_edge("attach_snapshot", "save_questions")
    graph.add_edge("save_questions", END)
    return graph.compile()
