# EPIC-015 — BKT (Bayesian Knowledge Tracing) 모델

---

## Revision History

| 버전 | 날짜 | 내용 |
|---|---|---|
| v1.0 | 2026-06-02 | 초안 작성 |
| v1.1 | 2026-06-02 | 디렉토리 구조 변경 — BKT 파이프라인을 ml-team/bkt/으로, 산출물을 .data/로 통합 |

---

## 개요

EPIC-013에서 구축한 가상 학생 답변 합성 파이프라인으로 축적된 종단 데이터를 활용하여  
**노드별 BKT 파라미터를 추정**하고, 세션 종료 후 **페르소나 조건부 mastery write-back** 구조를 확립한다.

BKT 모델은 각 지식 컴포넌트(KC = KG 노드)에 대해 4개의 파라미터를 추정한다:
- `p_L0` — 학습 전 초기 지식 보유 확률
- `p_T` — 한 번의 연습 후 모르는 상태 → 아는 상태로 전이 확률
- `p_G` — 모르는 상태에서 정답을 맞출 확률 (guess)
- `p_S` — 아는 상태에서 오답을 낼 확률 (slip)

향후 이 파라미터는 실제 학생의 지식 상태 추론(serving)과 개인 맞춤 문제 추천에 활용된다.

---

## 배경 및 전제

### 파이프라인 실행 구조

`student_answer_generation` 파이프라인을 반복 실행하여 종단 데이터를 축적한다.  
`question_generation` 파이프라인은 별도 진행하지 않으며, 기존에 published된 문제를 활용한다.

```
student_answer_generation 실행 × N
  → 각 실행마다 새 SimulationRun 생성
  → run 완료 후 prior_knowledge_level write-back
  → N회 반복으로 학생별 run 시퀀스 축적

ml-team/bkt/pipeline.py
  → 축적된 시퀀스로 BKT EM 학습
```

### 종단 학습 시퀀스 설계

가상 학생은 `SimulationRun` 단위로 문제를 풀고, 세션 종료 시 성과를 반영하여  
`prior_knowledge_level`이 갱신된다. 다음 세션은 갱신된 값에서 시작한다.

```
run_1 (prior=0.30): [0, 0, 1, 0] → write-back → prior=0.38
run_2 (prior=0.38): [0, 1, 1, 1] → write-back → prior=0.52
run_3 (prior=0.52): [1, 1, 1, 1] → write-back → prior=0.65
```

이 구조에서 `virtual_study_sessions`의 시계열이 BKT 학습의 입력이 된다.

### Interview 모드 제외

`SimulationRun.mode = 'interview'`는 별도 평가 체계를 따르므로 BKT 학습 대상에서 제외.  
BKT는 `mode = 'simple'` run의 답변 데이터만 사용한다.

### Mastery write-back 초기 구현 방식

BKT 파라미터 추정 이전에도 세션 종료 후 write-back이 동작해야 한다.  
초기에는 페르소나 조건부 EMA로 구현하고, BKT 파라미터 확보 후 BKT posterior로 교체한다.

---

## 목표

1. `virtual_study_sessions`에 `run_id` 추가 → 세션 경계 식별 가능
2. 세션 종료 후 페르소나 조건부 `prior_knowledge_level` write-back 구현
3. BKT 학습 파이프라인 구축 → node별 파라미터 추정 및 저장
4. 추후 실제 학생 지식 상태 추론(serving) 및 문제 추천에 사용 가능한 파라미터 확보

---

## 범위

### 포함

- `virtual_study_sessions.run_id` 컬럼 추가 (Alembic 마이그레이션)
- `bkt_node_params` 테이블 추가 (Alembic 마이그레이션)
- 세션 종료 후 `prior_knowledge_level` write-back 로직
  - 위치: `virtual-student-api` (run 완료 시점)
  - 공식: 페르소나 조건부 학습률 적용
- BKT 학습 파이프라인 (`ml-team/bkt/`)
  - Extract: `virtual_study_sessions` + `SimulationRun` (student_platform + virtual-student-api 두 DB)
  - 페르소나 피처 조인 (`virtual_student_feature_values`)
  - Fit: EM 알고리즘으로 node별 p_L0, p_T, p_G, p_S 추정
  - Save: `.data/bkt/` JSON 덤프 + `bkt_node_params` 테이블 upsert

### 제외 (Backlog)

- BKT posterior를 이용한 실시간 mastery 업데이트 (EMA 교체)
- 실제 학생 대상 BKT 추론 serving API
- 개인 맞춤 문제 추천 로직 연동
- 페르소나 그룹별 p_T 분리 추정 (데이터 충분 시 확장)

---

## 설계

### 1. 데이터 흐름

```
[virtual-student-api]            [student_platform DB]
  SimulationRun (run_id)   ──FK──► virtual_study_sessions.run_id (신규)
  VirtualStudentFeatureValue      virtual_node_mastery (기존)
  (prior_knowledge_level)◄─ write-back ─ 세션 종료 시

[BKT 학습 파이프라인]
  Extract
    ├─ virtual_study_sessions (student_platform DB)
    │    (student_id, node_id, run_id, is_correct, created_at)
    ├─ simulation_runs (virtual-student-api DB)
    │    (run_id, created_at) → run 순서 정렬 기준
    └─ virtual_student_feature_values (virtual-student-api DB)
         (prior_knowledge_level, learning_pace, conceptual_depth, ...)
  Format
    (student_id, node_id) 기준 run 순서 정렬 → 응답 시퀀스
  Fit
    pyBKT EM → p_L0, p_T, p_G, p_S per node_id
  Save
    ├─ .data/bkt/bkt_{subject_id}_{ts}.json
    └─ bkt_node_params 테이블 upsert
```

### 2. 페르소나 조건부 learning_rate

세션 종료 후 `prior_knowledge_level` 업데이트 공식:

```python
def compute_learning_rate(persona: dict) -> float:
    base = 0.3

    pace_map  = {"빠름": 1.4, "보통": 1.0, "느림": 0.6}
    depth_map = {"깊음": 1.2, "보통": 1.0, "얕음": 0.8}

    pace_mult  = pace_map.get(persona.get("learning_pace", "보통"), 1.0)
    depth_mult = depth_map.get(persona.get("conceptual_depth", "보통"), 1.0)

    # 낮은 prior일수록 향상 여지가 큼 (천장 효과 보정)
    prior = float(persona.get("prior_knowledge_level", 0.5))
    ceiling_factor = 1.0 - prior * 0.5

    return base * pace_mult * depth_mult * ceiling_factor


def write_back_mastery(old_prior: float, session_score: float, persona: dict) -> float:
    lr = compute_learning_rate(persona)
    delta = (session_score - old_prior) * lr
    return round(min(1.0, max(0.0, old_prior + delta)), 4)
```

### 3. BKT 학습 입력 형식

pyBKT 표준 입력 형식:

```
student_id | skill_name (= node_id) | correct | run_order
-----------+-----------------------+---------+----------
student_A  | node_X                |    0    |     1
student_A  | node_X                |    0    |     1
student_A  | node_X                |    1    |     2
student_A  | node_X                |    1    |     3
student_B  | node_X                |    1    |     1
...
```

- `run_order`: `SimulationRun.created_at` 기준 학생별 run 순번 (1, 2, 3, ...)
- 동일 run 내 여러 응답은 연속된 기회(opportunity)로 처리

### 4. 최소 관측 수 기준

| 조건 | 처리 |
|---|---|
| node당 응답 수 ≥ 30 | EM 추정 |
| node당 응답 수 < 30 | 기본값 사용 (p_L0=0.3, p_T=0.1, p_G=0.2, p_S=0.1) |

---

## DB 스키마 변경

### `virtual_study_sessions` — `run_id` 컬럼 추가

```python
# apps/student-platform/backend/models.py
class VirtualStudySession(Base):
    __tablename__ = "virtual_study_sessions"
    ...
    run_id = Column(String, nullable=True)  # SimulationRun.id 참조 (nullable: 기존 데이터 호환)
```

### `bkt_node_params` — 신규 테이블

```python
class BktNodeParams(Base):
    __tablename__ = "bkt_node_params"
    id           = Column(Integer, primary_key=True)
    subject_id   = Column(String, nullable=False)
    node_id      = Column(String, nullable=False)
    p_l0         = Column(Float, nullable=False)   # prior
    p_t          = Column(Float, nullable=False)   # transit
    p_g          = Column(Float, nullable=False)   # guess
    p_s          = Column(Float, nullable=False)   # slip
    n_students   = Column(Integer)
    n_responses  = Column(Integer)
    trained_at   = Column(DateTime)
    __table_args__ = (UniqueConstraint("subject_id", "node_id", name="uq_bkt_node"),)
```

마이그레이션: `apps/student-platform/backend/migrations/versions/003_add_run_id_and_bkt_params.py`

---

## 디렉토리 구조

```
curriculum-manager/
├── data-team/
│   └── pipeline/
│       └── student_answer_generation/   # 기존 — 산출물 .data/student_answer_generation/ 으로 이동
├── ml-team/                             # 신규
│   └── bkt/                             # BKT 학습 파이프라인
│       ├── pipeline.py
│       ├── bkt_model.py
│       ├── db.py
│       ├── config.yaml
│       └── requirements.txt
└── .data/                               # 신규 — 모든 파이프라인 산출물 통합
    ├── student_answer_generation/       # 기존 data-team/data/output/ 이동
    └── bkt/                             # BKT 파라미터 JSON
```

`.data/`는 `.gitignore`에 추가 (모델 파일·덤프 데이터 커밋 제외).

---

## 신규 파일

### `ml-team/bkt/`

```
ml-team/bkt/
├── pipeline.py      # 메인 — Extract → Format → Fit → Save
├── bkt_model.py     # pyBKT 래퍼: fit(), predict(), to_dict()
├── db.py            # DB 읽기/쓰기 헬퍼 (두 DB)
├── config.yaml      # DB URL, BKT 파라미터
└── requirements.txt # pyBKT, pandas, scikit-learn
```

#### `pipeline.py` CLI

```bash
python pipeline.py            # 전체 실행 (subject_id는 config.yaml에서 읽음)
python pipeline.py --evaluate # RMSE/AUC 검증 포함
python pipeline.py --min-responses 50  # 최소 관측 수 오버라이드
```

#### `db.py` 주요 함수

```python
# student_platform DB
fetch_virtual_sessions(engine, mode='simple') -> list[dict]
    # virtual_study_sessions (run_id 포함)

upsert_bkt_params(engine, params: list[dict]) -> int

# virtual-student-api DB
fetch_simulation_runs(engine, mode='simple') -> dict[str, datetime]
    # {run_id: created_at} — run_order 계산 기준

fetch_persona_features(engine, student_ids: list[str]) -> dict[str, dict]
    # {vs_api_id: {prior_knowledge_level, learning_pace, ...}}

update_prior_knowledge_level(engine, student_id: str, new_value: float)
    # VirtualStudentFeatureValue WHERE feature_key='prior_knowledge_level'
```

#### `config.yaml`

```yaml
subject_id: "<고정 subject UUID>"   # subject는 단일 고정

databases:
  student_platform: "sqlite:///../../../apps/student-platform/backend/student_platform.db"
  virtual_student:  "sqlite:///../../../apps/student-platform/virtual-student-api/data/virtual_students.db"

output_dir: "../../../.data/bkt"

bkt:
  min_responses_per_node: 30
  default_params:
    p_l0: 0.3
    p_t:  0.1
    p_g:  0.2
    p_s:  0.1
  em_max_iter: 100
  em_tol: 1.0e-4
```

---

## 변경 파일

### `apps/student-platform/virtual-student-api/routes/simulate.py`

simple mode run 완료 후 write-back 호출 추가 (`create_simulation_run` 내):

```python
# run 완료, db.commit() 전
for student, fvs, answers in zip(students, all_fvs, all_answers):
    scores = [a["score"] for a in answers if a.get("score") is not None]
    if scores:
        persona = {fv.feature_key: fv.value for fv in fvs}
        old_prior = float(persona.get("prior_knowledge_level", 0.5))
        new_prior = write_back_mastery(old_prior, sum(scores) / len(scores), persona)
        _update_feature_value(db, student.id, "prior_knowledge_level", str(new_prior))
```

### `data-team/pipeline/student_answer_generation/pipeline.py`

`load_to_db()` 내 `insert_study_sessions()` 호출 시 `run_id` 포함 (파이프라인 외부에서 run_id 생성 또는 전달).

---

## 작업 순서

### TICKET-001 — run_id 스키마 추가 및 파이프라인 수정

대상 파일:
- `apps/student-platform/backend/models.py` — `VirtualStudySession.run_id`, `BktNodeParams` 추가
- `apps/student-platform/backend/migrations/versions/003_add_run_id_and_bkt_params.py` 작성
- `data-team/pipeline/student_answer_generation/pipeline.py` — `run_id` 전달
- `data-team/pipeline/student_answer_generation/config.yaml` — `output_dir` → `../../../.data/student_answer_generation`
- `.data/student_answer_generation/` 디렉토리 생성 (`.gitkeep` 포함)
- `.gitignore` — `.data/` 추가

### TICKET-002 — 페르소나 조건부 mastery write-back

대상 파일:
- `apps/student-platform/virtual-student-api/routes/simulate.py` — write-back 로직 추가
- `apps/student-platform/virtual-student-api/routes/simulate.py` — `compute_learning_rate()`, `write_back_mastery()` 함수 추가
- `apps/student-platform/virtual-student-api/database.py` 또는 헬퍼 — `update_prior_knowledge_level()` 추가

### TICKET-003 — BKT 학습 파이프라인

대상 파일 (신규):
- `ml-team/bkt/config.yaml`
- `ml-team/bkt/requirements.txt`
- `ml-team/bkt/db.py`
- `ml-team/bkt/bkt_model.py`
- `ml-team/bkt/pipeline.py`
- `.data/bkt/` 디렉토리 생성 (`.gitkeep` 포함)
- `.gitignore` — `.data/` 추가

### TICKET-004 — 검증

검증 항목:
- write-back 후 여러 run에 걸쳐 `prior_knowledge_level`이 단조증가 추세인지
- BKT 추정 노드의 p_L0 분포가 데이터 초기 정답률과 유사한지
- p_T > 0 인 노드(학습 전이 감지)가 존재하는지
- `bkt_node_params` 기본값 처리 노드 비율 확인

---

## 검증 시나리오

```bash
# 1. 마이그레이션 적용
cd apps/student-platform/backend && alembic upgrade head

# 2. 가상 학생 데이터 수집 (반복 실행으로 run 시퀀스 축적)
cd data-team/pipeline/student_answer_generation
python pipeline.py  # N회 반복
# → .data/student_answer_generation/student_answers_*.json

# 3. BKT 학습
cd ml-team/bkt
python pipeline.py --evaluate

# 기대 출력:
# [1/4] 세션 데이터 추출 중...  → N개 응답 (M명 학생, K개 노드)
# [2/4] run 순서 정렬 및 포맷 변환...
# [3/4] BKT EM 학습 중...  → K개 노드 추정 완료 (X개 기본값 사용)
# [4/4] 파라미터 저장...  → .data/bkt/bkt_{ts}.json / DB K개 upsert
# AUC: 0.xx  RMSE: 0.xx

# 4. DB 확인
SELECT node_id, p_l0, p_t, p_g, p_s, n_responses
FROM bkt_node_params
WHERE subject_id = '<uuid>'
ORDER BY p_t DESC;
```

---

## 향후 진화 경로

```
현재  write-back:  페르소나 조건부 EMA
향후  write-back:  BKT posterior (p_T 추정 후 교체)

현재  BKT:        단일 모델, node-level 파라미터
향후  BKT:        페르소나 그룹별 p_T 분리 (learning_pace 기준 3그룹)

현재  저장:        JSON + SQLite bkt_node_params
향후  serving:     FastAPI endpoint → 실시간 P(knows|응답이력) 추론
                   개인 맞춤 문제 추천 연동
```
