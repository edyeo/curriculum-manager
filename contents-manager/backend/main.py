import uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db, SessionLocal
from models import User
from auth import hash_password
from routes import auth, subjects, nodes, research, questions, kg, blueprints, question_workbench

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
app.include_router(kg.router)


@app.on_event("startup")
def startup():
    init_db()
    _seed_admin()


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


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "contents-manager"}
