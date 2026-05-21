# EPIC-013 — 가상 학생 답변 합성 데이터 파이프라인

---

## Revision History

| 버전 | 날짜 | 내용 |
|---|---|---|
| v1.0 | 2026-05-21 | 초안 작성 |
| v1.1 | 2026-05-21 | 구현 반영 — 학생 소스·스키마·페르소나 변경 (하단 상세) |

---

### v1.1 변경 상세 (초안 → 구현)

#### 1. Extract 소스: 실제 학생 → 가상 학생

**초안:** `student_platform.students` (실제 학생 계정) 기준으로 추출  
**변경:** `virtual-student-api`의 `virtual_students` 테이블 기준으로 추출

가상 답변 합성의 목적이 추천·숙련도 알고리즘 테스트이므로, 실제 사용자 계정이 아닌 virtual-student-api에서 생성된 가상 학생이 대상이 되어야 함.

---

#### 2. 페르소나 구성: node_mastery 평균 → feature_values 직접 사용

**초안:** `avg(node_mastery)` → `prior_knowledge_level` 매핑 후 기본값 혼합  
**변경:** `virtual_student_feature_values`의 feature 값을 그대로 persona dict로 사용

가상 학생은 이미 생성 시점에 `prior_knowledge_level`, `conceptual_depth`, `reasoning_style` 등 feature를 갖고 있음. node_mastery 평균 추정 불필요.

```python
# 변경 전
persona = build_from_mastery_avg(student["node_mastery"])

# 변경 후
persona = fetch_virtual_student_features(vs_engine, student["vs_api_id"])
# → {prior_knowledge_level: 0.32, conceptual_depth: "표면적", reasoning_style: "단계적", ...}
```

---

#### 3. DB 스키마: 기존 테이블 직접 사용 → 가상 학생 전용 테이블 3개 추가

**초안:** 기존 `study_sessions`, `node_mastery` 직접 사용. Alembic 마이그레이션 없음.  
**변경:** 신규 테이블 3개 추가 (Alembic `002_virtual_tables`)

**원인:** `study_sessions.student_id`와 `node_mastery.student_id`가 `INTEGER FK → students(id)` 구조인데, 가상 학생 ID는 UUID(VARCHAR). 기존 테이블에 직접 삽입 불가.

**추가 테이블:**

| 테이블 | 설명 |
|---|---|
| `virtual_students` | student_platform 내 가상 학생 mirror. `id INTEGER PK`, `vs_api_id VARCHAR UNIQUE` (virtual-student-api UUID 참조) |
| `virtual_study_sessions` | `study_sessions`와 동일 스키마. `student_id INTEGER FK → virtual_students(id)` |
| `virtual_node_mastery` | `node_mastery`와 동일 스키마. `student_id INTEGER FK → virtual_students(id)` |

기존 `students`, `study_sessions`, `node_mastery` 테이블 **무변경**.

---

#### 4. DB 연결: 2개 → 3개

**초안:** `student_platform`, `contents_manager`  
**변경:** `virtual_student` DB 추가 (feature values 직접 읽기)

```yaml
# config.yaml
databases:
  student_platform: "sqlite:///..."
  contents_manager: "sqlite:///..."
  virtual_student:  "sqlite:///..."   # virtual-student-api DB (docker cp로 추출)
```

---

#### 5. 가상 학생 동기화 메커니즘 추가

**초안:** 해당 없음  
**변경:** virtual-student-api 가상 학생 생성 시 student_platform에 자동 동기화

- `virtual-student-api/routes/virtual_students.py`: `create_virtual_student` 완료 후 `POST {STUDENT_PLATFORM_URL}/virtual-students` 호출 (`STUDENT_PLATFORM_URL` 환경변수 활용)
- `student_platform/routes/virtual_students.py`: 동기화 수신 엔드포인트 `POST /virtual-students`, `GET /virtual-students` 추가

동기화 실패 시 가상 학생 생성은 계속 진행 (best-effort).  
기존 등록 학생은 최초 파이프라인 실행 전 수동 동기화 스크립트로 일괄 처리.

---

#### 6. Load 대상 변경

**초안:** `study_sessions`, `node_mastery`  
**변경:** `virtual_study_sessions`, `virtual_node_mastery`

`db.py`의 `insert_study_sessions()`, `upsert_node_mastery()`, `fetch_answered_question_ids()` 모두 virtual 테이블 대상으로 변경.

---

## 개요

학생 플랫폼에 실제 학습 데이터가 축적되기 전에,  
실제 학생 프로파일(숙련도)을 기반으로 가상 답변 데이터를 합성하여  
`study_sessions` / `node_mastery` 테이블을 채운다.

추천 알고리즘·숙련도 분석·대시보드를 실 데이터 없이 검증하기 위한 목적이다.

---

## 목표

- 실제 학생 프로파일(mastery)을 페르소나로 변환하여 현실적인 합성 답변 생성
- 학생 플랫폼의 `study_sessions`, `node_mastery` 테이블에 합성 데이터 적재
- 추천·숙련도 알고리즘 테스트 환경 조성
- 향후 Kafka 기반 스트리밍 파이프라인으로의 확장 경로 확보

---

## 설계 원칙

**순수 데이터 파이프라인 방식** (ETL):

| 단계 | 수단 | 대상 |
|---|---|---|
| Extract | DB 직접 읽기 | 학생 프로파일 + 숙련도 (student_platform DB) |
| Extract | DB 직접 읽기 | 발행된 문제 (contents_manager DB) |
| Transform | HTTP API 호출만 | Virtual Student API → 답변 + 채점 |
| Load | DB 직접 쓰기 | study_sessions, node_mastery (student_platform DB) |

API 호출은 답변·채점 획득 단계에만 사용.  
학생 계정 관리, 인증 토큰, 관리자 엔드포인트 불필요.

---

## 파이프라인 흐름

```
[student_platform DB]       [contents_manager DB]
  students                     question_items
  node_mastery                 (status='published')
       │                              │
       ▼                              ▼
  Step 1: 학생 프로파일 추출    Step 2: 문제 목록 추출
       │                              │
       └──────────┬───────────────────┘
                  │
                  ▼
       Step 3: Target 선정
       이미 study_sessions에 있는 (student × question) 제외
                  │
                  ▼
       Step 4: 가상 답변 생성 ──────► [Virtual Student API]
       학생 mastery → 페르소나 구성     POST /api/simulate/generate-and-grade
       학생 1인당 배치 호출             (persona + questions[] 배치)
       → answer_text, is_correct,
         score, feedback
                  │
                  ▼
       Step 5: 파일 덤프
       data/output/student_answers_{subject_id8}_{UTC}.json
                  │
                  ▼
       Step 6: DB 직접 적재
  [student_platform DB]
    INSERT study_sessions
    UPSERT node_mastery (EMA 공식)
```

---

## 범위

### 포함

- `data-team/pipeline/student_answer_generation/` 신규 파이프라인
  - `pipeline.py` — 6-step ETL 실행기
  - `db.py` — SQLAlchemy 기반 DB 읽기/쓰기 헬퍼
  - `config.yaml` — DB URL, API URL, 실행 파라미터
- Virtual Student API 신규 엔드포인트
  - `POST /api/simulate/generate-and-grade` — 인라인 페르소나 + 배치 문제 → 배치 답변+채점
  - stateless (가상 학생 DB 레코드 생성/삭제 없음)
- 페르소나 매핑: `avg(node_mastery)` → `prior_knowledge_level` (0.0~1.0)
- 덤프 파일 → 재적재(`--load-and-save`) 지원

### 제외 (Backlog)

- Kafka 연동 (향후: 파일 덤프 → Kafka Producer 교체)
- CDC 연동 (향후: DB dump → CDC 전용 테이블 교체)
- 자동 스케줄링 (Airflow / Celery)
- 학생 플랫폼 관리자 API 엔드포인트 추가

---

## 신규 파일

### `data-team/pipeline/student_answer_generation/`

#### `pipeline.py`

```python
class StudentAnswerPipeline:
    fetch_students()            # DB 직접 읽기 — 학생 + node_mastery
    fetch_questions()           # DB 직접 읽기 — published question_items
    select_targets()            # 미답변 (student × question) 필터
    generate_and_dump()         # Virtual Student API 배치 호출 + 파일 덤프
    load_to_db()                # DB 직접 쓰기 — study_sessions + node_mastery
```

CLI:
```bash
python pipeline.py --subject-id <id>              # 전체 실행
python pipeline.py --subject-id <id> --dry-run    # Target 선정까지만
python pipeline.py --load-and-save <dump_file>    # 덤프 파일 → DB 재적재
```

#### `db.py`

```python
fetch_students(engine, subject_id) -> list[dict]
    # students JOIN node_mastery → {id, name, node_mastery: [{node_id, mastery_score}]}

fetch_questions(engine, subject_id, question_types) -> list[dict]
    # question_items WHERE status='published' AND entity_id IN kg_nodes(subject_id)

fetch_answered_pairs(engine, student_id) -> set[tuple[int, str]]
    # (student_id, question_id) 집합

insert_study_sessions(engine, rows: list[dict])
    # bulk INSERT

upsert_node_mastery(engine, student_id, node_id, is_correct, score)
    # EMA: correct → min(1.0, cur + (1-cur)*0.3*score)
    #       wrong  → max(0.0, cur - cur*0.2)
    # INSERT ... ON CONFLICT DO UPDATE
```

#### `config.yaml`

```yaml
databases:
  student_platform: "postgresql://user:pass@localhost:5432/student_platform"
  contents_manager: "postgresql://user:pass@localhost:5432/contents_manager"

api:
  virtual_student_url: "http://localhost:8002"

output_dir: "../../data/output"

simulation:
  max_students: 20
  max_questions_per_student: 50
  question_types: ["MCQ", "OX", "short_answer"]
  request_timeout: 30

persona:
  mastery_to_knowledge_level: true
  default_features:
    conceptual_depth: "보통"
    reasoning_style: "단계적"
    verbosity: "보통"
```

---

## Virtual Student API 변경

### 신규 엔드포인트: `POST /api/simulate/generate-and-grade`

**파일:** `apps/student-platform/virtual-student-api/routes/simulate.py`

**Request:**
```json
{
  "persona": {
    "prior_knowledge_level": 0.7,
    "conceptual_depth": "깊은",
    "reasoning_style": "분석적",
    "verbosity": "보통"
  },
  "questions": [
    {
      "question_id": "uuid",
      "question_text": "...",
      "question_type": "MCQ",
      "options": [{"label": "A", "text": "..."}, ...],
      "correct_answer": "A"
    }
  ]
}
```

**Response:**
```json
[
  {
    "question_id": "uuid",
    "answer_text": "A",
    "is_correct": true,
    "score": 1.0,
    "feedback": "정확한 답변입니다."
  }
]
```

내부 재사용: `_build_persona_prompt()`, `persona_agent.generate_answer()`, `_grade()`.  
가상 학생 DB 레코드 불필요 — stateless.

---

## 덤프 파일 포맷

```json
{
  "subject_id": "...",
  "generated_at": "20260521T120000",
  "stats": {
    "students": 10,
    "total_targets": 300,
    "success": 295,
    "failed": 5
  },
  "answers": [
    {
      "student_id": 42,
      "question_id": "uuid",
      "node_id": "entity_id",
      "subject_id": "...",
      "question_text": "...",
      "question_type": "MCQ",
      "correct_answer": "A",
      "user_answer": "A",
      "is_correct": true,
      "score": 1.0,
      "feedback": "...",
      "time_taken_seconds": 0
    }
  ]
}
```

---

## 향후 진화 경로

```
현재  Extract:   DB dump (SQLAlchemy 직접 쿼리)
향후  Extract:   CDC 연동 전용 테이블

현재  Load:      파일 덤프 → DB 직접 쓰기 (pipeline.py 단일 프로세스)
향후  Load:      Kafka Producer (답변 결과) → Kafka Consumer (DB 적재, 별도 서비스)
```

파일 덤프 단계가 Kafka Producer로, `--load-and-save` 단계가 Consumer로 자연스럽게 전환.

---

## Alembic 마이그레이션

`apps/student-platform/backend/migrations/versions/002_virtual_tables.py`

- `virtual_students` — INTEGER PK, vs_api_id UNIQUE, name, subject_id
- `virtual_study_sessions` — study_sessions와 동일, student_id FK → virtual_students
- `virtual_node_mastery` — node_mastery와 동일, student_id FK → virtual_students

---

## 검증

```bash
# 0. DB 파일 준비 (Docker 볼륨에서 추출)
docker cp student-platform-backend:/app/db/student_platform.db ./sp.db
docker cp contents-manager-backend:/app/cm_db/contents_manager.db ./cm.db
docker cp virtual-student-api:/app/data/virtual_students.db ./vs.db

# 1. dry-run — 가상 학생 + 문제 확인
python pipeline.py --subject-id <id> --dry-run
# → "가상 학생 N명 (virtual_students 테이블) / 총 K개 답변 예정"

# 2. 전체 실행
python pipeline.py --subject-id <id>
# → data/output/student_answers_*.json
# → "virtual_study_sessions: K개 INSERT / virtual_node_mastery: K개 UPSERT"

# 3. 재적재
python pipeline.py --load-and-save data/output/student_answers_xxx.json

# 4. DB 확인
SELECT vs.name, count(*), avg(vss.score)
FROM virtual_study_sessions vss
JOIN virtual_students vs ON vs.id = vss.student_id
GROUP BY vs.id;

SELECT vs.name, vnm.node_id, vnm.mastery_score, vnm.attempt_count
FROM virtual_node_mastery vnm
JOIN virtual_students vs ON vs.id = vnm.student_id;
```
