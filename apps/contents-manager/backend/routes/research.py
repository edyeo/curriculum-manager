from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from models import User
import auth as auth_utils, gateway_client

router = APIRouter(prefix="/subjects/{subject_id}/research", tags=["research"])


@router.post("/start")
async def start_research(
    subject_id: str,
    current_user: User = Depends(auth_utils.get_current_user),
):
    return await gateway_client.start_research()


@router.get("/results")
async def get_results(
    subject_id: str,
    keyword: Optional[str] = None,
    source: Optional[str] = None,
    current_user: User = Depends(auth_utils.get_current_user),
):
    return await gateway_client.query_research(keyword=keyword, source=source)
