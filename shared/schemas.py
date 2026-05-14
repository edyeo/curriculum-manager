"""
schemas.py — Pydantic 모델 정의

EntityType / RelationType Enum은 ontology.yaml에서 동적으로 생성된다.
Pydantic의 strict validation은 동적 Enum에서도 동일하게 작동한다.
"""
from typing import Literal
from uuid import uuid4
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from src.ontology_loader import get_ontology

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── 온톨로지에서 동적 Enum 생성 ──────────────────────────────────
# 모듈 임포트 시 ontology.yaml을 읽어 Enum을 구성한다.
# 이후 코드는 정적 Enum과 동일하게 EntityType.Seed 형태로 사용 가능.

_ontology = get_ontology()
EntityType = _ontology.make_entity_enum()
RelationType = _ontology.make_relation_enum()


# ── Core 모델 ─────────────────────────────────────────────────

class Entity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: EntityType
    depth: Literal[1, 2, 3]
    name: str
    description: str
    metadata: dict = Field(default_factory=dict)
    created_at: str = Field(default_factory=_now_iso)
    created_by_trigger: str = Field(default="unknown")


class Edge(BaseModel):
    source_id: str
    target_id: str
    relation_type: RelationType
    logic_basis: str
    created_at: str = Field(default_factory=_now_iso)
    created_by_trigger: str = Field(default="unknown")


class GraphState(BaseModel):
    nodes: list[Entity] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)


# ── LLM structured output 스키마 ──────────────────────────────

class NodeOutput(BaseModel):
    """LLM이 생성하는 단일 노드"""
    name: str = Field(description="엔터티의 이름")
    description: str = Field(description="엔터티에 대한 2-3문장 설명")
    depth: Literal[1, 2, 3] = Field(description="추상화 레벨: 1=고수준/범주, 2=중간, 3=구체적/특정")
    metadata: dict = Field(default_factory=dict, description="추가 메타데이터")


class NodeGenerationOutput(BaseModel):
    """DRAFT 에이전트의 structured output"""
    nodes: list[NodeOutput] = Field(description="생성된 노드 목록 (최대 10개)")


class EdgeOutput(BaseModel):
    """LLM이 생성하는 단일 엣지"""
    source_id: str = Field(description="소스 엔터티의 UUID")
    target_id: str = Field(description="타겟 엔터티의 UUID")
    relation_type: RelationType = Field(description="관계 타입")
    logic_basis: str = Field(description="연결의 논리적 근거 (1-2문장)")


class EdgeGenerationOutput(BaseModel):
    """LINK / EXPAND 에이전트의 structured output"""
    edges: list[EdgeOutput] = Field(description="생성된 엣지 목록")


def _entity_type_description() -> str:
    """온톨로지에서 DebateNodeOutput의 type 필드 description을 동적 생성."""
    names = " | ".join(_ontology.entities.keys())
    return f"엔터티 타입: {names}"


class DebateNodeOutput(BaseModel):
    """Synthesizer가 생성하는 단일 노드 (type을 LLM이 직접 결정)"""
    name: str = Field(description="엔터티의 이름")
    description: str = Field(description="엔터티에 대한 2-3문장 설명")
    type: EntityType = Field(description=_entity_type_description())
    depth: Literal[1, 2, 3] = Field(description="추상화 레벨: 1=고수준/범주, 2=중간, 3=구체적/특정")
    metadata: dict = Field(default_factory=dict, description="추가 메타데이터")


class DebateNodeGenerationOutput(BaseModel):
    """Synthesizer의 structured output"""
    nodes: list[DebateNodeOutput] = Field(description="생성된 노드 목록 (최대 10개)")
    synthesis_rationale: str = Field(description="두 분석을 종합한 근거 요약")
