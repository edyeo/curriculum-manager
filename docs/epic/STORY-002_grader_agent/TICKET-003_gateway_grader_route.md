# TICKET-003: API Gateway — grader 라우팅 추가

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | agent-platform/agents/gateway |
| 파일 | `agent-platform/agents/gateway/` (기존) |
| 의존 | TICKET-001 |
| 선행 조건 | TICKET-001 완료 |

---

## 배경

student-platform/backend는 `GATEWAY_URL/grade`로 채점을 요청한다. API Gateway가 이 요청을 grader 에이전트(:8005)로 프록시해야 한다.

---

## 작업 내용

### 1. Gateway 환경변수 추가

`docker-compose.local.yml`:

```yaml
gateway:
  environment:
    GRADER_URL: http://grader:8005
```

### 2. Gateway 라우팅 추가

기존 gateway 코드에서 라우팅 추가 (구체적 파일은 gateway 구현 방식에 따름):

```
POST /grade  →  GRADER_URL/grade  (프록시)
```

### 3. grader 의존성 추가

```yaml
gateway:
  depends_on:
    - grader
```

---

## 완료 기준

- [ ] `POST GATEWAY_URL/grade` 요청이 grader:8005/grade로 프록시됨
- [ ] gateway 기동 시 grader 헬스체크 포함
- [ ] 기존 라우팅(/curriculum, /research 등)에 영향 없음
