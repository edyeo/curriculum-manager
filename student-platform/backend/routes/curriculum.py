from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Student, NodeMastery
import auth as auth_utils
import kg_client

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


@router.get("/subjects")
async def list_subjects(_: Student = Depends(auth_utils.get_current_student)):
    return await kg_client.get_subjects()


@router.get("/graph/{subject_id}")
async def get_graph(
    subject_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(auth_utils.get_current_student),
):
    nodes, edges = await kg_client.get_nodes(subject_id), await kg_client.get_edges(subject_id)

    mastery_records = db.query(NodeMastery).filter(
        NodeMastery.student_id == current_student.id,
        NodeMastery.subject_id == subject_id,
    ).all()
    mastery_map = {m.node_id: m.mastery_score for m in mastery_records}

    enriched_nodes = [
        {**node, "mastery_score": mastery_map.get(node["id"], None)}
        for node in nodes
    ]
    return {"nodes": enriched_nodes, "edges": edges}


@router.get("/nodes/{node_id}/questions")
async def get_questions(
    node_id: str,
    _: Student = Depends(auth_utils.get_current_student),
):
    questions = await kg_client.get_questions(node_id)
    return {"questions": questions}
