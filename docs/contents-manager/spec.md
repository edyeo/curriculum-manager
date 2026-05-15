# Technical Spec: Contents Manager

**버전:** 0.1 (초안)  
**작성일:** 2026-05-15

---

## 1. 아키텍처 개요

```
Browser (React SPA, port 3000)
    │  REST/JSON
    ▼
Contents Manager Backend (FastAPI, port 8010)
    ├── 인증 (JWT, python-jose)
    ├── Subject 메타데이터 DB (SQLite → PostgreSQL)
    │
    └── httpx 프록시
            │
            ▼
     API Gateway (port 9000)  ← 기존 인프라
          ├── Curriculum Manager   (8001)
          ├── Mental Model Manager (8002)
          ├── Researcher           (8003)
          └── Question Generator   (8004)
```

**원칙:** Contents Manager는 사용자·Subject 메타데이터만 자체 DB에 저장한다.
노드·엣지·문제·리서치 데이터는 AI 에이전트 측 JSON DB를 단일 진실 공급원으로 유지한다.

---

## 2. 디렉터리 구조 (신규)

```
apps/
└── contents_manager/
    ├── main.py              # FastAPI 앱 진입점 (port 8010)
    ├── auth.py              # JWT 발급·검증
    ├── database.py          # SQLite 연결 (SQLAlchemy)
    ├── models.py            # ORM 모델 (User, Subject)
    ├── routes/
    │   ├── auth.py          # POST /auth/login, /auth/logout, GET /auth/me
    │   ├── subjects.py      # CRUD /subjects
    │   ├── nodes.py         # 노드 편집 /subjects/{id}/nodes
    │   ├── edges.py         # 관계 편집 /subjects/{id}/edges
    │   ├── research.py      # 리서치 /subjects/{id}/research
    │   ├── questions.py     # 문제 /subjects/{id}/nodes/{node_id}/questions
    │   └── admin.py         # 사용자 관리 /admin/users
    └── frontend/
        ├── index.html
        ├── vite.config.js
        ├── package.json
        └── src/
            ├── main.jsx
            ├── App.jsx              # 메인 앱 (탭 전환, Subject 선택)
            ├── LoginPage.jsx        # 로그인 화면
            ├── components/
            │   ├── NodeTable.jsx    # 편집 탭 — 노드 테이블
            │   ├── NodePanel.jsx    # 슬라이드 패널 (노드 상세·관계·문제)
            │   ├── GraphView.jsx    # 그래프 탭 — SVG 시각화
            │   ├── ResearchTab.jsx  # 리서치 탭
            │   └── AdminTab.jsx     # Admin 탭
            └── services/
                └── contentsApi.js   # 모든 API 호출 추상화
```

---

## 3. Backend API

### 3.1 인증

| Method | Path | 설명 | Auth |
|--------|------|------|------|
| POST | `/auth/login` | 이메일·패스워드 → JWT | 불필요 |
| POST | `/auth/logout` | 클라이언트 토큰 폐기 안내 | 불필요 |
| GET | `/auth/me` | 현재 사용자 정보 반환 | 필요 |

**Request (login):**
```json
{ "email": "user@example.com", "password": "..." }
```

**Response (login):**
```json
{ "access_token": "eyJ...", "token_type": "bearer", "expires_in": 86400 }
```

---

### 3.2 Subject

| Method | Path | 설명 |
|--------|------|------|
| GET | `/subjects` | 목록 조회 (이름, 생성일, 노드 수, 상태) |
| POST | `/subjects` | 생성 + AI Draft 트리거 |
| GET | `/subjects/{id}` | 상세 조회 |
| DELETE | `/subjects/{id}` | 삭제 |

**POST /subjects Request:**
```json
{
  "name": "Distributed Systems",
  "description": "분산 시스템 핵심 개념 커리큘럼"
}
```

**동작:** Subject를 DB에 저장한 뒤 Gateway `POST /curriculum/generate`를 백그라운드 호출.
응답은 즉시 반환하고 Draft 생성은 비동기로 처리한다.

---

### 3.3 노드

| Method | Path | 대상 |
|--------|------|------|
| GET | `/subjects/{id}/nodes` | `GET /proxy/curriculum/api/curriculum/status` → nodes 파싱 |
| POST | `/subjects/{id}/nodes` | 에이전트 파일 DB 직접 저장 |
| PATCH | `/subjects/{id}/nodes/{node_id}` | 에이전트 파일 DB 직접 수정 |
| DELETE | `/subjects/{id}/nodes/{node_id}` | 에이전트 파일 DB 직접 삭제 |

**PATCH Request:**
```json
{ "name": "Load Balancing", "description": "수정된 설명..." }
```

> 노드 직접 편집은 현재 Gateway에 엔드포인트가 없으므로 에이전트 측 파일 DB를 직접 수정한다.
> 추후 Gateway에 편집 API 추가 시 교체 가능.

---

### 3.4 관계(엣지)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/subjects/{id}/edges` | 전체 관계 목록 |
| POST | `/subjects/{id}/edges` | 관계 추가 |
| DELETE | `/subjects/{id}/edges/{edge_id}` | 관계 삭제 |

**POST Request:**
```json
{
  "source_id": "node-uuid-1",
  "target_id": "node-uuid-2",
  "relation_type": "requires",
  "logic_basis": "Load Balancing을 이해하려면 Throughput 개념이 선행되어야 함"
}
```

---

### 3.5 AI Expand

| Method | Path | Gateway 대상 |
|--------|------|------|
| POST | `/subjects/{id}/curriculum/expand` | `POST /proxy/curriculum/api/curriculum/generate/expand` |

---

### 3.6 리서치

| Method | Path | Gateway 대상 | 설명 |
|--------|------|------|------|
| POST | `/subjects/{id}/research/start` | `POST /proxy/research/api/research/start` | Curriculum 기반 자동 리서치 시작 |
| GET | `/subjects/{id}/research/results` | `POST /proxy/research/api/research/query` (body 없음) | 전체 결과 조회 |
| GET | `/subjects/{id}/research/results?keyword=X&source=Y` | `POST /proxy/research/api/research/query` (필터 포함) | 필터 조회 |

**결과 항목:**
```json
{
  "id": "...",
  "keyword": "Load Balancing",
  "source": "blog",
  "title": "Understanding Load Balancing",
  "url": "https://...",
  "summary": "LLM 생성 요약..."
}
```

---

### 3.7 문제

| Method | Path | Gateway 대상 |
|--------|------|------|
| GET | `/subjects/{id}/nodes/{node_id}/questions` | `GET /proxy/questions/api/questions/entity/{node_id}` |
| POST | `/subjects/{id}/nodes/{node_id}/questions` | `POST /proxy/questions/api/questions/generate` |

---

### 3.8 사용자 관리 (Admin 전용)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/admin/users` | 사용자 목록 |
| POST | `/admin/users/invite` | 이메일 초대 (임시 패스워드 발급) |
| PATCH | `/admin/users/{id}/role` | 역할 변경 (admin/editor/viewer) |

---

## 4. 데이터 모델 (Contents Manager DB)

```sql
CREATE TABLE users (
    id          TEXT PRIMARY KEY,
    email       TEXT UNIQUE NOT NULL,
    hashed_pw   TEXT NOT NULL,
    role        TEXT DEFAULT 'editor',  -- admin | editor | viewer
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE subjects (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    owner_id    TEXT NOT NULL REFERENCES users(id),
    status      TEXT DEFAULT 'draft',   -- draft | active | archived
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

노드·엣지·문제·리서치는 AI 에이전트 측 JSON 파일
(`nodes.json`, `edges.json`, `questions.json`, `research_results.json`)에 저장된다.
Contents Manager DB에 중복 저장하지 않는다.

---

## 5. Frontend 상세

### 5.1 화면 흐름

```
[LoginPage]  →  인증 성공  →  [App]
                                 │
                    [Subject 드롭다운] + [새 Subject 버튼]
                                 │ Subject 선택 후 활성화
                    ┌────────────┼────────────┬──────────┐
               [편집 탭]   [그래프 탭]  [리서치 탭]  [Admin 탭]
```

### 5.2 편집 탭 레이아웃

```
┌─ 헤더: Subject명 + [AI 확장] [+ 노드 추가] ──────────────────────────┐
│ ┌─ 필터: [타입 ▼] [Depth ▼] [검색창_______________________] ──────┐ │
│ │                                                                  │ │
│ │  이름              타입       Depth  설명 (요약)       관계  문제 │ │
│ │  ─────────────────────────────────────────────────────────────  │ │
│ │  Throughput...     Seed         1   분산 시스템에서...   3     2  │ │
│ │  Load Balancing    Concept      2   여러 서버에...       2     5  │ │
│ │  Nginx             TechStack    3   오픈소스 웹...       1     3  │ │
│ │  [이름 입력___]    [Seed▼]    [1▼]  [설명 입력___]    저장 취소  │ │
│ └──────────────────────────────────────────────────────────────── ┘ │
└──────────────────────────────────── ▶ 행 클릭 시 우측 패널 열림 ───┘
                                                    │
                                        ┌───────────▼──────────────┐
                                        │ [노드 상세] [관계] [문제] │
                                        │ 이름: [_______________]  │
                                        │ 설명: [_______________]  │
                                        │              [저장]      │
                                        │ ─────────────────────── │
                                        │ 관계 목록                │
                                        │  → Nginx (implemented_by)│
                                        │  [+ 관계 추가]           │
                                        │ ─────────────────────── │
                                        │        [노드 삭제]       │
                                        └──────────────────────────┘
```

### 5.3 그래프 탭

- 커스텀 SVG 렌더링 (`KGExplorer.jsx` 참조)
- 노드 타입별 색상: Seed(amber), Concept(sky), TechStack(emerald)
- 엣지에 relation_type 라벨 표시
- 읽기 전용, 노드 클릭 시 이름·설명 툴팁

### 5.4 리서치 탭

```
┌─ [리서치 시작] 버튼  ──────────────────────────────────────────────┐
│ 필터: [keyword 검색___________] [source: 전체 ▼]                  │
│ ─────────────────────────────────────────────────────────────────  │
│ [blog]   Load Balancing  —  "Understanding Load Balancing"         │
│           LLM 요약 텍스트...                       [링크 열기]      │
│ [paper]  Consistent Hashing  —  "Dynamo: Amazon's..."              │
│           LLM 요약 텍스트...                       [링크 열기]      │
└────────────────────────────────────────────────────────────────────┘
```

### 5.5 라이브러리 선택

기존 `test-anti_gravity/assessor/frontend`와 동일한 경량 스택:

| 목적 | 선택 | 이유 |
|------|------|------|
| 빌드 | React 18 + Vite | 기존 프로젝트와 동일 |
| 라우팅 | 없음 (useState 탭 전환) | 기존 패턴 유지 |
| 상태 관리 | useState / useEffect | 외부 라이브러리 불필요 |
| API 통신 | fetch (services/contentsApi.js) | 기존 kgApi.js 패턴 |
| 그래프 | 커스텀 SVG | 기존 KGExplorer.jsx 참조 |
| 스타일 | 커스텀 CSS (다크 테마) | 기존 패턴 유지 |
| 인증 | JWT → localStorage | 신규 추가 |

### 5.6 contentsApi.js 구조

```js
const BASE = '/api'  // Vite proxy → port 8010

const headers = () => ({
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${localStorage.getItem('token')}`
})

// Auth
export const login = (email, password) => fetch(`${BASE}/auth/login`, { method: 'POST', body: JSON.stringify({ email, password }) })
export const getMe = () => fetch(`${BASE}/auth/me`, { headers: headers() })

// Subjects
export const getSubjects = () => fetch(`${BASE}/subjects`, { headers: headers() })
export const createSubject = (name, description) => fetch(`${BASE}/subjects`, { method: 'POST', headers: headers(), body: JSON.stringify({ name, description }) })
export const deleteSubject = (id) => fetch(`${BASE}/subjects/${id}`, { method: 'DELETE', headers: headers() })

// Nodes
export const getNodes = (subjectId) => fetch(`${BASE}/subjects/${subjectId}/nodes`, { headers: headers() })
export const createNode = (subjectId, node) => fetch(`${BASE}/subjects/${subjectId}/nodes`, { method: 'POST', headers: headers(), body: JSON.stringify(node) })
export const updateNode = (subjectId, nodeId, patch) => fetch(`${BASE}/subjects/${subjectId}/nodes/${nodeId}`, { method: 'PATCH', headers: headers(), body: JSON.stringify(patch) })
export const deleteNode = (subjectId, nodeId) => fetch(`${BASE}/subjects/${subjectId}/nodes/${nodeId}`, { method: 'DELETE', headers: headers() })

// Edges
export const getEdges = (subjectId) => fetch(`${BASE}/subjects/${subjectId}/edges`, { headers: headers() })
export const createEdge = (subjectId, edge) => fetch(`${BASE}/subjects/${subjectId}/edges`, { method: 'POST', headers: headers(), body: JSON.stringify(edge) })
export const deleteEdge = (subjectId, edgeId) => fetch(`${BASE}/subjects/${subjectId}/edges/${edgeId}`, { method: 'DELETE', headers: headers() })

// Research
export const startResearch = (subjectId) => fetch(`${BASE}/subjects/${subjectId}/research/start`, { method: 'POST', headers: headers() })
export const getResearchResults = (subjectId, filters = {}) => {
  const params = new URLSearchParams(filters).toString()
  return fetch(`${BASE}/subjects/${subjectId}/research/results${params ? '?' + params : ''}`, { headers: headers() })
}

// Questions
export const getQuestions = (subjectId, nodeId) => fetch(`${BASE}/subjects/${subjectId}/nodes/${nodeId}/questions`, { headers: headers() })
export const generateQuestions = (subjectId, nodeId) => fetch(`${BASE}/subjects/${subjectId}/nodes/${nodeId}/questions`, { method: 'POST', headers: headers() })
```

---

## 6. Docker Compose 추가

기존 `infra/docker-compose.yml`에 두 서비스 추가:

```yaml
contents-manager-backend:
  build:
    context: .
    dockerfile: apps/contents_manager/Dockerfile
  ports:
    - "8010:8010"
  environment:
    - GATEWAY_URL=http://api-gateway:9000
    - JWT_SECRET=${JWT_SECRET}
    - DATABASE_URL=sqlite:///./data/contents_manager.db
  volumes:
    - ./infra/data:/app/data
  depends_on:
    - api-gateway

contents-manager-frontend:
  build:
    context: apps/contents_manager/frontend
  ports:
    - "3000:3000"
  depends_on:
    - contents-manager-backend
```

---

## 7. 구현 순서 (권장)

| 단계 | 작업 | 산출물 |
|------|------|--------|
| 1 | Backend 뼈대 + 인증 | `/auth/login`, `/auth/me`, JWT 발급·검증 |
| 2 | Subject CRUD | `/subjects` GET/POST/DELETE + SQLite |
| 3 | 노드·관계 프록시 | `/subjects/{id}/nodes`, `/edges` |
| 4 | Frontend — 로그인·Subject 목록 | LoginPage, Subject 드롭다운 |
| 5 | Frontend — 편집 탭 | NodeTable + NodePanel (인라인 추가, 슬라이드 패널) |
| 6 | Frontend — 그래프 탭 | GraphView (SVG, KGExplorer 참조) |
| 7 | 리서치·문제 연동 | ResearchTab, Questions 패널 |
| 8 | Admin 탭 | 사용자 목록·초대 |
| 9 | Docker Compose 통합 | 전체 서비스 기동 확인 |
