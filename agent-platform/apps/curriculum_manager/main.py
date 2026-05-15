"""
Curriculum Manager API Server
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.curriculum_manager.routes import router

app = FastAPI(
    title="Curriculum Manager API",
    description="Pass-Iteration: Trigger-based Curriculum Generator",
    version="0.1.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(router)


@app.get("/health")
async def health():
    """헬스 체크"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
