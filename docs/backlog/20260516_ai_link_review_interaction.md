# AI Link 생성 결과 검토 및 승인 기능 (2026-05-16)

## 배경

현재 `link 추가(AI)` 실행 시 AI가 생성한 엣지가 즉시 그래프에 반영된다.
사용자가 생성 결과를 확인하고 선택적으로 승인할 수 있는 검토 단계가 없어,
의도하지 않은 엣지가 추가될 수 있다.

---

## 기능 요건

### 흐름 변경

**현재**
```
조건 입력 → AI Link 생성 → 즉시 저장
```

**변경 후**
```
조건 입력 → AI Link 생성 → 결과 검토 모달 → 승인 → 저장
```

### 결과 검토 모달

AI가 엣지 목록을 생성하면 기존 `AiLinkModal`이 결과 테이블로 전환된다.

**테이블 컬럼**

| 선택 | Source 노드 | Edge 타입 | Target 노드 | 근거 (logic_basis) |
|---|---|---|---|---|
| ☑ | [타입·D{depth}] 이름 | relation_type | [타입·D{depth}] 이름 | 1-2문장 |

- 행 단위 체크박스로 개별 선택/해제 가능
- 전체 선택/해제 토글
- 기본값: 전체 선택

**하단 액션**

- `[취소]` — 모달 닫기, 아무것도 저장하지 않음
- `[N개 엣지 승인]` — 선택된 행만 저장 (N은 선택 수 동적 표시)

### 공통 동작

- 승인 전까지 edges state에 반영되지 않음
- 승인 후 즉시 GraphView에 반영
- 생성된 엣지가 0개인 경우: "생성된 엣지가 없습니다" 메시지 + 닫기만 표시

---

## 구현 계획

### 레이어 구조 변경

현재 `/curriculum/link-ai` 는 생성 즉시 저장한다.
검토 기능을 위해 **생성과 저장을 분리**해야 한다.

```
[생성 단계]  조건 → AI 생성 → 후보 엣지 목록 반환 (저장 안 함)
[승인 단계]  선택된 엣지 목록 → 저장
```

### Step 1: agent-platform — 생성/저장 분리

**`harness.py`**: `trigger_link_ai_preview()` 추가
- 기존 `trigger_link_ai()`와 동일하되 `save_edges()` 호출하지 않음
- 생성된 후보 엣지 목록만 반환

**`routes.py`**: `POST /generate/link-ai/preview` 엔드포인트 추가
- Response: 후보 엣지 목록 (id, source_id, source_name, target_id, target_name, relation_type, logic_basis)

**`routes.py`**: `POST /generate/link-ai/confirm` 엔드포인트 추가
- Request: 승인된 엣지 목록 (엣지 객체 배열)
- 전달받은 엣지만 `save_edges()` 호출로 저장

---

### Step 2: gateway_client.py — 프리뷰/확정 함수 추가

```python
async def preview_ai_link(payload: dict) -> dict:
    # POST /proxy/curriculum/api/curriculum/generate/link-ai/preview

async def confirm_ai_link(edges: list) -> dict:
    # POST /proxy/curriculum/api/curriculum/generate/link-ai/confirm
```

---

### Step 3: backend nodes.py — 엔드포인트 추가

```
POST /subjects/{id}/curriculum/link-ai/preview
  → AI 생성 후보 엣지 목록 반환 (저장 없음)
  → Response: { "edges": [ { id, source_id, source_name, target_id, target_name, relation_type, logic_basis } ] }

POST /subjects/{id}/curriculum/link-ai/confirm
  → 승인된 엣지만 저장 → SubjectEdge 등록
  → Request: { "edges": [ Edge 객체 배열 ] }
  → Response: { "edges_saved": N }
```

---

### Step 4: contentsApi.js — API 함수 추가

```js
export const previewAiLink = (subjectId, payload) =>
  fetch(`/api/subjects/${subjectId}/curriculum/link-ai/preview`, { ... })

export const confirmAiLink = (subjectId, edges) =>
  fetch(`/api/subjects/${subjectId}/curriculum/link-ai/confirm`, { ... })
```

---

### Step 5: AiLinkModal.jsx — 단계 전환 UX

모달 내부에 두 단계를 상태로 관리:

```
phase: 'form'    → 조건 입력 화면 (현재)
phase: 'review'  → 결과 검토 테이블
```

**`form` 단계** (현재와 동일)
- 조건 입력 후 `AI Link 생성` 클릭 → `preview` API 호출 → `review` 단계로 전환

**`review` 단계**
- 후보 엣지 테이블 표시 (체크박스 포함)
- `[취소]` / `[N개 엣지 승인]` 버튼
- 승인 클릭 → 선택된 엣지만 `confirm` API 호출 → edges state 갱신 → 모달 닫기

---

### Step 6: App.jsx — 핸들러 분리

```js
handleAiLinkPreview(payload)  // previewAiLink() 호출, 결과를 모달로 전달
handleAiLinkConfirm(edges)    // confirmAiLink() 호출, edges state 갱신
```

---

## 완료 기준

- [ ] `preview` API: 저장 없이 후보 엣지 목록만 반환
- [ ] `confirm` API: 선택된 엣지만 저장
- [ ] 결과 테이블: source·target 노드 이름 + edge 타입 + logic_basis 표시
- [ ] 체크박스 행 단위 선택/해제 동작
- [ ] 전체 선택/해제 토글
- [ ] 승인 버튼에 선택 수 동적 표시 ("N개 엣지 승인")
- [ ] 0개 생성 시 빈 상태 메시지
- [ ] 취소 시 edges state 변경 없음
- [ ] 승인 후 GraphView 즉시 반영

---

## 영향 범위

- 기존 `POST /curriculum/link-ai` 엔드포인트는 유지 (하위 호환)
- 신규 `/preview`, `/confirm` 엔드포인트 추가
- `AiLinkModal`의 단계 전환 UX 변경

---

## 미결 사항

- logic_basis 텍스트가 길 경우 테이블 내 truncate 처리 방식
- preview 결과를 일시적으로 서버 세션에 캐싱할지 여부 (현재 계획: 프론트가 엣지 목록을 들고 있다가 confirm 시 전송)
