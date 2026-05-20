from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, JSON
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


# ── EPIC-007: Interview Agent ─────────────────────────────────────────────────

class InterviewSession(Base):
    """가상 인터뷰 세션. 실행 중 상태는 서버 메모리에서만 관리하며 완료 시 DB에 반영."""
    __tablename__ = "interview_sessions"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(String, nullable=False)
    status = Column(String, default="active")          # active | completed
    knowledge_snapshot = Column(JSON)                  # 세션 시작 시점 초기 mastery 기록용
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)


class InterviewTurn(Base):
    """인터뷰 한 턴 = 질문 + 학생 답변 + 평가 결과."""
    __tablename__ = "interview_turns"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    turn_number = Column(Integer, nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    score = Column(Float, nullable=False)
    feedback = Column(Text)
    action = Column(String)                            # follow_up | pivot
    target_nodes = Column(JSON)                        # 대상 노드 ID 목록
    created_at = Column(DateTime, default=datetime.utcnow)


class InterviewDiagnosis(Base):
    """세션 종료 시 산출되는 최종 진단 리포트."""
    __tablename__ = "interview_diagnoses"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), unique=True, nullable=False)
    overall_band = Column(String(1))                   # S/A/B/C/D
    strengths = Column(JSON)
    weaknesses = Column(JSON)
    not_covered = Column(JSON)                         # 인터뷰에서 다루지 않은 노드 이름 목록
    recommendations = Column(JSON)
    node_final_mastery = Column(JSON)                  # 최종 mastery 상태
    created_at = Column(DateTime, default=datetime.utcnow)
