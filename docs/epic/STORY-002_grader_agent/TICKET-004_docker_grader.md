# TICKET-004: docker-compose — grader 서비스 추가

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | agent-platform/infra |
| 파일 | `agent-platform/infra/docker-compose.local.yml` |
| 의존 | TICKET-001 |
| 선행 조건 | TICKET-001 완료 |

---

## 작업 내용

### `docker-compose.local.yml`에 grader 서비스 추가

```yaml
grader:
  build:
    context: ..
    dockerfile: Dockerfile
    args:
      AGENT: grader
  container_name: grader
  environment:
    AGENT: grader
    PORT: 8005
    ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
    LOG_LEVEL: DEBUG
  ports:
    - "8005:8005"
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8005/health"]
    interval: 10s
    timeout: 5s
    retries: 3
```

### `agent-platform/infra/.env.local` 추가 항목

```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## 완료 기준

- [ ] `docker compose up grader` 로 기동 가능
- [ ] `curl http://localhost:8005/health` 200 반환
- [ ] `ANTHROPIC_API_KEY` 없으면 기동은 되되 /grade 호출 시 명확한 에러
