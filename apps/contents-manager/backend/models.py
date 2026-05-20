from datetime import datetime
from sqlalchemy import Boolean, Column, Float, Integer, JSON, Text, ForeignKey, TIMESTAMP, func
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Text, primary_key=True)
    email = Column(Text, unique=True, nullable=False)
    hashed_pw = Column(Text, nullable=False)
    role = Column(Text, default="editor")  # admin | editor | viewer
    created_at = Column(TIMESTAMP, server_default=func.now())


class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    owner_id = Column(Text, ForeignKey("users.id"), nullable=False)
    status = Column(Text, default="draft")  # draft | active | archived
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class SubjectNode(Base):
    __tablename__ = "subject_nodes"
    subject_id = Column(Text, ForeignKey("subjects.id"), primary_key=True)
    node_id = Column(Text, primary_key=True)


class SubjectEdge(Base):
    __tablename__ = "subject_edges"
    subject_id = Column(Text, ForeignKey("subjects.id"), primary_key=True)
    edge_id = Column(Text, primary_key=True)


# ── EPIC-002: Blueprint Workspace ──────────────────────────────────────────────

class Blueprint(Base):
    __tablename__ = "blueprints"
    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    matrix = Column(Text)  # JSON: {layer: [cognitive_stage, ...]}
    owner_id = Column(Text, ForeignKey("users.id"), nullable=False)
    weight = Column(Float, default=1.0)
    required = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class BlueprintIntegrationItem(Base):
    __tablename__ = "blueprint_integration_items"
    id = Column(Text, primary_key=True)
    blueprint_id = Column(Text, ForeignKey("blueprints.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text)
    required_combinations = Column(Text)  # JSON: [{layer, stage}]
    created_at = Column(TIMESTAMP, server_default=func.now())


# ── EPIC-003: Question Generator Workbench ─────────────────────────────────────

class QuestionItem(Base):
    __tablename__ = "question_items"
    id = Column(Text, primary_key=True)
    entity_id = Column(Text, nullable=False)
    blueprint_id = Column(Text, ForeignKey("blueprints.id", ondelete="SET NULL"), nullable=True)
    question_text = Column(Text, nullable=False)
    # JSON: [{label, text, rationale, is_correct}]
    options = Column(Text, nullable=False)
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text)
    # JSON: snapshot of entity + related nodes at generation time (de-normalization)
    node_snapshot = Column(Text)
    question_type = Column(Text, default="MCQ")    # MCQ | OX | short_answer
    difficulty = Column(Text, default="medium")    # easy | medium | hard
    status = Column(Text, default="draft")         # draft | published | archived
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


# ── EPIC-007: Question Link Tables ────────────────────────────────────────────

class QuestionEntityLink(Base):
    __tablename__ = "question_entity_links"
    question_id = Column(Text, ForeignKey("question_items.id", ondelete="CASCADE"), primary_key=True)
    entity_id   = Column(Text, nullable=False, primary_key=True)


class QuestionMatrixLink(Base):
    __tablename__ = "question_matrix_links"
    question_id         = Column(Text, ForeignKey("question_items.id", ondelete="CASCADE"), primary_key=True)
    blueprint_id        = Column(Text, ForeignKey("blueprints.id", ondelete="CASCADE"), primary_key=True)
    layer               = Column(Text, nullable=False, primary_key=True)
    stage               = Column(Text, nullable=False, primary_key=True)
    integration_item_id = Column(Text, ForeignKey("blueprint_integration_items.id", ondelete="SET NULL"), nullable=True)


# ── KG Storage (EPIC-011 migration from JSON files) ───────────────────────────

class KGNode(Base):
    __tablename__ = "kg_nodes"
    id = Column(Text, primary_key=True)
    subject_id = Column(Text, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(Text, nullable=False)          # Seed | Concept | TechStack | System
    depth = Column(Integer, default=1)
    name = Column(Text, nullable=False)
    description = Column(Text)
    node_metadata = Column("metadata", JSON, default=dict)
    created_at = Column(TIMESTAMP, server_default=func.now())
    created_by_trigger = Column(Text)


class KGEdge(Base):
    __tablename__ = "kg_edges"
    id = Column(Text, primary_key=True)
    subject_id = Column(Text, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(Text, nullable=False)     # references kg_nodes.id (string, no enforced FK for flexibility)
    target_id = Column(Text, nullable=False)
    relation_type = Column(Text, nullable=False)
    logic_basis = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
    created_by_trigger = Column(Text)


class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    id = Column(Text, primary_key=True)
    entity_id = Column(Text, nullable=False)
    blueprint_id = Column(Text, nullable=True)
    integration_item_id = Column(Text, nullable=True)
    status = Column(Text, default="pending")  # pending | running | completed | failed
    result = Column(Text)   # JSON: list of generated question dicts
    error = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
