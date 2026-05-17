# STORY-001: KG Read API

## 개요

| 항목 | 내용 |
|---|---|
| Epic | [EPIC-001](../EPIC-001_student_platform.md) |
| 컴포넌트 | contents-manager/backend |
| 목표 | KG 데이터(subjects, nodes, edges, questions)를 외부 서비스가 읽을 수 있는 read-only API 노출 |

---

## 배경

현재 contents-manager의 모든 API는 JWT 인증(editor 사용자)을 요구한다. student-platform 등 외부 서비스가 KG 데이터를 읽을 수 있도록 서비스 간 전용 read-only 엔드포인트가 필요하다.

인증은 `X-Service-Token` 헤더 방식을 사용한다. student-platform은 이 token으로 읽기 전용 접근만 가능하며, 쓰기 권한은 없다.

---

## 노출할 엔드포인트

```
GET /kg/subjects
GET /kg/subjects/{subject_id}/nodes
GET /kg/subjects/{subject_id}/edges
GET /kg/nodes/{node_id}/questions
```

prefix `/kg`로 기존 editor API(`/api/...`)와 명확히 분리.

---

## Tickets

| Ticket | 제목 |
|---|---|
| [TICKET-001](TICKET-001_kg_service_token_auth.md) | 서비스 토큰 인증 미들웨어 |
| [TICKET-002](TICKET-002_kg_subjects_nodes_edges_endpoints.md) | subjects / nodes / edges 엔드포인트 |
| [TICKET-003](TICKET-003_kg_questions_endpoint.md) | questions 엔드포인트 |

---

## 완료 기준

- [ ] `X-Service-Token` 없는 요청은 401 반환
- [ ] `/kg/subjects` — 과목 목록 반환
- [ ] `/kg/subjects/{id}/nodes` — 노드 목록(id, type, name, depth, description) 반환
- [ ] `/kg/subjects/{id}/edges` — 엣지 목록(from, to, relation) 반환
- [ ] `/kg/nodes/{id}/questions` — 해당 노드의 문제 목록 반환
