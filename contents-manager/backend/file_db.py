"""Direct read/write access to the agent-side JSON files."""
import json
import os
from pathlib import Path

# Resolve from project root (same convention as shared/state_manager.py)
_BASE = Path(os.getenv("AGENT_DATA_DIR", "."))
NODES_FILE = _BASE / "nodes.json"
EDGES_FILE = _BASE / "edges.json"


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _write(path: Path, data: list[dict]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_nodes() -> list[dict]:
    return _read(NODES_FILE)


def write_nodes(nodes: list[dict]) -> None:
    _write(NODES_FILE, nodes)


def _edge_id(e: dict) -> str:
    """edge 고유 ID: schema에 id 없으면 source:target:relation으로 생성"""
    if "id" in e:
        return e["id"]
    return f"{e.get('source_id','')}:{e.get('target_id','')}:{e.get('relation_type','')}"


def read_edges() -> list[dict]:
    edges = _read(EDGES_FILE)
    for e in edges:
        if "id" not in e:
            e["id"] = _edge_id(e)
    return edges


def write_edges(edges: list[dict]) -> None:
    _write(EDGES_FILE, edges)
