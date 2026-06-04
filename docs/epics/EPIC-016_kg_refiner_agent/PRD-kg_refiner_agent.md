# EPIC-016 — KG Refiner Agent

---

## Revision History

| 버전 | 날짜 | 내용 |
|---|---|---|
| v1.0 | 2026-06-03 | 초안 작성 |
| v1.1 | 2026-06-03 | T_STRUCTURE/T_STUDENT 목적 구분 명확화, 이상 노드 검출 연산 확정 |

---

## 개요

기존에 생성된 Knowledge Graph(KG)를 자동으로 조회·분석하여  
노드 및 엣지의 계층 구조·연결 관계를 개선하는 LangGraph 기반 에이전트.

두 가지 트리거로 동작하며, 목적이 명확히 다르다:

| 트리거 | 목적 |
|---|---|
| **T_STRUCTURE** | 서브그래프 일괄 추출 → 에이전트 컨텍스트 주입 → 구조 검토 및 개선 제안 |
| **T_STUDENT** | 학생 문제풀이 데이터 기반 이상 노드 검출 → 원인 조사 및 재설계 제안 |

---

## 설계 원칙

**이상 노드 사전 필터링 (T_STUDENT):**
- 모든 노드를 에이전트가 탐색하게 하지 않음
- 백엔드에서 수학적 스코어를 계산해 이상 노드 TOP-K만 에이전트에 전달
- 에이전트는 원인 분석과 재설계 제안에만 집중

**CQRS 읽기 모델:**
- KG 구조 데이터: Neo4j (kg_neo4j_migration 파이프라인 이후 목적지)
- 학생 통계 데이터: student_platform.db (운영 DB)
- 두 소스를 읽는 전용 API를 contents-manager service layer에 추가

---

## 트리거 상세

### T_STRUCTURE — 서브그래프 컨텍스트 주입

**목적:** 에이전트가 KG 구조를 직접 검토하고 개선을 제안할 수 있도록 서브그래프 전체를 컨텍스트로 주입

**동작 방식:**
```
subject_id (또는 subgraph 범위 지정)
  → Neo4j에서 해당 범위 노드·엣지 일괄 추출
  → 에이전트에 서브그래프 전체를 컨텍스트로 주입
  → 에이전트: 구조 검토 + 개선 제안 생성
```

**에이전트 역할:**
- 노드 간 계층·연결 관계 검토
- 온톨로지 규칙(depth_range, valid_pairs) 준수 여부 확인
- 개선 제안 생성: Split / Merge / Relink / Reorder

---

### T_STUDENT — 학생 데이터 기반 이상 노드 검출

#### 분석 대상

- **노드 타입:** `Concept` 타입 노드만 대상
- **엣지 기준:** `requires` / `has_subtopic` 관계의 후행 노드

#### 탐지 목표: 개념 해상도 부족 노드

노드 A의 개념이 너무 넓으면(하위 개념 혼재), A를 학습한 학생들 사이에서도  
A의 후행 노드(B, C, D)에 대한 학습 성과 패턴이 갈린다.

```
A 학습 학생군
 ├── 그룹 1: B(높음) C(높음) D(낮음)
 └── 그룹 2: B(낮음) C(낮음) D(높음)
```

A가 B, C, D를 일관되게 게이팅하지 못함  
→ A는 실제로 두 개 이상의 하위 개념을 포함하는 이상 노드

#### 이상 스코어 계산

**1단계: mastery_snapshot 기반 level_weight 산출**

문제를 푼 당시의 학생 숙달 수준(`mastery_snapshot`)을 레벨로 구간화하여 정답 신호에 가중치를 부여한다.  
수준이 높은 학생이 틀리면 강한 이상 신호, 수준이 낮은 학생이 틀리면 약한 신호로 처리한다.

```
mastery_snapshot 구간 → level_weight

LOW  (0.0 ~ 0.4) : weight = 0.5   # 낮은 수준에서 오답은 예상 범위
MID  (0.4 ~ 0.7) : weight = 1.0   # 중립
HIGH (0.7 ~ 1.0) : weight = 1.5   # 높은 수준에서 오답은 강한 이상 신호
```

**2단계: weighted_score 계산**

```
weighted_score = is_correct × level_weight(mastery_snapshot)
```

**3단계: 후행 노드 간 weighted_score 상관 계산**

```
대상: 후행 노드(requires / has_subtopic)가 3개 이상인 Concept 노드
계산: 후행 노드 B, C, D 별 weighted_score의 학생 간 pairwise 상관계수
이상 스코어: 1 - avg_correlation  (낮은 상관 = 높은 이상 스코어)
필터: 샘플 학생 수 >= 10
출력: 이상 스코어 상위 TOP-K 노드
```

**데이터 소스:**
- `virtual_study_sessions` — question_id, is_correct, **session_id** (신규 FK)
- `virtual_answer_sessions` — session_id, student_id, node_id, **mastery_before** (신규)
- `kg_edges` — 후행 노드 목록 (relation_type: requires / has_subtopic)

**조회 예시:**
```sql
SELECT ss.question_id, ss.is_correct, vas.mastery_before, vas.node_id
FROM virtual_study_sessions ss
JOIN virtual_answer_sessions vas ON vas.id = ss.session_id
WHERE vas.node_id IN (후행 노드 목록)
  AND vas.subject_id = :subject_id
```

**에이전트 역할:**
- 이상 노드의 KG 맥락(연결 노드·엣지·depth) 조사
- 원인 추론: 개념 범위 과대 / 하위 개념 혼재
- 재설계 제안: Split (하위 노드 분리 + 엣지 재연결)

> **향후 확장:** T_STUDENT는 현재 이 분석 하나만 포함. 추가 이상 탐지 기준은 별도 티켓으로 관리.

---

## 스키마 변경

### virtual_answer_sessions — 신규 테이블

학습 세션 단위로 mastery 스냅샷을 기록하는 테이블.  
`question_id → session_id → mastery_before` 연결로 문제 풀이 당시 학생 수준을 정확히 추적한다.

```sql
CREATE TABLE virtual_answer_sessions (
    id          TEXT PRIMARY KEY,
    student_id  INTEGER NOT NULL REFERENCES virtual_students(id),
    node_id     TEXT NOT NULL,
    subject_id  TEXT NOT NULL,
    mastery_before FLOAT,   -- 세션 시작 시점 mastery (가중치 연산 기준)
    mastery_after  FLOAT,   -- 세션 종료 후 EMA 업데이트 결과
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### virtual_study_sessions — session_id FK 추가

```sql
ALTER TABLE virtual_study_sessions
ADD COLUMN session_id TEXT REFERENCES virtual_answer_sessions(id);
```

이로써 세 가지 정보가 연결된다:
```
virtual_study_sessions.question_id     → 어떤 문제를
virtual_study_sessions.session_id      → 어떤 학습 세션에서 풀었고
virtual_answer_sessions.mastery_before → 당시 학생 수준이 얼마였는지
```

**Alembic 마이그레이션:** `003_virtual_answer_sessions`

### pipeline.py load_to_db 순서 변경

```
현재: 전체 벌크 INSERT → 그룹별 mastery upsert

변경: (student, node) 그룹별로
  ① virtual_node_mastery 조회 → mastery_before 확보
  ② virtual_answer_sessions INSERT (id, student_id, node_id, mastery_before)
  ③ virtual_study_sessions INSERT (session_id FK 포함)
  ④ mastery upsert (EMA 업데이트) → mastery_after 확보
  ⑤ virtual_answer_sessions UPDATE (mastery_after 기록)
```

---

## API 명세

두 API 모두 contents-manager 백엔드 service layer에 추가.

### GET /kg/subgraph/{subject_id}

**소스:** Neo4j  
**용도:** T_STRUCTURE 컨텍스트 주입용 서브그래프 추출

**쿼리 파라미터:**

| 파라미터 | 설명 | 기본값 |
|---|---|---|
| `node_types` | 추출할 노드 타입 필터 | 전체 |
| `depth` | 서브그래프 탐색 깊이 | null (전체) |
| `root_node_id` | 특정 노드 중심 서브그래프 | null (전체) |

**응답:**
```json
{
  "subject_id": "...",
  "nodes": [{"id": "...", "name": "...", "type": "Seed", "depth": 1}],
  "edges": [{"source_id": "...", "target_id": "...", "relation_type": "requires"}]
}
```

---

### GET /kg/analytics/node-resolution/{subject_id}

**소스:** student_platform.db  
**용도:** T_STUDENT 이상 노드 검출 (Concept 타입 전용)

**쿼리 파라미터:**

| 파라미터 | 설명 | 기본값 |
|---|---|---|
| `top_k` | 반환할 이상 노드 수 | 50 |
| `min_students` | 최소 샘플 학생 수 | 10 |
| `min_successors` | 후행 노드 최소 수 | 3 |

**응답:**
```json
{
  "subject_id": "...",
  "computed_at": "2026-06-03T12:00:00Z",
  "anomalies": [
    {
      "node_id": "uuid",
      "name": "Database Indexing Strategies",
      "type": "Concept",
      "depth": 1,
      "successor_count": 6,
      "avg_successor_correlation": 0.21,
      "anomaly_score": 0.79,
      "sample_students": 34
    }
  ]
}
```

---

## 아키텍처

### contents-manager — 신규 service layer

```
apps/contents-manager/backend/
├── services/
│   ├── subgraph_service.py           # Neo4j 서브그래프 추출
│   └── node_resolution_service.py    # student_platform.db 이상 노드 계산
└── routes/
    └── kg_analytics.py               # 두 엔드포인트 라우터 등록
```

### kg-refiner 에이전트

```
agent-platform/agents/kg-refiner/
├── cli.py
├── skills/
│   ├── structure_skill.md            # T_STRUCTURE 시스템 프롬프트
│   └── student_skill.md              # T_STUDENT 시스템 프롬프트
└── src/
    ├── harness.py                    # 트리거 디스패처 (T_STRUCTURE / T_STUDENT)
    └── graphs/
        ├── structure_graph.py        # 서브그래프 검토 LangGraph
        └── student_graph.py          # 이상 노드 조사 LangGraph
```

### LangGraph 노드 구성

**T_STRUCTURE:**
```
fetch_subgraph → review → propose → validate → write
```

**T_STUDENT:**
```
fetch_anomalies → investigate → propose → validate → write
```

| 노드 | 역할 |
|---|---|
| `fetch_subgraph` | `GET /kg/subgraph/{subject_id}` 호출 |
| `fetch_anomalies` | `GET /kg/analytics/node-resolution/{subject_id}` 호출 |
| `review` / `investigate` | LLM: 구조 검토 또는 이상 원인 분석 |
| `propose` | LLM: 개선 제안 생성 (Split / Merge / Relink / Reorder) |
| `validate` | LLM: 온톨로지 규칙 준수 검증 |
| `write` | 제안 JSON 저장 (`logs/proposals_*.json`) |

---

## 개선 제안 출력 포맷

```json
{
  "subject_id": "...",
  "trigger": "T_STUDENT",
  "generated_at": "2026-06-03T12:00:00Z",
  "proposals": [
    {
      "proposal_id": "uuid",
      "type": "split",
      "target_node_id": "uuid",
      "target_node_name": "Database Indexing Strategies",
      "reason": "후행 노드 weighted_score 평균 상관 0.21 — 하위 개념 혼재 의심",
      "suggestion": {
        "new_nodes": [
          {"name": "B-Tree Index Design", "type": "Concept", "depth": 2},
          {"name": "Hash Index & Full-text Search", "type": "Concept", "depth": 2}
        ],
        "edges_to_remove": ["edge-id-1"],
        "edges_to_add": [
          {"source": "parent-id", "target": "new-node-1", "relation": "has_subtopic"},
          {"source": "parent-id", "target": "new-node-2", "relation": "has_subtopic"}
        ]
      },
      "ontology_valid": true,
      "confidence": 0.78
    }
  ]
}
```

---

## Docker Compose

```yaml
kg-refiner:
  port: 8007
  env:
    - CONTENTS_MANAGER_URL=http://contents-manager-backend:8010
    - STUDENT_PLATFORM_DB_PATH=/app/db/student_platform.db
```

---

## 트리거 CLI

```bash
# 서브그래프 검토
python cli.py --trigger T_STRUCTURE --subject-id <id>

# 이상 노드 탐지 + 재설계
python cli.py --trigger T_STUDENT --subject-id <id> --top-k 30
```

---

## 구현 범위 요약

| 항목 | 위치 | 내용 |
|---|---|---|
| virtual_answer_sessions 테이블 추가 | student-platform Alembic `003` | 세션 단위 mastery_before/after 기록 |
| virtual_study_sessions session_id FK 추가 | student-platform Alembic `003` | question → session → mastery 연결 |
| load_to_db 순서 변경 | data-team/pipeline/student_answer_generation | 그룹별 session 생성 + mastery 캡처 |
| subgraph_service.py | contents-manager/services | Neo4j 서브그래프 추출 |
| node_resolution_service.py | contents-manager/services | weighted_score 상관 기반 이상 노드 계산 |
| kg_analytics.py | contents-manager/routes | 두 엔드포인트 등록 |
| kg-refiner 에이전트 스캐폴딩 | agent-platform/agents/kg-refiner | harness + 2개 graph |
| Docker Compose | infra/docker-compose.local.yml | kg-refiner 서비스 8007 추가 |

---

## 미결 사항

| 항목 | 내용 |
|---|---|
| student_platform.db 접근 | contents-manager에서 직접 파일 마운트 vs. student-platform API 경유 |
| 제안 결과물 저장 | `logs/` JSON vs. contents-manager DB 별도 테이블 |
| 개선안 반영 | 운영자 수동 검토 후 적용 vs. 승인 workflow 연동 |
| T_STUDENT 추가 분석 | 향후 별도 티켓으로 확장 |
