"""Merger — applies dedup decisions to nodes.json / edges.json, then snapshots KG"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import file_db
from pydantic import BaseModel

from .dedup import DedupReport
from .extractor import ExtractionResult

_DATA_DIR = Path(os.getenv("AGENT_DATA_DIR", "."))


class AppliedDiff(BaseModel):
    added_nodes: list[dict]
    added_edges: list[dict]


def merge(
    extraction: ExtractionResult,
    dedup_report: DedupReport,
    dry_run: bool = False,
) -> AppliedDiff:
    existing_nodes = file_db.read_nodes()
    existing_edges = file_db.read_edges()

    name_to_id: dict[str, str] = {
        n["name"].lower().strip(): n["id"] for n in existing_nodes
    }
    node_map = {n.name.lower().strip(): n for n in extraction.nodes}
    edge_map = {
        (e.source_name.lower().strip(), e.target_name.lower().strip(), e.relation): e
        for e in extraction.edges
    }

    # ── Add nodes ────────────────────────────────────────────
    added_nodes: list[dict] = []
    now = datetime.now(timezone.utc).isoformat()

    for result in dedup_report.nodes:
        if result.decision != "add":
            continue
        node = node_map[result.name.lower().strip()]
        new_id = str(uuid.uuid4())
        record = {
            "id": new_id,
            "type": node.type,
            "depth": node.depth,
            "name": node.name,
            "description": node.description,
            "metadata": {"source_excerpt": node.source_excerpt} if node.source_excerpt else {},
            "created_at": now,
            "created_by_trigger": "INGESTION",
        }
        added_nodes.append(record)
        name_to_id[result.name.lower().strip()] = new_id

    # ── Add edges ────────────────────────────────────────────
    added_edges: list[dict] = []
    for result in dedup_report.edges:
        if result.decision != "add":
            continue
        key = (result.source_name.lower().strip(), result.target_name.lower().strip(), result.relation)
        edge = edge_map.get(key)
        if not edge:
            continue
        src_id = name_to_id.get(result.source_name.lower().strip())
        tgt_id = name_to_id.get(result.target_name.lower().strip())
        if not src_id or not tgt_id:
            continue
        record = {
            "id": str(uuid.uuid4()),
            "source_id": src_id,
            "target_id": tgt_id,
            "relation_type": result.relation,
            "logic_basis": edge.basis,
            "created_at": now,
            "created_by_trigger": "INGESTION",
        }
        added_edges.append(record)

    diff = AppliedDiff(added_nodes=added_nodes, added_edges=added_edges)

    if not dry_run:
        file_db.write_nodes(existing_nodes + added_nodes)
        file_db.write_edges(existing_edges + added_edges)
        _snapshot(existing_nodes + added_nodes, existing_edges + added_edges)

    return diff


def _snapshot(nodes: list[dict], edges: list[dict]) -> None:
    """KG 전체 상태를 _work/<timestamp>/ 에 저장 (INGESTION 트리거)."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    snap_dir = _DATA_DIR / "_work" / ts
    snap_dir.mkdir(parents=True, exist_ok=True)
    (snap_dir / "nodes.json").write_text(
        json.dumps(nodes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (snap_dir / "edges.json").write_text(
        json.dumps(edges, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (snap_dir / "manifest.json").write_text(
        json.dumps({
            "trigger": "INGESTION",
            "timestamp": ts,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
