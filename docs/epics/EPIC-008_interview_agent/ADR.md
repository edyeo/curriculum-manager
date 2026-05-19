# [ADR] EPIC-008 Interview Agent — 아키텍처 의사결정 기록

> Architecture Decision Records. 각 결정은 Context → Decision → Consequences 구조로 기록한다.

---

## ADR-001: LangGraph 미채택, 단순 함수형 에이전트 구현

**날짜:** 2026-05-19

**상태:** Accepted

### Context

PRD는 `agent-platform/agents/interview-agent`에 LangGraph 기반 그래프를 구현하도록 명시했다. LangGraph는 체크포인트(Checkpoint) 기반 상태 지속성, Human-in-the-Loop 일시정지, 그래프 시각화를 제공한다.

그러나 인터뷰 에이전트의 제품 원칙은 다음과 같다:
- **No Resume:** 중도 이탈 세션은 폐기. 상태를 DB에 지속할 필요 없음
- 질문 생성·답변 평가는 각각 독립적인 LLM 호출 1회로 완결됨
- 그래프의 분기(`follow_up | pivot`)는 단순 조건 분기로 충분히 표현 가능

### Decision

LangGraph를 사용하지 않는다. `student-platform/backend/interview_agent.py` 단일 파일에 순수 Python 함수로 에이전트 로직을 구현한다.

- 상태: 모듈 레벨 `_sessions: dict[int, dict]` (routes/interview.py)
- 질문 생성·평가·진단: `interview_agent.py`의 stateless 함수 (`generate_question`, `evaluate_answer`, `generate_diagnosis`)
- 적응형 전략: `select_target_nodes` 함수 (EMA + follow_up/pivot 분기)

### Consequences

**장점**
- 의존성 없음 (LangGraph, langgraph-checkpoint 불필요)
- 각 함수가 독립적으로 테스트 가능
- 코드량 대폭 감소, 추론이 쉬움

**단점 / 제약**
- 단일 프로세스 제한: 수평 확장 시 세션 공유 불가 (→ 향후 Redis 세션 스토어로 해결 가능)
- LangGraph 그래프 시각화·디버깅 도구 미활용
- agent-platform과의 아키텍처 불일치 (다른 에이전트들은 LangGraph 사용)

---

## ADR-002: LLM 모델 OpenAI gpt-4o 채택

**날짜:** 2026-05-19

**상태:** Accepted

### Context

PRD는 모델을 `claude-sonnet-4-6`으로 명시했다. 그러나 agent-platform의 기존 에이전트(curriculum-manager 등)는 모두 OpenAI SDK + `gpt-4o`를 사용한다.

### Decision

인터뷰 에이전트의 LLM API를 OpenAI `gpt-4o`로 변경한다.

- SDK: `openai>=1.0.0`
- 모델: `gpt-4o`
- API 키: `OPENAI_API_KEY` (기존 agent-platform 환경변수 그대로 재활용)
- Docker Compose 환경변수: `student-platform-backend`에 `OPENAI_API_KEY` 주입

### Consequences

**장점**
- agent-platform 전체에서 단일 LLM 공급자(OpenAI) 유지 → 키 관리 단순화
- 기존 `gpt-4o` 프롬프트 패턴 재활용 가능

**단점**
- PRD와 모델 불일치 → 추후 Claude 전환 시 프롬프트 재검증 필요
- Anthropic 모델 특성(긴 컨텍스트 이해, 한국어 품질)이 필요해질 경우 재검토

---

## ADR-003: Blueprint Clearance 인터뷰 연동 제외 ~~(초기 결정)~~

**날짜:** 2026-05-19

**상태:** ~~Accepted~~ → **Superseded by ADR-007**

초기 구현에서는 범위 축소를 이유로 blueprint 연동을 제외했으나, 이후 ADR-007에서 번복되었다. 이력 보존을 위해 항목을 유지한다.

---

## ADR-004: not_covered / weaknesses 분리

**날짜:** 2026-05-19

**상태:** Accepted

### Context

PRD 진단 스키마:
```
{ strengths, weaknesses, overall_band, recommendations }
```

초기 구현에서 `weaknesses`를 "낮은 mastery 노드 전체"로 채웠다. 그러나 인터뷰에서 한 번도 질문되지 않은 노드도 초기 mastery가 낮으면 `weaknesses`에 포함되어, 인터뷰 결과와 무관한 노드가 취약점으로 표시되는 문제가 발생했다.

### Decision

진단 산출 시 `assessed_node_ids`(인터뷰에서 실제 질문된 노드 집합)를 별도로 추적한다.

- `weaknesses`: assessed 노드 중 최종 mastery < 임계값인 노드
- `not_covered`: 세션에서 전혀 질문되지 않은 노드 (assessed_node_ids 외부)

`interview_diagnoses` 테이블에 `not_covered TEXT`(JSON 배열) 컬럼 추가.

### Consequences

진단의 의미론이 명확해진다:
- `weaknesses` = "인터뷰에서 평가한 결과 취약한 것으로 확인된 노드"
- `not_covered` = "이번 인터뷰에서 다루지 못한 노드 (향후 추가 인터뷰 권장)"

UI에서도 두 섹션을 구분해 표시하여 학생이 "취약"과 "미확인"을 혼동하지 않도록 한다.

---

## ADR-005: 세션 상태를 routes/interview.py 모듈 레벨 dict로 관리

**날짜:** 2026-05-19

**상태:** Accepted

### Context

인터뷰 세션 중 상태(working_mastery, 현재 질문, 턴 이력)를 어디에 보관할지 결정이 필요했다.

후보:
- A. `interview_store.py` 별도 파일의 전역 dict
- B. `routes/interview.py` 모듈 레벨 dict (`_sessions`)
- C. Redis 등 외부 세션 스토어
- D. DB per-turn 저장

D는 "세션 중 DB 쓰기 없음"이라는 제품 원칙에 위배된다. C는 현재 인프라에 Redis가 없다. A는 단순 분리로 불필요한 파일 분산을 초래한다.

### Decision

`routes/interview.py` 모듈 레벨에 `_sessions: dict[int, dict]`를 선언한다. 세션 상태는 이 dict에서만 읽고 쓴다.

세션 종료 시 `del _sessions[session_id]`로 메모리 해제. DB 쓰기는 종료 시 단 1회.

### Consequences

**장점**
- 가장 단순한 구조. 추가 파일·인프라 없음
- 세션 생명주기(생성→갱신→삭제)가 한 파일 안에서 완결됨

**단점**
- 단일 프로세스 한정: gunicorn workers > 1이면 세션 공유 불가 → `--workers 1` 또는 sticky session 필요
- 서버 재시작 시 모든 active 세션 소멸 (No Resume 원칙과 일치하므로 허용)
- 메모리 누수 가능성: `/end` 없이 이탈한 세션은 `_sessions`에 잔류. 현재 TTL/GC 로직 없음

---

## ADR-006: 연속 follow-up 상한 MAX_CONSECUTIVE_FOLLOWUPS=2 도입

**날짜:** 2026-05-19

**상태:** Accepted

### Context

PRD의 Adaptive Question Strategy는 follow-up / pivot 선택 기준(점수 임계값 0.5)만 명시하고, 연속 follow-up의 최대 횟수는 정의하지 않았다.

연속 follow-up에 상한이 없으면 하나의 노드에 집중적으로 질문이 몰려, 15턴을 모두 소진하고도 다른 약점 노드를 커버하지 못하는 상황이 발생할 수 있다.

### Decision

`MAX_CONSECUTIVE_FOLLOWUPS = 2` 상수를 도입한다.

- 동일 타겟에 연속 2회 follow-up 이후에는 점수와 무관하게 강제 pivot
- `state["consecutive_followups"]` 카운터로 추적, pivot 시 0으로 초기화

임계값 `FOLLOWUP_THRESHOLD = 0.5`도 상수화한다.

### Consequences

- 인터뷰가 특정 노드에 과집중되는 문제 방지
- 노드 커버리지 향상: 15턴 내 더 많은 약점 노드를 순회 가능
- 튜닝 가능: `MAX_CONSECUTIVE_FOLLOWUPS` 값은 향후 사용자 데이터로 조정

---

## ADR-007: Blueprint를 질문 생성·평가·mastery 갱신에 통합

**날짜:** 2026-05-19

**상태:** Accepted (ADR-003 번복)

### Context

ADR-003에서 blueprint clearance 연동을 제외했으나, 이는 다음 문제를 남겼다:

1. **질문의 역량 축 부재:** `generate_question`이 노드 이름과 설명만 참조하여 LLM이 어떤 역량 차원(layer × stage)을 검증해야 하는지 알 수 없었다.
2. **평가의 모호성:** `evaluate_answer`가 blueprint 관점 없이 전반적인 점수만 산출해, 피드백이 역량 차원과 무관하게 추상적이었다.
3. **blueprint mastery 미반영:** 인터뷰 수행 후 `NodeMastery`만 갱신되고 `BlueprintCellMastery` / `BlueprintItemMastery`는 변경되지 않아, 인터뷰 결과가 blueprint matrix에 반영되지 않았다.

### Decision

세 단계 모두에 blueprint 정보를 통합한다.

**1. 세션 시작 시 blueprint 선로드**

```python
# asyncio.gather로 전체 노드의 blueprint를 병렬 로드
blueprint_results = await asyncio.gather(
    *[kg_client.get_node_blueprints(n["id"]) for n in nodes],
    return_exceptions=True,
)
node_blueprints = { nodes[i]["id"]: blueprint_results[i] ... }
# _sessions[id]["node_blueprints"] = node_blueprints  (불변, 세션 내내 참조)
```

**2. 질문 생성 시 blueprint 컨텍스트 주입**

`generate_question(target_blueprints=...)` 파라미터 추가. 프롬프트에 평가 대상 blueprint명과 역량 차원(`layer×stage`) 포함:

```
Competency blueprints to assess (frame your question to test these skill dimensions):
- 알고리즘 이해도 (skill dimensions: knowledge×recall, apply×problem_solving)
- 구현 능력 (skill dimensions: apply×implementation)
```

**3. 답변 평가 시 blueprint 기준 적용**

`evaluate_answer(target_blueprints=...)` 파라미터 추가. LLM에게 blueprint 역량 차원별로 어떤 부분이 충족·미충족됐는지 피드백 생성을 지시한다.

**4. 세션 종료 시 BlueprintCellMastery / BlueprintItemMastery EMA 갱신**

```python
def _commit_blueprint_mastery(student_id, assessed_node_ids, final_mastery, node_blueprints, db):
    for node_id in assessed_node_ids:
        score = final_mastery[node_id]
        for bp in node_blueprints[node_id]:
            for item in bp["integration_items"]:
                for combo in item["required_combinations"]:
                    # BlueprintCellMastery EMA(α=0.3)
                for cell_scores → min → BlueprintItemMastery EMA(α=0.3)
```

`node_mastery`는 EMA이므로 `BlueprintCellMastery`/`BlueprintItemMastery`도 동일한 α=0.3을 사용한다.

### Consequences

**장점**
- 질문이 blueprint 역량 차원을 명시적으로 타겟해 측정의 타당성 향상
- 피드백이 "어떤 차원(Recall / Apply × Problem-Solving)에서 부족했는가"를 구체적으로 제시
- 인터뷰 수행 후 blueprint matrix(BlueprintCellMastery / BlueprintItemMastery)에 결과 반영 → 학생 역량 현황이 인터뷰로도 업데이트됨

**제약**
- 세션 시작 시 노드 수만큼 KG API 호출 발생 (asyncio.gather로 병렬화하여 완화)
- `StudyAttempt` 기반 clearance 비율(`correct_count / pub_count`)은 인터뷰로 갱신되지 않음 — 인터뷰는 문항 은행 풀이와 별개의 평가 채널이기 때문

**설계 경계**
- `BlueprintCellMastery` 갱신에 쓰이는 score는 해당 노드의 최종 EMA mastery 단일값이다. 향후 개선 시 turn별 cell 단위 LLM 평가(cell_scores JSON)를 도입해 더 세밀한 갱신이 가능하다.
