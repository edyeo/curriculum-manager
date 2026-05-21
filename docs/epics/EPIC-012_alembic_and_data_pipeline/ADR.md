# [ADR] EPIC-012 Alembic 마이그레이션 & 데이터 파이프라인 — 아키텍처 의사결정 기록

> Architecture Decision Records. 각 결정은 Context → Decision → Consequences 구조로 기록한다.

---

## ADR-001: Alembic 도입 — Pre-existing DB 자동 stamp 패턴

**날짜:** 2026-05-20

**상태:** Accepted

### Context

기존 서비스(`contents-manager-backend`, `student-platform-backend`, `virtual-student-api`)는 SQLAlchemy `create_all()`로 스키마를 관리했다. Alembic을 도입하면서 이미 테이블이 존재하는 DB에 `upgrade head`를 실행하면 "table already exists" 오류가 발생했다.

### Decision

각 백엔드에 `migrate.py`를 추가하고 다음 로직으로 서비스 기동 시 자동 실행한다:

```python
insp = inspect(engine)
tables = set(insp.get_table_names())

if tables and "alembic_version" not in tables:
    subprocess.run(["alembic", "stamp", "001"], check=True)

subprocess.run(["alembic", "upgrade", "head"], check=True)
```

- 테이블이 존재하고 `alembic_version`이 없으면 기존 DB로 판단 → `001` stamp 후 upgrade
- 신규 DB는 stamp 없이 바로 `upgrade head`

`docker-compose.dev.yml`의 CMD를 `sh -c "python3 migrate.py && uvicorn ..."` 형식으로 변경.

### Consequences

**장점**
- 기존 운영 DB 데이터 손실 없이 Alembic 체계로 자연스럽게 전환
- 신규·기존 DB 모두 동일한 기동 스크립트로 처리 — 환경 분기 불필요

**단점 / 제약**
- `001` revision이 최초 스키마와 정확히 일치해야 함 — 불일치 시 stamp 이후 upgrade 충돌 가능
- `stamp`는 실제 마이그레이션을 수행하지 않으므로 스키마 드리프트가 있으면 이후 revision에서 오류 발생

---

## ADR-002: SQLite / PostgreSQL 이중 호환 — server_default 대신 Python-side default

**날짜:** 2026-05-20

**상태:** Accepted

### Context

Alembic `002` revision에서 `kg_nodes`, `kg_edges` 테이블의 `created_at` 컬럼에 `sa.text("now()")` server_default를 사용했다. SQLite는 `now()` 함수를 지원하지 않아 `unknown function: now()` 오류가 발생했다.

`sa.func.now()`로 교체하면 DDL 생성 시 방언(dialect)에 맞게 컴파일되므로 migration 파일은 해결됐으나, SQLAlchemy ORM의 `INSERT … RETURNING` 패턴이 SQLite에서 `created_at` 값을 server에서 읽으려 할 때 추가 오류가 발생했다.

### Decision

두 레이어에서 모두 수정한다:

1. **Migration 파일**: `sa.text("now()")` → `sa.func.now()` (방언 인식 컴파일)
2. **모델**: `server_default=func.now()` → `default=lambda: datetime.now(timezone.utc)` (Python-side 기본값)

```python
# models.py
class KGNode(Base):
    created_at = Column(TIMESTAMP, default=lambda: datetime.now(timezone.utc))
```

### Consequences

**장점**
- SQLite(로컬 개발·테스트)와 PostgreSQL(운영) 모두에서 동일 동작 보장
- ORM INSERT 시 Python이 값을 채워 주므로 DB-level RETURNING 의존도 제거

**단점 / 제약**
- `default=lambda`는 Python 프로세스 시간 기준이므로 DB 서버 시간과 미세하게 다를 수 있음
- 다중 인스턴스 배포 시 인스턴스 간 시계 동기화 필요

---

## ADR-003: KG 노드·엣지 DB 이중 저장 — JSON 파일 + kg_nodes/kg_edges 테이블

**날짜:** 2026-05-20

**상태:** Accepted

### Context

기존 KG 데이터는 `backend/data/nodes.json`, `edges.json` 파일로만 관리됐다. 에이전트도 JSON 파일을 직접 읽고 썼다.

문제 생성 파이프라인에서 `entity_id`로 노드를 조회·필터링할 때 JSON 파일 기반 조회는 인덱스가 없어 비효율적이며, 다른 서비스(student-platform 등)가 KG 데이터에 접근하려면 파일 시스템 공유가 필요했다.

### Decision

`kg_nodes`, `kg_edges` 테이블을 추가(Alembic `002`)하고, 에이전트가 JSON에 쓸 때 백엔드 `_sync_json_to_db()`가 동일 데이터를 테이블에도 반영하는 이중 저장 구조를 유지한다.

- 에이전트: 기존 JSON 파일 R/W 유지 (에이전트 내부 로직 변경 최소화)
- 백엔드: JSON 변경 이후 DB 동기화
- 조회 API: `kg_nodes` 테이블 기반으로 인덱스 활용

### Consequences

**장점**
- 에이전트 코드 변경 없이 DB 조회 성능 확보
- `subject_id` 기준 노드 필터링이 인덱스로 처리
- 서비스 간 KG 접근이 HTTP API로 통일 (파일 시스템 공유 불필요)

**단점 / 제약**
- JSON ↔ DB 동기화 로직이 별도로 존재 — 동기화 누락 시 불일치 가능
- 장기적으로 에이전트도 DB를 직접 읽도록 전환해야 함 (현재는 기술 부채)

---

## ADR-004: 문제 생성 파이프라인 — 파일 덤프 → Storage API 저장 패턴

**날짜:** 2026-05-20

**상태:** Accepted

### Context

초기 PoC 파이프라인 설계에서 생성된 문제를 에이전트 job 완료 직후 바로 DB에 저장하는 방식을 검토했다. 이 방식은 재실행·검수·디버깅 시 중간 상태를 확인할 수 없고, 저장 실패 시 생성 결과가 유실된다.

향후 Airflow 전환을 고려할 때 local 파일 경로를 S3/GCS 경로로 교체하는 것이 자연스러운 마이그레이션 경로다.

### Decision

파이프라인을 두 단계로 분리한다:

**Step 4 — 생성 + 파일 덤프**
- 에이전트 job 완료 후 문제 목록을 수집
- `data-team/data/output/questions_{subject_id8}_{UTC타임스탬프}.json`으로 저장
- `max_questions` 전체 상한 도달 시 나머지 타겟 스킵

**Step 5 — 파일 로드 → Storage API 저장**
- 덤프 파일을 읽어 `POST /api/question-workbench/questions`(storage API) 호출
- `--load-and-save <file>` 플래그로 독립 실행 가능

```
data-team/
├── data/
│   ├── raw/        # 외부 원본 데이터
│   └── output/     # 파이프라인 산출물 (.gitignore 등록)
└── pipeline/
    └── question_generation/
```

### Consequences

**장점**
- 중간 파일로 생성 결과 검수·재처리 가능
- 저장 실패 시 덤프 파일로 재시도 (`--load-and-save` 단독 실행)
- Airflow 전환 시 local path → object storage 경로 교체만으로 마이그레이션

**단점 / 제약**
- 생성~저장 사이 덤프 파일이 수동 관리 대상으로 남음
- `max_questions`는 soft cap — 타겟당 마지막 배치가 상한을 초과할 수 있음

---

## ADR-005: 문제 생성 파이프라인 count 파라미터 전층 관통

**날짜:** 2026-05-20

**상태:** Accepted

### Context

문제 생성 agent(`workbench_question_graph.py`)의 프롬프트가 "총 3개"로 하드코딩되어 있었다. 파이프라인 PoC에서 타겟별 생성 수를 조절할 수 없었고, 전체 생성 상한(`max_questions`)을 추적할 방법이 없었다.

### Decision

`count` 파라미터를 파이프라인 config부터 LLM 프롬프트까지 전층 관통한다:

| 레이어 | 변경 내용 |
|---|---|
| `config.yaml` | `count_per_target`(조합당), `max_questions`(전체 누적 상한) 추가 |
| `pipeline.py` | payload에 `count` 포함, 누적 generated 추적 후 상한 도달 시 break |
| `POST /api/question-workbench/generate` | `GenerateRequest.count` 필드 추가 |
| `gateway_client.generate_questions_workbench` | `count` 파라미터 추가 |
| `WorkbenchState` | `count: int` 필드 추가 |
| LLM 프롬프트 | `"총 3개"` → `f"총 {count}개"` (f-string 동적 주입) |

### Consequences

**장점**
- 파이프라인 실행 시 생성 수를 외부 config로 제어 가능
- 전체 상한(`max_questions`)으로 API 비용·실행 시간 예측 가능

**단점 / 제약**
- `max_questions`는 soft cap — 마지막 배치 완료 후에야 상한 감지
- `count_per_target`이 크면 단일 LLM 응답이 길어져 파싱 실패 위험 증가

---

## ADR-006: 문제조회 탭 기본 필터 및 편집 폼 개선

**날짜:** 2026-05-21

**상태:** Accepted

### Context

파이프라인으로 생성·저장된 문제(`status: draft`)가 Contents Manager 문제조회 탭에서 보이지 않았다. 원인:
- `QuestionWorkbenchTab`이 `status: published` 고정 필터 사용
- `QuestionBankTab`의 기본 필터 `''`(전체)는 archived 포함 — 의도와 다른 기본 상태
- 편집 폼에 `correct_answer`, `difficulty` 필드가 없어 수정 불완전

학생 플랫폼은 `published`만 노출하므로 검수 후 publish하는 워크플로우가 필요했다.

### Decision

1. **기본 필터 변경**: `QuestionBankTab` 기본 상태를 `draft + published`(archived 제외)로 변경 — API 응답을 클라이언트 사이드에서 필터링
2. **편집 폼 완성**:
   - `correct_answer` 직접 입력 추가
   - `difficulty` 드롭다운 추가
   - MCQ 선지 체크박스로 정답 선택 시 `correct_answer` 자동 동기화
3. **백엔드**: `QuestionPatch`에 `difficulty` 필드 추가
4. **저장 API**: `POST /api/question-workbench/questions`에 `question_type`, `difficulty` 필드 반영

검수 워크플로우: pipeline → `draft` 저장 → Contents Manager에서 검수·편집 → "출제 등록" → `published` → 학생 플랫폼 노출.

### Consequences

**장점**
- 파이프라인 생성 문제가 Contents Manager에서 즉시 확인·편집 가능
- archived 문제가 기본 뷰에서 분리되어 노이즈 감소
- 편집 후 바로 출제 등록 가능 — 검수 루프 완성

**단점 / 제약**
- `draft + published` 기본 필터는 클라이언트 사이드 필터링 — API 응답에 archived 포함
- 학생 플랫폼 노출은 수동 publish 필요 — 파이프라인 자동 publish 미구현 (Backlog)
