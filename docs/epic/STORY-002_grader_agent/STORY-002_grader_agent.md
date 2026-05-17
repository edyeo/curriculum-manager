# STORY-002: Grader Agent

## 개요

| 항목 | 내용 |
|---|---|
| Epic | [EPIC-001](../EPIC-001_student_platform.md) |
| 컴포넌트 | agent-platform/agents/grader |
| 목표 | 주관식/서술형 문제 LLM 채점을 담당하는 독립 에이전트 구축 |

---

## 배경

student-platform/backend는 LLM을 직접 호출하지 않는다. 주관식·서술형 답안 채점은 이 grader 에이전트에 위임한다. 객관식(MULTIPLE_CHOICE)은 student-platform/backend가 자체적으로 정답 비교로 처리한다.

기존 에이전트(curriculum-manager, researcher 등)와 동일한 FastAPI 패턴을 따르며, API Gateway를 통해 노출된다.

---

## 아키텍처

```
student-platform/backend
    POST GATEWAY_URL/grade
        → api-gateway
            → grader:8005 POST /grade
                → Claude API (LLM 채점)
```

---

## Tickets

| Ticket | 제목 |
|---|---|
| [TICKET-001](TICKET-001_grader_scaffold.md) | Grader 에이전트 FastAPI 뼈대 |
| [TICKET-002](TICKET-002_grading_logic.md) | Claude API 기반 채점 로직 |
| [TICKET-003](TICKET-003_gateway_grader_route.md) | API Gateway grader 라우팅 추가 |
| [TICKET-004](TICKET-004_docker_grader.md) | docker-compose grader 서비스 추가 |

---

## 완료 기준

- [ ] `POST /grade` — 채점 요청을 받아 is_correct, score, feedback 반환
- [ ] `GET /health` — 헬스체크
- [ ] Gateway `/grade` 경로로 라우팅됨
- [ ] MULTIPLE_CHOICE 타입은 LLM 없이 자체 비교로 처리
- [ ] docker-compose에서 grader 서비스 기동 확인
