"""IngestionHarness — 파이프라인 진입점"""
import uuid
from datetime import datetime, timezone
from typing import Literal

from .dedup import DedupReport, EdgeDedupResult, NodeDedupResult, check
from .extractor import ExtractedEdge, ExtractedNode, ExtractionResult, extract
from .loader import load
from .logger import write_log
from .merger import merge


class _Miss:
    """dedup 결과 없을 때 기본값 placeholder."""
    status = "new"
    decision = "add"
    matched_node_id = None


def test_parse(session_id: str, db) -> dict:
    """Dry-run: stored source에서 extract+dedup 실행, DB 저장 없이 결과 반환."""
    from models import IngestionSource, Subject

    row = db.query(IngestionSource).filter(IngestionSource.id == session_id).first()
    if not row:
        raise ValueError(f"Source {session_id} not found")

    subject_name = subject_description = None
    if row.subject_id:
        subj = db.query(Subject).filter(Subject.id == row.subject_id).first()
        if subj:
            subject_name = subj.name
            subject_description = subj.description or ""

    extraction = extract(row.raw_text, subject_name=subject_name, subject_description=subject_description)
    dedup_report = check(extraction.nodes, extraction.edges)

    node_dedup = {r.name.lower().strip(): r for r in dedup_report.nodes}
    edge_dedup = {
        (r.source_name.lower().strip(), r.target_name.lower().strip(), r.relation): r
        for r in dedup_report.edges
    }

    _m = _Miss()
    return {
        "nodes": [
            {
                "name": n.name, "type": n.type, "depth": n.depth,
                "description": n.description, "source_excerpt": n.source_excerpt,
                "db_exists": (node_dedup.get(n.name.lower().strip()) or _m).status == "exact_duplicate",
                "decision": (node_dedup.get(n.name.lower().strip()) or _m).decision,
            }
            for n in extraction.nodes
        ],
        "edges": [
            {
                "source_name": e.source_name, "target_name": e.target_name,
                "relation": e.relation, "basis": e.basis,
                "db_exists": (edge_dedup.get(
                    (e.source_name.lower().strip(), e.target_name.lower().strip(), e.relation)
                ) or _m).status == "exact_duplicate",
                "decision": (edge_dedup.get(
                    (e.source_name.lower().strip(), e.target_name.lower().strip(), e.relation)
                ) or _m).decision,
            }
            for e in extraction.edges
        ],
        "extraction_notes": extraction.extraction_notes,
        "extracted_nodes": len(extraction.nodes),
        "extracted_edges": len(extraction.edges),
    }


def register_parse(session_id: str, db) -> dict:
    """extract+dedup 실행 후 pending 테이블에 저장, status → pending."""
    from models import IngestionPendingEdge, IngestionPendingNode, IngestionSource, Subject

    row = db.query(IngestionSource).filter(IngestionSource.id == session_id).first()
    if not row:
        raise ValueError(f"Source {session_id} not found")
    if row.status not in ("saved", "rejected"):
        raise ValueError(f"Cannot parse source with status '{row.status}'")

    subject_name = subject_description = None
    if row.subject_id:
        subj = db.query(Subject).filter(Subject.id == row.subject_id).first()
        if subj:
            subject_name = subj.name
            subject_description = subj.description or ""

    extraction = extract(row.raw_text, subject_name=subject_name, subject_description=subject_description)
    dedup_report = check(extraction.nodes, extraction.edges)

    now = datetime.now(timezone.utc)

    db.query(IngestionPendingNode).filter(IngestionPendingNode.session_id == session_id).delete()
    db.query(IngestionPendingEdge).filter(IngestionPendingEdge.session_id == session_id).delete()

    node_dedup = {r.name.lower().strip(): r for r in dedup_report.nodes}
    edge_dedup = {
        (r.source_name.lower().strip(), r.target_name.lower().strip(), r.relation): r
        for r in dedup_report.edges
    }

    for n in extraction.nodes:
        dr = node_dedup.get(n.name.lower().strip())
        db.add(IngestionPendingNode(
            id=str(uuid.uuid4()),
            session_id=session_id,
            name=n.name, type=n.type, depth=n.depth,
            description=n.description, source_excerpt=n.source_excerpt,
            db_exists=(dr.status == "exact_duplicate" if dr else False),
            matched_node_id=(dr.matched_node_id if dr else None),
            decision=(dr.decision if dr else "add"),
            created_at=now,
        ))

    for e in extraction.edges:
        key = (e.source_name.lower().strip(), e.target_name.lower().strip(), e.relation)
        dr = edge_dedup.get(key)
        db.add(IngestionPendingEdge(
            id=str(uuid.uuid4()),
            session_id=session_id,
            source_name=e.source_name, target_name=e.target_name,
            relation=e.relation, basis=e.basis, source_excerpt=e.source_excerpt,
            db_exists=(dr.status == "exact_duplicate" if dr else False),
            decision=(dr.decision if dr else "add"),
            created_at=now,
        ))

    row.status = "pending"
    row.extracted_node_count = len(extraction.nodes)
    row.extracted_edge_count = len(extraction.edges)
    row.extraction_notes = extraction.extraction_notes
    db.commit()

    return {
        "session_id": session_id,
        "extracted_nodes": len(extraction.nodes),
        "extracted_edges": len(extraction.edges),
    }


def approve(session_id: str, db) -> dict:
    """pending → KG merge, status → approved."""
    from models import IngestionPendingEdge, IngestionPendingNode, IngestionSource

    row = db.query(IngestionSource).filter(IngestionSource.id == session_id).first()
    if not row:
        raise ValueError(f"Source {session_id} not found")
    if row.status != "pending":
        raise ValueError(f"Cannot approve source with status '{row.status}'")

    pending_nodes = db.query(IngestionPendingNode).filter(IngestionPendingNode.session_id == session_id).all()
    pending_edges = db.query(IngestionPendingEdge).filter(IngestionPendingEdge.session_id == session_id).all()

    extraction = ExtractionResult(
        nodes=[ExtractedNode(
            name=n.name, type=n.type, depth=n.depth,
            description=n.description or "", source_excerpt=n.source_excerpt or "",
        ) for n in pending_nodes],
        edges=[ExtractedEdge(
            source_name=e.source_name, target_name=e.target_name,
            relation=e.relation, basis=e.basis or "", source_excerpt=e.source_excerpt or "",
        ) for e in pending_edges],
    )

    dedup = DedupReport(
        nodes=[NodeDedupResult(
            name=n.name, type=n.type,
            status="exact_duplicate" if n.db_exists else "new",
            decision=n.decision, matched_node_id=n.matched_node_id,
        ) for n in pending_nodes],
        edges=[EdgeDedupResult(
            source_name=e.source_name, target_name=e.target_name, relation=e.relation,
            status="exact_duplicate" if e.db_exists else "new",
            decision=e.decision,
        ) for e in pending_edges],
    )

    diff = merge(extraction, dedup, dry_run=False)

    row.status = "approved"
    db.commit()

    return {
        "session_id": session_id,
        "added_nodes": len(diff.added_nodes),
        "added_edges": len(diff.added_edges),
    }


def ingest(
    source_type: Literal["file", "url", "text"],
    source: str,
    dry_run: bool = False,
    subject_name: str | None = None,
    subject_description: str | None = None,
) -> dict:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    raw_text = load(source_type, source)
    extraction = extract(raw_text, subject_name=subject_name, subject_description=subject_description)
    dedup_report = check(extraction.nodes, extraction.edges)
    diff = merge(extraction, dedup_report, dry_run=dry_run)

    write_log(
        timestamp=timestamp,
        source_type=source_type,
        source=source,
        raw_text=raw_text,
        extraction=extraction,
        dedup_report=dedup_report,
        diff=diff,
        dry_run=dry_run,
    )

    return {
        "timestamp": timestamp,
        "dry_run": dry_run,
        "extracted_nodes": len(extraction.nodes),
        "extracted_edges": len(extraction.edges),
        "skipped_nodes": sum(1 for r in dedup_report.nodes if r.decision == "skip"),
        "skipped_edges": sum(1 for r in dedup_report.edges if r.decision == "skip"),
        "added_nodes": len(diff.added_nodes) if not dry_run else 0,
        "added_edges": len(diff.added_edges) if not dry_run else 0,
        "extraction_notes": extraction.extraction_notes,
    }
