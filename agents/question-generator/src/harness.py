"""
Question Generator Agent
주어진 entity를 기반으로 다양한 난이도의 문제를 생성한다.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from typing import Optional, List
import os
import json

from shared.schemas import Entity
from shared.db_client import get_db_client


class QuestionGenerator:
    """
    Question Generator: 문제 생성 및 통계 분석
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.8,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        kg_db, qb_db, _ = get_db_client()
        self.kg_db = kg_db
        self.qb_db = qb_db

    def generate_questions(
        self,
        entity_id: str,
        count: int = 5,
        difficulty_levels: List[str] = None
    ) -> dict:
        """
        주어진 entity에 대해 문제 생성

        Args:
            entity_id: Entity ID
            count: 생성할 문제 개수
            difficulty_levels: 난이도 목록 ('easy', 'medium', 'hard')

        Returns:
            생성된 문제 리스트
        """
        if difficulty_levels is None:
            difficulty_levels = ["easy", "medium", "hard"]

        try:
            entity = self.kg_db.query_entity(entity_id)
        except Exception as e:
            return {"error": str(e)}

        name = entity["name"]
        description = entity.get("description", "")

        # 기존 문제 통계 조회
        stats = self.qb_db.get_question_stats(entity_id)

        system_prompt = """당신은 교육 평가 전문가입니다.
주어진 개념에 대해 다양한 형식의 객관식 문제를 생성하세요.

응답 형식은 JSON으로:
{
  "questions": [
    {
      "question_text": "문제 텍스트",
      "options": [
        {"text": "선택지1", "is_correct": true},
        {"text": "선택지2", "is_correct": false},
        ...
      ],
      "correct_answer": "선택지1",
      "explanation": "해설",
      "difficulty_level": "easy|medium|hard"
    }
  ]
}"""

        user_message = f"""
개념: {name}
설명: {description}

현재 통계:
- 총 문제: {stats.get('total_questions', 0)}개
- 쉬움: {stats.get('easy_count', 0)}개
- 중간: {stats.get('medium_count', 0)}개
- 어려움: {stats.get('hard_count', 0)}개

{count}개의 새로운 문제를 생성해주세요.
난이도는 {', '.join(difficulty_levels)}을 포함해주세요."""

        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])

        # 응답 파싱
        try:
            # JSON 추출 (```json ... ``` 형식 처리)
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content)
            questions = data.get("questions", [])

            # DB에 저장
            saved_questions = []
            for q in questions:
                try:
                    saved = self.qb_db.create_question(
                        entity_id=entity_id,
                        question_text=q["question_text"],
                        options=q["options"],
                        correct_answer=q.get("correct_answer"),
                        difficulty_level=q.get("difficulty_level", "medium"),
                        explanation=q.get("explanation")
                    )
                    saved_questions.append(saved)
                except Exception as e:
                    print(f"Error saving question: {e}")

            return {
                "entity_id": entity_id,
                "entity_name": name,
                "generated_count": len(saved_questions),
                "questions": saved_questions,
                "stats_before": stats
            }

        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse LLM response: {e}"}

    def get_statistics(self, entity_id: str) -> dict:
        """Entity의 문제 통계"""
        return self.qb_db.get_question_stats(entity_id)

    def get_user_performance(self, user_id: str, entity_id: str = None) -> dict:
        """사용자의 성과 조회"""
        return self.qb_db.get_user_performance(user_id, entity_id)

    def record_response(
        self,
        question_id: str,
        response: str,
        is_correct: bool,
        user_id: str = None
    ) -> dict:
        """사용자 응답 기록"""
        return self.qb_db.record_response(
            question_id=question_id,
            response=response,
            is_correct=is_correct,
            user_id=user_id
        )


# 싱글턴 인스턴스
_generator: Optional[QuestionGenerator] = None


def get_generator() -> QuestionGenerator:
    """Generator 인스턴스 반환"""
    global _generator
    if _generator is None:
        _generator = QuestionGenerator()
    return _generator
