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

## 온톨로지 연동

**단일 진실 공급원(SSOT):** `agent-platform/shared/ontology.yaml`의 `entities` 블록이 전체 시스템에서 노드 타입(레이어)의 유일한 정의다. Blueprint의 매트릭스 행(layer)은 이 파일에서 동적으로 읽어야 한다. 새 엔티티 타입이 추가되거나 이름이 변경될 경우 Blueprint도 자동으로 반영된다.

현재 `contents-manager`의 문제점: `NodeTable.jsx`, `AiLinkModal.jsx`, `GraphView.jsx`, `routes/nodes.py` 등이 타입을 각자 하드코딩하고 있다. Blueprint 구현과 함께 백엔드에 온톨로지 로더를 추가하고 프론트엔드는 이를 통해 타입을 조회한다.

### 온톨로지 로더 — `contents-manager/backend/ontology.py`

```python
import os, yaml
from functools import lru_cache

ONTOLOGY_PATH = os.getenv(
    "ONTOLOGY_PATH",
    os.path.join(os.path.dirname(__file__), "../../agent-platform/shared/ontology.yaml")
)

@lru_cache(maxsize=1)
def load_ontology() -> dict:
    with open(ONTOLOGY_PATH) as f:
        return yaml.safe_load(f)

def get_entity_names() -> list[str]:
    """ontology.yaml entities 블록의 키 목록 반환."""
    return list(load_ontology()["entities"].keys())
```

Docker 컨테이너에서는 `ONTOLOGY_PATH` 환경변수로 경로를 주입한다.  
`docker-compose.local.yml`에 `contents-manager-backend` 서비스에 아래를 추가:

```yaml
environment:
  ONTOLOGY_PATH: /app/ontology.yaml
volumes:
  - ../../agent-platform/shared/ontology.yaml:/app/ontology.yaml:ro
```

### 온톨로지 API 엔드포인트

`routes/ontology.py`를 신규 추가하고 `main.py`에 등록.

```
GET /api/ontology/entities
```

응답:
```json
{
  "entities": [
    { "name": "System",     "description": "..." },
    { "name": "Seed",       "description": "..." },
    { "name": "Concept",    "description": "..." },
    { "name": "TechStack",  "description": "..." }
  ]
}
```

프론트엔드 전반(`NodeTable`, `AiLinkModal`, `BlueprintTab`)이 이 엔드포인트를 통해 타입 목록을 조회한다. 하드코딩된 `const TYPES = [...]` 배열은 모두 제거된다.

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
    layer        = Column(Text, nullable=False)            # ontology entity name (e.g. "Seed")
    label        = Column(Text, nullable=False)            # 인지 단계 이름
    position     = Column(Integer, nullable=False)         # 레이어 내 순서 (0-based)

# IntegrationItem — 통합 항목(Z-Axis)
class IntegrationItem(Base):
    __tablename__ = "integration_items"
    id           = Column(Text, primary_key=True)         # UUID
    blueprint_id = Column(Text, ForeignKey("blueprints.id"), nullable=False)
    name         = Column(Text, nullable=False)
    # 조합 목록: JSON 배열 [{"layer": "<entity_name>", "cell_id": "..."}]
    combinations = Column(Text, nullable=False)            # JSON string
    created_at   = Column(TIMESTAMP, server_default=func.now())
```

**기본값 seed:** Blueprint 생성 시, `get_entity_names()`가 반환하는 각 엔티티 타입마다 PRD 기준 초기 인지 단계 레이블 3개가 삽입된다.  
레이블 기본값은 `blueprints.py` 라우터에 `DEFAULT_LABELS: dict[str, list[str]]`로 정의하며, 온톨로지에 없는 엔티티가 키로 있어도 무시된다.

```python
DEFAULT_LABELS = {
    "Seed":       ["인식", "리스크", "통제"],
    "Concept":    ["원리", "매핑", "대안"],
    "TechStack":  ["스펙", "디버깅", "전환"],
}

def _seed_matrix(blueprint_id: str, db: Session):
    for entity in get_entity_names():
        labels = DEFAULT_LABELS.get(entity, ["기본"])
        for pos, label in enumerate(labels):
            db.add(MatrixCell(
                id=str(uuid.uuid4()),
                blueprint_id=blueprint_id,
                layer=entity,
                label=label,
                position=pos,
            ))
```

`MatrixCell` 저장 시 `layer` 값이 `get_entity_names()` 목록에 없으면 400을 반환한다.

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
    "System":    [],
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

`matrix`의 키는 `get_entity_names()`가 반환한 목록과 동일하게 구성된다. 현재 온톨로지 기준 `System, Seed, Concept, TechStack` 4개.

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

`src/services/contentsApi.js`에 함수 추가:

```js
// 온톨로지 — 타입 목록 (NodeTable, AiLinkModal, BlueprintTab 공통 사용)
export const getOntologyEntities = () => ...   // GET /api/ontology/entities

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

`BlueprintTab` 진입 시 `getOntologyEntities()`를 호출해 레이어 목록을 받아온다. `NodeTable`, `AiLinkModal`의 하드코딩된 `TYPES` 배열도 동일 API 호출로 교체한다 (STORY-002 TICKET-001에서 처리).

---

## Stories 상세

### STORY-001: Blueprint Backend

**목표:** 온톨로지 로더 + DB 모델 + CRUD API 구현

| Ticket | 제목 | 파일 |
|---|---|---|
| TICKET-001 | 온톨로지 로더 + `/api/ontology/entities` 엔드포인트 | `ontology.py`, `routes/ontology.py`, `main.py`, `docker-compose.local.yml` |
| TICKET-002 | DB 모델 추가 (Blueprint·MatrixCell·IntegrationItem) | `models.py` |
| TICKET-003 | Blueprint CRUD 라우터 + MatrixCell seed | `routes/blueprints.py`, `main.py` |
| TICKET-004 | MatrixCell·IntegrationItem API | `routes/blueprints.py` |

**완료 기준:**
- [ ] `GET /api/ontology/entities` → 온톨로지 엔티티 목록 반환 (인증 불필요)
- [ ] `ONTOLOGY_PATH` 환경변수로 yaml 경로 오버라이드 가능
- [ ] `POST /api/blueprints` → 온톨로지 엔티티 수 × 기본 레이블 수만큼 MatrixCell 자동 생성
- [ ] `GET /api/blueprints/{id}` → matrix 키가 온톨로지 엔티티 목록과 일치
- [ ] 온톨로지에 없는 layer 값으로 셀 추가 시 400 반환
- [ ] 마지막 셀 삭제 시 400 반환
- [ ] `DELETE /api/blueprints/{id}` soft delete — 목록 재조회 시 제외

---

### STORY-002: Blueprint Frontend

**목표:** 온톨로지 API 기반 타입 조회 + Blueprint 워크스페이스 탭 추가

| Ticket | 제목 | 파일 |
|---|---|---|
| TICKET-001 | 탭 등록 + `getOntologyEntities` 추가 + `NodeTable`·`AiLinkModal` 하드코딩 제거 | `App.jsx`, `BlueprintTab.jsx`, `contentsApi.js`, `NodeTable.jsx`, `AiLinkModal.jsx` |
| TICKET-002 | BlueprintList — 목록·생성·삭제 | `BlueprintList.jsx` |
| TICKET-003 | MatrixGrid — 인라인 편집·추가·삭제 | `BlueprintEditor.jsx`, `MatrixGrid.jsx` |
| TICKET-004 | IntegrationPanel — 통합 항목 관리 | `IntegrationPanel.jsx` |

**완료 기준:**
- [ ] `NodeTable`·`AiLinkModal`의 `const TYPES = [...]` 하드코딩 제거 → API 응답으로 대체
- [ ] 탭 클릭 시 Blueprint 목록 표시
- [ ] Blueprint 생성 → 온톨로지 엔티티 수만큼 레이어 행이 격자에 표시됨
- [ ] 셀 클릭 → 인라인 편집 → 저장 → 화면 반영
- [ ] "+ 단계 추가" → 셀 추가 → 저장
- [ ] 마지막 셀 삭제 시도 → 에러 토스트 표시
- [ ] 통합 항목 생성 (조합 2개 이상 선택) → 목록 반영
- [ ] 통합 항목 삭제 → 즉시 제거

---

## 의존성 및 제약

- **신규 패키지:** 백엔드에 `pyyaml` 추가 필요 (`requirements.txt`)
- **DB 마이그레이션:** SQLite 사용 중이므로 `database.py`의 `init_db()`가 `create_all()`로 테이블을 자동 생성 — Alembic 불필요
- **온톨로지 경로:** 로컬 개발은 상대경로 자동 탐색, Docker는 `ONTOLOGY_PATH` 환경변수 + bind mount로 주입
- **EPIC-003 연동 준비:** Blueprint_ID 컬럼은 이후 question 테이블이 외래키로 참조할 예정. 현재는 soft delete로 보호
- **인증:** `/api/ontology/entities`는 인증 불필요 (read-only 정적 스키마). 나머지 Blueprint 엔드포인트는 기존 JWT(`get_current_user`) 사용
