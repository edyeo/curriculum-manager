"""
Mental Model Manager Agent
개념의 mental model(심리적 모델)을 생성하여 학습자의 이해도를 높인다.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from typing import Optional
import os
import json

from shared.schemas import Entity
from shared.db_client import get_db_client


class MentalModelManager:
    """Mental model 초안 생성"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        kg_db, _, _ = get_db_client()
        self.kg_db = kg_db

    def generate_mental_model(
        self,
        entity_id: str,
        mental_model_type: str = "conceptual"
    ) -> dict:
        """
        주어진 entity의 mental model 생성

        Args:
            entity_id: Entity ID
            mental_model_type: 'conceptual', 'analogical', 'narrative'

        Returns:
            Mental model 데이터
        """
        try:
            entity = self.kg_db.query_entity(entity_id)
        except Exception as e:
            return {"error": str(e)}

        name = entity["name"]
        description = entity.get("description", "")

        # Mental model 유형별 프롬프트
        if mental_model_type == "conceptual":
            system_prompt = """당신은 학습 심리학 전문가입니다.
주어진 개념에 대해 학습자가 쉽게 이해할 수 있는 'mental model'을 생성하세요.

다음 구성으로 작성하세요:
1. **핵심 개념**: 1-2줄의 간단한 정의
2. **주요 특징**: 3-5개의 주요 특성
3. **학습자 오류**: 학습자가 자주 범하는 오류 2-3가지
4. **구체적 예시**: 실제 예제 2가지
5. **유추/메타포**: 더 친숙한 개념과의 비교"""

        elif mental_model_type == "analogical":
            system_prompt = """당신은 교육 전문가입니다.
주어진 개념을 학습자가 이미 알고 있는 친숙한 개념과 비교하여 설명하세요.

다음 구성으로 작성하세요:
1. **타겟 개념**: 학습할 개념
2. **유추 개념**: 비슷한 친숙한 개념
3. **공통점**: 3-4가지 유사성
4. **차이점**: 2-3가지 차이점
5. **학습 조언**: 이 유추를 사용할 때의 주의사항"""

        else:  # narrative
            system_prompt = """당신은 과학 저술가입니다.
주어진 개념을 일관된 스토리로 설명하여 학습자가 깊이 있게 이해할 수 있게 하세요.

다음 구성으로 작성하세요:
1. **개념의 역사**: 이 개념이 어떻게 발전했는가
2. **문제 해결**: 이 개념으로 어떤 문제를 해결하는가
3. **실제 응용**: 현실의 사례
4. **학습 전략**: 이 개념을 효과적으로 배우는 방법"""

        user_message = f"""
개념: {name}
설명: {description}

위 개념에 대해 {mental_model_type} 유형의 mental model을 생성해주세요.
"""

        # LLM 호출
        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])

        return {
            "entity_id": entity_id,
            "mental_model_type": mental_model_type,
            "content": response.content,
            "entity": {
                "id": entity["id"],
                "name": entity["name"],
                "description": entity.get("description")
            }
        }

    def generate_all_types(self, entity_id: str) -> dict:
        """모든 유형의 mental model 생성"""
        models = {}
        for mm_type in ["conceptual", "analogical", "narrative"]:
            models[mm_type] = self.generate_mental_model(entity_id, mm_type)

        return {
            "entity_id": entity_id,
            "mental_models": models
        }


# 싱글턴 인스턴스
_manager: Optional[MentalModelManager] = None


def get_manager() -> MentalModelManager:
    """Manager 인스턴스 반환"""
    global _manager
    if _manager is None:
        _manager = MentalModelManager()
    return _manager
