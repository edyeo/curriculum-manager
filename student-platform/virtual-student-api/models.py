import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base


def _uuid():
    return str(uuid.uuid4())


class VirtualStudentFeatureDefinition(Base):
    __tablename__ = "virtual_student_feature_definitions"

    key = Column(String, primary_key=True)
    display_name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    value_type = Column(String, nullable=False)  # categorical | numeric | text
    value_options = Column(JSON, nullable=True)
    value_range = Column(JSON, nullable=True)
    default_value = Column(String, nullable=True)
    category = Column(String, nullable=False)
    is_builtin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    values = relationship("VirtualStudentFeatureValue", back_populates="definition")


class VirtualStudent(Base):
    __tablename__ = "virtual_students"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    subject_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    feature_values = relationship(
        "VirtualStudentFeatureValue",
        back_populates="student",
        cascade="all, delete-orphan",
    )


class VirtualStudentFeatureValue(Base):
    __tablename__ = "virtual_student_feature_values"

    id = Column(String, primary_key=True, default=_uuid)
    virtual_student_id = Column(String, ForeignKey("virtual_students.id"), nullable=False)
    feature_key = Column(
        String,
        ForeignKey("virtual_student_feature_definitions.key"),
        nullable=False,
    )
    value = Column(Text, nullable=False)

    student = relationship("VirtualStudent", back_populates="feature_values")
    definition = relationship("VirtualStudentFeatureDefinition", back_populates="values")


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id = Column(String, primary_key=True, default=_uuid)
    subject_id = Column(String, nullable=False)
    mode = Column(String, nullable=False)          # simple | interview
    question_source = Column(String, nullable=False)  # kg | manual | none
    questions = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    results = relationship("SimulationResult", back_populates="run", cascade="all, delete-orphan")


class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id = Column(String, primary_key=True, default=_uuid)
    run_id = Column(String, ForeignKey("simulation_runs.id"), nullable=False)
    virtual_student_id = Column(String, ForeignKey("virtual_students.id"), nullable=False)
    answers = Column(JSON, nullable=False, default=list)
    diagnosis = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("SimulationRun", back_populates="results")
    student = relationship("VirtualStudent")
