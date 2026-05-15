"""
Mental Model Manager API Server
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.mental_model_manager.routes import router

app = FastAPI(
    title="Mental Model Manager API",
    description="Generate mental models for better understanding",
    version="0.1.0"
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
    uvicorn.run(app, host="0.0.0.0", port=8002)
