from sqlalchemy import create_engine, Column, Text, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = "sqlite:///./contents_manager.db"

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
    from models import User, Subject, SubjectNode, SubjectEdge  # noqa
    Base.metadata.create_all(bind=engine)
