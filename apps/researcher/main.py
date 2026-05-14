"""
Researcher API Server
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.researcher.routes import router

app = FastAPI(
    title="Researcher API",
    description="Research and gather information",
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
    uvicorn.run(app, host="0.0.0.0", port=8003)
