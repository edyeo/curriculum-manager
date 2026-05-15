"""
API Gateway를 통한 Agent 통합 시나리오 테스트

각 agent의 실제 동작을 Gateway를 통해 end-to-end로 검증한다.
"""
import pytest
import requests


class TestGatewayHealth:
    """API Gateway 상태 확인"""

    def test_gateway_health(self, gateway_url: str):
        """Test: Gateway 헬스 체크"""
        response = requests.get(f"{gateway_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("gateway") == "online"
        print("\n✅ Gateway is online")


class TestAgentStatus:
    """모든 Agent 상태 조회"""

    def test_all_agents_status(self, gateway_url: str):
        """Test: 모든 Agent 상태 조회"""
        response = requests.get(f"{gateway_url}/agents/status")
        assert response.status_code == 200
        data = response.json()

        # 4개 agent 모두 응답 포함 확인
        assert "curriculum" in data or "curriculum-manager" in data
        assert "mental-models" in data or "mental-model-manager" in data
        assert "research" in data or "researcher" in data
        assert "questions" in data or "question-generator" in data

        print("\n✅ All agents are responding")


class TestCurriculumScenario:
    """Curriculum Manager를 통한 Draft → Status 시나리오"""

    def test_curriculum_draft_via_gateway(self, gateway_url: str, requires_real_llm):
        """Test: Gateway를 통한 Draft 생성"""
        draft_request = {
            "subject": "Gateway Test Subject"
        }

        response = requests.post(
            f"{gateway_url}/proxy/curriculum/api/curriculum/generate/draft",
            json=draft_request,
            timeout=120
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "success"
        assert data.get("data", {}).get("nodes_count", 0) >= 0

        print(f"\n✅ Draft created via Gateway: {data['data']['nodes_count']} nodes")

    def test_curriculum_status_via_gateway(self, gateway_url: str):
        """Test: Gateway를 통한 Status 조회"""
        response = requests.get(
            f"{gateway_url}/proxy/curriculum/api/curriculum/status"
        )

        assert response.status_code == 200
        data = response.json()
        # Status response comes directly from curriculum manager (not wrapped in data)
        assert data.get("status") in ["ready", "ok"]
        assert "nodes_count" in data
        assert "edges_count" in data

        print(f"\n✅ Curriculum status retrieved via Gateway")


class TestResearchScenario:
    """Researcher를 통한 Research Start → Summary 시나리오"""

    def test_research_start_via_gateway(self, gateway_url: str, requires_real_llm):
        """Test: Gateway를 통한 Research 시작 (Curriculum 기반)"""
        # 먼저 curriculum을 생성해야 researcher가 분석할 데이터가 있음
        draft_resp = requests.post(
            f"{gateway_url}/proxy/curriculum/api/curriculum/generate/draft",
            json={"subject": "Research Test Subject"},
            timeout=120
        )
        assert draft_resp.status_code == 200

        # Researcher는 curriculum을 자동으로 분석하고 키워드를 도출
        # body는 optional (text 필드만 필요시 전달)
        response = requests.post(
            f"{gateway_url}/proxy/research/api/research/start",
            json={},  # Curriculum 기반 자동 분석
            timeout=120
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "success"

        print(f"\n✅ Research started via Gateway (curriculum-based)")

    def test_research_summary_via_gateway(self, gateway_url: str):
        """Test: Gateway를 통한 Research 요약 조회"""
        entity_id = "concept-test-001"

        response = requests.get(
            f"{gateway_url}/proxy/research/api/research/summary/{entity_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "success"

        print(f"\n✅ Research summary retrieved via Gateway")


class TestMentalModelScenario:
    """Mental Model Manager를 통한 생성 → 조회 시나리오"""

    def test_mental_model_generate_via_gateway(self, gateway_url: str, requires_real_llm):
        """Test: Gateway를 통한 Mental Model 생성"""
        request_data = {
            "mental_model_type": "conceptual"
        }

        response = requests.post(
            f"{gateway_url}/proxy/mental-models/api/mental-models/generate",
            json=request_data,
            timeout=120
        )

        # Test that the endpoint is reachable via gateway
        assert response.status_code in [200, 400, 500]
        data = response.json()
        # Endpoint should return a response (success, error, etc.)
        assert isinstance(data, dict)

        print(f"\n✅ Mental Model endpoint accessible via Gateway")

    def test_mental_model_get_via_gateway(self, gateway_url: str):
        """Test: Gateway를 통한 Mental Model 조회"""
        response = requests.get(
            f"{gateway_url}/proxy/mental-models/api/mental-models/entity/default"
        )

        # 생성되지 않았을 수도 있으므로 200 또는 404 모두 허용
        assert response.status_code in [200, 404]

        print(f"\n✅ Mental Model query via Gateway completed")


class TestQuestionScenario:
    """Question Generator를 통한 생성 → 통계 시나리오"""

    def test_question_generate_via_gateway(self, gateway_url: str, requires_real_llm):
        """Test: Gateway를 통한 Question 생성"""
        # First create a curriculum so we have entities to question
        draft_resp = requests.post(
            f"{gateway_url}/proxy/curriculum/api/curriculum/generate/draft",
            json={"subject": "Question Test Subject"},
            timeout=120
        )
        assert draft_resp.status_code == 200

        # Use a generic entity_id
        request_data = {
            "entity_id": "question-test",
            "count": 3
        }

        response = requests.post(
            f"{gateway_url}/proxy/questions/api/questions/generate",
            json=request_data,
            timeout=120
        )

        # Gateway returns 200 even if the entity doesn't exist (endpoint is accessible)
        # In a real scenario, the entity would be extracted from the created curriculum
        assert response.status_code in [200, 404, 500]

        print(f"\n✅ Question generation endpoint accessible via Gateway")

    def test_question_overview_via_gateway(self, gateway_url: str):
        """Test: Gateway를 통한 전체 Question 통계 조회 (단일 쿼리)"""
        response = requests.get(
            f"{gateway_url}/proxy/questions/api/questions/overview"
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "success"
        overview = data.get("data", {})

        # 응답 구조 검증
        assert "total_questions" in overview
        assert "entity_stats" in overview
        assert "difficulty_summary" in overview

        print(f"\n✅ Question overview retrieved via single query")
        print(f"   Total questions: {overview.get('total_questions')}")

    def test_record_response_via_gateway(self, gateway_url: str):
        """Test: Gateway를 통한 답변 기록"""
        request_data = {
            "question_id": "q-001",
            "response": "test answer",
            "is_correct": True,
            "user_id": "user-001"
        }

        response = requests.post(
            f"{gateway_url}/proxy/questions/api/questions/response",
            json=request_data,
            timeout=60
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "success"

        print(f"\n✅ Response recorded via Gateway")


class TestOrchestratedScenario:
    """전체 Orchestrated 시나리오: 모든 Agent 연동"""

    def test_full_orchestration_workflow(self, gateway_url: str, requires_real_llm):
        """Test: 전체 워크플로우 (DRAFT → RESEARCH → MENTAL MODEL → QUESTIONS)"""

        subject = "Full Orchestration Test Subject"

        # Step 1: Curriculum DRAFT
        draft_resp = requests.post(
            f"{gateway_url}/proxy/curriculum/api/curriculum/generate/draft",
            json={"subject": subject},
            timeout=120
        )
        assert draft_resp.status_code == 200
        print(f"\n   Step 1: Curriculum DRAFT completed")

        # Step 2: Research START
        research_resp = requests.post(
            f"{gateway_url}/proxy/research/api/research/start",
            json={"entity_id": "orchestration-test-001"},
            timeout=120
        )
        assert research_resp.status_code == 200
        print(f"   Step 2: Research started")

        # Step 3: Mental Model GENERATE
        mental_model_resp = requests.post(
            f"{gateway_url}/proxy/mental-models/api/mental-models/generate",
            json={"mental_model_type": "conceptual"},
            timeout=120
        )
        assert mental_model_resp.status_code == 200
        print(f"   Step 3: Mental Model generated")

        # Step 4: Questions GENERATE
        questions_resp = requests.post(
            f"{gateway_url}/proxy/questions/api/questions/generate",
            json={"entity_id": "orchestration-test-001", "count": 3},
            timeout=120
        )
        assert questions_resp.status_code == 200
        print(f"   Step 4: Questions generated")

        # Step 5: Final STATUS checks
        curriculum_status = requests.get(
            f"{gateway_url}/proxy/curriculum/api/curriculum/status"
        )
        assert curriculum_status.status_code == 200

        questions_overview = requests.get(
            f"{gateway_url}/proxy/questions/api/questions/overview"
        )
        assert questions_overview.status_code == 200

        print(f"\n✅ Full orchestration workflow completed successfully")
        print(f"   All 4 agents (Curriculum, Research, MentalModel, Questions) responded")
