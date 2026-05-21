import uuid, json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from database import get_db
from models import User, Blueprint, BlueprintIntegrationItem, QuestionItem, GenerationJob, QuestionEntityLink, QuestionMatrixLink
import auth as auth_utils
import gateway_client

router = APIRouter(prefix="/question-workbench", tags=["question-workbench"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    entity_id: str
    blueprint_id: Optional[str] = None
    integration_item_id: Optional[str] = None
    question_type: Optional[str] = "MCQ"
    count: Optional[int] = 3

class SubgraphSearchRequest(BaseModel):
    integration_item_id: str

class QuestionPatch(BaseModel):
    question_text: Optional[str] = None
    options: Optional[List[dict]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: Optional[str] = None


def _job_to_dict(job: GenerationJob) -> dict:
    return {
        "id": job.id,
        "entity_id": job.entity_id,
        "blueprint_id": job.blueprint_id,
        "integration_item_id": job.integration_item_id,
        "status": job.status,
        "result": json.loads(job.result) if job.result else None,
        "error": job.error,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


def _question_to_dict(q: QuestionItem, db=None) -> dict:
    base = {
        "id": q.id,
        "entity_id": q.entity_id,
        "blueprint_id": q.blueprint_id,
        "question_text": q.question_text,
        "options": json.loads(q.options) if q.options else [],
        "correct_answer": q.correct_answer,
        "explanation": q.explanation,
        "node_snapshot": json.loads(q.node_snapshot) if q.node_snapshot else None,
        "question_type": q.question_type or "MCQ",
        "difficulty": q.difficulty or "medium",
        "status": q.status,
        "created_at": q.created_at.isoformat() if q.created_at else None,
        "updated_at": q.updated_at.isoformat() if q.updated_at else None,
    }
    if db is not None:
        entity_links = [r.entity_id for r in db.query(QuestionEntityLink).filter(QuestionEntityLink.question_id == q.id).all()]
        matrix_links = [
            {"blueprint_id": r.blueprint_id, "layer": r.layer, "stage": r.stage, "integration_item_id": r.integration_item_id}
            for r in db.query(QuestionMatrixLink).filter(QuestionMatrixLink.question_id == q.id).all()
        ]
        base["entity_links"] = entity_links
        base["matrix_links"] = matrix_links
    return base


# ── Background worker ──────────────────────────────────────────────────────────

def _run_generation(job_id: str, entity_id: str, blueprint_id: Optional[str],
                    integration_item_id: Optional[str], blueprint_context: str = "",
                    question_type: str = "MCQ", count: int = 3):
    from database import SessionLocal
    db = SessionLocal()
    try:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        job.status = "running"
        db.commit()

        import asyncio
        result = asyncio.run(gateway_client.generate_questions_workbench(
            entity_id=entity_id,
            blueprint_id=blueprint_id,
            integration_item_id=integration_item_id,
            blueprint_context=blueprint_context,
            question_type=question_type,
            count=count,
        ))

        job.status = "completed"
        job.result = json.dumps(result)
        db.commit()
    except Exception as e:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error = str(e)
            db.commit()
    finally:
        db.close()


# ── Generation job ─────────────────────────────────────────────────────────────

@router.post("/generate", status_code=202)
def start_generation(
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    """문제 생성 비동기 작업 시작. job_id로 상태 폴링."""
    blueprint_context = ""
    if body.blueprint_id:
        bp = db.query(Blueprint).filter(Blueprint.id == body.blueprint_id).first()
        if not bp:
            raise HTTPException(404, "Blueprint not found")
        lines = [f"Blueprint: {bp.name}"]
        if bp.description:
            lines.append(f"설명: {bp.description}")
        if body.integration_item_id:
            item = db.query(BlueprintIntegrationItem).filter(
                BlueprintIntegrationItem.id == body.integration_item_id
            ).first()
            if item:
                lines.append(f"통합항목: {item.name}")
                combos = json.loads(item.required_combinations) if item.required_combinations else []
                if combos:
                    combo_str = ', '.join(c['layer'] + '/' + c['stage'] for c in combos)
                    lines.append(f"요구 인지 조합: {combo_str}")
        blueprint_context = "\n".join(lines)

    job = GenerationJob(
        id=str(uuid.uuid4()),
        entity_id=body.entity_id,
        blueprint_id=body.blueprint_id,
        integration_item_id=body.integration_item_id,
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(
        _run_generation,
        job.id,
        body.entity_id,
        body.blueprint_id,
        body.integration_item_id,
        blueprint_context,
        body.question_type or "MCQ",
        body.count or 3,
    )
    return {"job_id": job.id, "status": "pending"}


@router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    """생성 작업 상태 폴링"""
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return _job_to_dict(job)


# ── Subgraph search (Feature 2.2) ──────────────────────────────────────────────

@router.post("/subgraph-search")
async def subgraph_search(
    body: SubgraphSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    """Blueprint 통합항목 기반 에이전트 서브그래프 검색 (Path B)"""
    item = db.query(BlueprintIntegrationItem).filter(
        BlueprintIntegrationItem.id == body.integration_item_id
    ).first()
    if not item:
        raise HTTPException(404, "Integration item not found")

    result = await gateway_client.subgraph_search(
        integration_item_id=body.integration_item_id,
        item_name=item.name,
        item_description=item.description or "",
        required_combinations=json.loads(item.required_combinations) if item.required_combinations else [],
    )
    return result


# ── Question CRUD ──────────────────────────────────────────────────────────────

@router.get("/questions")
def list_questions(
    blueprint_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    status: Optional[str] = None,
    question_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(auth_utils.get_user_or_service),
):
    q = db.query(QuestionItem)
    if blueprint_id:
        q = q.filter(QuestionItem.blueprint_id == blueprint_id)
    if entity_id:
        q = q.filter(QuestionItem.entity_id == entity_id)
    if status:
        q = q.filter(QuestionItem.status == status)
    if question_type:
        q = q.filter(QuestionItem.question_type == question_type)
    if difficulty:
        q = q.filter(QuestionItem.difficulty == difficulty)
    questions = q.order_by(QuestionItem.created_at.desc()).all()
    return {"questions": [_question_to_dict(qi) for qi in questions]}


@router.get("/questions/{question_id}")
def get_question(
    question_id: str,
    db: Session = Depends(get_db),
    _=Depends(auth_utils.get_user_or_service),
):
    qi = db.query(QuestionItem).filter(QuestionItem.id == question_id).first()
    if not qi:
        raise HTTPException(404, "Question not found")
    return _question_to_dict(qi, db)


@router.post("/questions", status_code=201)
def save_question(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    """생성된 문항 초안 저장 (job result → DB)"""
    qi = QuestionItem(
        id=str(uuid.uuid4()),
        entity_id=body["entity_id"],
        blueprint_id=body.get("blueprint_id"),
        question_text=body["question_text"],
        options=json.dumps(body.get("options", [])),
        correct_answer=body["correct_answer"],
        explanation=body.get("explanation"),
        node_snapshot=json.dumps(body.get("node_snapshot")) if body.get("node_snapshot") else None,
        question_type=body.get("question_type", "MCQ"),
        difficulty=body.get("difficulty", "medium"),
        status="draft",
    )
    db.add(qi)
    db.flush()

    # Entity link
    db.add(QuestionEntityLink(question_id=qi.id, entity_id=qi.entity_id))

    # Matrix links — integration_item의 required_combinations에서 자동 추출
    iid = body.get("integration_item_id")
    if iid and qi.blueprint_id:
        item = db.query(BlueprintIntegrationItem).filter(BlueprintIntegrationItem.id == iid).first()
        if item and item.required_combinations:
            for combo in json.loads(item.required_combinations):
                db.add(QuestionMatrixLink(
                    question_id=qi.id,
                    blueprint_id=qi.blueprint_id,
                    layer=combo["layer"],
                    stage=combo["stage"],
                    integration_item_id=iid,
                ))

    db.commit()
    db.refresh(qi)
    return _question_to_dict(qi, db)


@router.patch("/questions/{question_id}")
def update_question(
    question_id: str,
    body: QuestionPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    """인라인 편집 (Feature 2.4)"""
    qi = db.query(QuestionItem).filter(QuestionItem.id == question_id).first()
    if not qi:
        raise HTTPException(404, "Question not found")
    if body.question_text is not None:
        qi.question_text = body.question_text
    if body.options is not None:
        qi.options = json.dumps(body.options)
    if body.correct_answer is not None:
        qi.correct_answer = body.correct_answer
    if body.explanation is not None:
        qi.explanation = body.explanation
    if body.difficulty is not None:
        qi.difficulty = body.difficulty
    db.commit()
    db.refresh(qi)
    return _question_to_dict(qi)


@router.post("/questions/{question_id}/unpublish")
def unpublish_question(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    """출제 취소: published → draft"""
    qi = db.query(QuestionItem).filter(QuestionItem.id == question_id).first()
    if not qi:
        raise HTTPException(404, "Question not found")
    if qi.status != "published":
        raise HTTPException(400, "Only published questions can be unpublished")
    qi.status = "draft"
    db.commit()
    db.refresh(qi)
    return _question_to_dict(qi)


@router.post("/questions/{question_id}/archive")
def archive_question(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    """보관: published → archived"""
    qi = db.query(QuestionItem).filter(QuestionItem.id == question_id).first()
    if not qi:
        raise HTTPException(404, "Question not found")
    if qi.status != "published":
        raise HTTPException(400, "Only published questions can be archived")
    qi.status = "archived"
    db.commit()
    db.refresh(qi)
    return _question_to_dict(qi)


@router.post("/questions/{question_id}/publish")
def publish_question(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    """최종 등록: draft → published"""
    qi = db.query(QuestionItem).filter(QuestionItem.id == question_id).first()
    if not qi:
        raise HTTPException(404, "Question not found")
    if qi.status == "published":
        raise HTTPException(400, "Already published")
    qi.status = "published"
    db.commit()
    db.refresh(qi)
    return _question_to_dict(qi)


@router.delete("/questions/{question_id}", status_code=204)
def delete_question(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    qi = db.query(QuestionItem).filter(QuestionItem.id == question_id).first()
    if not qi:
        raise HTTPException(404, "Question not found")
    if qi.status == "published":
        raise HTTPException(409, "Published questions must be archived before deletion")
    db.delete(qi)
    db.commit()
