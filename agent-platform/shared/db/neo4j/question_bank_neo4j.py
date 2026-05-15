"""
Neo4j implementation of QuestionBankDB (stub for future implementation)
"""
from shared.db_client import QuestionBankDB


class QuestionBankNeo4j(QuestionBankDB):
    """Neo4j implementation of Question Bank database"""

    def __init__(self, config):
        raise NotImplementedError("Neo4j implementation coming in Phase 3")

    def query_questions(self, entity_id=None, difficulty_level=None, limit=100):
        raise NotImplementedError()

    def create_question(self, entity_id, question_text, options, correct_answer=None, difficulty_level=None, explanation=None, metadata=None):
        raise NotImplementedError()

    def upsert_questions(self, questions):
        raise NotImplementedError()

    def get_question_stats(self, entity_id):
        raise NotImplementedError()

    def record_response(self, question_id, response, is_correct, user_id=None, response_time_sec=None, metadata=None):
        raise NotImplementedError()

    def get_user_performance(self, user_id, entity_id=None):
        raise NotImplementedError()
