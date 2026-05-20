# Curriculum Manager — Claude 작업 가이드

## 프로젝트 구조

```
curriculum-manager/
├── infra/                   # Docker Compose 설정 (전체 스택)
│   ├── docker-compose.local.yml
│   ├── docker-compose.dev.yml
│   ├── docker-compose.worktree.yml
│   └── worktree-up.sh
├── agent-platform/          # AI 에이전트 서비스 (LangGraph 기반)
│   ├── agents/
│   │   └── curriculum-manager/src/
│   │       ├── graphs/      # LangGraph 파이프라인 (draft / link / expand)
│   │       └── harness.py   # 트리거 진입점 디스패처
│   └── shared/              # 공유 스키마·유틸
├── apps/                    # FE/BE 애플리케이션
│   ├── contents-manager/
│   │   ├── backend/         # FastAPI (노드·엣지 CRUD, AI 트리거 프록시)
│   │   └── frontend/        # React + Vite (편집·그래프·리서치 탭)
│   └── student-platform/
│       ├── backend/         # FastAPI (학생 플랫폼 API)
│       ├── frontend/        # React + Vite (학생 UI)
│       ├── virtual-student-api/
│       └── virtual-student-ui/
└── docs/backlog/            # 기능 요건 및 티켓 문서
```

## 워크트리에서 개발 서버 띄우기

각 worktree는 절대경로가 달라 별도 Docker 볼륨 설정이 필요하다.
`worktree-up.sh`가 이를 자동으로 처리한다.

### 1. OPENAI_API_KEY 설정

```bash
# infra/.env.local
OPENAI_API_KEY=sk-...   # 실제 키 입력
```

`.env.local`이 없으면 `worktree-up.sh`가 템플릿을 생성한다.

### 2. 서비스 기동

```bash
cd infra
bash worktree-up.sh          # 기동 (up)
bash worktree-up.sh down     # 종료
```

스크립트가 자동으로 처리하는 항목:
- `WORKTREE_ROOT` 감지 → `.env.local`에 주입
- `nodes.json` / `edges.json` 파일 초기화 (없거나 빈 디렉토리이면 main repo에서 복사)
- `backend/data/` 내 잔류 빈 디렉토리 정리
- `docker compose` 3파일 조합으로 기동

### 3. 직접 실행 (스크립트 없이)

```bash
cd infra

# .env.local 에 WORKTREE_ROOT 추가
echo "WORKTREE_ROOT=$(cd .. && pwd)" >> .env.local

docker compose --env-file .env.local \
  -f docker-compose.local.yml \
  -f docker-compose.dev.yml \
  -f docker-compose.worktree.yml \
  up -d
```

### 서비스 URL

| 서비스 | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8010 |
| API Gateway | http://localhost:9000 |
| Curriculum Manager Agent | http://localhost:8001 |

### 주의사항

- `docker-compose.worktree.yml`은 `.gitignore`에 포함 — 커밋하지 않음
- `restart` 명령은 환경변수를 반영하지 않음. 환경변수 변경 시 `--force-recreate` 사용:
  ```bash
  docker compose --env-file .env.local \
    -f docker-compose.local.yml \
    -f docker-compose.dev.yml \
    -f docker-compose.worktree.yml \
    up -d --force-recreate <서비스명>
  ```
- `.env.local`은 API 키 포함 — 절대 커밋 금지

## AI 파이프라인 트리거

| 트리거 | 역할 |
|---|---|
| `T1 DRAFT` | 주제 기반 노드 초안 생성 (Seed·Concept·TechStack 병렬) |
| `T2 LINK` | 타입 간 엣지 생성 |
| `T3 EXPAND` | 토론 기반 그래프 확장 (Critic → Devil's Advocate → Synthesizer → Linker) |
| `AI LINK` | 사용자 지정 조건(타입·depth·특정 노드)으로 엣지 생성 |

## 온톨로지

`agent-platform/shared/ontology.yaml` 참조.

주요 관계 타입:
- `has_subtopic` — 동일 타입 내 부모→자식 계층
- `requires` — Seed → Concept
- `implemented_by` — Concept → TechStack
- `relied_on` — System → Seed

## backlog 문서

`docs/backlog/` 하위에 기능 요건 및 티켓 문서 관리.
신규 기능 작업 전 요건 문서를 먼저 작성한다.
