"""Ingestion API — source 기반 KG 자동 확장"""
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from models import IngestionPendingEdge, IngestionPendingNode, IngestionSource, Subject, User
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

import auth as auth_utils
from database import get_db
from ingestion.harness import approve, ingest, register_parse, test_parse
from ingestion.loader import load
from ingestion.logger import get_log, list_logs
from ingestion.snapshot import get_snapshot_diff, list_snapshots, rollback

_ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


# ── 기존 엔드포인트 (하위 호환) ────────────────────────────────────────────────

class IngestRequest(BaseModel):
    source_type: Literal["file", "url", "text"]
    source: str
    dry_run: bool = False
    subject_id: str | None = None


@router.post("/run")
async def run_ingestion(
    req: IngestRequest,
    current_user: User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    subject_name = subject_description = None
    if req.subject_id:
        subject = db.query(Subject).filter(Subject.id == req.subject_id).first()
        if not subject:
            raise HTTPException(status_code=404, detail=f"Subject '{req.subject_id}' not found")
        subject_name = subject.name
        subject_description = subject.description or ""

    try:
        return ingest(req.source_type, req.source, req.dry_run,
                      subject_name=subject_name, subject_description=subject_description)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_ingestion(
    file: UploadFile = File(...),
    dry_run: bool = Form(False),
    subject_id: str | None = Form(None),
    current_user: User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식: {ext}. PDF, TXT, MD만 허용됩니다.")

    subject_name = subject_description = None
    if subject_id:
        subject = db.query(Subject).filter(Subject.id == subject_id).first()
        if not subject:
            raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")
        subject_name = subject.name
        subject_description = subject.description or ""

    content = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        return ingest("file", tmp_path, dry_run,
                      subject_name=subject_name, subject_description=subject_description)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)


@router.get("/logs")
async def get_logs(current_user: User = Depends(auth_utils.get_current_user)):
    return {"logs": list_logs()}


@router.get("/logs/{timestamp}")
async def get_log_detail(timestamp: str, current_user: User = Depends(auth_utils.get_current_user)):
    log = get_log(timestamp)
    if log is None:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@router.get("/snapshots")
async def get_snapshots(current_user: User = Depends(auth_utils.get_current_user)):
    return {"snapshots": list_snapshots()}


@router.get("/snapshots/{timestamp}/diff")
async def get_snapshot_diff_endpoint(timestamp: str, current_user: User = Depends(auth_utils.get_current_user)):
    diff = get_snapshot_diff(timestamp)
    if diff is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return diff


@router.post("/snapshots/{timestamp}/rollback")
async def rollback_snapshot(timestamp: str, current_user: User = Depends(auth_utils.get_current_user)):
    result = rollback(timestamp)
    if result is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return result


# ── EPIC-015: 소스 저장 / dry-run / 파싱 등록 / Audit / 승인 ──────────────────

class SaveSourceRequest(BaseModel):
    source_type: Literal["file", "url", "text"]
    source: str
    subject_id: str | None = None


def _load_raw(source_type: str, source: str) -> str:
    try:
        return load(source_type, source)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sources")
async def save_source(
    req: SaveSourceRequest,
    current_user: User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    raw_text = _load_raw(req.source_type, req.source)
    summary = req.source[:300] if req.source_type in ("url", "text") else req.source
    row = IngestionSource(
        id=str(uuid.uuid4()),
        source_type=req.source_type,
        source_summary=summary,
        raw_text=raw_text,
        subject_id=req.subject_id or None,
        status="saved",
        created_by=current_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "status": "saved"}


@router.post("/sources/upload")
async def save_source_upload(
    file: UploadFile = File(...),
    subject_id: str | None = Form(None),
    current_user: User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식: {ext}. PDF, TXT, MD만 허용됩니다.")

    content = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        raw_text = _load_raw("file", tmp_path)
    finally:
        os.unlink(tmp_path)

    row = IngestionSource(
        id=str(uuid.uuid4()),
        source_type="file",
        source_summary=file.filename or "uploaded_file",
        raw_text=raw_text,
        subject_id=subject_id or None,
        status="saved",
        created_by=current_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "status": "saved"}


@router.get("/sources")
async def list_sources(
    current_user: User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(IngestionSource).order_by(desc(IngestionSource.created_at)).all()
    return {"sources": [
        {
            "id": r.id,
            "source_type": r.source_type,
            "source_summary": r.source_summary,
            "subject_id": r.subject_id,
            "status": r.status,
            "extracted_node_count": r.extracted_node_count,
            "extracted_edge_count": r.extracted_edge_count,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]}


@router.post("/sources/{session_id}/dry-run")
async def dry_run_source(
    session_id: str,
    current_user: User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return test_parse(session_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sources/{session_id}/parse")
async def parse_source(
    session_id: str,
    current_user: User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return register_parse(session_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit")
async def get_audit(
    session_id: str | None = None,
    current_user: User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    node_q = db.query(IngestionPendingNode)
    edge_q = db.query(IngestionPendingEdge)
    if session_id:
        node_q = node_q.filter(IngestionPendingNode.session_id == session_id)
        edge_q = edge_q.filter(IngestionPendingEdge.session_id == session_id)

    nodes = node_q.order_by(IngestionPendingNode.created_at).all()
    edges = edge_q.order_by(IngestionPendingEdge.created_at).all()

    return {
        "nodes": [
            {
                "id": n.id, "session_id": n.session_id,
                "name": n.name, "type": n.type, "depth": n.depth,
                "description": n.description, "source_excerpt": n.source_excerpt,
                "db_exists": n.db_exists, "matched_node_id": n.matched_node_id,
                "decision": n.decision,
            }
            for n in nodes
        ],
        "edges": [
            {
                "id": e.id, "session_id": e.session_id,
                "source_name": e.source_name, "target_name": e.target_name,
                "relation": e.relation, "basis": e.basis,
                "db_exists": e.db_exists, "decision": e.decision,
            }
            for e in edges
        ],
    }


@router.post("/sources/{session_id}/approve")
async def approve_source(
    session_id: str,
    current_user: User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return approve(session_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/sources/{session_id}/reject")
async def reject_source(
    session_id: str,
    current_user: User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(IngestionSource).filter(IngestionSource.id == session_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Source not found")
    row.status = "rejected"
    db.commit()
    return {"session_id": session_id, "status": "rejected"}
