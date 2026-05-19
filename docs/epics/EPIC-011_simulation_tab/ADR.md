# [ADR] EPIC-011 Simulation Tab — 아키텍처 의사결정 기록

> Architecture Decision Records. 각 결정은 Context → Decision → Consequences 구조로 기록한다.

---

## ADR-001: Interview Agent와 Persona Agent 역할 분리

**날짜:** 2026-05-19

**상태:** Accepted

### Context

PRD 초기 설계에서는 `interview_agent.py`에 `generate_answer_as_persona()` 함수를 추가해, 인터뷰어(질문 생성·평가)와 학생(답변 생성)을 동일 에이전트가 수행하도록 했다.

구현 중 다음 문제가 식별됐다:
- 인터뷰어가 학생의 답변을 직접 생성하는 것은 역할 경계가 모호
- `interview_agent.py`의 책임이 "인터뷰어"와 "학생"으로 혼재되어 단위 테스트 및 이후 교체가 어려움
- 향후 실제 학생이 답변하는 시나리오로 전환할 때 인터페이스 변경 범위가 확대됨

### Decision

`persona_agent.py`를 별도 모듈로 신설한다.

| 모듈 | 역할 |
|---|---|
| `interview_agent.py` | 인터뷰어: 질문 생성, 답변 평가, 타겟 노드 선택, 진단 생성 |
| `persona_agent.py` | 학생: 주어진 페르소나 프롬프트로 질문에 답변 생성 |

`interview_agent.py`에서 `generate_answer_as_persona` 함수를 제거하고, 세션 오케스트레이션 루프에서 두 모듈을 순서대로 호출한다.

```
step() 흐름:
  1. persona_agent.generate_answer(question, persona_prompt, ...)  ← 학생 역할
  2. interview_agent.evaluate_answer(question, answer, ...)        ← 인터뷰어 역할
  3. interview_agent.select_target_nodes(...)                      ← 인터뷰어 역할
  4. interview_agent.generate_question(target_node, ...)           ← 인터뷰어 역할 (다음 턴용)
```

### Consequences

**장점**
- 역할 경계가 명확해져 각 모듈을 독립적으로 교체·테스트 가능
- `persona_agent`를 실제 학생 입력 핸들러로 교체하거나 다른 LLM 모델을 쓰도록 변경할 때 인터뷰 로직에 영향 없음
- `interview_agent.py`가 순수 인터뷰어 역할에 집중

**단점 / 제약**
- 파일이 하나 늘어남
- `persona_agent`와 `interview_agent`가 동일한 OpenAI API를 두 번 호출 — 비용 증가

---

## ADR-002: Interview Session 방식 전환 — Batch → Step-by-step API

**날짜:** 2026-05-19

**상태:** Accepted

### Context

PRD의 원래 설계:
- 백엔드에 `POST /interview/virtual-run` 단일 엔드포인트
- 요청 1회로 모든 턴을 자동 완료 후 결과 반환 (배치 방식)

이 방식의 한계:
- 사용자가 대화 진행 과정을 볼 수 없음 — 결과만 확인 가능
- 멀티턴 LLM 호출이 직렬로 쌓여 HTTP 타임아웃 위험 (8턴 × 2회 LLM 호출 ≈ 30~60초)
- 인터뷰 중간에 중단하거나 특정 턴에서 흐름을 확인하는 것 불가

### Decision

배치 엔드포인트 대신 세 개의 엔드포인트로 인터뷰 세션을 관리한다:

| 엔드포인트 | 역할 |
|---|---|
| `POST /api/simulate/interview/start` | 세션 생성, 학생 페르소나 확인, 첫 번째 질문 반환 |
| `POST /api/simulate/interview/{id}/step` | 페르소나 에이전트 답변 생성 → 평가 → 다음 질문 반환 |
| `POST /api/simulate/interview/{id}/finish` | 진단 생성, SimulationRun DB 저장, 세션 메모리 해제 |

프론트엔드가 "다음 턴 →" 버튼 클릭 시에만 `step`을 호출해 UI가 턴 진행 속도를 제어한다.

세션 상태(`_virt_sessions: dict[str, dict]`)는 `virtual-student-api/routes/simulate.py` 모듈 레벨 dict로 관리한다 (EPIC-008 ADR-005와 동일 패턴).

### Consequences

**장점**
- 사용자가 채팅 UI에서 질문·답변을 턴 단위로 확인 가능
- 요청 하나의 응답 시간이 1~2회 LLM 호출로 한정 → 타임아웃 위험 제거
- `finish`를 호출하지 않으면 중간 상태 보존 가능

**단점 / 제약**
- 단일 프로세스 제한: 수평 확장 시 세션 공유 불가 → `--workers 1` 필요
- 클라이언트가 `finish` 없이 이탈하면 `_virt_sessions`에 세션 잔류 (TTL/GC 없음)

---

## ADR-003: 백엔드 Stateless Service 엔드포인트 노출 + 오케스트레이션 이전

**날짜:** 2026-05-19

**상태:** Accepted

### Context

PRD 원래 설계에서는 백엔드(`student-platform/backend`)의 `/interview/virtual-run`이 인터뷰 세션 전체 루프(질문 생성 → 답변 생성 → 평가 → 반복)를 오케스트레이션했다.

ADR-001(역할 분리)과 ADR-002(Step-by-step)을 채택한 이후:
- 답변 생성이 `persona_agent`(virtual-student-api)로 이전됨
- 세션 상태가 `virtual-student-api`에 있음
- `virtual-student-api`가 인터뷰 루프를 직접 주도하는 것이 자연스러운 구조

그러나 `interview_agent.py`의 핵심 LLM 로직(질문 생성·평가·진단)은 `student-platform/backend`에 남아 있어, `virtual-student-api`가 직접 호출할 수 있는 인터페이스가 없었다.

### Decision

`student-platform/backend`에 4개의 Stateless Service 엔드포인트를 노출한다 (`X-Service-Token` 인증):

| 엔드포인트 | 래핑 함수 |
|---|---|
| `POST /interview/service/question` | `interview_agent.generate_question` |
| `POST /interview/service/evaluate` | `interview_agent.evaluate_answer` |
| `POST /interview/service/next-target` | `interview_agent.select_target_nodes` |
| `POST /interview/service/diagnose` | `interview_agent.generate_diagnosis` |

`virtual-student-api`의 `simulate.py`가 이 4개를 순서대로 HTTP 호출하며 인터뷰 루프를 오케스트레이션한다.

```
virtual-student-api (simulate.py)       student-platform/backend
  start()  ─── /service/question ──────→ generate_question()
  step()   ─── /service/evaluate ──────→ evaluate_answer()
           ─── /service/next-target ───→ select_target_nodes()
           ─── /service/question ──────→ generate_question()
  finish() ─── /service/diagnose ──────→ generate_diagnosis()
```

### Consequences

**장점**
- `interview_agent.py`의 핵심 LLM 로직을 변경 없이 재활용
- 오케스트레이션 책임이 `virtual-student-api`에 집중 — 학생 데이터·세션 컨텍스트와 같은 위치
- 각 Service 엔드포인트가 단일 책임 → 독립 테스트 가능

**단점 / 제약**
- `virtual-student-api` → `student-platform/backend` HTTP 호출 추가 (네트워크 홉 증가)
- `STUDENT_PLATFORM_URL` 환경변수 관리 필요
- 서비스 간 호출 장애 시 에러 전파 경로가 길어짐

---

## ADR-004: Simple 모드 Grader Agent 연동 — Backlog 항목 조기 구현

**날짜:** 2026-05-19

**상태:** Accepted

### Context

PRD Backlog:
> "채점 기반 정답률 분석 (결과 저장만, 채점 연동은 추후)"

Simple Answer 모드에서 `correct_answer`를 입력할 수 있도록 UI에 제공했으나 채점 결과가 없으면 답변 비교 테이블에 점수 열이 비어 있어 시뮬레이션의 유용성이 낮았다.

그라더 에이전트(포트 8005, `GATEWAY_URL/grade`)는 이미 구현·운영 중이며:
- MCQ / OX: 정답 레이블과 exact match
- SHORT_ANSWER / DESCRIPTIVE: LLM 기반 채점 (0.0~1.0 점수 + 피드백)

### Decision

Simple 모드 실행 시 `correct_answer`가 있는 질문에 대해 Grader Agent를 호출한다.

```python
async def _grade(question_text, answer_text, correct_answer, question_type, options):
    mapped_type = _TYPE_MAP.get(question_type, "SHORT_ANSWER")
    payload = {"question": question_text, "answer": answer_text,
               "correct_answer": correct_answer, "question_type": mapped_type, ...}
    resp = await httpx.post(f"{GATEWAY_URL}/grade", json=payload)
    return resp["score"], resp["feedback"], resp["is_correct"]
```

`correct_answer`가 없으면 채점을 건너뛰고 `score=None`으로 저장한다.

### Consequences

**장점**
- 답변 비교 테이블에 점수·피드백이 표시되어 시뮬레이션 결과의 해석 가치 향상
- 기존 Grader Agent 재활용 — 추가 LLM 구현 없음

**단점 / 제약**
- `correct_answer` 미입력 시 점수 없음 → KG 질문 사용 시 `correct_answer` 제공 여부에 의존
- Grader Agent 미기동 시 채점 없이 `score=None`으로 graceful fallback

---

## ADR-005: MCQ 답변을 선택지 Label만 응답하도록 제한

**날짜:** 2026-05-19

**상태:** Accepted

### Context

`persona_agent.generate_answer()`의 초기 구현에서는 질문 유형에 무관하게 동일한 프롬프트를 사용했다. MCQ 문제에 대해 학생 에이전트가 "A번이라고 생각합니다. 왜냐하면..." 식의 서술형 답변을 생성했다.

Grader Agent의 MCQ 채점은 exact match (A/B/C/D) 기반이므로 서술형 응답은 채점 불가 또는 오채점이 발생했다.

### Decision

`persona_agent`에서 질문 유형을 감지해 MCQ 응답 방식을 변경한다:

```python
if is_mcq:
    # 선택지 목록을 프롬프트에 포함
    # "Respond with ONLY the letter of your choice (A, B, C, or D)." 지시
    # max_tokens=5 로 제한
    # 응답에서 레이블(A-D)만 추출 (정규식 fallback 포함)
else:
    # 자유 서술형 (max_tokens=400)
```

MCQ 판별 기준: `question_type in ("MCQ", "OX", "MULTIPLE_CHOICE")` 또는 `options` 비어있지 않음.

### Consequences

**장점**
- MCQ 채점 exact match 조건과 응답 형식 일치 → 채점 정확도 향상
- `max_tokens=5`로 토큰 낭비 제거

**단점 / 제약**
- LLM이 지시를 따르지 않을 경우 정규식 추출 실패 → `score=None` fallback
- OX 문제에서 "O"/"X"가 아닌 다른 표현 사용 시 채점 실패 가능성 존재

---

## ADR-006: Interview 모드 학생 선택 1인 제한

**날짜:** 2026-05-19

**상태:** Accepted

### Context

PRD는 모든 모드에서 다중 학생 선택(체크박스)을 명시했다. Simple 모드는 다중 선택 후 병렬로 답변을 생성하는 것이 자연스럽지만, Interview 모드에서는:

- 인터뷰 세션이 1:1 구조 (인터뷰어 ↔ 단일 학생)
- 복수 학생을 동시에 인터뷰하려면 세션을 여러 개 열어야 함
- UI에서 채팅 뷰가 단일 대화 스트림으로 표시되어 복수 학생 처리 시 표현이 복잡해짐
- `interview_agent`의 mastery 추적 및 `select_target_nodes` 로직이 단일 학생 기준으로 설계됨

### Decision

Interview 모드에서 학생 선택 UI를 라디오 버튼으로 변경하여 1인만 선택 가능하도록 제한한다.

- Simple 모드: 체크박스 (다중 선택 유지)
- Interview 모드: 라디오 버튼 (단일 선택 강제)

모드 전환 시 선택 상태를 초기화한다.

### Consequences

**장점**
- 채팅 UI가 단일 대화 스트림으로 명확하게 표현됨
- 인터뷰 세션 상태 관리가 단순 (세션 당 학생 1명 보장)
- 사용자에게 "인터뷰는 1:1"이라는 개념 모델을 명확히 전달

**단점 / 제약**
- 복수 학생을 인터뷰하려면 모드를 반복 실행해야 함
- Backlog: 복수 학생 병렬 인터뷰 세션 관리 (향후 배치 인터뷰 기능으로 해결 가능)
