# EPIC-002: Blueprint Workspace — 구현 명세

## 개요

| 항목 | 내용 |
|---|---|
| Epic | EPIC-002 Blueprint Workspace |
| 컴포넌트 | contents-manager/backend + contents-manager/frontend |
| 목표 | 출제 관리자가 레이어별 인지 단계 매트릭스와 통합 항목(Z-Axis)을 설계·관리하는 워크스페이스 |
| 접근 방식 | 기존 contents-manager에 새 탭 + 백엔드 라우터 추가 (신규 서비스 없음) |

---

## Stories

| Story | 제목 | 컴포넌트 |
|---|---|---|
| STORY-001 | Blueprint Backend | contents-manager/backend |
| STORY-002 | Blueprint Frontend | contents-manager/frontend |

---

## DB 스키마

기존 `contents-manager/backend/models.py`에 3개 모델 추가.

```python
# Blueprint — 평가 기준 단위
class Blueprint(Base):
    __tablename__ = "blueprints"
    id          = Column(Text, primary_key=True)          # UUID
    name        = Column(Text, nullable=False)
    description = Column(Text)
    owner_id    = Column(Text, ForeignKey("users.id"), nullable=False)
    deleted_at  = Column(TIMESTAMP, nullable=True)        # soft delete
    created_at  = Column(TIMESTAMP, server_default=func.now())
    updated_at  = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

# MatrixCell — 레이어별 인지 단계 1행
class MatrixCell(Base):
    __tablename__ = "matrix_cells"
    id           = Column(Text, primary_key=True)         # UUID
    blueprint_id = Column(Text, ForeignKey("blueprints.id"), nullable=False)
    layer        = Column(Text, nullable=False)            # "Seed" | "Concept" | "TechStack"
    label        = Column(Text, nullable=False)            # 인지 단계 이름
    position     = Column(Integer, nullable=False)         # 레이어 내 순서 (0-based)

# IntegrationItem — 통합 항목(Z-Axis)
class IntegrationItem(Base):
    __tablename__ = "integration_items"
    id           = Column(Text, primary_key=True)         # UUID
    blueprint_id = Column(Text, ForeignKey("blueprints.id"), nullable=False)
    name         = Column(Text, nullable=False)
    # 조합 목록: JSON 배열 [{"layer": "Seed", "cell_id": "..."}]
    combinations = Column(Text, nullable=False)            # JSON string
    created_at   = Column(TIMESTAMP, server_default=func.now())
```

**기본값 seed:** Blueprint 생성 시 아래 MatrixCell 9개가 자동 삽입된다.

| layer | labels |
|---|---|
| Seed | 인식, 리스크, 통제 |
| Concept | 원리, 매핑, 대안 |
| TechStack | 스펙, 디버깅, 전환 |

---

## API 엔드포인트

라우터 파일: `contents-manager/backend/routes/blueprints.py`  
`main.py`에 `app.include_router(blueprints.router, prefix="/api")` 등록.

모든 엔드포인트는 기존 JWT 인증(`get_current_user`)을 재사용한다.

### Blueprint CRUD

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/api/blueprints` | 목록 (deleted_at IS NULL) |
| `POST` | `/api/blueprints` | 생성 + 기본 MatrixCell 9개 seed |
| `GET` | `/api/blueprints/{id}` | 단건 조회 |
| `PATCH` | `/api/blueprints/{id}` | name / description 수정 |
| `DELETE` | `/api/blueprints/{id}` | soft delete (deleted_at 설정) |

**POST /api/blueprints 요청 바디:**
```json
{ "name": "백엔드 엔지니어링 v1", "description": "..." }
```

**GET /api/blueprints 응답:**
```json
{
  "blueprints": [
    { "id": "uuid", "name": "...", "description": "...", "created_at": "..." }
  ]
}
```

**GET /api/blueprints/{id} 응답:**
```json
{
  "id": "uuid",
  "name": "...",
  "description": "...",
  "matrix": {
    "Seed":      [{ "id": "uuid", "label": "인식", "position": 0 }, ...],
    "Concept":   [...],
    "TechStack": [...]
  },
  "integrations": [
    {
      "id": "uuid",
      "name": "풀스택 아키텍팅",
      "combinations": [
        { "layer": "Seed", "cell_id": "uuid" },
        { "layer": "TechStack", "cell_id": "uuid" }
      ]
    }
  ]
}
```

### MatrixCell 조작

| Method | Path | 설명 |
|---|---|---|
| `POST` | `/api/blueprints/{id}/cells` | 단계 추가 |
| `PATCH` | `/api/blueprints/{id}/cells/{cell_id}` | label 수정 |
| `DELETE` | `/api/blueprints/{id}/cells/{cell_id}` | 단계 삭제 (레이어 내 마지막 1개면 거부 400) |

**POST 요청 바디:** `{ "layer": "Seed", "label": "위험노출" }`  
**PATCH 요청 바디:** `{ "label": "새이름" }`

### IntegrationItem 조작

| Method | Path | 설명 |
|---|---|---|
| `POST` | `/api/blueprints/{id}/integrations` | 통합 항목 생성 (combinations 2개 이상 검증) |
| `DELETE` | `/api/blueprints/{id}/integrations/{item_id}` | 통합 항목 삭제 |

**POST 요청 바디:**
```json
{
  "name": "제약-개념 정렬",
  "combinations": [
    { "layer": "Seed", "cell_id": "uuid" },
    { "layer": "Concept", "cell_id": "uuid" }
  ]
}
```

---

## 프론트엔드 구조

### 새 탭 추가

`App.jsx`의 탭 목록에 `blueprint` 추가:

```jsx
// 기존
{['editor', 'graph', 'research'].map(...)}

// 변경 후
{['editor', 'graph', 'research', 'blueprint'].map(...)}
// 레이블: blueprint → 'Blueprint'
```

### 신규 컴포넌트

| 파일 | 역할 |
|---|---|
| `src/components/BlueprintTab.jsx` | 탭 루트: 목록 ↔ 편집 화면 전환 상태 관리 |
| `src/components/BlueprintList.jsx` | Blueprint 목록 테이블 + 생성/삭제 버튼 |
| `src/components/BlueprintEditor.jsx` | 선택된 Blueprint 편집 화면 (매트릭스 + Z-Axis 통합) |
| `src/components/MatrixGrid.jsx` | 레이어 × 단계 격자, 인라인 편집·추가·삭제 |
| `src/components/IntegrationPanel.jsx` | 통합 항목 목록 + 생성 모달 |

### API 클라이언트

`src/services/contentsApi.js`에 Blueprint 관련 함수 추가:

```js
// Blueprint
export const getBlueprints = () => ...
export const createBlueprint = (name, description) => ...
export const getBlueprint = (id) => ...
export const updateBlueprint = (id, patch) => ...
export const deleteBlueprint = (id) => ...

// MatrixCell
export const addMatrixCell = (blueprintId, layer, label) => ...
export const updateMatrixCell = (blueprintId, cellId, label) => ...
export const deleteMatrixCell = (blueprintId, cellId) => ...

// IntegrationItem
export const addIntegration = (blueprintId, name, combinations) => ...
export const deleteIntegration = (blueprintId, itemId) => ...
```

---

## Stories 상세

### STORY-001: Blueprint Backend

**목표:** DB 마이그레이션 + CRUD API 구현

| Ticket | 제목 | 파일 |
|---|---|---|
| TICKET-001 | DB 모델 추가 + Alembic 마이그레이션 | `models.py`, `database.py` |
| TICKET-002 | Blueprint CRUD 라우터 | `routes/blueprints.py`, `main.py` |
| TICKET-003 | MatrixCell API + 기본값 seed | `routes/blueprints.py` |
| TICKET-004 | IntegrationItem API | `routes/blueprints.py` |

**완료 기준:**
- [ ] `GET /api/blueprints` 빈 목록 반환 (인증 없으면 401)
- [ ] `POST /api/blueprints` → 9개 기본 MatrixCell 자동 생성 확인
- [ ] `GET /api/blueprints/{id}` → matrix/integrations 포함 응답
- [ ] 마지막 셀 삭제 시 400 반환
- [ ] `DELETE /api/blueprints/{id}` soft delete — 목록 재조회 시 제외

---

### STORY-002: Blueprint Frontend

**목표:** 기존 contents-manager 탭에 Blueprint 워크스페이스 탭 추가

| Ticket | 제목 | 파일 |
|---|---|---|
| TICKET-001 | 탭 등록 + BlueprintTab 뼈대 | `App.jsx`, `BlueprintTab.jsx` |
| TICKET-002 | BlueprintList — 목록·생성·삭제 | `BlueprintList.jsx` |
| TICKET-003 | MatrixGrid — 인라인 편집·추가·삭제 | `BlueprintEditor.jsx`, `MatrixGrid.jsx` |
| TICKET-004 | IntegrationPanel — 통합 항목 관리 | `IntegrationPanel.jsx` |

**완료 기준:**
- [ ] 탭 클릭 시 Blueprint 목록 표시
- [ ] Blueprint 생성 → 3개 레이어 × 3개 단계 격자 즉시 표시
- [ ] 셀 클릭 → 인라인 편집 → 저장 → 화면 반영
- [ ] "+ 단계 추가" → 셀 추가 → 저장
- [ ] 마지막 셀 삭제 시도 → 에러 토스트 표시
- [ ] 통합 항목 생성 (조합 2개 이상 선택) → 목록 반영
- [ ] 통합 항목 삭제 → 즉시 제거

---

## 의존성 및 제약

- **신규 패키지 없음:** 백엔드는 기존 FastAPI/SQLAlchemy 스택, 프론트엔드는 기존 React
- **DB 마이그레이션:** SQLite 사용 중이므로 `database.py`의 `init_db()`가 `create_all()`로 테이블을 자동 생성 — Alembic 불필요
- **EPIC-003 연동 준비:** Blueprint_ID 컬럼은 이후 question 테이블이 외래키로 참조할 예정. 현재는 soft delete로 보호
- **인증:** 기존 JWT(`get_current_user`) 그대로 사용. KG 서비스 토큰 불필요 (editor 전용 기능)
