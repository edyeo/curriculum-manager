import os
import httpx

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:9000")
TIMEOUT = 120.0


async def generate_curriculum(subject: str, description: str = "") -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            f"{GATEWAY_URL}/curriculum/generate",
            json={"subject": subject, "description": description,
                  "include_research": False, "include_mental_models": False,
                  "include_questions": False},
        )
        r.raise_for_status()
        return r.json()


async def expand_curriculum() -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{GATEWAY_URL}/proxy/curriculum/api/curriculum/generate/expand")
        r.raise_for_status()
        return r.json()


async def link_ai_curriculum(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            f"{GATEWAY_URL}/proxy/curriculum/api/curriculum/generate/link-ai",
            json=payload,
        )
        r.raise_for_status()
        return r.json()


async def preview_ai_link(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            f"{GATEWAY_URL}/proxy/curriculum/api/curriculum/generate/link-ai/preview",
            json=payload,
        )
        r.raise_for_status()
        return r.json()


async def start_research() -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{GATEWAY_URL}/proxy/research/api/research/start", json={})
        r.raise_for_status()
        return r.json()


async def query_research(keyword: str = None, source: str = None) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        body = {}
        if keyword:
            body["keyword"] = keyword
        if source:
            body["source"] = source
        r = await client.post(f"{GATEWAY_URL}/proxy/research/api/research/query", json=body)
        r.raise_for_status()
        return r.json()


async def get_questions(entity_id: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"{GATEWAY_URL}/proxy/questions/api/questions/entity/{entity_id}")
        r.raise_for_status()
        return r.json()


async def generate_questions(entity_id: str, count: int = 5) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            f"{GATEWAY_URL}/proxy/questions/api/questions/generate",
            json={"entity_id": entity_id, "count": count},
        )
        r.raise_for_status()
        return r.json()


async def generate_questions_workbench(
    entity_id: str,
    blueprint_id: str = None,
    integration_item_id: str = None,
    blueprint_context: str = "",
    question_type: str = "MCQ",
    count: int = 3,
) -> list:
    """EPIC-003: blueprint context를 포함한 문항 생성"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            f"{GATEWAY_URL}/proxy/questions/api/questions/generate-workbench",
            json={
                "entity_id": entity_id,
                "blueprint_id": blueprint_id,
                "integration_item_id": integration_item_id,
                "blueprint_context": blueprint_context,
                "question_type": question_type,
                "count": count,
            },
        )
        r.raise_for_status()
        return r.json().get("data", [])


async def subgraph_search(
    integration_item_id: str,
    item_name: str,
    item_description: str,
    required_combinations: list,
) -> dict:
    """EPIC-003 Feature 2.2: 통합항목 기반 서브그래프 검색"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            f"{GATEWAY_URL}/proxy/questions/api/questions/subgraph-search",
            json={
                "integration_item_id": integration_item_id,
                "item_name": item_name,
                "item_description": item_description,
                "required_combinations": required_combinations,
            },
        )
        r.raise_for_status()
        return r.json()


async def confirm_ai_link(subject_id: str, edges: list) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            f"{GATEWAY_URL}/proxy/curriculum/api/curriculum/generate/link-ai/confirm",
            json={"edges": edges},
        )
        r.raise_for_status()
        return r.json()
