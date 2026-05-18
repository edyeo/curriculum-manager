# [PRD] Question Bank

## 1. 개요 (Overview)

[EPIC-003](../EPIC-003_question_generator_workbench/PRD-question_generator_workbench.md)에서 생성·등록된 문항을 관리자가 열람·편집·상태 관리할 수 있는 **Question Bank 조회 탭**과, 학생이 등록된 문항을 탐색하고 실제로 풀 수 있는 **Student Question Solver**를 제공하는 EPIC.

출제된 문항의 생애주기(draft → published → archived)를 관리하고, 학습자가 실전에서 문제를 접할 수 있는 end-to-end 흐름을 완성한다.

> **의존:** EPIC-003 문항 생성 워크벤치가 완성된 이후 진행한다.

---

## 2. 제품 원칙 (Product Principles)

**Single Source of Truth:** 문항 데이터는 `QuestionItem` 테이블 하나가 정본이며, Curriculum Manager와 Student Platform이 동일한 소스를 참조한다. 단, 학생에게 노출되는 데이터는 `published` 상태의 문항으로만 한정한다.

**Auditability:** 문항의 생성 경로(어떤 entity, 어떤 Blueprint)와 편집 이력이 항상 추적 가능해야 한다. `node_snapshot`의 de-normalization 설계를 그대로 유지한다.

**Human Gate:** `draft` 상태의 문항은 학생에게 노출되지 않는다. 관리자의 명시적 publish 액션이 있어야만 학생에게 공개된다.

---

## 3. 핵심 기능 명세 (Feature Specifications)

### Feature 5.1: Question Bank 조회 탭 (Question Bank Browser)

**상세 설명:** Curriculum Manager `contents-manager/frontend`에 **문제조회** 탭을 추가한다. 등록된 문항 전체를 목록으로 조회하고, 좌측 목록에서 문항을 선택하면 우측 패널에 상세 정보가 표시되는 마스터-디테일(Master-Detail) 레이아웃.

**레이아웃:**

```
┌────────────────────┬──────────────────────────────────────┐
│  필터 + 문항 목록   │  선택된 문항 상세                     │
│  (좌측 패널)        │  (우측 패널)                         │
│                    │                                      │
│  [Blueprint ▼]     │  [지문]                              │
│  [Entity ▼]        │  [선지 A/B/C/D + rationale]         │
│  [타입 ▼]          │  [정답] [해설]                        │
│  [난이도 ▼]        │  [node_snapshot 메타데이터]           │
│  [상태 ▼]          │  [Blueprint / 생성일 / 상태 배지]     │
│                    │                                      │
│  ─────────────     │                                      │
│  문항 카드 목록     │                                      │
│  (클릭 → 선택)     │                                      │
└────────────────────┴──────────────────────────────────────┘
```

**필터 항목:**
- Blueprint (드롭다운, 전체/특정 Blueprint)
- Entity 이름 (텍스트 검색)
- 문제 타입 (MCQ / O/X / 단답형 / 전체)
- 난이도 (easy / medium / hard / 전체)
- 상태 (draft / published / archived / 전체)

**문항 목록 카드:** 지문 앞 60자, 난이도 배지, 타입, 상태, 생성일 표시.

**비즈니스 가치:** 출제위원이 기 생성된 문항 전체를 한 화면에서 파악하고, 미완성(draft) 문항과 등록(published) 문항을 구분하여 관리할 수 있음.

**인수 조건 (Acceptance Criteria):**

- Blueprint / 상태 / 난이도 필터를 조합하여 문항을 동적으로 필터링할 수 있어야 한다.
- 문항 목록에서 행을 클릭하면 우측 상세 패널에 전체 정보(지문, 선지, rationale, 해설, node_snapshot 요약, 생성 파라미터)가 표시되어야 한다.
- 문항이 없는 경우 빈 상태 메시지와 EPIC-003 워크벤치로 이동하는 안내를 표시한다.

---

### Feature 5.2: 문항 편집·삭제·상태 관리 (Question Lifecycle Management)

**상세 설명:** 우측 상세 패널에서 선택된 문항의 내용을 수정하거나 상태를 변경하고 삭제할 수 있는 기능.

**지원 액션:**

| 액션 | 조건 | 설명 |
|---|---|---|
| 편집 저장 | draft / published 모두 가능 | 지문·선지·해설 텍스트 인라인 편집 후 저장 |
| 출제 등록 (Publish) | draft → published | 학생에게 문항 공개 |
| 공개 취소 (Unpublish) | published → draft | 학생 노출 차단, 재편집 가능 상태로 전환 |
| 보관 (Archive) | published → archived | 더 이상 학생에게 노출하지 않으나 이력 보존 |
| 삭제 | draft / archived 만 허용 | hard delete. published 문항은 archive 후 삭제 |

**비즈니스 가치:** AI 생성 오류나 내용 변경 시 즉각 수정·회수할 수 있어 문항 품질을 지속 유지할 수 있음.

**인수 조건 (Acceptance Criteria):**

- 지문·선지·해설 텍스트가 상세 패널에서 직접 편집 가능하고, 저장 시 즉시 목록에 반영된다.
- published 상태의 문항은 삭제 버튼이 비활성화되며, archive 후에만 삭제할 수 있다.
- 상태 변경(publish / unpublish / archive) 후 목록 카드의 상태 배지가 즉시 갱신된다.

---

### Feature 5.3: Student Platform 문제 탐색 및 풀기 (Student Question Solver)

**상세 설명:** Student Platform(`student-platform/frontend`)에서 출제 등록(published)된 문항을 탐색하고 선택하여 풀 수 있는 기능. 기존 EPIC-001의 문제 풀기 플로우를 확장하여 **문항 선택 자유도**를 추가한다.

**기존 EPIC-001 플로우:**
> 커리큘럼 맵 노드 클릭 → 해당 entity의 추천 문제 1개 자동 제시 → 풀기

**EPIC-005 추가 플로우:**
> 문제 탐색 화면 → Blueprint / 난이도 필터 → 문항 카드 목록 → 문항 선택 → 풀기 → 채점·rationale 확인

**문제 탐색 화면 구성:**
- 상단: Blueprint 필터, 난이도 필터, 문제 타입 필터
- 본문: published 문항 카드 목록 (지문 앞 50자, 난이도 배지, Blueprint 이름)
- 카드 클릭 → 문제 풀기 화면으로 이동

**문제 풀기 화면 구성:**
- 지문 전체 표시
- 선지 (MCQ: A/B/C/D 라디오, O/X: 두 버튼, 단답형: 텍스트 입력)
- [제출] 버튼 → 채점 API 호출
- 채점 후: 정답 여부, 정답 강조, 선택 선지의 rationale, 종합 해설 표시
- [다음 문제] 버튼 → 같은 Blueprint·난이도의 다음 문항으로 이동

**비즈니스 가치:** 커리큘럼 맵 중심의 수동 학습 외에도, 학습자가 자신의 취약 Blueprint 영역에 집중하여 문제를 자기주도적으로 풀 수 있어 학습 효율이 높아짐.

**인수 조건 (Acceptance Criteria):**

- published 상태의 문항만 학생에게 노출된다. draft / archived 문항은 조회되지 않는다.
- Blueprint / 난이도 필터 조합으로 문항을 탐색할 수 있어야 한다.
- 답안 제출 시 Grader 에이전트를 통해 정답 여부를 채점하고, 선택 선지의 rationale을 즉시 표시해야 한다.
- 풀이 결과(정답·오답·소요 시간)는 학습 이력 DB에 기록되어 마스터리 대시보드에 반영된다.

---

## 4. API 요구사항 (API Requirements)

### Curriculum Manager Backend (`contents-manager/backend`)

| Method | Path | 설명 | 신규/기존 |
|---|---|---|---|
| `GET` | `/api/question-workbench/questions` | 문항 목록 (필터 파라미터 확장) | 기존 확장 |
| `GET` | `/api/question-workbench/questions/{id}` | 문항 상세 | 신규 |
| `PATCH` | `/api/question-workbench/questions/{id}` | 문항 편집 | 기존 |
| `POST` | `/api/question-workbench/questions/{id}/publish` | published 전환 | 기존 |
| `POST` | `/api/question-workbench/questions/{id}/unpublish` | draft 전환 | 신규 |
| `POST` | `/api/question-workbench/questions/{id}/archive` | archived 전환 | 신규 |
| `DELETE` | `/api/question-workbench/questions/{id}` | hard delete (draft/archived만) | 신규 |

### Student Platform Backend (`student-platform/backend`)

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/api/questions/published` | published 문항 목록 (blueprint_id / difficulty / type 필터) |
| `GET` | `/api/questions/{id}` | 문항 상세 (정답 필드 제외) |
| `POST` | `/api/questions/{id}/submit` | 답안 제출 → Grader 채점 → 정답+rationale 반환 |

---

## 5. 제약사항 및 비기능 요구사항 (Technical Constraints)

**정답 보안:** Student Platform의 `GET /api/questions/{id}` 응답에는 `correct_answer` 필드를 포함하지 않는다. 정답은 `/submit` 응답에서만 반환된다.

**상태 전이 제약:** `published` → `deleted`의 직접 전이는 허용하지 않는다. 반드시 `archived`를 거쳐야 삭제할 수 있다. 이를 통해 학생 풀이 이력이 남아있는 문항이 갑자기 사라지는 것을 방지한다.

**컴포넌트 위치:**
- Curriculum Manager: `contents-manager/frontend` 내 **문제조회** 탭 신규 추가
- Student Platform: `student-platform/frontend` 내 **문제탐색** 라우트(`/questions`) 신규 추가, 기존 문제 풀기 화면 재활용

**Gateway 경유:** Student Platform → Curriculum Manager의 QuestionItem에 접근할 때는 API Gateway를 경유한다. 직접 DB 접근은 허용하지 않는다.
