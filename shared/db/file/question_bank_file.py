"""
File-based implementation of QuestionBankDB
Uses questions.json and responses.json for storage
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4
from datetime import datetime

from shared.db_client import QuestionBankDB, ValidationError


class QuestionBankFile(QuestionBankDB):
    """File-based implementation using JSON files"""

    def __init__(self, config: Dict = None):
        """
        Initialize file-based storage

        Args:
            config: Dictionary with optional keys:
                - questions_file: Path to questions.json
                - responses_file: Path to responses.json
        """
        self.config = config or {}
        self.questions_file = Path(self.config.get("questions_file", "questions.json"))
        self.responses_file = Path(self.config.get("responses_file", "responses.json"))

        self._init_files()
        self._load()

    def _init_files(self):
        """Initialize JSON files if they don't exist"""
        if not self.questions_file.exists():
            with open(self.questions_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

        if not self.responses_file.exists():
            with open(self.responses_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def _load(self):
        """Load data from files"""
        try:
            with open(self.questions_file, "r", encoding="utf-8") as f:
                self.questions = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self.questions = []

        try:
            with open(self.responses_file, "r", encoding="utf-8") as f:
                self.responses = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self.responses = []

    def _save(self):
        """Save data to files"""
        with open(self.questions_file, "w", encoding="utf-8") as f:
            json.dump(self.questions, f, ensure_ascii=False, indent=2)

        with open(self.responses_file, "w", encoding="utf-8") as f:
            json.dump(self.responses, f, ensure_ascii=False, indent=2)

    # ========== Question Operations ==========

    def query_questions(
        self,
        entity_id: str = None,
        difficulty_level: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query questions with optional filters"""
        results = self.questions

        if entity_id:
            results = [q for q in results if q.get("entity_id") == entity_id]

        if difficulty_level:
            results = [q for q in results if q.get("difficulty_level") == difficulty_level]

        return results[:limit]

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

        question = {
            "id": question_id,
            "entity_id": entity_id,
            "question_text": question_text,
            "options": options,
            "correct_answer": correct_answer,
            "difficulty_level": difficulty_level,
            "explanation": explanation,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        self.questions.append(question)
        self._save()
        return question

    def upsert_questions(self, questions: List[Dict]) -> List[Dict]:
        """Create or update multiple questions"""
        results = []
        for q in questions:
            q_id = q.get("id", str(uuid4())[:8])

            # Try to find and update
            found = False
            for i, existing_q in enumerate(self.questions):
                if existing_q.get("id") == q_id:
                    self.questions[i].update(q)
                    self.questions[i]["updated_at"] = datetime.now().isoformat()
                    found = True
                    results.append(self.questions[i])
                    break

            if not found:
                result = self.create_question(**q)
                results.append(result)

        self._save()
        return results

    # ========== Statistics ==========

    def get_question_stats(self, entity_id: str) -> Dict:
        """Get question statistics for entity"""
        entity_questions = [q for q in self.questions if q.get("entity_id") == entity_id]

        stats = {
            "entity_id": entity_id,
            "total_questions": len(entity_questions),
            "easy_count": len([q for q in entity_questions if q.get("difficulty_level") == "easy"]),
            "medium_count": len([q for q in entity_questions if q.get("difficulty_level") == "medium"]),
            "hard_count": len([q for q in entity_questions if q.get("difficulty_level") == "hard"]),
        }

        # Calculate response stats
        entity_responses = [r for r in self.responses if any(
            req.get("question_id") == r.get("question_id")
            for req in [self.questions[i] for i in range(len(self.questions))
                       if self.questions[i].get("entity_id") == entity_id]
        )]

        stats["total_responses"] = len(entity_responses)

        if entity_responses:
            correct = len([r for r in entity_responses if r.get("is_correct")])
            stats["avg_correct_rate"] = round(100.0 * correct / len(entity_responses), 2)
        else:
            stats["avg_correct_rate"] = None

        return stats

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

        response_obj = {
            "id": response_id,
            "question_id": question_id,
            "user_id": user_id,
            "response": response,
            "is_correct": is_correct,
            "response_time_sec": response_time_sec,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        }

        self.responses.append(response_obj)
        self._save()
        return response_obj

    def get_user_performance(
        self,
        user_id: str,
        entity_id: str = None
    ) -> Dict:
        """Get user's performance metrics"""
        user_responses = [r for r in self.responses if r.get("user_id") == user_id]

        if entity_id:
            entity_question_ids = {q.get("id") for q in self.questions if q.get("entity_id") == entity_id}
            user_responses = [r for r in user_responses if r.get("question_id") in entity_question_ids]

        stats = {
            "user_id": user_id,
            "total_attempts": len(user_responses),
            "correct_count": len([r for r in user_responses if r.get("is_correct")]),
            "correct_rate": 0.0,
            "avg_response_time_sec": None
        }

        if user_responses:
            stats["correct_rate"] = round(
                100.0 * stats["correct_count"] / stats["total_attempts"], 2
            )
            response_times = [r.get("response_time_sec") for r in user_responses if r.get("response_time_sec")]
            if response_times:
                stats["avg_response_time_sec"] = round(sum(response_times) / len(response_times), 2)

        return stats
