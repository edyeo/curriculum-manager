import json
from pathlib import Path
from src.schemas import GraphState

STATE_FILE = Path("state.json")
SKILLS_DIR = Path("skills")


def load_state() -> GraphState:
    """state.json 로드. 파일이 없으면 빈 상태 반환."""
    if not STATE_FILE.exists():
        return GraphState()
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return GraphState.model_validate(data)


def save_state(state: GraphState) -> None:
    """GraphState를 state.json에 저장."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state.model_dump(), f, ensure_ascii=False, indent=2)
    print(f"  ✓ state.json 저장 완료 (nodes={len(state.nodes)}, edges={len(state.edges)})")


def load_skill(skill_filename: str) -> str:
    """skills/ 디렉토리에서 skill.md 파일 로드."""
    skill_path = SKILLS_DIR / skill_filename
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill file not found: {skill_path}")
    return skill_path.read_text(encoding="utf-8")
