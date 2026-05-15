"""
ResearcherHarness: Curriculum 기반 노드 조사
"""
import json
import os
from pathlib import Path
from shared.db_client import get_db_client
from agents.researcher.src.graphs.research_graph import build_research_graph

# nodes.json 위치: 환경 변수로 오버라이드 가능
NODES_FILE = Path(os.getenv("NODES_FILE", "nodes.json"))
# 한 번 리서치 시 최대 조사 노드 수 (과도한 API 호출 방지)
MAX_NODES_PER_RUN = int(os.getenv("RESEARCH_MAX_NODES", "5"))


class ResearcherHarness:
    def __init__(self):
        _, _, self.res_db = get_db_client()

    def _load_nodes(self) -> list:
        """nodes.json에서 노드 목록 로드"""
        if not NODES_FILE.exists():
            print(f"Warning: {NODES_FILE} not found")
            return []
        try:
            with open(NODES_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load {NODES_FILE}: {e}")
            return []

    def trigger_research(self, text: str = None) -> int:
        """
        nodes.json의 실제 노드를 순회하며 웹 검색 → 요약 → 저장

        Args:
            text: 미사용 (API 호환성 유지용)

        Returns:
            실제로 조사한 노드 수
        """
        print(f"\n🔬 [RESEARCH] Loading curriculum nodes from {NODES_FILE}...")

        nodes = self._load_nodes()
        if not nodes:
            print("  No nodes found. Generate curriculum first.")
            return 0

        nodes_to_research = nodes[:MAX_NODES_PER_RUN]
        print(f"  Researching {len(nodes_to_research)} of {len(nodes)} nodes")

        researched = 0
        for node in nodes_to_research:
            node_id = node.get("id", "")
            node_name = node.get("name") or node.get("label") or node_id
            if not node_id:
                continue

            print(f"  → Researching: {node_name} ({node_id})")
            try:
                graph = build_research_graph()
                graph.invoke({
                    "entity_id": node_id,
                    "entity": None,
                    "keywords": [],
                    "search_results": [],
                    "saved_results": []
                })
                researched += 1
            except Exception as e:
                print(f"  ✗ Research failed for {node_id}: {e}")

        print(f"✅ RESEARCH 완료: {researched}개 노드 조사")
        return researched

    def research(self, text: str = None) -> dict:
        """
        Curriculum 기반 조사 수행

        Args:
            text: 추가 컨텍스트 (optional, 현재 미사용)

        Returns:
            조사 결과 요약
        """
        count = self.trigger_research(text)
        return {
            "status": "research_completed",
            "nodes_researched": count,
            "results_saved": count > 0
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
