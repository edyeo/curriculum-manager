# TICKET-001: Grader 에이전트 FastAPI 뼈대

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | agent-platform/agents/grader |
| 파일 | `agent-platform/agents/grader/` (신규 디렉토리) |
| 의존 | 없음 |
| 선행 조건 | 없음 |

---

## 배경

기존 에이전트(researcher 등)와 동일한 구조로 grader 에이전트 디렉토리를 구성한다. 채점 로직은 TICKET-002에서 구현하고, 여기서는 뼈대와 요청/응답 스키마만 확정한다.

---

## 작업 내용

### 디렉토리 구조

```
agent-platform/agents/grader/
├── main.py
├── requirements.txt
└── Dockerfile
```

### `main.py`

```python
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Literal

app = FastAPI(title="Grader Agent")

class GradeRequest(BaseModel):
    question_type: Literal["MULTIPLE_CHOICE", "SHORT_ANSWER", "DESCRIPTIVE"]
    question_text: str
    correct_answer: str
    user_answer: str
    explanation: str = ""      # 채점 참고용 해설 (선택)

class GradeResponse(BaseModel):
    is_correct: bool
    score: float               # 0.0 ~ 1.0
    feedback: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/grade", response_model=GradeResponse)
async def grade(req: GradeRequest) -> GradeResponse:
    ...  # TICKET-002에서 구현
```

### `requirements.txt`

```
fastapi
uvicorn
anthropic
pydantic
```

---

## 완료 기준

- [ ] `GET /health` 200 반환
- [ ] `POST /grade` 엔드포인트 존재 (로직은 stub)
- [ ] GradeRequest / GradeResponse 스키마 확정
- [ ] `uvicorn main:app --port 8005`로 기동 확인
