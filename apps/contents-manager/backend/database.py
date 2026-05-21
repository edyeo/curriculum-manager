import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

_default_url = "sqlite:///{}".format(os.getenv("CM_DB_PATH", "./contents_manager.db"))
DATABASE_URL = os.getenv("DATABASE_URL", _default_url)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
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
    pass  # schema managed by Alembic — runs `alembic upgrade head` at container start
