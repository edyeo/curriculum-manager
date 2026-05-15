"""
Pytest 설정 및 Fixture: Docker Compose 관리, 서비스 헬스 체크, 테스트 데이터 정리
"""
import subprocess
import time
import requests
import pytest
import shutil
import tempfile
import os
import json
from typing import Generator
from pathlib import Path


@pytest.fixture(scope="session")
def docker_compose_setup() -> Generator[None, None, None]:
    """
    Session 시작 시 docker-compose up, 종료 시 docker-compose down
    """
    print("\n🚀 Starting docker-compose services...")

    # Docker compose up (detached mode)
    result = subprocess.run(
        ["docker-compose", "-f", "infra/docker-compose.yml", "-f", "infra/docker-compose.local.yml", "up", "-d"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to start docker-compose: {result.stderr}")

    print("✅ Docker compose started")
    print("⏳ Waiting for services to be ready...")

    # 서비스 헬스 체크 (최대 60초)
    services = [
        ("Curriculum Manager", "http://localhost:8001/health"),
        ("API Gateway", "http://localhost:9000/health"),
    ]

    for service_name, url in services:
        max_retries = 30
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"✅ {service_name} is ready")
                    break
            except requests.exceptions.RequestException:
                pass

            if attempt == max_retries - 1:
                raise TimeoutError(f"Service {service_name} did not become ready in time")
            time.sleep(2)

    yield

    # Teardown: docker compose down
    print("\n🛑 Stopping docker-compose services...")
    subprocess.run(
        ["docker-compose", "-f", "infra/docker-compose.yml", "-f", "infra/docker-compose.local.yml", "down"],
        capture_output=True,
        text=True
    )
    print("✅ Docker compose stopped")


@pytest.fixture
def api_base_url() -> str:
    """API Gateway URL"""
    return "http://localhost:9000"


@pytest.fixture
def curriculum_api_url() -> str:
    """Curriculum Manager API URL"""
    return "http://localhost:8001"


@pytest.fixture
def gateway_url() -> str:
    """API Gateway URL"""
    return "http://localhost:9000"


@pytest.fixture
def mental_model_url() -> str:
    """Mental Model Manager API URL"""
    return "http://localhost:8002"


@pytest.fixture
def researcher_url() -> str:
    """Researcher Agent API URL"""
    return "http://localhost:8003"


@pytest.fixture
def question_generator_url() -> str:
    """Question Generator Agent API URL"""
    return "http://localhost:8004"


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """
    Test 데이터 자동 백업/복구 (Option A)

    테스트 시작 전에 JSON 데이터 파일을 백업하고,
    테스트 종료 후 원래 상태로 복구한다.
    """
    # Test 시작 전: 데이터 파일 백업
    project_root = Path(__file__).parent.parent
    data_files = ["nodes.json", "edges.json", "questions.json", "research_results.json"]
    backups = {}

    for filename in data_files:
        filepath = project_root / filename
        if filepath.exists():
            # 임시 파일에 내용을 복사
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
                with open(filepath, 'r') as src:
                    tmp.write(src.read())
                backups[filepath] = tmp.name

    yield  # Test 실행

    # Test 종료 후: 데이터 파일 복구
    for filepath, backup_path in backups.items():
        try:
            shutil.copy(backup_path, filepath)
        finally:
            os.unlink(backup_path)


@pytest.fixture
def requires_real_llm():
    """
    LLM 통합 테스트 스킵 조건

    OPENAI_API_KEY가 실제 키가 아닌 경우 (테스트 키, 설정되지 않음 등)
    이 fixture를 사용하는 테스트는 자동으로 skip된다.
    """
    key = os.getenv("OPENAI_API_KEY", "")
    if not key or key.startswith("sk-test") or key == "sk-your-key-here":
        pytest.skip("OPENAI_API_KEY not set or test key — LLM test skipped")
