# [EPIC-005] Question Bank — Technical Spec

## 1. 범위 요약

| 컴포넌트 | 작업 유형 | 설명 |
|---|---|---|
| `contents-manager/backend` | 기존 확장 + 신규 | unpublish / archive / delete 제약 추가, 필터 확장 |
| `contents-manager/frontend` | 신규 탭 | QuestionBankTab (마스터-디테일 레이아웃) |
| `student-platform/backend` | 신규 라우트 | published 문항 조회·상세·제출 API |
| `student-platform/frontend` | 신규 라우트 | `/questions` 탐색 + 문제 풀기 화면 |
| `agent-platform/infra` | 설정 없음 | Grader 에이전트는 기존 EPIC-002 그대로 사용 |

---

## 2. Backend — Curriculum Manager (`contents-manager/backend`)

### 2.1 기존 엔드포인트 확장

#### `GET /api/question-workbench/questions`
기존 필터 파라미터에 `question_type`, `difficulty` 추가.

```
query params:
  blueprint_id  : str  (선택)
  entity_id     : str  (선택)
  status        : str  (선택) — draft | published | archived
  question_type : str  (선택) — MCQ | OX | short_answer
  difficulty    : str  (선택) — easy | medium | hard
```

`QuestionItem` 모델에 `question_type`, `difficulty` 컬럼이 없으면 마이그레이션 필요.

#### `DELETE /api/question-workbench/questions/{id}`
기존: 상태 제약 없이 삭제 가능.  
변경: `status == "published"` 이면 `HTTP 409` 반환.

```python
if qi.status == "published":
    raise HTTPException(409, "Published questions must be archived before deletion")
```

### 2.2 신규 엔드포인트

#### `GET /api/question-workbench/questions/{id}`
단건 상세 조회. `_question_to_dict` 그대로 반환.

#### `POST /api/question-workbench/questions/{id}/unpublish`
```
전이: published → draft
선행 조건: status == "published"
오류: 400 if status != "published"
```

#### `POST /api/question-workbench/questions/{id}/archive`
```
전이: published → archived
선행 조건: status == "published"
오류: 400 if status != "published"
```

### 2.3 상태 전이 다이어그램

```
draft ──[publish]──► published ──[unpublish]──► draft
                          │
                      [archive]
                          ▼
                       archived
                          │
                       [delete]  (hard delete)
draft ──────────────────[delete]
```

`published` → `deleted` 직접 전이는 허용하지 않는다.

### 2.4 QuestionItem 모델 확장

`question_type`과 `difficulty`가 기존 모델에 없는 경우 다음 컬럼을 추가한다.

```python
question_type = Column(String, default="MCQ")   # MCQ | OX | short_answer
difficulty    = Column(String, default="medium") # easy | medium | hard
```

Alembic 마이그레이션 스크립트 작성 필요.

---

## 3. Backend — Student Platform (`student-platform/backend`)

### 3.1 신규 라우트: `routes/questions.py`

Gateway를 경유하여 Curriculum Manager의 `QuestionItem`에 접근한다.  
Student Platform 자체 DB에는 `QuestionItem`을 복제하지 않는다.

#### `GET /api/questions/published`
```
query params:
  blueprint_id  : str  (선택)
  difficulty    : str  (선택)
  question_type : str  (선택)

응답:
  { "questions": [ QuestionSummary, ... ] }

QuestionSummary:
  id, question_text(앞 50자), difficulty, question_type, blueprint_id
  — correct_answer 필드 제외
```

내부 동작: API Gateway → `GET /api/question-workbench/questions?status=published&...`

#### `GET /api/questions/{id}`
```
응답: QuestionDetail (correct_answer 필드 제외)
  id, question_text, options(text + rationale), explanation, difficulty,
  question_type, blueprint_id, node_snapshot 요약
```

#### `POST /api/questions/{id}/submit`
```
요청: { "answer": str }

응답: {
  "is_correct": bool,
  "correct_answer": str,
  "selected_rationale": str,
  "explanation": str,
  "elapsed_ms": int
}
```

내부 동작:
1. Gateway → `GET /api/question-workbench/questions/{id}` (정답 포함)
2. Grader 에이전트 채점 (기존 EPIC-002 Grader 재사용)
3. `StudyAttempt` 테이블에 결과 기록
4. 클라이언트에 결과 반환 (정답 포함)

### 3.2 StudyAttempt 테이블

```sql
CREATE TABLE study_attempt (
  id            UUID PRIMARY KEY,
  user_id       UUID NOT NULL REFERENCES users(id),
  question_id   UUID NOT NULL,
  answer        TEXT NOT NULL,
  is_correct    BOOLEAN NOT NULL,
  elapsed_ms    INTEGER,
  created_at    TIMESTAMP DEFAULT now()
);
```

---

## 4. Frontend — Curriculum Manager (`contents-manager/frontend`)

### 4.1 신규 파일: `src/components/QuestionBankTab.jsx`

마스터-디테일 레이아웃. 좌측 240px 고정 패널(필터 + 카드 목록), 우측 나머지(상세 패널).

**상태:**
```js
filters: { blueprint_id, entity_name, question_type, difficulty, status }
questions: QuestionItem[]
selectedId: string | null
editMode: boolean
```

**주요 컴포넌트 분해:**
- `FilterBar` — 5개 필터 컨트롤
- `QuestionCard` — 지문 60자 미리보기, 배지들
- `QuestionDetail` — 전체 지문, 선지, rationale, 해설, node_snapshot 요약
- `LifecycleButtons` — 상태별 조건부 버튼 렌더링

**LifecycleButtons 로직:**
```
status === "draft"     → [출제 등록], [삭제(활성)]
status === "published" → [공개 취소], [보관], [삭제(비활성, 툴팁)]
status === "archived"  → [삭제(활성)]
```

### 4.2 App.jsx 변경

```jsx
// tabs 배열에 추가
['question-bank', '문제조회'],

// 탭 렌더 추가
{currentTab === 'question-bank' && <QuestionBankTab />}
```

### 4.3 contentsApi.js 확장

```js
export const getQuestion = (id) =>
  api.get(`/question-workbench/questions/${id}`)

export const unpublishQuestion = (id) =>
  api.post(`/question-workbench/questions/${id}/unpublish`)

export const archiveQuestion = (id) =>
  api.post(`/question-workbench/questions/${id}/archive`)

export const deleteQuestion = (id) =>
  api.delete(`/question-workbench/questions/${id}`)
```

---

## 5. Frontend — Student Platform (`student-platform/frontend`)

### 5.1 신규 라우트: `/questions`

`src/pages/QuestionBrowsePage.jsx`

**구성:**
- 상단: Blueprint / 난이도 / 문제 타입 필터
- 본문: published 문항 카드 목록 (50자 미리보기, 난이도 배지, Blueprint 이름)
- 카드 클릭 → `/questions/:id` 로 이동

### 5.2 신규 라우트: `/questions/:id`

`src/pages/QuestionSolvePage.jsx`

**구성:**
- 지문 전체 표시
- 답안 입력 UI (MCQ / OX / 단답형 분기)
- [제출] → `POST /api/questions/{id}/submit`
- 채점 결과 표시 (정답 강조, rationale, 해설)
- [다음 문제] → 같은 Blueprint·난이도 다음 문항

**정답 보안:** `/questions/:id` 조회 응답에 `correct_answer` 미포함. 제출 응답에서만 공개.

---

## 6. API Gateway 라우팅 추가

Student Platform → Curriculum Manager 문항 접근을 위한 Gateway 프록시 규칙 추가.

```
GET  /cm/question-workbench/questions         → contents-manager-backend:8010
GET  /cm/question-workbench/questions/{id}    → contents-manager-backend:8010
```

인증: Student Platform 서비스 토큰 (기존 Gateway 인증 체계 준용).

---

## 7. 구현 순서 (권장)

1. **Backend CM 확장** — `question_workbench.py`에 신규 엔드포인트 추가, DELETE 제약 수정, 모델 마이그레이션
2. **Frontend CM 탭** — `QuestionBankTab.jsx` 구현, `App.jsx` 등록
3. **Backend SP** — `routes/questions.py` 신규 작성, `StudyAttempt` 마이그레이션
4. **Frontend SP** — `QuestionBrowsePage`, `QuestionSolvePage` 구현
5. **Gateway** — 프록시 규칙 추가
6. **E2E 테스트** — 출제 등록 → 학생 탐색 → 제출 → 이력 기록 전체 흐름 검증

---

## 8. 테스트 시나리오

| # | 시나리오 | 검증 포인트 |
|---|---|---|
| T1 | draft 문항 출제 등록 | status → published, 학생 조회 목록에 노출 |
| T2 | published 문항 직접 삭제 시도 | HTTP 409 반환 |
| T3 | published 문항 archive 후 삭제 | HTTP 204 정상 |
| T4 | 학생 `/questions` 조회 | draft/archived 미노출, published만 노출 |
| T5 | 학생 문제 풀기 — 정답 | is_correct=true, rationale, 해설 반환 |
| T6 | 학생 문제 풀기 — 오답 | is_correct=false, 정답 강조 표시 |
| T7 | 답안 제출 후 StudyAttempt 기록 | DB에 row 생성, 마스터리 대시보드 반영 |
| T8 | 문항 상세 조회 (학생) | correct_answer 필드 미포함 확인 |
