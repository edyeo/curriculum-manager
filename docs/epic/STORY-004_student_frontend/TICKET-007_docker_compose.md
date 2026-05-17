# TICKET-007: docker-compose — student-frontend 추가

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | agent-platform/infra |
| 파일 | `agent-platform/infra/docker-compose.local.yml` |
| 의존 | STORY-003 TICKET-006 |
| 선행 조건 | student-platform/frontend Dockerfile 완성 |

---

## 작업 내용

### `docker-compose.local.yml`에 추가

```yaml
student-platform-frontend:
  build:
    context: ../../student-platform/frontend
    dockerfile: Dockerfile
  container_name: student-platform-frontend
  ports:
    - "3001:3001"
  depends_on:
    - student-platform-backend
  environment:
    VITE_API_BASE_URL: http://student-platform-backend:8020
  healthcheck:
    test: ["CMD", "wget", "-q", "--spider", "http://localhost:3001"]
    interval: 10s
    timeout: 5s
    retries: 3
```

### `student-platform/frontend/Dockerfile`

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
RUN npm install -g serve
EXPOSE 3001
CMD ["serve", "-s", "dist", "-l", "3001"]
```

---

## 완료 기준

- [ ] `docker compose up student-platform-frontend` 기동 확인
- [ ] `http://localhost:3001` 접근 시 학생 로그인 화면 표시
- [ ] `/api/*` 요청이 student-platform-backend:8020으로 라우팅됨
