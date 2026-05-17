# EPIC-001: Student Learning Platform (Phase 1)

## 개요

| 항목 | 내용 |
|---|---|
| 목표 | 학생 학습용 독립 서비스 구축 |
| 범위 | Phase 1 — contents-manager KG API 노출 + student-platform 신규 구축 |
| 분리 원칙 | mono-repo 내 완전 독립 서비스, 추후 별도 repo 추출 용이 |

---

## 배경

contents-manager가 구축한 Knowledge Graph(Seed / Concept / TechStack 노드, requires / implemented_by / has_subtopic 엣지, 노드별 문제)를 학생이 활용해 학습하고 개념별 이해도(mastery score)를 축적하는 독립 서비스가 필요하다.

KG는 contents-manager가 편집·구축하는 독립 데이터 레이어다. student-platform은 KG를 소비하는 클라이언트이며, 향후 다른 서비스도 동일한 KG API를 통해 소비할 수 있다.

---

## 아키텍처

```
contents-manager (KG 편집·구축)
    ↓ KG_API_URL (read-only)
student-platform/backend (:8020)
    ↓ GATEWAY_URL (AI 채점)
agent-platform / grader agent (:8005)

student-platform/frontend (:3001)
    ↓ API
student-platform/backend
```

### 서비스별 데이터 소유

| 데이터 | 소유 서비스 | student-platform 접근 방식 |
|---|---|---|
| subjects | contents-manager | KG API 읽기 |
| nodes (KG) | contents-manager | KG API 읽기 |
| edges (KG) | contents-manager | KG API 읽기 |
| questions | contents-manager → question-generator | KG API 읽기 |
| Student | student-platform | 자체 DB |
| NodeMastery | student-platform | 자체 DB |
| StudySession | student-platform | 자체 DB |

### student-platform 환경변수

```
KG_API_URL=http://contents-manager-backend:8010   # KG 데이터 소스
GATEWAY_URL=http://api-gateway:9000               # AI 서비스
STUDENT_JWT_SECRET=...
```

---

## 서비스 포트

| 서비스 | 포트 | 비고 |
|---|---|---|
| contents-manager-backend | 8010 | 기존, KG API 엔드포인트 추가 |
| api-gateway | 9000 | 기존, grader 라우팅 추가 |
| grader agent | 8005 | 신규 |
| student-platform-backend | 8020 | 신규 |
| student-platform-frontend | 3001 | 신규 |

---

## Stories

| Story | 제목 | 컴포넌트 |
|---|---|---|
| [STORY-001](STORY-001_kg_read_api/STORY-001_kg_read_api.md) | KG Read API | contents-manager/backend |
| [STORY-002](STORY-002_grader_agent/STORY-002_grader_agent.md) | Grader Agent | agent-platform |
| [STORY-003](STORY-003_student_backend/STORY-003_student_backend.md) | Student Backend | student-platform/backend |
| [STORY-004](STORY-004_student_frontend/STORY-004_student_frontend.md) | Student Frontend | student-platform/frontend |

---

## 완료 기준

- [ ] 학생이 과목을 선택하고 KG 노드(Seed/Concept/TechStack)와 엣지 관계를 탐색할 수 있다
- [ ] 노드를 선택해 문제를 풀고 채점 결과(정오 + 피드백)를 받을 수 있다
- [ ] 풀이 결과가 NodeMastery에 반영되고 ConceptMap에 시각화된다
- [ ] student-platform은 KG_API_URL 변경만으로 다른 KG 소스를 가리킬 수 있다
- [ ] student-platform/backend는 LLM을 직접 호출하지 않는다
