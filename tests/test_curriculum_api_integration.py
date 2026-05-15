"""
Curriculum Manager API 통합 테스트: DB API 데이터 등록 및 조회 검증
"""
import pytest
import requests
import json
import time
import os


class TestCurriculumAPIIntegration:
    """Curriculum Manager API 통합 테스트"""

    def test_curriculum_health_check(self, curriculum_api_url: str):
        """Test 1: 헬스 체크"""
        response = requests.get(f"{curriculum_api_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("\n✅ Test 1 passed: Health check successful")

    def test_generate_draft_with_sample_data(self, curriculum_api_url: str):
        """Test 2: DRAFT 트리거로 샘플 데이터 생성"""
        draft_request = {
            "subject": "Machine Learning Basics",
            "description": "Introduction to ML concepts and algorithms"
        }

        response = requests.post(
            f"{curriculum_api_url}/api/curriculum/generate/draft",
            json=draft_request,
            timeout=60
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Draft generated" in data["message"]
        assert data["data"]["nodes_count"] > 0

        nodes_count = data["data"]["nodes_count"]
        print(f"\n✅ Test 2 passed: Generated {nodes_count} nodes from DRAFT")
        print(f"   Subject: {draft_request['subject']}")
        print(f"   Message: {data['message']}")

    def test_get_curriculum_status(self, curriculum_api_url: str):
        """Test 3: 커리큘럼 상태 조회"""
        response = requests.get(f"{curriculum_api_url}/api/curriculum/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "nodes_count" in data
        assert "edges_count" in data

        print(f"\n✅ Test 3 passed: Status check successful")
        print(f"   Nodes: {data['nodes_count']}")
        print(f"   Edges: {data['edges_count']}")

    def test_generate_link_between_entities(self, curriculum_api_url: str):
        """Test 4: LINK 트리거로 엔티티 간 관계 생성"""
        # 먼저 draft로 데이터를 생성
        draft_request = {
            "subject": "Python Programming Fundamentals"
        }
        response = requests.post(
            f"{curriculum_api_url}/api/curriculum/generate/draft",
            json=draft_request,
            timeout=60
        )
        assert response.status_code == 200

        # 이제 link를 생성
        link_request = {
            "source_type": "Concept",
            "target_type": "Skill"
        }

        response = requests.post(
            f"{curriculum_api_url}/api/curriculum/generate/link",
            json=link_request,
            timeout=60
        )

        # API가 성공적으로 응답했는지 확인
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        print(f"\n✅ Test 4 passed: Link generation successful")
        print(f"   Source Type: {link_request['source_type']}")
        print(f"   Target Type: {link_request['target_type']}")
        print(f"   Message: {data['message']}")
        if data["data"]:
            print(f"   Edges Count: {data['data'].get('edges_count', 0)}")

    def test_generate_expand_graph(self, curriculum_api_url: str):
        """Test 5: EXPAND 트리거로 그래프 확장"""
        # 먼저 draft로 데이터를 생성
        draft_request = {
            "subject": "Advanced Data Structures"
        }
        response = requests.post(
            f"{curriculum_api_url}/api/curriculum/generate/draft",
            json=draft_request,
            timeout=60
        )
        assert response.status_code == 200

        # EXPAND 실행
        response = requests.post(
            f"{curriculum_api_url}/api/curriculum/generate/expand",
            timeout=120
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Graph expanded" in data["message"]

        print(f"\n✅ Test 5 passed: Graph expansion successful")
        print(f"   Message: {data['message']}")
        if data["data"]:
            print(f"   Final Nodes: {data['data'].get('nodes_count', 0)}")
            print(f"   Final Edges: {data['data'].get('edges_count', 0)}")

    def test_multiple_drafts_sequence(self, curriculum_api_url: str):
        """Test 6: 여러 과목의 DRAFT를 순차적으로 생성"""
        subjects = [
            {"subject": "Web Development", "description": "HTML, CSS, JavaScript"},
            {"subject": "Database Design", "description": "SQL and NoSQL"},
            {"subject": "Cloud Computing", "description": "AWS, Azure, GCP basics"}
        ]

        for subject_info in subjects:
            response = requests.post(
                f"{curriculum_api_url}/api/curriculum/generate/draft",
                json=subject_info,
                timeout=60
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            print(f"   ✓ Generated curriculum for: {subject_info['subject']}")

        # 최종 상태 확인
        response = requests.get(f"{curriculum_api_url}/api/curriculum/status")
        assert response.status_code == 200
        data = response.json()

        print(f"\n✅ Test 6 passed: Multiple DRAFT sequences completed")
        print(f"   Total Nodes: {data['nodes_count']}")
        print(f"   Total Edges: {data['edges_count']}")

    def test_api_response_structure(self, curriculum_api_url: str):
        """Test 7: API 응답 구조 검증"""
        draft_request = {
            "subject": "API Response Test Subject"
        }

        response = requests.post(
            f"{curriculum_api_url}/api/curriculum/generate/draft",
            json=draft_request,
            timeout=60
        )

        assert response.status_code == 200
        data = response.json()

        # 응답 구조 검증
        assert "status" in data
        assert "message" in data
        assert "data" in data
        assert isinstance(data["status"], str)
        assert isinstance(data["message"], str)
        assert isinstance(data["data"], dict) or data["data"] is None

        print(f"\n✅ Test 7 passed: Response structure validation successful")
        print(f"   Response keys: {list(data.keys())}")


class TestDataPersistence:
    """데이터 지속성 테스트"""

    def test_draft_creates_persistent_data(self, curriculum_api_url: str):
        """Test 8: DRAFT로 생성된 데이터가 파일에 저장되는지 확인"""
        draft_request = {
            "subject": "Persistence Test Subject"
        }

        response = requests.post(
            f"{curriculum_api_url}/api/curriculum/generate/draft",
            json=draft_request,
            timeout=60
        )

        assert response.status_code == 200

        # nodes.json 파일 확인
        time.sleep(1)  # 파일 저장 대기

        nodes_file = "./nodes.json"
        if os.path.exists(nodes_file):
            with open(nodes_file, 'r') as f:
                nodes_data = json.load(f)

            assert isinstance(nodes_data, list)
            assert len(nodes_data) > 0
            print(f"\n✅ Test 8 passed: Data persistence verified")
            print(f"   Nodes file exists: {nodes_file}")
            print(f"   Total nodes in file: {len(nodes_data)}")
        else:
            print(f"\n⚠️  Test 8 warning: nodes.json not found at expected location")

    def test_edges_persistence(self, curriculum_api_url: str):
        """Test 9: LINK로 생성된 엣지가 파일에 저장되는지 확인"""
        # 먼저 draft로 데이터 생성
        draft_request = {"subject": "Edge Persistence Test"}
        requests.post(
            f"{curriculum_api_url}/api/curriculum/generate/draft",
            json=draft_request,
            timeout=60
        )

        # Link 생성
        link_request = {
            "source_type": "Concept",
            "target_type": "Skill"
        }
        response = requests.post(
            f"{curriculum_api_url}/api/curriculum/generate/link",
            json=link_request,
            timeout=60
        )

        assert response.status_code == 200

        # edges.json 파일 확인
        time.sleep(1)
        edges_file = "./edges.json"
        if os.path.exists(edges_file):
            with open(edges_file, 'r') as f:
                edges_data = json.load(f)

            assert isinstance(edges_data, list)
            print(f"\n✅ Test 9 passed: Edges persistence verified")
            print(f"   Edges file exists: {edges_file}")
            print(f"   Total edges in file: {len(edges_data)}")
        else:
            print(f"\n⚠️  Test 9 warning: edges.json not found at expected location")


@pytest.mark.usefixtures("docker_compose_setup")
class TestCurriculumAPIWithServices:
    """Docker Compose 서비스를 사용하는 통합 테스트"""

    def test_full_workflow(self, curriculum_api_url: str):
        """Test 10: 전체 워크플로우 (DRAFT → STATUS → LINK → EXPAND)"""
        # 1. DRAFT
        draft_req = {"subject": "Full Workflow Test"}
        resp1 = requests.post(
            f"{curriculum_api_url}/api/curriculum/generate/draft",
            json=draft_req,
            timeout=60
        )
        assert resp1.status_code == 200
        nodes_count_1 = resp1.json()["data"]["nodes_count"]
        print(f"\n   Step 1: DRAFT created {nodes_count_1} nodes")

        # 2. STATUS 확인
        resp2 = requests.get(f"{curriculum_api_url}/api/curriculum/status")
        assert resp2.status_code == 200
        status_data = resp2.json()
        print(f"   Step 2: STATUS - Nodes: {status_data['nodes_count']}, Edges: {status_data['edges_count']}")

        # 3. LINK 생성 시도 (데이터가 있으면 성공)
        link_req = {"source_type": "Concept", "target_type": "Skill"}
        resp3 = requests.post(
            f"{curriculum_api_url}/api/curriculum/generate/link",
            json=link_req,
            timeout=60
        )
        assert resp3.status_code == 200
        print(f"   Step 3: LINK created edges")

        # 4. 최종 STATUS 확인
        resp4 = requests.get(f"{curriculum_api_url}/api/curriculum/status")
        assert resp4.status_code == 200
        final_status = resp4.json()
        print(f"   Step 4: Final STATUS - Nodes: {final_status['nodes_count']}, Edges: {final_status['edges_count']}")

        print(f"\n✅ Test 10 passed: Full workflow completed successfully")
