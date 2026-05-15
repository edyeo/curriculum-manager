"""
PostgreSQL implementation of QuestionBankDB
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional
import json
from uuid import uuid4

from shared.db_client import QuestionBankDB, ValidationError


class QuestionBankPostgres(QuestionBankDB):
    """PostgreSQL implementation of Question Bank database"""

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

    # ========== Question Operations ==========

    def query_questions(
        self,
        entity_id: str = None,
        difficulty_level: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query questions with optional filters"""
        cursor = self._get_cursor()
        try:
            query = "SELECT * FROM qb.question WHERE 1=1"
            params = []

            if entity_id:
                query += " AND entity_id = %s"
                params.append(entity_id)

            if difficulty_level:
                query += " AND difficulty_level = %s"
                params.append(difficulty_level)

            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            self._close_cursor(cursor)

    def create_question(
        self,
        entity_id: str,
        question_text: str,
        options: List[Dict],
        correct_answer: str = None,
        difficulty_level: str = None,
        explanation: str = None,
        metadata: Dict = None
    ) -> Dict:
        """Create new question"""
        question_id = str(uuid4())[:8]
        metadata = metadata or {}

        cursor = self._get_cursor()
        try:
            cursor.execute(
                """
                INSERT INTO qb.question
                (id, entity_id, question_text, options, correct_answer, difficulty_level, explanation, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    question_id, entity_id, question_text, json.dumps(options),
                    correct_answer, difficulty_level, explanation, json.dumps(metadata)
                )
            )
            row = cursor.fetchone()
            self.conn.commit()
            return dict(row)
        except psycopg2.Error as e:
            self.conn.rollback()
            raise ValidationError(f"Failed to create question: {e}")
        finally:
            self._close_cursor(cursor)

    def upsert_questions(self, questions: List[Dict]) -> List[Dict]:
        """Create or update multiple questions"""
        results = []
        for q in questions:
            q_id = q.get("id", str(uuid4())[:8])
            cursor = self._get_cursor()
            try:
                # Try to create (simpler for bulk operations)
                cursor.execute(
                    """
                    INSERT INTO qb.question
                    (id, entity_id, question_text, options, correct_answer, difficulty_level, explanation, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        question_text = EXCLUDED.question_text,
                        options = EXCLUDED.options,
                        correct_answer = EXCLUDED.correct_answer,
                        difficulty_level = EXCLUDED.difficulty_level,
                        explanation = EXCLUDED.explanation,
                        metadata = EXCLUDED.metadata,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING *
                    """,
                    (
                        q_id, q["entity_id"], q["question_text"],
                        json.dumps(q["options"]),
                        q.get("correct_answer"),
                        q.get("difficulty_level"),
                        q.get("explanation"),
                        json.dumps(q.get("metadata", {}))
                    )
                )
                row = cursor.fetchone()
                self.conn.commit()
                results.append(dict(row))
            except psycopg2.Error as e:
                self.conn.rollback()
                raise ValidationError(f"Failed to upsert question: {e}")
            finally:
                self._close_cursor(cursor)

        return results

    # ========== Statistics ==========

    def get_question_stats(self, entity_id: str) -> Dict:
        """Get question statistics for entity"""
        cursor = self._get_cursor()
        try:
            cursor.execute(
                """
                SELECT
                    entity_id,
                    total_questions,
                    easy_count,
                    medium_count,
                    hard_count,
                    total_responses,
                    avg_correct_rate
                FROM qb.vw_question_stats
                WHERE entity_id = %s
                """,
                (entity_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else {
                "entity_id": entity_id,
                "total_questions": 0,
                "easy_count": 0,
                "medium_count": 0,
                "hard_count": 0,
                "total_responses": 0,
                "avg_correct_rate": None
            }
        finally:
            self._close_cursor(cursor)

    # ========== User Response ==========

    def record_response(
        self,
        question_id: str,
        response: str,
        is_correct: bool,
        user_id: str = None,
        response_time_sec: int = None,
        metadata: Dict = None
    ) -> Dict:
        """Record user's response to question"""
        response_id = str(uuid4())[:8]
        metadata = metadata or {}

        cursor = self._get_cursor()
        try:
            cursor.execute(
                """
                INSERT INTO qb.question_response
                (id, question_id, user_id, response, is_correct, response_time_sec, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    response_id, question_id, user_id, response, is_correct,
                    response_time_sec, json.dumps(metadata)
                )
            )
            row = cursor.fetchone()
            self.conn.commit()
            return dict(row)
        except psycopg2.Error as e:
            self.conn.rollback()
            raise ValidationError(f"Failed to record response: {e}")
        finally:
            self._close_cursor(cursor)

    def get_user_performance(
        self,
        user_id: str,
        entity_id: str = None
    ) -> Dict:
        """Get user's performance metrics"""
        cursor = self._get_cursor()
        try:
            if entity_id:
                cursor.execute(
                    """
                    SELECT
                        qr.user_id,
                        COUNT(*) as total_attempts,
                        COUNT(CASE WHEN qr.is_correct THEN 1 END) as correct_count,
                        ROUND(100.0 * COUNT(CASE WHEN qr.is_correct THEN 1 END)::NUMERIC / COUNT(*), 2) as correct_rate,
                        ROUND(AVG(qr.response_time_sec)::NUMERIC, 2) as avg_response_time_sec
                    FROM qb.question_response qr
                    INNER JOIN qb.question q ON qr.question_id = q.id
                    WHERE qr.user_id = %s AND q.entity_id = %s
                    GROUP BY qr.user_id
                    """,
                    (user_id, entity_id)
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM qb.vw_user_performance WHERE user_id = %s
                    """,
                    (user_id,)
                )

            row = cursor.fetchone()
            return dict(row) if row else {
                "user_id": user_id,
                "total_attempts": 0,
                "correct_count": 0,
                "correct_rate": 0.0,
                "avg_response_time_sec": None
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
