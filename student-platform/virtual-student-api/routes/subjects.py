import os
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/virtual-students/subjects", tags=["subjects"])

KG_API_URL = os.getenv("KG_API_URL", "")
KG_SERVICE_TOKEN = os.getenv("KG_SERVICE_TOKEN", "")


@router.get("")
def list_subjects():
    if not KG_API_URL:
        return {"subjects": []}
    try:
        resp = httpx.get(
            f"{KG_API_URL}/kg/subjects",
            headers={"X-Service-Token": KG_SERVICE_TOKEN},
            timeout=5.0,
        )
        if not resp.is_success:
            raise HTTPException(resp.status_code, resp.text)
        return JSONResponse(content=resp.json())
    except httpx.RequestError as e:
        raise HTTPException(503, f"KG API unavailable: {e}")
