"""
ResearcherHarness: Entity 강화를 위한 자동 키워드 추출 및 조사
"""
from shared.db_client import get_db_client
from agents.researcher.src.graphs.research_graph import build_research_graph


class ResearcherHarness:
    def __init__(self):
        _, _, self.res_db = get_db_client()

    def trigger_research(self, entity_id: str) -> None:
        """
        Entity 분석 → 키워드 추출 → 웹 검색 → 요약 → 저장

        Args:
            entity_id: 강화할 Entity ID
        """
        print(f"\n🔬 [RESEARCH] Entity ID: {entity_id}")

        graph = build_research_graph()
        result = graph.invoke({
            "entity_id": entity_id,
            "entity": None,
            "keywords": [],
            "search_results": [],
            "saved_results": []
        })

        saved_count = len(result.get("saved_results", []))
        print(f"✅ RESEARCH 완료: {saved_count}개 결과 저장")

    def get_summary(self, entity_id: str) -> dict:
        """Entity의 조사 요약 반환"""
        return self.res_db.get_research_summary(entity_id)

    def query_results(
        self,
        entity_id: str = None,
        keyword: str = None,
        source: str = None,
        limit: int = 100
    ) -> dict:
        """조사 결과 조회"""
        results = self.res_db.query_research_results(
            entity_id=entity_id,
            keyword=keyword,
            source=source,
            limit=limit
        )
        return {
            "entity_id": entity_id,
            "keyword": keyword,
            "source": source,
            "results_count": len(results),
            "results": results
        }

    def show_entity_research(self, entity_id: str) -> None:
        """Entity의 조사 결과 표시"""
        summary = self.get_summary(entity_id)

        print(f"\n📊 [RESEARCH 요약] Entity: {entity_id}")
        print(f"  총 결과: {summary.get('total_results', 0)}개")
        print(f"  조사 키워드: {summary.get('keyword_count', 0)}개")
        print(f"  마지막 업데이트: {summary.get('last_updated', 'N/A')}")

        if summary.get("total_results", 0) > 0:
            print(f"\n  출처별 분포:")
            for source in ["blog_count", "github_count", "paper_count", "linkedin_count"]:
                count = summary.get(source, 0)
                source_name = source.replace("_count", "").upper()
                if count > 0:
                    print(f"    {source_name}: {count}개")


def get_researcher() -> ResearcherHarness:
    """Researcher 인스턴스 반환"""
    return ResearcherHarness()
