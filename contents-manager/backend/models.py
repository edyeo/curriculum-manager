from sqlalchemy import Column, Text, ForeignKey, TIMESTAMP, func
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
