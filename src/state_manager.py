import json
from pathlib import Path
from src.schemas import Entity, Edge, GraphState

NODES_FILE = Path("nodes.json")
EDGES_FILE = Path("edges.json")
SKILLS_DIR = Path("skills")


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
