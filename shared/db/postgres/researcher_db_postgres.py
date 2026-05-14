"""
PostgreSQL implementation of ResearcherDB
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional
import json
from uuid import uuid4

from shared.db_client import ResearcherDB, ValidationError


class ResearcherDBPostgres(ResearcherDB):
    """PostgreSQL implementation of Researcher database"""

    def __init__(self, config: Dict):
        """Initialize PostgreSQL connection"""
        self.config = config
        self._connect()

    def _connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(
                host=self.config["host"],
                port=self.config["port"],
                database=self.config["database"],
                user=self.config["user"],
                password=self.config["password"],
            )
            self.conn.autocommit = False
        except psycopg2.Error as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}")

    def _get_cursor(self):
        """Get database cursor with dict output"""
        return self.conn.cursor(cursor_factory=RealDictCursor)

    def _close_cursor(self, cursor):
        """Close cursor and commit"""
        if cursor:
            cursor.close()
        self.conn.commit()

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
        metadata = metadata or {}

        cursor = self._get_cursor()
        try:
            cursor.execute(
                """
                INSERT INTO res.research_result
                (id, entity_id, keyword, source, title, url, summary, full_content, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    result_id, entity_id, keyword, source, title, url,
                    summary, full_content, json.dumps(metadata)
                )
            )
            row = cursor.fetchone()
            self.conn.commit()
            return dict(row)
        except psycopg2.Error as e:
            self.conn.rollback()
            raise ValidationError(f"Failed to create research result: {e}")
        finally:
            self._close_cursor(cursor)

    def query_research_results(
        self,
        entity_id: str = None,
        keyword: str = None,
        source: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query research results with optional filters"""
        cursor = self._get_cursor()
        try:
            query = "SELECT * FROM res.research_result WHERE 1=1"
            params = []

            if entity_id:
                query += " AND entity_id = %s"
                params.append(entity_id)

            if keyword:
                query += " AND keyword ILIKE %s"
                params.append(f"%{keyword}%")

            if source:
                query += " AND source = %s"
                params.append(source)

            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            self._close_cursor(cursor)

    def get_research_summary(self, entity_id: str) -> Dict:
        """Get research summary for entity"""
        cursor = self._get_cursor()
        try:
            cursor.execute(
                """
                SELECT
                    entity_id,
                    total_results,
                    keyword_count,
                    blog_count,
                    linkedin_count,
                    paper_count,
                    github_count,
                    last_updated
                FROM res.vw_research_summary
                WHERE entity_id = %s
                """,
                (entity_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else {
                "entity_id": entity_id,
                "total_results": 0,
                "keyword_count": 0,
                "blog_count": 0,
                "linkedin_count": 0,
                "paper_count": 0,
                "github_count": 0,
                "last_updated": None
            }
        finally:
            self._close_cursor(cursor)

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __del__(self):
        """Ensure connection is closed on object deletion"""
        self.close()
