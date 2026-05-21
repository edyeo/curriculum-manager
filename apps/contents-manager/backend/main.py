import uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db, SessionLocal
from models import User, SubjectNode, SubjectEdge, KGNode, KGEdge
from auth import hash_password
from routes import auth, subjects, nodes, research, questions, kg, blueprints, question_workbench, ingestion
import file_db

app = FastAPI(title="Contents Manager", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(subjects.router, prefix="/api")
app.include_router(nodes.router, prefix="/api")
app.include_router(research.router, prefix="/api")
app.include_router(questions.router, prefix="/api")
app.include_router(blueprints.router, prefix="/api")
app.include_router(question_workbench.router, prefix="/api")
app.include_router(ingestion.router, prefix="/api")
app.include_router(kg.router)


@app.on_event("startup")
def startup():
    init_db()
    _seed_admin()
    _import_kg_from_json()


def _seed_admin():
    """Create default admin account if no users exist."""
    import os
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            admin = User(
                id=str(uuid.uuid4()),
                email=os.getenv("ADMIN_EMAIL", "admin@example.com"),
                hashed_pw=hash_password(os.getenv("ADMIN_PASSWORD", "admin1234")),
                role="admin",
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


def _import_kg_from_json():
    """nodes.json + SubjectNode/SubjectEdge → KGNode/KGEdge 일회성 임포트.

    kg_nodes 테이블이 비어 있을 때만 실행.
    nodes.json 파일이 없거나 SubjectNode 매핑이 없으면 조용히 종료.
    """
    db = SessionLocal()
    try:
        if db.query(KGNode).count() > 0:
            return

        json_nodes = file_db.read_nodes()
        json_edges = file_db.read_edges()
        if not json_nodes:
            return

        node_map = {n["id"]: n for n in json_nodes}
        edge_map = {}
        for e in json_edges:
            eid = e.get("id") or f"{e.get('source_id')}:{e.get('target_id')}:{e.get('relation_type')}"
            edge_map[eid] = e

        imported_nodes = 0
        imported_edges = 0

        for row in db.query(SubjectNode).all():
            n = node_map.get(row.node_id)
            if n:
                db.merge(KGNode(
                    id=n["id"],
                    subject_id=row.subject_id,
                    type=n.get("type", "Concept"),
                    depth=n.get("depth", 1),
                    name=n.get("name", ""),
                    description=n.get("description"),
                    node_metadata=n.get("metadata", {}),
                    created_by_trigger=n.get("created_by_trigger"),
                ))
                imported_nodes += 1

        for row in db.query(SubjectEdge).all():
            e = edge_map.get(row.edge_id)
            if e:
                db.merge(KGEdge(
                    id=row.edge_id,
                    subject_id=row.subject_id,
                    source_id=e.get("source_id", ""),
                    target_id=e.get("target_id", ""),
                    relation_type=e.get("relation_type", ""),
                    logic_basis=e.get("logic_basis"),
                    created_by_trigger=e.get("created_by_trigger"),
                ))
                imported_edges += 1

        db.commit()
        if imported_nodes:
            print(f"[startup] KG import: {imported_nodes} nodes, {imported_edges} edges → DB")
    except Exception as exc:
        print(f"[startup] KG import skipped: {exc}")
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "contents-manager"}
