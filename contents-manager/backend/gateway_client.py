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
