"""
Web Search Utility
"""
from typing import List, Dict, Optional


def search_web(query: str, num_results: int = 5) -> List[Dict]:
    """
    웹 검색 수행 (시뮬레이션)

    Args:
        query: 검색 쿼리
        num_results: 반환할 결과 수

    Returns:
        검색 결과 리스트 (title, snippet, url 포함)
    """
    try:
        return _simulate_search(query, num_results)
    except Exception as e:
        print(f"Web search failed for '{query}': {e}")
        return []


def _simulate_search(query: str, num_results: int) -> List[Dict]:
    """개발/테스트용 시뮬레이션 검색"""
    return [
        {
            "title": f"Search result {i+1}: {query}",
            "snippet": f"This is a simulated search result for '{query}'. "
                      f"In production, this would contain actual web content.",
            "url": f"https://example.com/result{i+1}"
        }
        for i in range(num_results)
    ]


def fetch_url(url: str) -> Optional[str]:
    """특정 URL에서 콘텐츠 추출"""
    try:
        return _simulate_fetch(url)
    except Exception as e:
        print(f"Failed to fetch URL '{url}': {e}")
        return None


def _simulate_fetch(url: str) -> str:
    """URL 페칭 시뮬레이션"""
    return f"Content from {url}\n\nThis is simulated content in development environment."
