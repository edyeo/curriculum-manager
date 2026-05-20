import os
from sqlalchemy import create_engine, Column, Text, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import DeclarativeBase, sessionmaker

_db_path = os.getenv("CM_DB_PATH", "./contents_manager.db")
DATABASE_URL = f"sqlite:///{_db_path}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models import (  # noqa
        User, Subject, SubjectNode, SubjectEdge,
        Blueprint, BlueprintIntegrationItem,
        QuestionItem, GenerationJob,
    )
    Base.metadata.create_all(bind=engine)
    _migrate_question_items()


def _migrate_question_items():
    """Add question_type / difficulty columns to existing question_items tables."""
    with engine.connect() as conn:
        from sqlalchemy import text
        for col, default in [("question_type", "MCQ"), ("difficulty", "medium")]:
            try:
                conn.execute(text(f"ALTER TABLE question_items ADD COLUMN {col} TEXT DEFAULT '{default}'"))
                conn.commit()
            except Exception:
                pass  # column already exists
