# AI Link 추가 기능 (2026-05-16)

## 배경

현재 T2 LINK는 `source_type` + `target_type` 단위로 전체 노드 간 엣지를 일괄 생성한다.
편집 탭에서 사용자가 직접 링크 조건을 지정하고 AI가 엣지를 생성하는 수동 트리거 기능이 없음.

### 현재 링크 구조의 한계

- EXPAND로 추가된 새 노드는 `source_id in new_node_ids` 조건으로 인해 child(target)가 될 수 없음
- T2 LINK는 타입 단위만 지원 — depth 단위 필터링 불가
- 특정 노드를 source로 고정한 링크 생성 불가

---

## 기능 요건

### 진입점

편집 탭 툴바에 **"link 추가(AI)"** 버튼 추가 → 모달 오픈

### 모드 1: 전체 node 기준

> 조건에 맞는 노드 집합 전체를 source로 삼아 링크 생성

| 입력 | 선택지 |
|---|---|
| Source 타입 | Seed / Concept / TechStack / System |
| Source depth | 1 / 2 / 3 |
| Target 타입 | Seed / Concept / TechStack / System |
| Target depth | 1 / 2 / 3 |
| Edge 타입 | has_subtopic / requires / implemented_by / relied_on |

**동작**: source 조건에 맞는 모든 노드 → target 조건에 맞는 모든 노드 간 AI 링크 생성

### 모드 2: 특정 node 기준

> 단일 source 노드를 고정하여 링크 생성

| 입력 | 선택지 |
|---|---|
| Source 노드 | 현재 subject의 노드 목록에서 선택 (이름 표시, type·depth 병기) |
| Target 타입 | Seed / Concept / TechStack / System |
| Target depth | 1 / 2 / 3 |
| Edge 타입 | has_subtopic / requires / implemented_by / relied_on |

**동작**: 선택한 단일 노드 → target 조건에 맞는 모든 노드 간 AI 링크 생성

### 공통 동작

- AI가 생성한 엣지 중 이미 존재하는 (source, target) 쌍은 중복 제거
- 생성 완료 후 edges 목록을 즉시 갱신 (새로고침 없이)
- 생성 중 로딩 상태 표시

---

## 온톨로지 valid_pairs 참고

| Edge 타입 | 허용 쌍 |
|---|---|
| `has_subtopic` | Seed→Seed, Concept→Concept, TechStack→TechStack, System→System |
| `requires` | Seed→Concept |
| `implemented_by` | Concept→TechStack |
| `relied_on` | System→Seed |

UI에서 source/target 타입 조합 기반 유효 edge 타입 자동 필터링은 v2 범위.
초기 구현에서는 모든 edge 타입을 표시.

---

## 구현 계획

### 레이어 구조

```
Frontend (AiLinkModal)
  → contentsApi.aiLinkCurriculum()
  → contents-manager backend: POST /subjects/{id}/curriculum/link-ai
  → gateway_client.link_ai_curriculum()
  → agent-platform: POST /api/curriculum/generate/link-ai
  → harness.trigger_link_ai()
  → link_graph (edge_type_constraint 주입)
```

---

### Step 1: `link_graph.py` — edge_type 제약 추가

**파일**: `agent-platform/agents/curriculum-manager/src/graphs/link_graph.py`

- `LinkState`에 `edge_type_constraint: str | None` 필드 추가 (기본값 `None`)
- `link_node`의 HumanMessage에 edge_type 제약 문구 조건부 주입
  ```
  "반드시 '{edge_type}' 타입의 엣지만 생성하세요."
  ```

---

### Step 2: `harness.py` — `trigger_link_ai()` 추가

**파일**: `agent-platform/agents/curriculum-manager/src/harness.py`

```python
def trigger_link_ai(
    self,
    source_type: str | None = None,
    source_depth: int | None = None,
    target_type: str | None = None,
    target_depth: int | None = None,
    edge_type: str | None = None,
    source_node_id: str | None = None,
) -> list[Edge]:
```

- `source_node_id` 지정 시: 해당 단일 노드를 source 목록으로 사용 (모드 2)
- `source_node_id` 없을 시: type + depth로 source 노드 필터링 (모드 1)
- target: type + depth로 필터링
- link_graph 호출 시 `edge_type_constraint` 전달
- 기존 엣지와 중복 제거 후 `save_edges()` 호출
- 신규 엣지 목록 반환

---

### Step 3: `routes.py` — 새 엔드포인트 추가

**파일**: `agent-platform/apps/curriculum_manager/routes.py`

```
POST /api/curriculum/generate/link-ai
```

Request body:
```json
{
  "source_type": "Seed",        // 모드 1 (source_node_id 없을 때)
  "source_depth": 1,            // 모드 1
  "source_node_id": "uuid",     // 모드 2 (source_type/depth 대신)
  "target_type": "Concept",
  "target_depth": 1,
  "edge_type": "requires"
}
```

Response:
```json
{
  "status": "success",
  "message": "...",
  "data": { "edges_added": 3, "total_edges": 42 }
}
```

---

### Step 4: `gateway_client.py` — 프록시 함수 추가

**파일**: `contents-manager/backend/gateway_client.py`

```python
async def link_ai_curriculum(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            f"{GATEWAY_URL}/proxy/curriculum/api/curriculum/generate/link-ai",
            json=payload,
        )
        r.raise_for_status()
        return r.json()
```

---

### Step 5: `nodes.py` — 백엔드 엔드포인트 추가

**파일**: `contents-manager/backend/routes/nodes.py`

```
POST /subjects/{subject_id}/curriculum/link-ai
```

- 기존 엣지 ID 스냅샷 → `gateway_client.link_ai_curriculum(payload)` 호출
- 신규 엣지 ID를 `SubjectEdge` 테이블에 등록
- Response: `{ "edges_added": N }`

---

### Step 6: `contentsApi.js` — API 함수 추가

**파일**: `contents-manager/frontend/src/services/contentsApi.js`

```js
export const aiLinkCurriculum = (subjectId, payload) =>
  fetch(`${BASE}/subjects/${subjectId}/curriculum/link-ai`, {
    method: 'POST', headers: headers(), body: JSON.stringify(payload)
  }).then(handle)
```

---

### Step 7: `AiLinkModal.jsx` — 모달 컴포넌트 신규 생성

**파일**: `contents-manager/frontend/src/components/AiLinkModal.jsx`

구성:
- 상단: 모드 토글 ("전체 node 기준" / "특정 node 기준")
- 모드 1 폼: Source 타입 select + depth select, Target 타입 select + depth select, Edge 타입 select
- 모드 2 폼: Source 노드 select (nodes 목록, `[타입·D{depth}] 이름` 형식), Target 타입 select + depth select, Edge 타입 select
- 하단: [취소] [AI Link 생성] 버튼 (생성 중 로딩)
- 완료 후: "N개 엣지 추가됨" 결과 표시 후 닫기

---

### Step 8: `NodeTable.jsx` + `App.jsx` — UI 연결

**NodeTable.jsx**:
- 툴바에 `"link 추가(AI)"` 버튼 추가
- props: `onAiLink`, `aiLinking`

**App.jsx**:
- `showAiLink`, `aiLinking` state 추가
- `handleAiLink(payload)` 핸들러: `aiLinkCurriculum()` 호출 → edges 갱신
- `AiLinkModal` 렌더링

---

## 완료 기준

- [ ] 모드 1: 타입+depth 조합으로 AI 링크 생성 성공
- [ ] 모드 2: 특정 노드 선택 후 AI 링크 생성 성공
- [ ] 중복 엣지 미생성 확인
- [ ] 생성 완료 후 GraphView 즉시 반영
- [ ] edge_type 제약이 LLM 프롬프트에 반영됨 확인

---

## v2 범위 (이번 구현 제외)

- UI에서 source/target 타입 조합 기반 valid edge 타입 자동 필터링
- 생성된 엣지 온톨로지 위반 시 경고 메시지
- 모드 2에서 source 노드 이름 검색/필터링
