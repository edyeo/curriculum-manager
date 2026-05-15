"""
Backend API Gateway
모든 에이전트 API를 조율하고 조합하는 중앙 서버
향후 인증, 레이트 리미팅, 로깅 등을 추가
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import httpx

app = FastAPI(
    title="Curriculum Platform API Gateway",
    description="Central API for multi-agent curriculum system",
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

# 에이전트 서버 주소 (env var로 override 가능, 로컬 실행 시 활용)
import os
AGENTS = {
    "curriculum": os.getenv("CURRICULUM_URL", "http://curriculum-manager:8001"),
    "mental-models": os.getenv("MENTAL_MODEL_URL", "http://mental-model-manager:8002"),
    "research": os.getenv("RESEARCH_URL", "http://researcher:8003"),
    "questions": os.getenv("QUESTIONS_URL", "http://question-generator:8004"),
}


# ========== Request/Response Models ==========

class CurriculumGenerationRequest(BaseModel):
    subject: str
    description: Optional[str] = None
    include_mental_models: Optional[bool] = True
    include_research: Optional[bool] = True
    include_questions: Optional[bool] = True


class IntegratedCurriculumResponse(BaseModel):
    subject: str
    curriculum: dict
    mental_models: Optional[dict] = None
    research_results: Optional[dict] = None
    questions: Optional[dict] = None


# ========== Gateway Routes ==========

@app.get("/health")
async def health():
    """헬스 체크"""
    return {"status": "healthy", "gateway": "online"}


@app.get("/agents/status")
async def agents_status():
    """모든 에이전트 상태 확인"""
    status = {}
    async with httpx.AsyncClient() as client:
        for agent_name, agent_url in AGENTS.items():
            try:
                response = await client.get(f"{agent_url}/health", timeout=5.0)
                status[agent_name] = {"status": "online", "code": response.status_code}
            except Exception as e:
                status[agent_name] = {"status": "offline", "error": str(e)}
    return status


# ========== Curriculum Generation Workflow ==========

@app.post("/curriculum/generate", response_model=IntegratedCurriculumResponse)
async def generate_curriculum(request: CurriculumGenerationRequest):
    """
    통합 커리큘럼 생성 워크플로우:
    1. Curriculum Manager: 커리큘럼 구조 생성
    2. (선택) Researcher: 조사 자료 수집
    3. (선택) Mental Model Manager: 개념 설명 생성
    4. (선택) Question Generator: 문제 생성
    """
    try:
        result = {
            "subject": request.subject,
            "curriculum": None,
            "mental_models": None,
            "research_results": None,
            "questions": None
        }

        # Step 1: Curriculum 생성
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AGENTS['curriculum']}/api/curriculum/generate/draft",
                json={"subject": request.subject, "description": request.description},
                timeout=30.0
            )
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to generate curriculum")
            result["curriculum"] = response.json()

            # Step 2: Research 수집 (선택)
            if request.include_research and result["curriculum"]:
                try:
                    response = await client.post(
                        f"{AGENTS['research']}/api/research/start",
                        json={
                            "entity_id": request.subject,
                            "keywords": [request.subject],
                            "sources": ["blog", "github"]
                        },
                        timeout=30.0
                    )
                    if response.status_code == 200:
                        result["research_results"] = response.json()
                except Exception as e:
                    print(f"Warning: Research failed: {e}")

            # Step 3: Mental Models 생성 (선택)
            if request.include_mental_models and result["curriculum"]:
                try:
                    response = await client.post(
                        f"{AGENTS['mental-models']}/api/mental-models/generate-all",
                        json={"entity_id": request.subject},
                        timeout=30.0
                    )
                    if response.status_code == 200:
                        result["mental_models"] = response.json()
                except Exception as e:
                    print(f"Warning: Mental models failed: {e}")

            # Step 4: Questions 생성 (선택)
            if request.include_questions and result["curriculum"]:
                try:
                    response = await client.post(
                        f"{AGENTS['questions']}/api/questions/generate",
                        json={
                            "entity_id": request.subject,
                            "count": 5,
                            "difficulty_levels": ["easy", "medium", "hard"]
                        },
                        timeout=30.0
                    )
                    if response.status_code == 200:
                        result["questions"] = response.json()
                except Exception as e:
                    print(f"Warning: Question generation failed: {e}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow error: {str(e)}")


# ========== Proxy Routes (에이전트 API 직접 호출) ==========

@app.api_route("/proxy/{agent}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(agent: str, path: str, request: Request):
    """
    에이전트 API 프록시
    사용: /proxy/curriculum/api/curriculum/status
    """
    if agent not in AGENTS:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent}")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            url = f"{AGENTS[agent]}/{path}"

            # GET 요청인 경우 body 없음
            body = None
            if request.method in ["POST", "PUT"]:
                try:
                    body = await request.json()
                except Exception:
                    body = None

            response = await client.request(
                method=request.method,
                url=url,
                json=body,
                params=request.query_params if request.method == "GET" else None,
                timeout=120.0
            )

            try:
                response_data = response.json()
                return response_data
            except Exception as json_error:
                # If JSON parsing fails, return raw content
                print(f"Failed to parse JSON from {url}: {json_error}")
                print(f"Response status: {response.status_code}, content: {response.text[:200]}")
                return {"status": "error", "detail": f"Failed to parse response: {str(json_error)}"}
    except httpx.ConnectError as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"Proxy error for {agent}/{path}: {error_msg}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
