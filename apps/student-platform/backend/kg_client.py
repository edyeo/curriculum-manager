"""KG API client — reads curriculum data from contents-manager KG endpoints."""
import os
import httpx
from fastapi import HTTPException

KG_API_URL = os.getenv("KG_API_URL", "http://localhost:8010")
KG_SERVICE_TOKEN = os.getenv("KG_SERVICE_TOKEN", "kg-service-secret")
HEADERS = {"X-Service-Token": KG_SERVICE_TOKEN}
TIMEOUT = 30.0


async def get_subjects() -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.get(f"{KG_API_URL}/kg/subjects", headers=HEADERS)
            r.raise_for_status()
            return r.json()
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="KG API unavailable")


async def get_nodes(subject_id: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.get(f"{KG_API_URL}/kg/subjects/{subject_id}/nodes", headers=HEADERS)
            r.raise_for_status()
            return r.json().get("nodes", [])
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="KG API unavailable")


async def get_edges(subject_id: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.get(f"{KG_API_URL}/kg/subjects/{subject_id}/edges", headers=HEADERS)
            r.raise_for_status()
            return r.json().get("edges", [])
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="KG API unavailable")


async def get_questions(node_id: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.get(f"{KG_API_URL}/kg/nodes/{node_id}/questions", headers=HEADERS)
            r.raise_for_status()
            return r.json().get("questions", [])
        except (httpx.ConnectError, httpx.HTTPStatusError):
            return []


async def get_node_blueprints(node_id: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.get(f"{KG_API_URL}/kg/nodes/{node_id}/blueprints", headers=HEADERS)
            r.raise_for_status()
            return r.json().get("blueprints", [])
        except (httpx.ConnectError, httpx.HTTPStatusError):
            return []


async def get_all_blueprints() -> list[dict]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.get(f"{KG_API_URL}/kg/blueprints", headers=HEADERS)
            r.raise_for_status()
            return r.json().get("blueprints", [])
        except (httpx.ConnectError, httpx.HTTPStatusError):
            return []
