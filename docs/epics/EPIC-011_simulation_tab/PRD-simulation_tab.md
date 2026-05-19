# EPIC-011 — Virtual Student Simulation Tab

## 개요

Virtual Student Manager에 **Simulation 탭**을 추가한다.  
가상 학생들이 선택된 질문에 대해 어떻게 답변하는지 시뮬레이션하고,  
학생별 답변 패턴을 비교 분석할 수 있도록 한다.

---

## 목표

- 가상 학생 페르소나 기반 답변 생성의 실제 동작 확인
- 학생 특성(feature)별 답변 패턴 차이 시각화
- 향후 Virtual Student Agent 고도화를 위한 데이터 수집

---

## 범위

### 포함
- 가상 학생 선택 (다중)
- 질문 선택 (KG API 조회 또는 직접 입력)
- 답변 생성 두 가지 Mode
  - **Mode 1 — Simple Answer**: 학생 페르소나 → LLM이 단일 질문에 답변 생성 (stateless)
  - **Mode 2 — Interview Session**: interview_agent 재활용, prior_knowledge_level 기반 initial mastery 주입, LLM이 자동 멀티턴 진행
- 시뮬레이션 결과 저장 (virtual-student-api DB)
- 결과 비교 뷰 (학생별 답변 목록 + 특성별 패턴 비교)

### 제외 (Backlog)
- feature → node별 mastery 파생 로직 (prior_knowledge_level 균등 초기화로 대체)
- 채점 기반 정답률 분석 (결과 저장만, 채점 연동은 추후)
- 실시간 스트리밍 답변 (batch 결과 반환)

---

## 데이터 모델 (신규, virtual-student-api DB)

```
SimulationRun
  id              UUID PK
  subject_id      str
  mode            str  ("simple" | "interview")
  question_source str  ("kg" | "manual")
  questions       JSON  [{question_text, question_id?, correct_answer?}]
  created_at      datetime

SimulationResult
  id              UUID PK
  run_id          FK → SimulationRun
  virtual_student_id  FK → VirtualStudent
  answers         JSON  [{question_text, answer_text, turn_data?}]
  diagnosis       JSON  (interview mode만, interview_agent 진단 결과)
  created_at      datetime
```

---

## API 설계 (virtual-student-api)

### POST /api/simulate/runs
시뮬레이션 실행 (동기)

**Request**
```json
{
  "subject_id": "string",
  "mode": "simple | interview",
  "student_ids": ["uuid", ...],
  "questions": [
    {"question_text": "...", "question_id": "optional", "correct_answer": "optional"}
  ]
}
```

**Response** — `201 Created`
```json
{
  "run_id": "uuid",
  "results": [
    {
      "student_id": "uuid",
      "student_name": "string",
      "answers": [{"question_text": "...", "answer_text": "..."}],
      "diagnosis": null
    }
  ]
}
```

### GET /api/simulate/runs
과거 시뮬레이션 목록

### GET /api/simulate/runs/{run_id}
시뮬레이션 상세 (결과 포함)

---

## API 설계 (student-platform/backend 수정)

### interview_agent.py 수정
`_load_initial_mastery`에 `initial_mastery_override: dict | None = None` 파라미터 추가.  
override가 있으면 DB 조회 없이 해당 값을 사용.

### POST /interview/virtual-run (신규, X-Service-Token 인증)
가상 학생 1명에 대한 인터뷰 세션 자동 완주 (LLM이 질문 생성 + 답변 생성 모두 수행)

**Request**
```json
{
  "subject_id": "string",
  "initial_mastery": {"node_id": 0.3},
  "persona_prompt": "string",
  "max_turns": 5
}
```

**Response**
```json
{
  "turns": [{"question": "...", "answer": "...", "score": 0.7}],
  "diagnosis": {"overall_band": "B", "strengths": [], "weaknesses": [], "recommendations": []}
}
```

---

## 프론트엔드 (virtual-student-ui)

### 신규 탭: Simulation

**Step 1 — 학생 선택**
- subject 내 가상 학생 목록 테이블 + 체크박스 다중 선택

**Step 2 — 질문 설정**
- Mode 토글: Simple Answer / Interview Session
- 질문 소스 탭: KG 질문 검색 | 직접 입력
  - KG: subject 기준 published 질문 목록, 체크박스 선택
  - 직접 입력: 질문 텍스트 추가 (여러 개)
- Interview 모드는 질문 불필요 (interview_agent가 자동 생성)

**Step 3 — 실행**
- "시뮬레이션 실행" 버튼
- 진행 중 spinner

**Step 4 — 결과 분석**
- **답변 비교 테이블**: 행=학생, 열=질문, 셀=답변 텍스트 (클릭 시 전체 보기)
- **패턴 비교**: feature 값 기준 그룹핑 후 답변 길이 분포 시각화
- Interview 모드: 학생별 diagnosis 카드 (overall_band, strengths, weaknesses)
- 과거 실행 목록 (최근 10개)

---

## Backlog

- feature 조합 → node 타입별 mastery 파생
  (예: conceptual_depth='surface' → Concept 노드 mastery 낮게, TechStack 별도 가중치)
- 채점 연동: correct_answer 있을 때 정답률 자동 계산 및 집계
- SSE 기반 실시간 진행 상황 push
- 시뮬레이션 결과 CSV 다운로드

---

## ADDENDUM — 구현 중 변경·추가된 사항

> PRD 확정 후 개발 과정에서 결정된 내용을 기록한다. 상세 배경은 [ADR.md](./ADR.md)를 참조.

### 추가된 기능

#### persona_agent.py 신설 (ADR-001)

`virtual-student-api`에 `persona_agent.py` 모듈을 신규 추가한다.  
학생 답변 생성 역할을 `interview_agent`에서 분리하여 전담시킨다.

- MCQ / OX 질문: 선택지 목록을 프롬프트에 포함, label(A/B/C/D)만 응답 (`max_tokens=5`)
- 서술형 질문: 페르소나 프롬프트 기반 자유 서술 (`max_tokens=400`)
- `conversation_history` 파라미터로 멀티턴 맥락 전달 지원

#### Simple 모드 Grader Agent 연동 (ADR-004)

PRD Backlog 항목 "채점 연동"을 조기 구현한다.  
`correct_answer`가 있는 질문에 한해 `GATEWAY_URL/grade`를 호출하여 점수·피드백을 결과에 포함한다.

- MCQ / OX: exact match 채점
- SHORT_ANSWER / DESCRIPTIVE: LLM 기반 채점 (0.0~1.0)
- `correct_answer` 미제공 시 `score=null`로 graceful skip

#### Interview Session Step-by-step API (ADR-002)

PRD의 단일 배치 엔드포인트(`/interview/virtual-run`) 대신 3개 엔드포인트로 구현한다:

| 엔드포인트 | 설명 |
|---|---|
| `POST /api/simulate/interview/start` | 세션 생성, 첫 번째 질문 반환 |
| `POST /api/simulate/interview/{id}/step` | 1턴 실행 (답변 생성 → 평가 → 다음 질문) |
| `POST /api/simulate/interview/{id}/finish` | 진단 생성, DB 저장, 세션 해제 |

#### 백엔드 Stateless Service 엔드포인트 (ADR-003)

`student-platform/backend`에 4개의 서비스 전용 엔드포인트를 추가한다 (`X-Service-Token` 인증):

```
POST /interview/service/question      ← generate_question 래퍼
POST /interview/service/evaluate      ← evaluate_answer 래퍼
POST /interview/service/next-target   ← select_target_nodes 래퍼
POST /interview/service/diagnose      ← generate_diagnosis 래퍼
```

`virtual-student-api`가 이 엔드포인트들을 순서대로 호출하며 인터뷰 루프를 오케스트레이션한다.

### 변경된 설계

#### Interview 모드 학생 선택 1인 제한 (ADR-006)

PRD의 "다중 선택(체크박스)"에서 **Interview 모드만 1인 선택(라디오 버튼)으로 변경**한다.  
Simple 모드는 기존대로 다중 선택 유지.

#### MCQ 응답 형식 제한 (ADR-005)

`persona_agent`가 MCQ 질문에 선택지 레이블만 응답하도록 강제한다.  
Grader Agent의 exact match 채점과 형식 일치를 보장하기 위함.

### Backlog 업데이트

| 항목 | 상태 |
|---|---|
| feature 조합 → node 타입별 mastery 파생 | Backlog 유지 |
| 채점 연동 (Simple 모드) | **완료** (ADR-004) |
| SSE 기반 실시간 진행 상황 push | Backlog 유지 |
| 시뮬레이션 결과 CSV 다운로드 | Backlog 유지 |
| 복수 학생 병렬 인터뷰 세션 | Backlog 신규 추가 (ADR-006) |
| Interview 세션 TTL / GC | Backlog 신규 추가 (ADR-002) |
