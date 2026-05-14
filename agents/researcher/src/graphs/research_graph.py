"""
Research Graph
Entity 정보를 분석하여 강화 키워드를 추출하고, 웹 검색으로 정보를 수집한다.
"""
import os
from typing import Annotated, Optional
from datetime import datetime
import operator

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from shared.schemas import Entity
from shared.state_manager import load_nodes, load_skill
from shared.db_client import get_db_client


class KeywordExtractionOutput(TypedDict):
    """LLM이 추출하는 keyword 목록"""
    keywords: list[dict]  # [{"keyword": str, "rationale": str, "sources": list[str], "priority": str}]


class ResearchState(TypedDict):
    entity_id: str
    entity: Optional[Entity]
    keywords: list[dict]
    search_results: list[dict]
    saved_results: list[dict]


def _load_entity_node(state: ResearchState) -> dict:
    """Knowledge Graph에서 entity 로드"""
    entity_id = state["entity_id"]
    nodes = load_nodes()

    entity = next((n for n in nodes if n.id == entity_id), None)
    if not entity:
        raise ValueError(f"Entity {entity_id} not found in knowledge graph")

    print(f"\n📚 Entity 로드: {entity.name} ({entity.type.value})")
    return {"entity": entity}


def _extract_keywords_node(state: ResearchState) -> dict:
    """Entity 정보 분석 → 강화 필요 keyword 추출"""
    entity = state["entity"]

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        temperature=0.7
    )
    structured_llm = llm.with_structured_output(KeywordExtractionOutput, method="function_calling")

    skill = load_skill("keyword_extractor_skill.md")

    user_message = f"""Entity 분석:
- 이름: {entity.name}
- 설명: {entity.description}
- 타입: {entity.type.value}
- Depth: {entity.depth}

이 Entity를 깊게 이해하기 위해 조사해야 할 키워드를 추출하세요."""

    response = structured_llm.invoke([
        SystemMessage(content=skill),
        HumanMessage(content=user_message)
    ])

    keywords = response.get("keywords", [])
    print(f"🔍 추출된 키워드: {len(keywords)}개")
    for kw in keywords:
        print(f"  - {kw['keyword']} ({kw['priority']})")

    return {"keywords": keywords}


def _search_keywords_node(state: ResearchState) -> dict:
    """각 keyword에 대해 WebSearch 실행"""
    from shared.web_search import search_web

    keywords = state["keywords"]
    entity_id = state["entity_id"]
    search_results = []

    for kw_obj in keywords:
        keyword = kw_obj["keyword"]
        sources = kw_obj.get("sources", ["blog", "github"])
        priority = kw_obj.get("priority", "medium")

        print(f"\n🔎 검색 중: '{keyword}'")

        try:
            # WebSearch 수행
            raw_results = search_web(keyword, num_results=3)

            search_result = {
                "keyword": keyword,
                "entity_id": entity_id,
                "priority": priority,
                "sources": sources,
                "raw_results": raw_results,
                "searched_at": datetime.now().isoformat()
            }
            search_results.append(search_result)
            print(f"  ✓ {len(raw_results)}개 결과 수집")
        except Exception as e:
            print(f"  ✗ 검색 실패: {e}")

    return {"search_results": search_results}


def _summarize_results_node(state: ResearchState) -> dict:
    """웹 검색 결과 요약"""
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.5
    )

    search_results = state["search_results"]
    summarized = []

    for search_result in search_results:
        keyword = search_result["keyword"]
        raw_results = search_result["raw_results"]

        if not raw_results:
            continue

        # 원본 텍스트 취합
        raw_content = "\n\n".join([
            f"[{r.get('title', 'No title')}]\n{r.get('snippet', '')}"
            for r in raw_results[:3]
        ])

        # LLM으로 요약
        try:
            summarizer_skill = load_skill("research_summarizer_skill.md")
            summary_response = llm.invoke([
                SystemMessage(content=summarizer_skill),
                HumanMessage(content=f"""키워드: {keyword}\n\n검색 결과:\n{raw_content}""")
            ])

            summary = summary_response.content
        except Exception as e:
            print(f"  요약 생성 실패 ({keyword}): {e}")
            summary = f"검색 결과 요약 생성 중 오류 발생: {e}"

        summarized.append({
            "keyword": keyword,
            "raw_content": raw_content,
            "summary": summary,
            "raw_results_count": len(raw_results),
            "priority": search_result["priority"]
        })

    return {"search_results": summarized}


def _save_results_node(state: ResearchState) -> dict:
    """Research DB에 저장"""
    _, _, res_db = get_db_client()

    entity_id = state["entity_id"]
    search_results = state["search_results"]
    saved = []

    for result in search_results:
        keyword = result["keyword"]

        try:
            saved_result = res_db.create_research_result(
                entity_id=entity_id,
                keyword=keyword,
                source="web_search",
                title=f"Research: {keyword}",
                url=None,
                summary=result["summary"],
                full_content=result["raw_content"],
                metadata={
                    "priority": result["priority"],
                    "results_count": result["raw_results_count"],
                    "timestamp": datetime.now().isoformat()
                }
            )
            saved.append(saved_result)
            print(f"✅ 저장 완료: {keyword}")
        except Exception as e:
            print(f"❌ 저장 실패 ({keyword}): {e}")

    print(f"\n📊 총 {len(saved)}개 결과 저장 완료")
    return {"saved_results": saved}


def build_research_graph():
    """Research Graph 구성"""
    graph = StateGraph(ResearchState)

    graph.add_node("load_entity", _load_entity_node)
    graph.add_node("extract_keywords", _extract_keywords_node)
    graph.add_node("search_keywords", _search_keywords_node)
    graph.add_node("summarize_results", _summarize_results_node)
    graph.add_node("save_results", _save_results_node)

    graph.add_edge(START, "load_entity")
    graph.add_edge("load_entity", "extract_keywords")
    graph.add_edge("extract_keywords", "search_keywords")
    graph.add_edge("search_keywords", "summarize_results")
    graph.add_edge("summarize_results", "save_results")
    graph.add_edge("save_results", END)

    return graph.compile()
