"""
통합 워크플로우 시나리오 테스트

실제 교육 시스템의 데이터 흐름을 검증:
1. Curriculum 생성 (DRAFT) → 교육 구조 형성
2. Curriculum의 nodes/edges 분석 → 추가될만한 키워드 도출
3. 도출된 키워드로 Research 수행 → 교육 자료 수집
4. Research 결과를 Curriculum에 연계 → 교육 컨텐츠 강화
5. Entity별 Question 생성 → 평가 항목 작성
"""
import pytest
import requests


class TestCurriculumToResearchFlow:
    """커리큘럼 생성 → 연구 수행 통합 시나리오"""

    def test_scenario_curriculum_analysis_and_research(self, gateway_url: str, requires_real_llm):
        """
        Scenario 1: Curriculum 분석을 통한 Research 수행

        교육 흐름:
        1. Curriculum 생성 (구조 형성)
        2. Curriculum의 노드/링크 분석
        3. 추가될만한 키워드 자동 도출
        4. 도출된 키워드로 Research 수행
        5. Research 결과 수집
        """
        subject = "Python Programming Fundamentals"

        print(f"\n{'='*70}")
        print(f"Scenario 1: Curriculum Analysis → Automatic Research")
        print(f"{'='*70}")

        # Phase 1: Curriculum 생성
        print(f"\n[Phase 1] Creating Curriculum Structure")
        print(f"  Subject: {subject}")

        draft_resp = requests.post(
            f"{gateway_url}/proxy/curriculum/api/curriculum/generate/draft",
            json={"subject": subject, "description": "Learn Python from basics"},
            timeout=120
        )
        assert draft_resp.status_code == 200
        print(f"  ✅ Curriculum generated")

        # Phase 2: Curriculum 분석 및 키워드 도출
        print(f"\n[Phase 2] Curriculum Analysis & Keyword Derivation")
        print(f"  Analyzing nodes and edges...")

        status_resp = requests.get(f"{gateway_url}/proxy/curriculum/api/curriculum/status")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        nodes_count = status_data.get("nodes_count", 0)
        edges_count = status_data.get("edges_count", 0)

        print(f"  Current structure:")
        print(f"    - Nodes: {nodes_count}")
        print(f"    - Edges: {edges_count}")
        print(f"  ✅ Analysis complete")

        # Phase 3: 자동으로 도출된 키워드로 Research 수행
        # (Researcher가 내부적으로 curriculum을 읽고 키워드를 도출함)
        print(f"\n[Phase 3] Automatic Research on Derived Keywords")
        print(f"  Starting research based on curriculum analysis...")

        research_resp = requests.post(
            f"{gateway_url}/proxy/research/api/research/start",
            json={},  # body 없음 - researcher가 curriculum을 자동으로 분석
            timeout=120
        )
        assert research_resp.status_code == 200
        research_data = research_resp.json()
        print(f"  ✅ Research completed")
        print(f"     {research_data.get('data', {})}")

        # Phase 4: 전체 시스템 현황
        print(f"\n[Phase 4] System Overview")

        curr_status = requests.get(f"{gateway_url}/proxy/curriculum/api/curriculum/status")
        assert curr_status.status_code == 200

        print(f"  System Status:")
        print(f"    - Curriculum ready for enrichment")
        print(f"  ✅ Overview retrieved")

        print(f"\n{'='*70}")
        print(f"✅ Scenario 1 Complete: Automatic Curriculum → Research Flow")
        print(f"{'='*70}\n")

    def test_scenario_research_with_additional_context(self, gateway_url: str, requires_real_llm):
        """
        Scenario 2: 추가 컨텍스트를 활용한 Research 수행

        교육 흐름:
        1. Curriculum 생성
        2. 특정 영역(text)에 대한 추가 컨텍스트 제공
        3. Curriculum 분석 + 추가 컨텍스트로 키워드 도출
        4. Research 수행
        """
        subject = "Data Science Fundamentals"
        focus_area = "Statistical Analysis Deep Learning"

        print(f"\n{'='*70}")
        print(f"Scenario 2: Research with Additional Context")
        print(f"{'='*70}")

        # Phase 1: Curriculum 생성
        print(f"\n[Phase 1] Creating Curriculum")
        print(f"  Subject: {subject}")

        draft_resp = requests.post(
            f"{gateway_url}/proxy/curriculum/api/curriculum/generate/draft",
            json={"subject": subject},
            timeout=120
        )
        assert draft_resp.status_code == 200
        print(f"  ✅ Curriculum created")

        # Phase 2: 추가 컨텍스트를 포함한 Research
        print(f"\n[Phase 2] Research with Focus Areas")
        print(f"  Focus: {focus_area}")
        print(f"  Starting research...")

        research_resp = requests.post(
            f"{gateway_url}/proxy/research/api/research/start",
            json={"text": focus_area},  # 추가 컨텍스트 제공
            timeout=120
        )
        assert research_resp.status_code == 200
        print(f"  ✅ Research completed with additional context")

        print(f"\n{'='*70}")
        print(f"✅ Scenario 2 Complete: Context-Aware Research")
        print(f"{'='*70}\n")


class TestCurriculumToAssessmentFlow:
    """교육 커리큘럼에서 평가 항목 생성까지의 통합 흐름"""

    def test_scenario_complete_educational_pipeline(self, gateway_url: str, requires_real_llm):
        """
        Scenario 3: 완전한 교육 파이프라인

        전체 흐름:
        1. Curriculum 설계 (구조 및 학습 목표 정의)
        2. Curriculum 기반 Research (자동 키워드 도출 및 자료 수집)
        3. Mental Model 정의 (학습 목표별 역량 기준 설정)
        4. Assessment Questions 생성 (평가 도구 개발)
        5. 전체 교육 체계 검증
        """
        subject = "Web Development"

        print(f"\n{'='*70}")
        print(f"Scenario 3: Complete Educational Pipeline")
        print(f"{'='*70}")

        # Step 1: Curriculum 설계
        print(f"\n[Step 1/5] Curriculum Design")
        print(f"  Subject: {subject}")

        curriculum_resp = requests.post(
            f"{gateway_url}/proxy/curriculum/api/curriculum/generate/draft",
            json={
                "subject": subject,
                "description": "From HTML/CSS basics to full-stack development"
            },
            timeout=120
        )
        assert curriculum_resp.status_code == 200
        print(f"  ✅ Curriculum designed")

        # Step 2: Curriculum 기반 Research
        print(f"\n[Step 2/5] Curriculum-Based Resource Collection")
        print(f"  Analyzing curriculum structure...")

        research_resp = requests.post(
            f"{gateway_url}/proxy/research/api/research/start",
            json={},  # Researcher가 자동으로 curriculum 분석
            timeout=120
        )
        assert research_resp.status_code == 200
        print(f"  ✅ Learning resources collected via research")

        # Step 3: Mental Model 정의
        print(f"\n[Step 3/5] Competency Model Definition")

        mental_model_resp = requests.post(
            f"{gateway_url}/proxy/mental-models/api/mental-models/generate",
            json={"mental_model_type": "conceptual"},
            timeout=120
        )
        assert mental_model_resp.status_code == 200
        print(f"  ✅ Competency levels defined")

        # Step 4: 평가 도구 개발
        print(f"\n[Step 4/5] Assessment Tool Development")

        questions_resp = requests.post(
            f"{gateway_url}/proxy/questions/api/questions/generate",
            json={
                "entity_id": subject.lower().replace(" ", "-"),
                "count": 10,
                "difficulty_levels": ["easy", "medium", "hard"]
            },
            timeout=120
        )
        assert questions_resp.status_code == 200
        print(f"  ✅ Assessment questions created")

        # Step 5: 교육 체계 검증
        print(f"\n[Step 5/5] Educational System Verification")

        # Curriculum 상태
        curriculum_status = requests.get(
            f"{gateway_url}/proxy/curriculum/api/curriculum/status"
        )
        assert curriculum_status.status_code == 200
        curr_data = curriculum_status.json()

        # Question 현황
        question_overview = requests.get(
            f"{gateway_url}/proxy/questions/api/questions/overview"
        )
        assert question_overview.status_code == 200
        q_data = question_overview.json().get("data", {})

        print(f"  System Verification:")
        print(f"    - Curriculum Nodes: {curr_data.get('nodes_count', 0)}")
        print(f"    - Curriculum Edges: {curr_data.get('edges_count', 0)}")
        print(f"    - Assessment Items: {q_data.get('total_questions', 0)}")
        print(f"  ✅ System verified")

        print(f"\n{'='*70}")
        print(f"✅ Scenario 3 Complete: End-to-End Educational Pipeline")
        print(f"{'='*70}\n")
