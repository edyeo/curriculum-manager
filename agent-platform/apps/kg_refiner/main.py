"""
KG Refiner API Server
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.kg_refiner.routes import router

app = FastAPI(
    title="KG Refiner API",
    description="학생 데이터·서브그래프 기반 지식 그래프 재정의 제안",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)
