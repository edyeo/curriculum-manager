"""
ResearcherHarness: Curriculum 기반 키워드 도출 및 조사
"""
import json
from pathlib import Path
from shared.db_client import get_db_client
from agents.researcher.src.graphs.research_graph import build_research_graph


class ResearcherHarness:
    def __init__(self):
        _, _, self.res_db = get_db_client()

    def _load_curriculum_data(self) -> dict:
        """
        Curriculum의 nodes.json을 읽어서 현재 노드들을 반환

        Returns:
            {"nodes": [...], "edges": [...], "keywords": [...]}
        """
        nodes_file = Path("nodes.json")
        edges_file = Path("edges.json")

        nodes = []
        edges = []
        keywords = set()

        # Nodes 로드
        if nodes_file.exists():
            try:
                with open(nodes_file) as f:
                    nodes = json.load(f)
                    # 모든 node의 label/name에서 키워드 추출
                    for node in nodes:
                        if isinstance(node, dict):
                            keywords.add(node.get("label") or node.get("name", ""))
            except Exception as e:
                print(f"Warning: Could not load nodes.json: {e}")

        # Edges 로드
        if edges_file.exists():
            try:
                with open(edges_file) as f:
                    edges = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load edges.json: {e}")

        return {
            "nodes": nodes,
            "edges": edges,
            "existing_keywords": list(keywords)
        }

    def _derive_keywords(self, curriculum_data: dict, additional_text: str = None) -> list:
        """
        Curriculum의 nodes와 edges를 분석하여 추가될만한 키워드를 도출

        Args:
            curriculum_data: curriculum의 노드/엣지 정보
            additional_text: 키워드 도출 시 참고할 추가 텍스트

        Returns:
            추가 조사가 필요한 키워드 리스트
        """
        existing = set(curriculum_data.get("existing_keywords", []))

        # 기본 추가 키워드 (실제로는 LLM을 통해 도출할 수 있음)
        suggested = []

        # 현재 nodes가 적으면 추가 키워드 제시
        if len(existing) < 5:
            suggested = ["Best Practices", "Tools", "Use Cases", "Performance", "Security"]

        # additional_text가 있으면 그것도 포함
        if additional_text:
            suggested.extend(additional_text.split())

        # 이미 있는 키워드는 제외
        new_keywords = [k for k in suggested if k.lower() not in {e.lower() for e in existing}]

        return new_keywords[:5]  # 최대 5개

    def trigger_research(self, text: str = None) -> None:
        """
        Curriculum 분석 → 키워드 도출 → 웹 검색 → 요약 → 저장

        Args:
            text: 키워드 도출 시 추가 컨텍스트
        """
        print(f"\n🔬 [RESEARCH] Analyzing curriculum and deriving keywords...")

        # Curriculum 데이터 로드
        curriculum_data = self._load_curriculum_data()
        print(f"  Current keywords: {len(curriculum_data['existing_keywords'])}")
        print(f"  Nodes: {len(curriculum_data['nodes'])}")

        # 추가될만한 키워드 도출
        new_keywords = self._derive_keywords(curriculum_data, text)
        print(f"  Keywords to research: {new_keywords}")

        # 각 키워드에 대해 research 수행
        for keyword in new_keywords:
            print(f"  → Researching: {keyword}")
            graph = build_research_graph()
            result = graph.invoke({
                "entity_id": keyword.lower(),
                "entity": None,
                "keywords": [keyword],
                "search_results": [],
                "saved_results": []
            })

        print(f"✅ RESEARCH 완료: {len(new_keywords)}개 키워드 조사")

    def research(self, text: str = None) -> dict:
        """
        Curriculum 기반 조사 수행

        Args:
            text: 키워드 도출 시 추가 컨텍스트 (optional)

        Returns:
            조사 결과 요약
        """
        self.trigger_research(text)
        return {
            "status": "research_completed",
            "keywords_researched": 5,
            "results_saved": True
        }

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
