"""Ingestion Logger — per-run audit files under _work/ingestion/<timestamp>/"""
import json
import os
from pathlib import Path

from .dedup import DedupReport
from .extractor import ExtractionResult
from .merger import AppliedDiff

_DATA_DIR = Path(os.getenv("AGENT_DATA_DIR", "."))
_LOG_DIR = _DATA_DIR / "_work" / "ingestion"


def write_log(
    timestamp: str,
    source_type: str,
    source: str,
    raw_text: str,
    extraction: ExtractionResult,
    dedup_report: DedupReport,
    diff: AppliedDiff | None,
    dry_run: bool,
) -> Path:
    log_dir = _LOG_DIR / timestamp
    log_dir.mkdir(parents=True, exist_ok=True)

    source_summary = source if len(source) <= 120 else source[:117] + "..."

    (log_dir / "source_meta.json").write_text(json.dumps({
        "source_type": source_type,
        "source_summary": source_summary,
        "raw_text_chars": len(raw_text),
        "processed_at": timestamp,
        "dry_run": dry_run,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    (log_dir / "extraction_result.json").write_text(
        extraction.model_dump_json(indent=2), encoding="utf-8"
    )
    (log_dir / "dedup_report.json").write_text(
        dedup_report.model_dump_json(indent=2), encoding="utf-8"
    )

    if diff is not None and not dry_run:
        (log_dir / "applied_diff.json").write_text(
            diff.model_dump_json(indent=2), encoding="utf-8"
        )

    skipped_nodes = sum(1 for r in dedup_report.nodes if r.decision == "skip")
    skipped_edges = sum(1 for r in dedup_report.edges if r.decision == "skip")
    added_nodes = len(diff.added_nodes) if diff and not dry_run else 0
    added_edges = len(diff.added_edges) if diff and not dry_run else 0

    (log_dir / "manifest.json").write_text(json.dumps({
        "timestamp": timestamp,
        "source_type": source_type,
        "source_summary": source_summary,
        "raw_text_chars": len(raw_text),
        "dry_run": dry_run,
        "extracted_nodes": len(extraction.nodes),
        "extracted_edges": len(extraction.edges),
        "skipped_nodes": skipped_nodes,
        "skipped_edges": skipped_edges,
        "added_nodes": added_nodes,
        "added_edges": added_edges,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    return log_dir


def list_logs() -> list[dict]:
    if not _LOG_DIR.exists():
        return []
    results = []
    for ts_dir in sorted(_LOG_DIR.iterdir(), reverse=True):
        p = ts_dir / "manifest.json"
        if p.exists():
            results.append(json.loads(p.read_text(encoding="utf-8")))
    return results


def get_log(timestamp: str) -> dict | None:
    log_dir = _LOG_DIR / timestamp
    if not log_dir.exists():
        return None
    result: dict = {}
    for fname in ["source_meta", "extraction_result", "dedup_report", "applied_diff", "manifest"]:
        p = log_dir / f"{fname}.json"
        if p.exists():
            result[fname] = json.loads(p.read_text(encoding="utf-8"))
    return result
