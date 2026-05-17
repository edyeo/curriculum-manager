# TICKET-001: KG API — 서비스 토큰 인증 미들웨어

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | contents-manager/backend |
| 파일 | `contents-manager/backend/auth.py`, `contents-manager/backend/main.py` |
| 의존 | 없음 |
| 선행 조건 | 없음 |

---

## 배경

student-platform 등 서비스 간 호출에서 editor JWT 없이 KG 데이터를 읽을 수 있어야 한다. `X-Service-Token` 헤더를 검증하는 별도 의존성 함수를 추가한다.

---

## 작업 내용

### 1. 환경변수 추가

`contents-manager/backend/.env` (및 docker-compose):

```
KG_SERVICE_TOKEN=kg-service-secret-change-in-prod
```

### 2. `auth.py`에 서비스 토큰 검증 함수 추가

```python
import os
from fastapi import Header, HTTPException

KG_SERVICE_TOKEN = os.getenv("KG_SERVICE_TOKEN", "")

async def verify_service_token(x_service_token: str = Header(...)):
    if not KG_SERVICE_TOKEN or x_service_token != KG_SERVICE_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid service token")
```

### 3. `main.py`에 `/kg` 라우터 등록

```python
from routes import kg
app.include_router(kg.router)
```

### 4. `docker-compose.local.yml` 환경변수 추가

```yaml
contents-manager-backend:
  environment:
    KG_SERVICE_TOKEN: ${KG_SERVICE_TOKEN:-kg-service-secret}
```

---

## 완료 기준

- [ ] `KG_SERVICE_TOKEN` 환경변수 로드
- [ ] `X-Service-Token` 헤더 없으면 401
- [ ] 올바른 token이면 통과
- [ ] 기존 editor JWT 인증 경로에 영향 없음
