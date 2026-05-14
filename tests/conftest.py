"""
Pytest 설정 및 Fixture: Docker Compose 관리, 서비스 헬스 체크
"""
import subprocess
import time
import requests
import pytest
from typing import Generator


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
