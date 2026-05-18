# [PRD] Interview Agent

## 1. 개요 (Overview)

EPIC-006에서 구축한 Competency Rubric(blueprint clearance + node mastery)을 기반으로, **가상 인터뷰를 통해 학생의 이해도를 진단하는 멀티턴 AI 에이전트**를 구현한다.

학생은 채팅 형식으로 AI 면접관과 대화하며, 에이전트는 매 턴마다 학생의 지식 상태를 갱신하고 약점을 추적하여 다음 질문을 동적으로 생성한다. 세션 종료 시 최종 진단 리포트를 산출한다.

> **의존:** EPIC-005 Question Bank, EPIC-006 Competency Rubric이 완성된 이후 진행한다.

---

## 2. 제품 원칙 (Product Principles)

**동적 질문 생성:** 사전 문항 풀을 사용하지 않는다. 매 턴마다 학생의 현재 지식 상태를 컨텍스트로 LLM이 새 질문을 생성한다.

**Subject 단위 인터뷰:** 인터뷰는 반드시 특정 subject를 선택한 후 시작한다. 해당 subject 하위 노드·blueprint만 대상으로 한다.

**In-memory 상태 관리:** 세션 진행 중 mastery/clearance 갱신은 LangGraph State(메모리)에서만 수행한다. DB 쓰기는 세션 종료 시 한 번에 커밋한다. 중도 이탈 시 State가 소멸되어 DB에 아무것도 반영되지 않는다.

**No Resume:** 세션은 재개(resume)를 지원하지 않는다. 중도 이탈한 세션은 폐기된다.

**비침습적 통합:** 기존 mastery/clearance 산출 로직(EMA, blueprint weighted score)을 재사용한다. 인터뷰 최종 점수는 α=0.3으로 EMA에 합산한다.

**진단 중심:** 단순 점수 산출이 아닌 "어떤 노드·blueprint가 약한가"를 shape로 보존한 최종 리포트를 목표로 한다.

---

## 3. 핵심 개념

### Interview Session

학생이 시작한 하나의 인터뷰 세션. `active` → `completed` 상태를 가진다.

### Interview Turn

한 턴 = 질문 1개 + 학생 답변 1개 + 평가 결과. 세션은 N개의 턴으로 구성된다.

### Knowledge State Snapshot

세션 시작 시점에 DB에서 로드하는 학생 지식 상태 (subject 범위로 필터):
```
{
  subject_id: "...",
  node_mastery: { node_id: mastery_score, ... },      // 해당 subject 노드별 이해도 (0~1)
  blueprint_clearance: { blueprint_id: cleared, ... } // 해당 subject blueprint 달성 여부
}
```
이 snapshot은 LangGraph State에 복사되어 세션 내내 in-memory로 갱신된다. 세션 종료 시에만 DB에 반영된다.

### Adaptive Question Strategy

매 턴 종료 후 에이전트는 두 가지 경로 중 하나를 선택한다:

- **Follow-up:** 직전 답변에서 불확실하거나 얕게 답한 부분을 심화 질문
- **Pivot:** 아직 다루지 않은 약점(낮은 mastery 또는 미달성 blueprint)으로 전환

### Interview Diagnosis

세션 종료 시 산출되는 최종 진단:
```
strengths:    잘 이해된 노드/blueprint 목록
weaknesses:   취약한 노드/blueprint 목록 + 근거
overall_band: 전반적 이해도 등급 (S/A/B/C/D)
recommendations: 다음 학습 우선순위 제안
```

---

## 4. 핵심 기능 명세

### Feature 7.1: Interview Session API (Student Backend)

**대상:** `student-platform/backend`

**엔드포인트:**

| Method | Path | 설명 |
|---|---|---|
| `POST` | `/api/interview/sessions` | 세션 시작 — subject_id 필수, knowledge state snapshot 생성, 첫 질문 반환 |
| `GET` | `/api/interview/sessions/{id}` | 세션 상태 + 턴 이력 조회 |
| `POST` | `/api/interview/sessions/{id}/answer` | 답변 제출 → 평가 + 다음 질문 반환 |
| `POST` | `/api/interview/sessions/{id}/end` | 세션 종료 → 최종 진단 반환 |
| `GET` | `/api/interview/sessions/{id}/diagnosis` | 진단 리포트 조회 |

**요청/응답 예시 (answer 제출):**
```json
// POST /api/interview/sessions/{id}/answer
// Request
{ "answer": "학생 답변 텍스트" }

// Response
{
  "turn": {
    "turn_number": 3,
    "question": "방금 언급한 개념의 시간복잡도를 설명해주세요.",
    "score": 0.72,
    "feedback": "핵심 개념은 파악했으나 엣지 케이스 설명이 부족합니다.",
    "updated_nodes": ["node_id_1"],
    "updated_blueprints": []
  },
  "session_status": "active"
}
```

---

### Feature 7.2: Interview Agent (LangGraph)

**대상:** `agent-platform/agents/interview-agent`

**그래프 구조:**

```
[START]
  │
  ▼
load_knowledge_state       ← node mastery + blueprint clearance 로드
  │
  ▼
select_target              ← 약점 노드/blueprint 선택 (mastery 낮은 순)
  │
  ▼
generate_question          ← LLM: 컨텍스트 기반 동적 질문 생성
  │
  ▼
[HUMAN_IN_LOOP: 학생 답변 대기]
  │
  ▼
evaluate_answer            ← LLM: 답변 채점 + 피드백 + 이해도 추정
  │
  ▼
update_knowledge_state     ← mastery EMA 갱신, blueprint clearance 재계산
  │
  ▼
decide_next_action ────────→ [end_session] → generate_diagnosis
  │
  └──────────────────────→ [follow_up | pivot] → generate_question (루프)
```

**노드별 책임:**

| 노드 | 입력 | 출력 |
|---|---|---|
| `load_knowledge_state` | student_id | node_mastery, blueprint_clearance |
| `select_target` | knowledge_state | target_nodes, target_blueprints |
| `generate_question` | target, conversation_history | question_text |
| `evaluate_answer` | question, answer, target | score (0~1), feedback, demonstrated_concepts |
| `update_knowledge_state` | score, demonstrated_concepts | updated mastery/clearance |
| `decide_next_action` | turn_count, coverage, min_mastery | follow_up \| pivot \| end |
| `generate_diagnosis` | session_history, final_state | diagnosis |

**세션 종료 조건 (모두 OR):**
- 학생이 직접 종료 요청
- 최대 턴 수 도달 (기본 15턴)
- 핵심 노드 전체 커버 + 약점 해소 확인

---

### Feature 7.3: DB 모델 (Student Backend)

```sql
-- 인터뷰 세션
CREATE TABLE interview_sessions (
  id            UUID PRIMARY KEY,
  student_id    UUID REFERENCES students(id),
  subject_id    UUID NOT NULL,               -- 인터뷰 대상 subject (필수)
  status        VARCHAR(20) DEFAULT 'active',  -- active | completed
  knowledge_snapshot JSONB,   -- 세션 시작 시점 snapshot (subject 범위)
  started_at    TIMESTAMP DEFAULT NOW(),
  ended_at      TIMESTAMP
);

-- 인터뷰 턴
CREATE TABLE interview_turns (
  id            UUID PRIMARY KEY,
  session_id    UUID REFERENCES interview_sessions(id),
  turn_number   INT,
  question      TEXT,
  answer        TEXT,
  score         FLOAT,
  feedback      TEXT,
  target_nodes  UUID[],
  target_blueprints UUID[],
  created_at    TIMESTAMP DEFAULT NOW()
);

-- 최종 진단
CREATE TABLE interview_diagnoses (
  id            UUID PRIMARY KEY,
  session_id    UUID REFERENCES interview_sessions(id) UNIQUE,
  overall_band  CHAR(1),       -- S/A/B/C/D
  strengths     JSONB,
  weaknesses    JSONB,
  recommendations JSONB,
  created_at    TIMESTAMP DEFAULT NOW()
);
```

---

### Feature 7.4: Knowledge State 연동

**읽기 (세션 시작 시 1회):**
- node mastery: Student Backend `GET /api/mastery/{student_id}?subject_id=...` (subject 필터)
- blueprint clearance: Student Backend `GET /api/competency/{student_id}?subject_id=...` (subject 필터)
- 로드한 값을 LangGraph State에 복사 → 세션 내내 in-memory로 갱신

**쓰기 (세션 정상 종료 시 1회 커밋):**
- node mastery: EMA 공식 `새값 = 0.3 × 인터뷰점수 + 0.7 × 기존값` 적용 후 DB 반영
- blueprint clearance: EPIC-006의 `blueprint_clearance` 재계산 트리거
- **중도 이탈 시:** State 소멸, DB 쓰기 없음 → 세션 전 상태 유지

---

## 5. 비기능 요건

| 항목 | 요건 |
|---|---|
| 응답 시간 | 질문 생성/평가 각 3초 이내 (스트리밍 권장) |
| 동시 세션 | 학생당 1개 active 세션만 허용 |
| 데이터 보존 | 세션/턴/진단 영구 보존 (학습 이력) |
| 모델 | claude-sonnet-4-6 (질문 생성, 답변 평가) |

---

## 6. 스토리 분해

| 스토리 | 내용 | 의존 |
|---|---|---|
| STORY-001 | Interview Session API + DB 모델 | EPIC-006 |
| STORY-002 | LangGraph Interview Agent (질문 생성 + 답변 평가) | STORY-001 |
| STORY-003 | Adaptive Question Strategy (follow-up / pivot 로직) | STORY-002 |
| STORY-004 | Knowledge State 갱신 연동 | STORY-002 |
| STORY-005 | 최종 진단 리포트 생성 | STORY-003, STORY-004 |
| STORY-006 | 채팅 UI (인터뷰 화면 + 진단 뷰) | STORY-005 |

> STORY-006(UI)은 마지막에 진행.

---

## 7. 미결 사항

- [ ] EMA α=0.3 가중치 실험 후 조율 필요 (현재 임의값)
