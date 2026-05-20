"""IngestionHarness — 파이프라인 진입점"""
from datetime import datetime, timezone
from typing import Literal

from .dedup import check
from .extractor import extract
from .loader import load
from .logger import write_log
from .merger import merge


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
