"""Snapshot management — list, diff, rollback for KG version history"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import file_db

_DATA_DIR = Path(os.getenv("AGENT_DATA_DIR", "."))
_WORK_DIR = _DATA_DIR / "_work"


def _snap_dir(timestamp: str) -> Path:
    return _WORK_DIR / timestamp


def list_snapshots() -> list[dict]:
    if not _WORK_DIR.exists():
        return []
    snaps = []
    for d in sorted(_WORK_DIR.iterdir(), reverse=True):
        if not d.is_dir() or d.name == "ingestion":
            continue
        manifest_path = d / "manifest.json"
        if not manifest_path.exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            snaps.append(manifest)
        except (json.JSONDecodeError, OSError):
            continue
    return snaps


def get_snapshot_diff(timestamp: str) -> dict:
    """Diff between snapshot@timestamp and current KG."""
    snap = _snap_dir(timestamp)
    if not snap.exists():
        return None

    snap_nodes = _read_json(snap / "nodes.json")
    snap_edges = _read_json(snap / "edges.json")
    cur_nodes = file_db.read_nodes()
    cur_edges = file_db.read_edges()

    snap_node_ids = {n["id"] for n in snap_nodes}
    cur_node_ids = {n["id"] for n in cur_nodes}
    snap_edge_ids = {_edge_key(e) for e in snap_edges}
    cur_edge_ids = {_edge_key(e) for e in cur_edges}

    added_nodes = [n for n in cur_nodes if n["id"] not in snap_node_ids]
    removed_nodes = [n for n in snap_nodes if n["id"] not in cur_node_ids]
    added_edges = [e for e in cur_edges if _edge_key(e) not in snap_edge_ids]
    removed_edges = [e for e in snap_edges if _edge_key(e) not in cur_edge_ids]

    manifest = {}
    manifest_path = snap / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    return {
        "timestamp": timestamp,
        "manifest": manifest,
        "snapshot_node_count": len(snap_nodes),
        "snapshot_edge_count": len(snap_edges),
        "current_node_count": len(cur_nodes),
        "current_edge_count": len(cur_edges),
        "added_nodes": added_nodes,
        "removed_nodes": removed_nodes,
        "added_edges": added_edges,
        "removed_edges": removed_edges,
    }


def rollback(timestamp: str) -> dict:
    """Restore KG to the state at the given snapshot timestamp."""
    snap = _snap_dir(timestamp)
    if not snap.exists():
        return None

    snap_nodes = _read_json(snap / "nodes.json")
    snap_edges = _read_json(snap / "edges.json")

    file_db.write_nodes(snap_nodes)
    file_db.write_edges(snap_edges)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    new_snap = _WORK_DIR / ts
    new_snap.mkdir(parents=True, exist_ok=True)
    (new_snap / "nodes.json").write_text(
        json.dumps(snap_nodes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (new_snap / "edges.json").write_text(
        json.dumps(snap_edges, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (new_snap / "manifest.json").write_text(
        json.dumps({
            "trigger": "ROLLBACK",
            "timestamp": ts,
            "rolled_back_to": timestamp,
            "node_count": len(snap_nodes),
            "edge_count": len(snap_edges),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "rolled_back_to": timestamp,
        "new_snapshot": ts,
        "node_count": len(snap_nodes),
        "edge_count": len(snap_edges),
    }


def _read_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _edge_key(e: dict) -> str:
    return f"{e.get('source_id','')}:{e.get('target_id','')}:{e.get('relation_type','')}"
