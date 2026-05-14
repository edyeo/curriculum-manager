"""
Researcher Agent
주어진 키워드를 검색하고 조사 결과를 정리하여 knowledge graph를 강화한다.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from typing import Optional, List
import os
import json
from datetime import datetime

from shared.db_client import get_db_client


class Researcher:
    """
    Researcher: 키워드 기반 조사 및 결과 저장
    (현재는 시뮬레이션, 향후 실제 웹 스크래핑 통합)
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        _, _, res_db = get_db_client()
        self.res_db = res_db

    def research(
        self,
        entity_id: str,
        keywords: List[str] = None,
        sources: List[str] = None
    ) -> dict:
        """
        주어진 entity에 대해 조사 수행

        Args:
            entity_id: Entity ID
            keywords: 검색 키워드 목록
            sources: 검색 대상 ('blog', 'linkedin', 'github', 'paper')

        Returns:
            조사 결과 리스트
        """
        if sources is None:
            sources = ["blog", "github"]

        if keywords is None:
            keywords = ["python", "programming"]

        results = []

        system_prompt = """당신은 리서치 어시스턴트입니다.
주어진 키워드로 찾은 관련 자료를 요약하여 제시하세요.

각 결과는 다음 형식으로 작성하세요:
- 제목: 간결한 제목
- 요약: 2-3줄의 요약
- 핵심 포인트: 3가지 주요 내용"""

        for keyword in keywords:
            for source in sources:
                # 시뮬레이션: LLM으로 가상의 조사 결과 생성
                user_message = f"""
키워드: {keyword}
출처: {source}

위 키워드와 출처를 바탕으로 조사 결과를 작성해주세요.
(실제 웹 검색 결과를 시뮬레이션하는 가상의 정보)"""

                response = self.llm.invoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_message)
                ])

                # DB에 저장
                try:
                    result = self.res_db.create_research_result(
                        entity_id=entity_id,
                        keyword=keyword,
                        source=source,
                        title=f"{keyword} - {source}",
                        summary=response.content[:300],
                        full_content=response.content,
                        metadata={"timestamp": datetime.now().isoformat()}
                    )
                    results.append(result)
                except Exception as e:
                    print(f"Error saving research result: {e}")

        return {
            "entity_id": entity_id,
            "keywords": keywords,
            "sources": sources,
            "results_count": len(results),
            "results": results
        }

    def get_summary(self, entity_id: str) -> dict:
        """Entity의 조사 요약 반환"""
        return self.res_db.get_research_summary(entity_id)

    def query_results(
        self,
        entity_id: str = None,
        keyword: str = None,
        source: str = None
    ) -> dict:
        """조사 결과 조회"""
        results = self.res_db.query_research_results(
            entity_id=entity_id,
            keyword=keyword,
            source=source
        )
        return {
            "entity_id": entity_id,
            "keyword": keyword,
            "source": source,
            "results_count": len(results),
            "results": results
        }


# 싱글턴 인스턴스
_researcher: Optional[Researcher] = None


def get_researcher() -> Researcher:
    """Researcher 인스턴스 반환"""
    global _researcher
    if _researcher is None:
        _researcher = Researcher()
    return _researcher
