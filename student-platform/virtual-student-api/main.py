from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routes import feature_definitions, stats, seed, subjects, generate, virtual_students

app = FastAPI(title="Virtual Student API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3010", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# stats and seed must be included before virtual_students to avoid /{id} shadowing
app.include_router(feature_definitions.router)
app.include_router(stats.router)
app.include_router(seed.router)
app.include_router(subjects.router)
app.include_router(generate.router)
app.include_router(virtual_students.router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "service": "virtual-student-api"}
