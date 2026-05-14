"""
File-based implementation of ResearcherDB
Uses research_results.json for storage
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4
from datetime import datetime

from shared.db_client import ResearcherDB, ValidationError


class ResearcherDBFile(ResearcherDB):
    """File-based implementation using JSON files"""

    def __init__(self, config: Dict = None):
        """
        Initialize file-based storage

        Args:
            config: Dictionary with optional key:
                - research_file: Path to research_results.json
        """
        self.config = config or {}
        self.research_file = Path(self.config.get("research_file", "research_results.json"))

        self._init_files()
        self._load()

    def _init_files(self):
        """Initialize JSON file if it doesn't exist"""
        if not self.research_file.exists():
            with open(self.research_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def _load(self):
        """Load data from file"""
        try:
            with open(self.research_file, "r", encoding="utf-8") as f:
                self.research_results = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self.research_results = []

    def _save(self):
        """Save data to file"""
        with open(self.research_file, "w", encoding="utf-8") as f:
            json.dump(self.research_results, f, ensure_ascii=False, indent=2)

    def create_research_result(
        self,
        entity_id: str,
        keyword: str,
        source: str,
        title: str,
        url: str = None,
        summary: str = None,
        full_content: str = None,
        metadata: Dict = None
    ) -> Dict:
        """Save research result"""
        result_id = str(uuid4())[:8]

        result = {
            "id": result_id,
            "entity_id": entity_id,
            "keyword": keyword,
            "source": source,
            "title": title,
            "url": url,
            "summary": summary,
            "full_content": full_content,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        }

        self.research_results.append(result)
        self._save()
        return result

    def query_research_results(
        self,
        entity_id: str = None,
        keyword: str = None,
        source: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query research results with optional filters"""
        results = self.research_results

        if entity_id:
            results = [r for r in results if r.get("entity_id") == entity_id]

        if keyword:
            results = [r for r in results if keyword.lower() in r.get("keyword", "").lower()]

        if source:
            results = [r for r in results if r.get("source") == source]

        return results[:limit]

    def get_research_summary(self, entity_id: str) -> Dict:
        """Get research summary for entity"""
        entity_results = [r for r in self.research_results if r.get("entity_id") == entity_id]

        summary = {
            "entity_id": entity_id,
            "total_results": len(entity_results),
            "keyword_count": len(set(r.get("keyword") for r in entity_results)),
            "blog_count": len([r for r in entity_results if r.get("source") == "blog"]),
            "linkedin_count": len([r for r in entity_results if r.get("source") == "linkedin"]),
            "paper_count": len([r for r in entity_results if r.get("source") == "paper"]),
            "github_count": len([r for r in entity_results if r.get("source") == "github"]),
            "last_updated": max([r.get("created_at") for r in entity_results]) if entity_results else None
        }

        return summary
