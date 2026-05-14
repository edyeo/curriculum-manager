"""
OntologyLoader — ontology.yaml (또는 원격 URL)을 로드하여
런타임에 Enum + Pydantic 모델을 동적으로 생성한다.

사용:
    from src.ontology_loader import load_ontology
    ontology = load_ontology("ontology.yaml")
    EntityType = ontology.make_entity_enum()
    RelationType = ontology.make_relation_enum()
"""
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator


# ── Ontology 정의 Pydantic 모델 ────────────────────────────────

class AntiSolutionConstraint(BaseModel):
    enabled: bool = False
    rule: str = ""
    focus: list[str] = Field(default_factory=list)
    naming_patterns: list[str] = Field(default_factory=list)


class EntityConstraints(BaseModel):
    anti_solution: AntiSolutionConstraint = Field(
        default_factory=AntiSolutionConstraint
    )


class OntologyEntityDef(BaseModel):
    description: str
    depth_range: list[int] = Field(default=[1, 3])
    constraints: EntityConstraints = Field(default_factory=EntityConstraints)

    @model_validator(mode="after")
    def validate_depth_range(self) -> "OntologyEntityDef":
        if len(self.depth_range) != 2:
            raise ValueError("depth_range must have exactly 2 elements [min, max]")
        if not (1 <= self.depth_range[0] <= self.depth_range[1] <= 3):
            raise ValueError("depth_range must be within [1, 3]")
        return self


class OntologyRelationDef(BaseModel):
    description: str
    valid_pairs: list[list[str]] = Field(default_factory=list)


class Ontology(BaseModel):
    """온톨로지 전체 정의. ontology.yaml의 구조와 1:1 대응."""
    version: str
    name: str
    description: str = ""
    entities: dict[str, OntologyEntityDef]
    relations: dict[str, OntologyRelationDef]

    @model_validator(mode="after")
    def validate_valid_pairs(self) -> "Ontology":
        """valid_pairs에 존재하지 않는 entity 타입이 있으면 에러"""
        known = set(self.entities.keys())
        for rel_name, rel_def in self.relations.items():
            for pair in rel_def.valid_pairs:
                for entity_name in pair:
                    if entity_name not in known:
                        raise ValueError(
                            f"Relation '{rel_name}' references unknown entity '{entity_name}'. "
                            f"Known entities: {sorted(known)}"
                        )
        return self

    # ── 동적 Enum 생성 ──────────────────────────────────────────

    def make_entity_enum(self) -> type[Enum]:
        """
        ontology.yaml의 entities 키로 EntityType Enum을 동적 생성.
        Pydantic은 동적 Enum도 정적 Enum과 동일하게 strict validate 한다.
        """
        return Enum(  # type: ignore[return-value]
            "EntityType",
            {name: name for name in self.entities},
            type=str,
        )

    def make_relation_enum(self) -> type[Enum]:
        """ontology.yaml의 relations 키로 RelationType Enum을 동적 생성."""
        return Enum(  # type: ignore[return-value]
            "RelationType",
            {name: name for name in self.relations},
            type=str,
        )

    # ── 프롬프트 주입용 헬퍼 ────────────────────────────────────

    def get_entity_prompt_block(self, entity_name: str) -> str:
        """
        에이전트 시스템 프롬프트에 주입할 entity 제약 블록을 생성한다.
        seed_agent_skill.md 등의 Rules 섹션을 동적으로 대체·보완하는 데 사용.
        """
        entity = self.entities.get(entity_name)
        if not entity:
            return ""

        lines = [f"## [{entity_name}] Entity 정의 (Ontology v{self.version})"]
        lines.append(entity.description.strip())

        ac = entity.constraints.anti_solution
        if ac.enabled:
            lines.append("\n### Anti-Solution Constraint (자동 주입)")
            lines.append(ac.rule.strip())
            if ac.focus:
                lines.append("\n**초점:**")
                for f in ac.focus:
                    lines.append(f"  - {f}")
            if ac.naming_patterns:
                lines.append("\n**권장 네이밍 패턴:**")
                for p in ac.naming_patterns:
                    lines.append(f"  - `{p}`")

        return "\n".join(lines)

    def get_relation_valid_pairs_text(self) -> str:
        """링킹 에이전트 프롬프트에 주입할 valid_pairs 텍스트."""
        lines = [f"## Relation 정의 (Ontology v{self.version})"]
        for rel_name, rel_def in self.relations.items():
            pairs_str = ", ".join(f"{a}→{b}" for a, b in rel_def.valid_pairs)
            lines.append(f"- **{rel_name}**: {rel_def.description} (허용 페어: {pairs_str})")
        return "\n".join(lines)

    def to_manifest_dict(self) -> dict[str, Any]:
        """snapshot_work() manifest.json에 포함될 온톨로지 요약."""
        return {
            "version": self.version,
            "name": self.name,
            "entities": list(self.entities.keys()),
            "relations": list(self.relations.keys()),
        }


# ── 로더 ────────────────────────────────────────────────────────

def load_ontology(source: str | Path = "ontology.yaml") -> Ontology:
    """
    파일 경로 또는 HTTP URL에서 온톨로지를 로드하여 Ontology 모델로 반환.

    향후 외부 서비스로 전환 시:
        load_ontology("https://ontology-service/v1/schemas/engineering-curriculum")
    """
    source = str(source)

    if source.startswith("http://") or source.startswith("https://"):
        import urllib.request
        with urllib.request.urlopen(source) as resp:
            raw = yaml.safe_load(resp.read().decode("utf-8"))
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Ontology file not found: {path.resolve()}")
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

    return Ontology.model_validate(raw)


# ── 싱글턴 ─────────────────────────────────────────────────────
# 애플리케이션 시작 시 한 번만 로드되도록 모듈 수준에서 캐싱.
# cli.py → harness → 여기서 최초 로드 → 이후 import 시 재사용.

_ONTOLOGY_SOURCE = "ontology.yaml"
_ontology_cache: Ontology | None = None


def get_ontology() -> Ontology:
    """캐싱된 Ontology 인스턴스를 반환. 최초 호출 시만 파일 읽기."""
    global _ontology_cache
    if _ontology_cache is None:
        _ontology_cache = load_ontology(_ONTOLOGY_SOURCE)
    return _ontology_cache
