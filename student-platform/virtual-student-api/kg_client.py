"""KG API client for virtual-student-api."""
import asyncio
import os

import httpx
from fastapi import HTTPException

KG_API_URL = os.getenv("KG_API_URL", "http://localhost:8010")
KG_SERVICE_TOKEN = os.getenv("KG_SERVICE_TOKEN", "kg-service-secret")
_HEADERS = {"X-Service-Token": KG_SERVICE_TOKEN}
_TIMEOUT = 30.0


async def get_nodes(subject_id: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            r = await client.get(f"{KG_API_URL}/kg/subjects/{subject_id}/nodes", headers=_HEADERS)
            r.raise_for_status()
            return r.json().get("nodes", [])
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="KG API unavailable")


async def get_subjects() -> list[dict]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            r = await client.get(f"{KG_API_URL}/kg/subjects", headers=_HEADERS)
            r.raise_for_status()
            return r.json().get("subjects", [])
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="KG API unavailable")


async def get_node_blueprints(node_id: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            r = await client.get(f"{KG_API_URL}/kg/nodes/{node_id}/blueprints", headers=_HEADERS)
            r.raise_for_status()
            return r.json().get("blueprints", [])
        except (httpx.ConnectError, httpx.HTTPStatusError):
            return []


async def get_node_blueprints_bulk(nodes: list[dict]) -> dict[str, list]:
    """노드 목록의 blueprint를 병렬로 조회한다."""
    results = await asyncio.gather(
        *[get_node_blueprints(n["id"]) for n in nodes],
        return_exceptions=True,
    )
    return {
        nodes[i]["id"]: (results[i] if not isinstance(results[i], Exception) else [])
        for i in range(len(nodes))
    }
