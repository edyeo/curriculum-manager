# [Feature Requirements] EPIC-004: Ontology API — 온톨로지 기반 타입 시스템

## 1. 배경 및 문제 정의

현재 `contents-manager` 전반에서 노드 타입(Seed / Concept / TechStack / System)이 여러 파일에 각자 하드코딩되어 있다.

| 파일 | 하드코딩 위치 |
|---|---|
| `frontend/src/components/NodeTable.jsx` | `const TYPES = ['Seed', 'Concept', 'TechStack']` |
| `frontend/src/components/AiLinkModal.jsx` | `const TYPES = ['Seed', 'Concept', 'TechStack', 'System']` |
| `frontend/src/components/GraphView.jsx` | 타입별 색상 맵 객체 |
| `backend/routes/nodes.py` | 주석 `# Seed \| Concept \| TechStack` |

`agent-platform/shared/ontology.yaml`이 타입의 단일 진실 공급원(SSOT)으로 이미 존재하지만, `contents-manager`는 이를 참조하지 않는다. 새 엔티티 타입이 추가되거나 이름이 변경될 경우 위 파일들을 수작업으로 모두 갱신해야 한다.

---

## 2. 목표

`agent-platform/shared/ontology.yaml`을 SSOT로 삼아 `contents-manager`(백엔드·프론트엔드) 전체가 타입 목록을 단일 엔드포인트에서 동적으로 조회하도록 전환한다.

---

## 3. 기능 요건

### F-001: 온톨로지 로더 (백엔드)

- `contents-manager/backend/ontology.py`를 신규 추가한다.
- `agent-platform/shared/ontology.yaml`을 서버 시작 시 1회 로드하고 캐시(`lru_cache`)한다.
- 파일 경로는 `ONTOLOGY_PATH` 환경변수로 오버라이드 가능해야 한다.
- Docker 환경에서는 `docker-compose.local.yml`에 bind mount + 환경변수로 경로를 주입한다.

```
ONTOLOGY_PATH 경로 우선순위:
  1. 환경변수 ONTOLOGY_PATH
  2. 상대경로 ../../agent-platform/shared/ontology.yaml (로컬 개발 기본값)
```

온톨로지 변경 후에는 컨테이너 재시작이 필요하다. (로컬 `uvicorn --reload` 환경에서는 자동 갱신.)

### F-002: 온톨로지 엔티티 API 엔드포인트

```
GET /api/ontology/entities
```

- 인증 불필요 (정적 스키마, 공개 정보)
- 응답:
```json
{
  "entities": [
    { "name": "System",    "description": "..." },
    { "name": "Seed",      "description": "..." },
    { "name": "Concept",   "description": "..." },
    { "name": "TechStack", "description": "..." }
  ]
}
```
- `name`은 `ontology.yaml` entities 블록의 키, `description`은 해당 엔티티의 description 필드

### F-003: 프론트엔드 하드코딩 제거

아래 파일에서 하드코딩된 타입 배열/객체를 제거하고 `GET /api/ontology/entities` 응답으로 교체한다.

| 파일 | 변경 내용 |
|---|---|
| `NodeTable.jsx` | `const TYPES` 제거 → API 조회 결과 사용 |
| `AiLinkModal.jsx` | `const TYPES` 제거 → API 조회 결과 사용 |
| `GraphView.jsx` | 타입별 색상 맵을 동적으로 생성 (온톨로지에 없는 타입은 기본 색상 폴백) |

API 응답은 앱 초기화 시 1회 조회하여 Context 또는 상위 컴포넌트 state로 내려준다. 각 컴포넌트가 개별 호출하지 않는다.

### F-004: 기존 데이터 정합성 원칙

온톨로지 변경 시 이미 저장된 데이터(노드 type 컬럼, MatrixCell layer 컬럼 등)에 대한 정책:

| 변경 종류 | 기존 데이터 | 처리 방침 |
|---|---|---|
| 엔티티 추가 | 영향 없음 | 자동 반영 (신규 생성 시 새 타입 선택 가능) |
| 엔티티 삭제 | 기존 레코드의 type 값이 고아 상태 | **원칙적으로 금지.** 불가피할 경우 DB 마이그레이션 스크립트 병행 |
| 엔티티 이름 변경 | 기존 레코드의 type 값이 구 이름 참조 | **원칙적으로 금지.** 불가피할 경우 DB 마이그레이션 스크립트 병행 |
| description만 변경 | 영향 없음 | 서버 재시작 시 자동 반영 |

**운영 원칙:** `ontology.yaml`의 entities 키(이름)는 한 번 정의된 후 변경하지 않는다. 이름 변경이 필요할 경우 반드시 DB 마이그레이션 스크립트를 작성하고 동시에 배포한다.

---

## 4. 비기능 요건

- **신규 패키지:** 백엔드 `pyyaml` 추가 (`requirements.txt`)
- **하위 호환성:** 기존 노드 type 값(파일 DB의 nodes.json)은 변경하지 않는다. API가 현재 타입 목록을 반환하는 것으로 충분
- **성능:** 엔드포인트 응답은 lru_cache 덕에 파일 I/O 없이 처리됨

---

## 5. 영향 범위

```
contents-manager/
├── backend/
│   ├── ontology.py              ← 신규
│   ├── routes/ontology.py       ← 신규
│   ├── main.py                  ← router 등록
│   └── requirements.txt         ← pyyaml 추가
├── frontend/src/
│   ├── services/contentsApi.js  ← getOntologyEntities() 추가
│   ├── components/NodeTable.jsx ← TYPES 하드코딩 제거
│   ├── components/AiLinkModal.jsx ← TYPES 하드코딩 제거
│   └── components/GraphView.jsx ← 색상 맵 동적화
└── infra/docker-compose.local.yml ← bind mount + 환경변수 추가
```

---

## 6. 선행 조건 및 의존성

- 이 Epic은 다른 Epic의 구현을 블로킹하지 않는다.
- EPIC-002(Blueprint), EPIC-003(Question Generator)에서 타입을 참조하는 부분은 이 Epic 완료 전까지 로컬 상수로 임시 관리하고, 완료 후 교체한다.
- 온톨로지 파일 경로(`agent-platform/shared/ontology.yaml`)가 안정적으로 유지되는 것을 전제한다.
