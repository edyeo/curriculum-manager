# [ADDENDUM] EPIC-008 Interview Agent — 구현 보완 사항

> PRD(PRD-interview_agent.md) 대비 실제 구현에서 추가되거나 변경된 기능을 기록한다.
> 구조적 의사결정은 별도 ADR.md에 정리한다.

---

## 1. 스코프 변경 (PRD 계획 → 실제 구현)

### 1-1. Blueprint Clearance 연동 제외

**PRD 계획**
- 세션 시작 시 `node_mastery + blueprint_clearance` 두 가지를 Knowledge Snapshot으로 로드
- 매 턴 blueprint clearance도 in-memory 갱신
- 세션 종료 시 blueprint clearance DB 반영

**실제 구현**
- `node_mastery`만 로드·갱신·반영
- blueprint clearance는 인터뷰 플로우에서 제외

**근거:** Blueprint clearance는 여러 노드를 합산한 파생 지표이므로 매 턴 갱신이 필요한 게 아니라 세션 후 일괄 재계산하면 충분하다. 그러나 현재 구현에서는 이마저도 생략되어 있어 추후 보완이 필요하다. (→ ADR-003 참조)

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

Blueprint 연동이 제외됨에 따라 함께 제거되었다.

---

## 2. 추가 기능 (PRD에 없던 항목)

### 2-1. `not_covered` 진단 필드

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

### 2-2. `node_final_mastery` 진단 필드

세션 종료 시 각 노드의 최종 mastery 점수(EMA 적용 후)를 `interview_diagnoses.node_final_mastery` JSON으로 저장한다. 진단 상세 조회 시 노드별 최종 이해도 확인이 가능하다.

---

### 2-3. `GET /interview/sessions` 목록 엔드포인트

**PRD API 표에 없던 엔드포인트.**

완료된 세션 목록과 각 세션의 진단 요약(`overall_band`, `turn_count`, 날짜)을 반환한다. 인터뷰 히스토리 UI를 위해 추가되었다.

```
GET /interview/sessions
Response: { sessions: [{ session_id, subject_id, overall_band, turn_count, started_at, ended_at }] }
```

---

### 2-4. `action` 컬럼 (interview_turns)

PRD 스키마에 없던 `action VARCHAR` 컬럼이 `interview_turns`에 추가되었다. 각 턴에서 에이전트가 선택한 전략(`follow_up` / `pivot` / `end`)을 기록한다. 추후 에이전트 전략 분석·튜닝에 활용 가능하다.

---

### 2-5. consecutive_followups 제한 로직

**내용**
- `MAX_CONSECUTIVE_FOLLOWUPS = 2` 상수 도입
- 연속 2회 follow-up 후에는 점수와 무관하게 강제 pivot

**이유**
- PRD는 follow-up / pivot 선택 기준만 명시했고, 연속 follow-up 상한은 미정의였다.
- 상한 없이 follow-up을 허용하면 하나의 노드에 과도하게 집중되어 다른 약점 노드를 커버하지 못할 위험이 있다.

---

### 2-6. 인터뷰 서브탭 UI

**PRD UI 요건:** "채팅 UI" 단순 명시

**실제 구현:**
- `인터뷰 수행` 서브탭: idle → active 채팅 → 종료 후 진단 결과 3단계 플로우
- `인터뷰 히스토리` 서브탭: 완료 세션 카드 목록 → 클릭 시 **대화기록(Q&A 전체 턴) + 진단 결과** 펼치기

대화기록 조회는 `GET /interview/sessions/{id}`(턴 목록)와 `GET /interview/sessions/{id}/diagnosis`(진단)를 병렬 호출하여 구성한다.

---

## 3. 미완 사항 (추후 작업 필요)

| 항목 | 내용 |
|---|---|
| Blueprint clearance 갱신 | 인터뷰 종료 후 해당 subject의 blueprint clearance 재계산 트리거 필요 |
| 자동 종료 조건 | 핵심 노드 전부 커버 + 약점 해소 시 자동 종료 (현재 max_turns만 체크) |
| EMA α 튜닝 | α=0.3은 임의값. 학습 데이터 기반 실험 후 조율 필요 |
| 응답 스트리밍 | 현재 동기 응답. 질문 생성 3초+ 소요 시 UX 저하 — SSE 스트리밍 도입 검토 |
| 프로세스 재시작 시 세션 유실 | 메모리 dict 특성상 서버 재시작 = 모든 active 세션 소멸. Redis 등 외부 세션 스토어 검토 필요 (단, No Resume 원칙 범위 내에서) |
