# STORY-004: Student Platform Frontend

## 개요

| 항목 | 내용 |
|---|---|
| Epic | [EPIC-001](../EPIC-001_student_platform.md) |
| 컴포넌트 | student-platform/frontend |
| 목표 | 학생 학습 UI — 개념 탐색, 문제 풀기, 이해도 시각화 |

---

## 배경

contents-manager/frontend(에디터용)와 완전히 독립된 React + Vite 앱. student-platform/backend(:8020)만 바라보며 학습 흐름 전체를 담당한다.

---

## 화면 흐름

```
[로그인 / 가입]
      ↓
[과목 선택]
      ↓
[ConceptMap]  ← Seed/Concept/TechStack 노드 + 엣지
              ← 노드별 mastery 색상 (빨강→노랑→초록)
      ↓ (노드 클릭 → 문제 선택)
[QuestionSolver]  ← 객관식 or 주관식
      ↓ (제출)
[ResultView]  ← 정오 + 피드백 + mastery 변화 (before/after)
      ↓
[추천 배너]  ← 다음 노드/문제 추천
      ↓
다시 [ConceptMap] 또는 [QuestionSolver]
```

---

## Tickets

| Ticket | 제목 |
|---|---|
| [TICKET-001](TICKET-001_vite_scaffold.md) | Vite 프로젝트 구조 및 API 클라이언트 |
| [TICKET-002](TICKET-002_auth_pages.md) | 로그인 / 가입 페이지 |
| [TICKET-003](TICKET-003_concept_map.md) | ConceptMap — 노드/엣지/mastery 시각화 |
| [TICKET-004](TICKET-004_question_solver.md) | QuestionSolver — 문제 풀기 |
| [TICKET-005](TICKET-005_result_view.md) | ResultView — 채점 결과 + mastery 변화 |
| [TICKET-006](TICKET-006_mastery_dashboard.md) | MasteryDashboard — 전체 이해도 현황 |
| [TICKET-007](TICKET-007_docker_compose.md) | docker-compose student-frontend 추가 |

---

## 완료 기준

- [ ] 학생이 로그인 후 과목을 선택할 수 있다
- [ ] ConceptMap에서 Seed/Concept/TechStack 노드와 관계 엣지를 볼 수 있다
- [ ] 노드별 mastery 점수가 색상으로 표시된다
- [ ] 노드 클릭 → 문제 목록 → QuestionSolver 진입 흐름이 동작한다
- [ ] 제출 후 ResultView에서 정오, 피드백, mastery 변화를 확인할 수 있다
