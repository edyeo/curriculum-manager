"""
MentalModelManagerHarness: Entity별 평가 기준(Rubric) 생성
"""
from shared.db_client import get_db_client
from agents.mental_model_manager.src.graphs.mental_model_generation_graph import build_mental_model_generation_graph


class MentalModelManagerHarness:
    def __init__(self):
        self.mental_models = {}  # 메모리 캐시

    def trigger_generate(self, entity_id: str) -> None:
        """
        Entity에 대한 평가 기준(Mental Model Rubric) 생성

        Args:
            entity_id: 평가 기준을 생성할 Entity ID
        """
        print(f"\n🧠 [GENERATE] Entity ID: {entity_id}")

        graph = build_mental_model_generation_graph()
        result = graph.invoke({
            "entity_id": entity_id,
            "entity": None,
            "entity_context": "",
            "rubric": {},
            "saved_result": None
        })

        # 메모리에 저장
        if result.get("saved_result"):
            self.mental_models[entity_id] = result["saved_result"]
            print(f"✅ GENERATE 완료: 평가 기준 생성 및 저장")

    def get_mental_model(self, entity_id: str) -> dict:
        """Entity의 Mental Model(평가 기준) 조회"""
        if entity_id not in self.mental_models:
            return {"error": f"Mental model not found for entity {entity_id}"}
        return self.mental_models[entity_id]

    def show_rubric(self, entity_id: str, level: str = None) -> None:
        """Mental Model의 평가 기준 표시"""
        model = self.get_mental_model(entity_id)

        if "error" in model:
            print(f"\n❌ {model['error']}")
            return

        print(f"\n📋 [Mental Model Rubric] {model.get('entity_name', entity_id)}")
        print(f"   Entity Type: {model.get('entity_type')} | Depth: {model.get('entity_depth')}")

        levels = {
            "junior": ("주니어 (Can Execute)", model.get("junior_rubric", [])),
            "senior": ("시니어 (Can Design)", model.get("senior_rubric", [])),
            "staff": ("스태프 (Can Predict Failure)", model.get("staff_rubric", []))
        }

        if level:
            levels = {level: levels.get(level, ("Unknown", []))}

        for key, (label, items) in levels.items():
            print(f"\n   {label}:")
            for i, item in enumerate(items, 1):
                print(f"     {i}. {item}")

    def get_level_count(self, entity_id: str) -> dict:
        """각 수준의 평가 항목 개수 반환"""
        model = self.get_mental_model(entity_id)

        if "error" in model:
            return model

        return {
            "entity_id": entity_id,
            "entity_name": model.get("entity_name"),
            "junior_count": len(model.get("junior_rubric", [])),
            "senior_count": len(model.get("senior_rubric", [])),
            "staff_count": len(model.get("staff_rubric", []))
        }


def get_manager() -> MentalModelManagerHarness:
    """Mental Model Manager 인스턴스 반환"""
    return MentalModelManagerHarness()
