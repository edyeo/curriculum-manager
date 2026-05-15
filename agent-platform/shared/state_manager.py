import json
import datetime
from pathlib import Path
from shared.schemas import Entity, Edge, GraphState
from shared.ontology_loader import get_ontology

NODES_FILE = Path("nodes.json")
EDGES_FILE = Path("edges.json")
# Skills are located in the curriculum-manager agent directory
# Try multiple possible paths for flexibility
_possible_skills_dirs = [
    Path("agents/curriculum-manager/skills"),  # Local: project root
    Path("/app/agents/curriculum-manager/skills"),  # Docker: absolute path
    Path("skills"),  # Fallback: relative
]
SKILLS_DIR = next((p for p in _possible_skills_dirs if p.exists()), Path("skills"))
WORK_DIR = Path("_work")


# ── Nodes ──────────────────────────────────────────────────────

def load_nodes() -> list[Entity]:
    """nodes.json 로드. 파일이 없으면 빈 리스트 반환."""
    if not NODES_FILE.exists():
        return []
    with open(NODES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Entity.model_validate(n) for n in data]


def save_nodes(nodes: list[Entity]) -> None:
    """노드 리스트를 nodes.json에 저장."""
    with open(NODES_FILE, "w", encoding="utf-8") as f:
        json.dump([n.model_dump() for n in nodes], f, ensure_ascii=False, indent=2)
    print(f"  ✓ nodes.json 저장 완료 ({len(nodes)}개)")


# ── Edges ──────────────────────────────────────────────────────

def load_edges() -> list[Edge]:
    """edges.json 로드. 파일이 없으면 빈 리스트 반환."""
    if not EDGES_FILE.exists():
        return []
    with open(EDGES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Edge.model_validate(e) for e in data]


def save_edges(edges: list[Edge]) -> None:
    """엣지 리스트를 edges.json에 저장."""
    with open(EDGES_FILE, "w", encoding="utf-8") as f:
        json.dump([e.model_dump() for e in edges], f, ensure_ascii=False, indent=2)
    print(f"  ✓ edges.json 저장 완료 ({len(edges)}개)")


# ── Composite ──────────────────────────────────────────────────

def load_state() -> GraphState:
    """nodes.json + edges.json을 합쳐 GraphState로 반환."""
    return GraphState(nodes=load_nodes(), edges=load_edges())


def save_state(state: GraphState) -> None:
    """GraphState를 nodes.json + edges.json으로 분리 저장."""
    save_nodes(state.nodes)
    save_edges(state.edges)


# ── Skills ─────────────────────────────────────────────────────

def load_skill(skill_filename: str) -> str:
    """skills/ 디렉토리에서 skill.md 파일 로드."""
    skill_path = SKILLS_DIR / skill_filename
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill file not found: {skill_path}")
    return skill_path.read_text(encoding="utf-8")


# ── Work Snapshots ─────────────────────────────────────────────

def snapshot_work(
    nodes: list[Entity],
    edges: list[Edge],
    trigger: str,
    subject: str = "",
) -> Path:
    """
    _work/<timestamp>/ 하위에 nodes.json + edges.json + manifest.json을
    스냅샷으로 저장한다. 각 실행 결과가 타임스탬프 기반으로 버전관리된다.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_dir = WORK_DIR / timestamp
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # nodes.json
    nodes_path = snapshot_dir / "nodes.json"
    with open(nodes_path, "w", encoding="utf-8") as f:
        json.dump([n.model_dump() for n in nodes], f, ensure_ascii=False, indent=2)

    # edges.json
    edges_path = snapshot_dir / "edges.json"
    with open(edges_path, "w", encoding="utf-8") as f:
        json.dump([e.model_dump() for e in edges], f, ensure_ascii=False, indent=2)

    # manifest.json — 메타 정보
    from collections import Counter
    node_type_counts = Counter(n.type.value for n in nodes)
    rel_type_counts = Counter(e.relation_type.value for e in edges)

    manifest = {
        "timestamp": timestamp,
        "trigger": trigger,
        "subject": subject,
        "ontology": get_ontology().to_manifest_dict(),
        "summary": {
            "total_nodes": len(nodes),
            "nodes_by_type": dict(node_type_counts),
            "total_edges": len(edges),
            "edges_by_relation": dict(rel_type_counts),
        },
    }
    manifest_path = snapshot_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"  📁 스냅샷 저장: _work/{timestamp}/ (nodes={len(nodes)}, edges={len(edges)})")
    return snapshot_dir
