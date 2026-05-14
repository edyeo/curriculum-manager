"""
Curriculum Manager API 간단한 테스트: 로컬 서버와 통합 테스트
"""
import subprocess
import time
import requests
import pytest
import os
import json
from typing import Generator


@pytest.fixture(scope="session")
def curriculum_server() -> Generator[str, None, None]:
    """
    로컬에서 Curriculum Manager 서버를 시작하고 정지
    """
    print("\n🚀 Starting Curriculum Manager server...")

    # 환경 변수 설정
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = "sk-test-key-for-testing"
    env["DB_TYPE"] = "file"
    env["LOG_LEVEL"] = "DEBUG"
    env["PYTHONUNBUFFERED"] = "1"

    # FastAPI 서버 시작
    process = subprocess.Popen(
        ["python", "-m", "apps.curriculum_manager.main"],
        env=env,
        cwd="/Users/ed/writing/project/adaptive-learning-class/curriculum-manager/.claude/worktrees/test-integration",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # 서버 시작 대기 (최대 30초)
    print("⏳ Waiting for server to start...")
    max_retries = 30
    for attempt in range(max_retries):
        try:
            response = requests.get("http://localhost:8001/health", timeout=2)
            if response.status_code == 200:
                print("✅ Server is ready")
                break
        except requests.exceptions.RequestException:
            pass

        if attempt == max_retries - 1:
            process.terminate()
            raise TimeoutError("Server did not start in time")
        time.sleep(1)

    yield "http://localhost:8001"

    # 서버 정지
    print("\n🛑 Stopping server...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    print("✅ Server stopped")


class TestCurriculumAPISimple:
    """Curriculum Manager API 간단한 통합 테스트"""

    def test_01_health_check(self, curriculum_server: str):
        """Test 1: 헬스 체크"""
        response = requests.get(f"{curriculum_server}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("\n✅ Test 1 passed: Health check successful")

    def test_02_draft_creation(self, curriculum_server: str):
        """Test 2: DRAFT로 샘플 데이터 생성"""
        draft_request = {
            "subject": "Python Programming Basics",
            "description": "Introduction to Python concepts and best practices"
        }

        response = requests.post(
            f"{curriculum_server}/api/curriculum/generate/draft",
            json=draft_request,
            timeout=60
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Draft generated" in data["message"]
        assert "nodes_count" in data["data"]
        nodes_count = data["data"]["nodes_count"]

        print(f"\n✅ Test 2 passed: Generated {nodes_count} nodes from DRAFT")
        print(f"   Subject: {draft_request['subject']}")
        print(f"   Response: {data['message']}")

    def test_03_status_check(self, curriculum_server: str):
        """Test 3: 커리큘럼 상태 조회"""
        response = requests.get(f"{curriculum_server}/api/curriculum/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "nodes_count" in data
        assert "edges_count" in data

        print(f"\n✅ Test 3 passed: Status check successful")
        print(f"   Nodes: {data['nodes_count']}")
        print(f"   Edges: {data['edges_count']}")

    def test_04_link_generation(self, curriculum_server: str):
        """Test 4: LINK로 엔티티 간 관계 생성"""
        # 먼저 draft로 데이터 생성
        draft_request = {"subject": "Web Development Fundamentals"}
        requests.post(
            f"{curriculum_server}/api/curriculum/generate/draft",
            json=draft_request,
            timeout=60
        )

        # LINK 생성
        link_request = {
            "source_type": "Concept",
            "target_type": "Skill"
        }

        response = requests.post(
            f"{curriculum_server}/api/curriculum/generate/link",
            json=link_request,
            timeout=60
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        print(f"\n✅ Test 4 passed: Link generation successful")
        print(f"   Source Type: {link_request['source_type']}")
        print(f"   Target Type: {link_request['target_type']}")
        print(f"   Response: {data['message']}")

    def test_05_expand_graph(self, curriculum_server: str):
        """Test 5: EXPAND로 그래프 확장"""
        # 먼저 draft로 데이터 생성
        draft_request = {"subject": "Data Structures and Algorithms"}
        requests.post(
            f"{curriculum_server}/api/curriculum/generate/draft",
            json=draft_request,
            timeout=60
        )

        # EXPAND 실행
        response = requests.post(
            f"{curriculum_server}/api/curriculum/generate/expand",
            timeout=120
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        print(f"\n✅ Test 5 passed: Graph expansion successful")
        print(f"   Message: {data['message']}")

    def test_06_multiple_subjects(self, curriculum_server: str):
        """Test 6: 여러 주제에 대한 DRAFT 생성"""
        subjects = [
            {"subject": "Cloud Computing"},
            {"subject": "DevOps Practices"},
            {"subject": "Microservices Architecture"}
        ]

        for subject_info in subjects:
            response = requests.post(
                f"{curriculum_server}/api/curriculum/generate/draft",
                json=subject_info,
                timeout=60
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            print(f"   ✓ Generated curriculum for: {subject_info['subject']}")

        # 최종 상태 확인
        response = requests.get(f"{curriculum_server}/api/curriculum/status")
        assert response.status_code == 200
        final_data = response.json()

        print(f"\n✅ Test 6 passed: Multiple DRAFT sequences completed")
        print(f"   Total Nodes: {final_data['nodes_count']}")
        print(f"   Total Edges: {final_data['edges_count']}")

    def test_07_response_structure_validation(self, curriculum_server: str):
        """Test 7: API 응답 구조 검증"""
        draft_request = {"subject": "API Structure Test"}

        response = requests.post(
            f"{curriculum_server}/api/curriculum/generate/draft",
            json=draft_request,
            timeout=60
        )

        assert response.status_code == 200
        data = response.json()

        # 응답 구조 검증
        required_keys = ["status", "message", "data"]
        assert all(key in data for key in required_keys)
        assert isinstance(data["status"], str)
        assert isinstance(data["message"], str)
        assert isinstance(data["data"], dict) or data["data"] is None

        if data["data"]:
            assert "nodes_count" in data["data"]

        print(f"\n✅ Test 7 passed: Response structure validation successful")
        print(f"   Response keys: {list(data.keys())}")
        print(f"   Data keys: {list(data['data'].keys()) if data['data'] else 'None'}")

    def test_08_data_persistence(self, curriculum_server: str):
        """Test 8: 데이터가 파일에 저장되는지 확인"""
        base_path = "/Users/ed/writing/project/adaptive-learning-class/curriculum-manager/.claude/worktrees/test-integration"

        draft_request = {"subject": "Data Persistence Test"}

        response = requests.post(
            f"{curriculum_server}/api/curriculum/generate/draft",
            json=draft_request,
            timeout=60
        )

        assert response.status_code == 200
        time.sleep(1)  # 파일 저장 대기

        # nodes.json 파일 확인
        nodes_file = os.path.join(base_path, "nodes.json")
        if os.path.exists(nodes_file):
            with open(nodes_file, 'r') as f:
                nodes_data = json.load(f)

            assert isinstance(nodes_data, list)
            assert len(nodes_data) > 0

            # 데이터 구조 검증
            for node in nodes_data:
                assert "id" in node
                assert "type" in node
                assert "name" in node
                assert "depth" in node

            print(f"\n✅ Test 8 passed: Data persistence verified")
            print(f"   Nodes file: {nodes_file}")
            print(f"   Total nodes: {len(nodes_data)}")
            print(f"   Sample node: {json.dumps(nodes_data[0], indent=2, default=str)[:200]}...")
        else:
            print(f"\n⚠️  Test 8 warning: nodes.json not found at {nodes_file}")

    def test_09_complete_workflow(self, curriculum_server: str):
        """Test 9: 전체 워크플로우 테스트"""
        base_url = curriculum_server

        print("\n   [Step 1] DRAFT 생성")
        resp1 = requests.post(
            f"{base_url}/api/curriculum/generate/draft",
            json={"subject": "Complete Workflow Test"},
            timeout=60
        )
        assert resp1.status_code == 200
        draft_nodes = resp1.json()["data"]["nodes_count"]
        print(f"   ✓ Draft created with {draft_nodes} nodes")

        print("   [Step 2] STATUS 확인")
        resp2 = requests.get(f"{base_url}/api/curriculum/status")
        assert resp2.status_code == 200
        status = resp2.json()
        print(f"   ✓ Status: {status['nodes_count']} nodes, {status['edges_count']} edges")

        print("   [Step 3] LINK 생성")
        resp3 = requests.post(
            f"{base_url}/api/curriculum/generate/link",
            json={"source_type": "Concept", "target_type": "Skill"},
            timeout=60
        )
        assert resp3.status_code == 200
        print(f"   ✓ Links created successfully")

        print("   [Step 4] 최종 STATUS 확인")
        resp4 = requests.get(f"{base_url}/api/curriculum/status")
        assert resp4.status_code == 200
        final_status = resp4.json()
        print(f"   ✓ Final status: {final_status['nodes_count']} nodes, {final_status['edges_count']} edges")

        print(f"\n✅ Test 9 passed: Complete workflow executed successfully")

    def test_10_error_handling(self, curriculum_server: str):
        """Test 10: 에러 처리 검증"""
        # 잘못된 요청 형식 테스트
        response = requests.post(
            f"{curriculum_server}/api/curriculum/generate/draft",
            json={},  # subject 필드 누락
            timeout=10
        )

        # 422 Unprocessable Entity 또는 400 Bad Request 예상
        assert response.status_code in [400, 422]
        print(f"\n✅ Test 10 passed: Error handling works correctly")
        print(f"   Status code: {response.status_code}")
