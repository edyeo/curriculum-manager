# [ADDENDUM] EPIC-008 Interview Agent — 구현 보완 사항

> PRD(PRD-interview_agent.md) 대비 실제 구현에서 추가되거나 변경된 기능을 기록한다.
> 구조적 의사결정은 별도 ADR.md에 정리한다.

---

## 1. 스코프 변경 (PRD 계획 → 실제 구현)

### 1-1. Blueprint Clearance 연동 방식 변경

**PRD 계획**
- 세션 시작 시 `node_mastery + blueprint_clearance` 두 가지를 Knowledge Snapshot으로 로드
- 매 턴 blueprint clearance도 in-memory 갱신
- 세션 종료 시 blueprint clearance DB 반영

**실제 구현**
- Knowledge Snapshot은 `node_mastery`만 포함 (blueprint_clearance 제외)
- 세션 시작 시 전체 노드의 blueprint를 KG에서 병렬 로드 → `state["node_blueprints"]`에 보관
- 매 턴마다 타겟 노드의 blueprint를 질문 생성·평가에 활용
- 세션 종료 시 `BlueprintCellMastery` / `BlueprintItemMastery`를 EMA로 갱신

**변경 이유:** PRD가 말한 "blueprint clearance"는 `StudyAttempt` 기반 정답률(`correct_count / pub_count`)로 계산되며, 인터뷰의 자유형 Q&A로는 직접 갱신할 수 없다. 대신 인터뷰 점수를 `BlueprintCellMastery` / `BlueprintItemMastery`에 EMA로 반영하여 blueprint matrix가 인터뷰 결과를 반영하도록 했다. (→ ADR-007 참조)

---

### 1-2. LangGraph 미채택

**PRD 계획**
- `agent-platform/agents/interview-agent`에 LangGraph 그래프 구현
- `load_knowledge_state → select_target → generate_question → [HUMAN_IN_LOOP] → evaluate_answer → update_knowledge_state → decide_next_action → generate_diagnosis` 노드 구조

**실제 구현**
- `student-platform/backend/interview_agent.py` 단일 파일에 순수 함수로 구현
- LangGraph 의존 없음
- 상태는 `routes/interview.py`의 모듈 레벨 `_sessions` dict가 보관

**근거:** → ADR-001 참조

---

### 1-3. LLM 모델 변경

**PRD 계획:** `claude-sonnet-4-6`

**실제 구현:** `gpt-4o` (OpenAI SDK)

**근거:** → ADR-002 참조

---

### 1-4. DB Primary Key 타입

**PRD 계획:** UUID

**실제 구현:** Integer (SQLAlchemy 기본값, SQLite 호환)

SQLite는 UUID PK를 네이티브로 지원하지 않아 마이그레이션 없이 Integer를 사용했다. PostgreSQL 전환 시 UUID로 교체 가능하다.

---

### 1-5. 세션 종료 조건 단순화

**PRD 계획 (OR 조건):**
1. 학생 직접 종료 요청
2. 최대 턴 수(15) 도달
3. 핵심 노드 전체 커버 + 약점 해소 확인

**실제 구현:**
1. 학생 직접 종료 요청 (`POST /end`)
2. 최대 턴 수(15) 도달 → 클라이언트가 `/end` 호출 유도

조건 3(자동 종료)은 구현되지 않았다. 현재는 클라이언트에서 `session_status === 'max_turns_reached'` 응답 수신 시 종료 버튼을 안내하는 방식으로 처리한다.

---

### 1-6. interview_turns.target_blueprints 제거

**PRD 계획:** `target_blueprints UUID[]` 컬럼 포함

**실제 구현:** `target_nodes` 배열만 저장, `target_blueprints` 컬럼 없음

Blueprint 정보는 세션 메모리(`node_blueprints`)에서 실시간 조회하므로 turn별 저장이 불필요하다.

---

## 2. 추가 기능 (PRD에 없던 항목)

### 2-1. Blueprint 기반 질문 생성·평가

**내용**
- `generate_question(target_blueprints=...)`: 대상 노드의 blueprint명과 역량 차원(`layer×stage`)을 LLM 프롬프트에 포함
- `evaluate_answer(target_blueprints=...)`: 평가 피드백이 blueprint 역량 차원별로 무엇이 충족/미충족됐는지 명시
- `_format_blueprints()` 헬퍼: blueprint 목록을 프롬프트용 텍스트로 변환

**이유:** 노드 이름만으로는 LLM이 어떤 역량 차원(예: "지식×재현" vs "적용×문제해결")을 테스트해야 하는지 알 수 없다. blueprint를 함께 전달하면 질문의 측정 타당성이 높아진다. (→ ADR-007 참조)

---

### 2-2. 세션 시작 시 blueprint 병렬 로드

세션 시작(`POST /interview/sessions`) 시 `asyncio.gather`로 전체 노드의 blueprint를 병렬 로드해 `state["node_blueprints"]`에 저장한다. 이후 매 턴에서 KG 추가 호출 없이 메모리에서 조회한다.

---

### 2-3. `_commit_blueprint_mastery` (세션 종료 시 blueprint mastery 갱신)

세션 종료 시 assessed 노드의 최종 mastery를 해당 노드의 blueprint cell/item에 EMA(α=0.3)로 반영한다.

- `BlueprintCellMastery` (blueprint_id, layer, stage) → EMA 갱신 또는 신규 생성
- `BlueprintItemMastery` (integration_item_id) → 해당 item의 cell 점수 min으로 EMA 갱신

---

### 2-4. `not_covered` 진단 필드

**내용**
- `interview_diagnoses` 테이블에 `not_covered TEXT` 컬럼 추가
- 인터뷰 중 한 번도 질문되지 않은 노드 목록을 진단 결과에 포함

**이유**
- `not_covered` 없이 모든 저mastery 노드를 `weaknesses`에 넣으면, 인터뷰에서 아예 평가하지 않은 노드가 "취약점"으로 오진된다.
- 평가된 노드(`assessed_node_ids`)와 미방문 노드를 분리해 진단의 정확도를 높인다.

**진단 구조 변화:**
```
PRD:    { strengths, weaknesses, overall_band, recommendations }
실제:   { strengths, weaknesses, not_covered, overall_band, recommendations, node_final_mastery }
```

---

### 2-5. `node_final_mastery` 진단 필드

세션 종료 시 각 노드의 최종 mastery 점수(EMA 적용 후)를 `interview_diagnoses.node_final_mastery` JSON으로 저장한다.

---

### 2-6. `GET /interview/sessions` 목록 엔드포인트

**PRD API 표에 없던 엔드포인트.**

완료된 세션 목록과 각 세션의 진단 요약(`overall_band`, `turn_count`, 날짜)을 반환한다. 인터뷰 히스토리 UI를 위해 추가되었다.

---

### 2-7. `action` 컬럼 (interview_turns)

각 턴에서 에이전트가 선택한 전략(`follow_up` / `pivot` / `end`)을 `interview_turns.action`에 기록한다. 에이전트 전략 분석·튜닝에 활용 가능하다.

---

### 2-8. consecutive_followups 제한 로직

`MAX_CONSECUTIVE_FOLLOWUPS = 2` 상수 도입. 연속 2회 follow-up 후에는 점수와 무관하게 강제 pivot한다. (→ ADR-006 참조)

---

### 2-9. 인터뷰 서브탭 UI

**PRD UI 요건:** "채팅 UI" 단순 명시

**실제 구현:**
- `인터뷰 수행` 서브탭: idle → active 채팅 → 종료 후 진단 결과 3단계 플로우
- `인터뷰 히스토리` 서브탭: 완료 세션 카드 목록 → 클릭 시 **대화기록(Q&A 전체 턴) + 진단 결과** 펼치기

---

## 3. 미완 사항 (추후 작업 필요)

| 항목 | 내용 |
|---|---|
| 자동 종료 조건 | 핵심 노드 전부 커버 + 약점 해소 시 자동 종료 (현재 max_turns만 체크) |
| EMA α 튜닝 | α=0.3은 임의값. 학습 데이터 기반 실험 후 조율 필요 |
| 응답 스트리밍 | 현재 동기 응답. 질문 생성 3초+ 소요 시 UX 저하 — SSE 스트리밍 도입 검토 |
| 프로세스 재시작 시 세션 유실 | 메모리 dict 특성상 서버 재시작 = 모든 active 세션 소멸. Redis 등 외부 세션 스토어 검토 필요 (단, No Resume 원칙 범위 내에서) |
| turn별 cell 단위 평가 | 현재 BlueprintCellMastery 갱신은 노드 최종 mastery 단일값 사용. 향후 turn별 cell_scores JSON을 LLM에서 산출하여 더 세밀한 갱신 가능 |
