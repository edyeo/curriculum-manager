# TICKET-006: docker-compose — student-backend 추가

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | agent-platform/infra |
| 파일 | `agent-platform/infra/docker-compose.local.yml` |
| 의존 | TICKET-001 |
| 선행 조건 | student-platform/backend Dockerfile 완성 |

---

## 작업 내용

### `docker-compose.local.yml`에 추가

```yaml
student-platform-backend:
  build:
    context: ../../student-platform/backend
    dockerfile: Dockerfile
  container_name: student-platform-backend
  environment:
    KG_API_URL: http://contents-manager-backend:8010
    KG_SERVICE_TOKEN: ${KG_SERVICE_TOKEN:-kg-service-secret}
    GATEWAY_URL: http://api-gateway:9000
    STUDENT_JWT_SECRET: ${STUDENT_JWT_SECRET:-student-secret-change-in-prod}
    DATABASE_URL: sqlite:////app/db/student_platform.db
  ports:
    - "8020:8020"
  depends_on:
    - contents-manager-backend
    - gateway
  volumes:
    - student_db:/app/db
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8020/health"]
    interval: 10s
    timeout: 5s
    retries: 3

volumes:
  student_db:
    driver: local
```

---

## 완료 기준

- [ ] `docker compose up student-platform-backend` 기동 확인
- [ ] `curl http://localhost:8020/health` 200 반환
- [ ] DB 볼륨 마운트로 재기동 시 데이터 유지
