"""Ingestion API — source 기반 KG 자동 확장"""
import os
import tempfile
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from models import Subject, User
from pydantic import BaseModel
from sqlalchemy.orm import Session

import auth as auth_utils
from database import get_db
from ingestion.harness import ingest
from ingestion.logger import get_log, list_logs
from ingestion.snapshot import get_snapshot_diff, list_snapshots, rollback

_ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


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
    subject_name = None
    subject_description = None
    if req.subject_id:
        subject = db.query(Subject).filter(Subject.id == req.subject_id).first()
        if not subject:
            raise HTTPException(status_code=404, detail=f"Subject '{req.subject_id}' not found")
        subject_name = subject.name
        subject_description = subject.description or ""

    try:
        return ingest(
            req.source_type, req.source, req.dry_run,
            subject_name=subject_name,
            subject_description=subject_description,
        )
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

    subject_name = None
    subject_description = None
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
        return ingest(
            "file", tmp_path, dry_run,
            subject_name=subject_name,
            subject_description=subject_description,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)


@router.get("/logs")
async def get_logs(
    current_user: User = Depends(auth_utils.get_current_user),
):
    return {"logs": list_logs()}


@router.get("/logs/{timestamp}")
async def get_log_detail(
    timestamp: str,
    current_user: User = Depends(auth_utils.get_current_user),
):
    log = get_log(timestamp)
    if log is None:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@router.get("/snapshots")
async def get_snapshots(
    current_user: User = Depends(auth_utils.get_current_user),
):
    return {"snapshots": list_snapshots()}


@router.get("/snapshots/{timestamp}/diff")
async def get_snapshot_diff_endpoint(
    timestamp: str,
    current_user: User = Depends(auth_utils.get_current_user),
):
    diff = get_snapshot_diff(timestamp)
    if diff is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return diff


@router.post("/snapshots/{timestamp}/rollback")
async def rollback_snapshot(
    timestamp: str,
    current_user: User = Depends(auth_utils.get_current_user),
):
    result = rollback(timestamp)
    if result is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return result
