"""
QuestionGeneratorHarness: Entity 기반 문제 자동 생성
"""
from shared.db_client import get_db_client
from agents.question_generator.src.graphs.question_generation_graph import build_question_generation_graph


class QuestionGeneratorHarness:
    def __init__(self):
        _, self.qb_db, _ = get_db_client()

    def trigger_generate(self, entity_id: str) -> None:
        """
        Entity에 대한 문제 생성

        Args:
            entity_id: 문제를 생성할 Entity ID
        """
        print(f"\n❓ [GENERATE] Entity ID: {entity_id}")

        graph = build_question_generation_graph()
        result = graph.invoke({
            "entity_id": entity_id,
            "entity": None,
            "related_context": "",
            "difficulty_distribution": {},
            "questions": [],
            "saved_questions": []
        })

        saved_count = len(result.get("saved_questions", []))
        print(f"✅ GENERATE 완료: {saved_count}개 문제 생성")

    def get_statistics(self, entity_id: str) -> dict:
        """Entity의 문제 통계"""
        return self.qb_db.get_question_stats(entity_id)

    def query_questions(
        self,
        entity_id: str = None,
        difficulty_level: str = None,
        limit: int = 100
    ) -> dict:
        """문제 조회"""
        try:
            questions = self.qb_db.query_questions(
                entity_id=entity_id,
                difficulty_level=difficulty_level,
                limit=limit
            )
            return {
                "entity_id": entity_id,
                "difficulty_level": difficulty_level,
                "count": len(questions),
                "questions": questions
            }
        except Exception as e:
            return {"error": str(e)}

    def show_statistics(self, entity_id: str) -> None:
        """Entity의 문제 통계 표시"""
        stats = self.get_statistics(entity_id)

        print(f"\n📊 [문제 통계] Entity: {entity_id}")
        print(f"  총 문제: {stats.get('total_questions', 0)}개")

        if stats.get('total_questions', 0) > 0:
            print(f"  난이도별 분포:")
            print(f"    쉬움(Easy): {stats.get('easy_count', 0)}개")
            print(f"    중간(Medium): {stats.get('medium_count', 0)}개")
            print(f"    어려움(Hard): {stats.get('hard_count', 0)}개")


def get_generator() -> QuestionGeneratorHarness:
    """Question Generator 인스턴스 반환"""
    return QuestionGeneratorHarness()
