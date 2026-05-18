from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from database import Base


class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    hashed_pw = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class NodeMastery(Base):
    __tablename__ = "node_mastery"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    node_id = Column(String, nullable=False)       # KG 외부 참조
    subject_id = Column(String, nullable=False)    # KG 외부 참조
    mastery_score = Column(Float, default=0.5)
    attempt_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("student_id", "node_id", name="uq_student_node"),)


class StudySession(Base):
    __tablename__ = "study_sessions"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    question_id = Column(String, nullable=False)   # question-generator 외부 참조
    node_id = Column(String, nullable=False)
    subject_id = Column(String, nullable=False)
    user_answer = Column(Text)
    is_correct = Column(Boolean)
    score = Column(Float)
    feedback = Column(Text)
    time_taken_seconds = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class StudyAttempt(Base):
    """Question Bank 문항에 대한 학생 풀이 이력."""
    __tablename__ = "study_attempts"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    question_id = Column(String, nullable=False)   # QuestionItem.id (CM 외부 참조)
    blueprint_id = Column(String, nullable=True)
    user_answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    score = Column(Float)
    feedback = Column(Text)
    elapsed_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── EPIC-007: Blueprint Matrix Mastery ────────────────────────────────────────

class BlueprintCellMastery(Base):
    """Blueprint matrix 셀(layer/stage) 단위 역량 점수."""
    __tablename__ = "blueprint_cell_mastery"
    id            = Column(Integer, primary_key=True)
    student_id    = Column(Integer, ForeignKey("students.id"), nullable=False)
    blueprint_id  = Column(String, nullable=False)
    layer         = Column(String, nullable=False)
    stage         = Column(String, nullable=False)
    mastery_score = Column(Float, default=0.0)
    attempt_count = Column(Integer, default=0)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("student_id", "blueprint_id", "layer", "stage", name="uq_cell_mastery"),)


class BlueprintItemMastery(Base):
    """IntegrationItem 단위 역량 점수 (required_combinations 셀 min)."""
    __tablename__ = "blueprint_item_mastery"
    id                  = Column(Integer, primary_key=True)
    student_id          = Column(Integer, ForeignKey("students.id"), nullable=False)
    integration_item_id = Column(String, nullable=False)
    mastery_score       = Column(Float, default=0.0)
    attempt_count       = Column(Integer, default=0)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("student_id", "integration_item_id", name="uq_item_mastery"),)
