import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/virtual_students.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    _seed_default_features()  # schema managed by Alembic; only seed static data here


def _seed_default_features():
    from seed_data.default_features import DEFAULT_FEATURES
    from models import VirtualStudentFeatureDefinition

    db = SessionLocal()
    try:
        if db.query(VirtualStudentFeatureDefinition).count() == 0:
            for f in DEFAULT_FEATURES:
                db.add(VirtualStudentFeatureDefinition(**f))
            db.commit()
    finally:
        db.close()
