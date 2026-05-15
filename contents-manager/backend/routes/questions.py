from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from models import User
import auth as auth_utils, gateway_client

router = APIRouter(prefix="/subjects/{subject_id}/nodes/{node_id}/questions", tags=["questions"])


class GenerateRequest(BaseModel):
    count: Optional[int] = 5


@router.get("")
async def get_questions(
    subject_id: str,
    node_id: str,
    current_user: User = Depends(auth_utils.get_current_user),
):
    return await gateway_client.get_questions(node_id)


@router.post("")
async def generate_questions(
    subject_id: str,
    node_id: str,
    req: GenerateRequest = GenerateRequest(),
    current_user: User = Depends(auth_utils.get_current_user),
):
    return await gateway_client.generate_questions(node_id, req.count)
