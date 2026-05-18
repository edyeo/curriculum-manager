# [EPIC-005] Question Bank — User Stories

## Feature 5.1: Question Bank 조회 탭

### US-5.1.1 — 문항 목록 조회
**As** 출제위원(관리자)  
**I want** 등록된 문항 전체를 한 화면에서 목록으로 볼 수 있으면  
**So that** 현재까지 생성된 문항 수와 상태를 한눈에 파악할 수 있다.

**Acceptance Criteria:**
- Curriculum Manager UI에 **문제조회** 탭이 존재한다.
- 탭 진입 시 `GET /api/question-workbench/questions` 를 호출하여 전체 문항을 불러온다.
- 각 카드에는 지문 앞 60자, 난이도 배지, 문제 타입, 상태 배지, 생성일이 표시된다.
- 문항이 없을 때 빈 상태 메시지와 문제출제 워크벤치로 이동하는 안내 링크를 표시한다.

---

### US-5.1.2 — 문항 필터링
**As** 출제위원  
**I want** Blueprint, Entity 이름, 문제 타입, 난이도, 상태를 조합하여 문항을 필터링하고 싶다  
**So that** 특정 Blueprint의 draft 문항만 빠르게 추려 검토할 수 있다.

**Acceptance Criteria:**
- 좌측 패널 상단에 Blueprint(드롭다운), Entity(텍스트), 타입(드롭다운), 난이도(드롭다운), 상태(드롭다운) 필터가 있다.
- 필터 변경 시 문항 목록이 동적으로 갱신된다.
- 각 필터는 독립적으로, 그리고 조합하여 적용할 수 있다.

---

### US-5.1.3 — 문항 상세 조회
**As** 출제위원  
**I want** 목록에서 문항 카드를 클릭하면 우측 패널에 전체 상세 정보를 볼 수 있으면  
**So that** 별도 페이지 이동 없이 지문·선지·정답·해설·메타데이터를 한 번에 확인할 수 있다.

**Acceptance Criteria:**
- 카드 클릭 시 우측 상세 패널에 지문 전체, 선지(A/B/C/D + rationale), 정답, 해설, node_snapshot 요약, Blueprint, 생성일, 상태 배지가 표시된다.
- 상세 패널은 마스터-디테일 레이아웃으로 목록과 동시에 표시된다.

---

## Feature 5.2: 문항 편집·삭제·상태 관리

### US-5.2.1 — 문항 인라인 편집
**As** 출제위원  
**I want** 상세 패널에서 지문·선지·해설을 직접 수정하고 저장하고 싶다  
**So that** AI 생성 오류나 표현 개선을 별도 화면 이동 없이 즉시 처리할 수 있다.

**Acceptance Criteria:**
- 지문, 선지 텍스트, 해설 필드가 인라인 편집 가능하다.
- [저장] 클릭 시 `PATCH /api/question-workbench/questions/{id}` 를 호출한다.
- 저장 성공 후 목록 카드의 지문 미리보기가 즉시 갱신된다.

---

### US-5.2.2 — 문항 출제 등록 (Publish)
**As** 출제위원  
**I want** draft 문항을 검토한 뒤 [출제 등록] 버튼으로 학생에게 공개하고 싶다  
**So that** 미완성 문항이 학생에게 노출되는 것을 방지하고 품질을 보장할 수 있다.

**Acceptance Criteria:**
- draft 상태 문항의 상세 패널에 [출제 등록] 버튼이 표시된다.
- 버튼 클릭 시 `POST /api/question-workbench/questions/{id}/publish` 를 호출한다.
- 성공 후 상태 배지가 `published`로 즉시 변경된다.

---

### US-5.2.3 — 문항 공개 취소 (Unpublish)
**As** 출제위원  
**I want** 오류가 발견된 published 문항을 draft 상태로 되돌리고 싶다  
**So that** 학생 노출을 즉시 차단하고 수정 후 재출제할 수 있다.

**Acceptance Criteria:**
- published 상태 문항의 상세 패널에 [공개 취소] 버튼이 표시된다.
- 버튼 클릭 시 `POST /api/question-workbench/questions/{id}/unpublish` 를 호출한다.
- 성공 후 상태 배지가 `draft`로 즉시 변경된다.

---

### US-5.2.4 — 문항 보관 (Archive)
**As** 출제위원  
**I want** 더 이상 출제하지 않을 문항을 archived 상태로 보관하고 싶다  
**So that** 이력은 보존하면서 학생에게 노출되지 않도록 관리할 수 있다.

**Acceptance Criteria:**
- published 상태 문항의 상세 패널에 [보관] 버튼이 표시된다.
- 버튼 클릭 시 `POST /api/question-workbench/questions/{id}/archive` 를 호출한다.
- 성공 후 상태 배지가 `archived`로 즉시 변경된다.

---

### US-5.2.5 — 문항 삭제
**As** 출제위원  
**I want** draft 또는 archived 상태의 불필요한 문항을 삭제하고 싶다  
**So that** 문항 목록을 깔끔하게 유지할 수 있다.

**Acceptance Criteria:**
- draft 또는 archived 상태 문항에만 [삭제] 버튼이 활성화된다.
- published 상태 문항의 [삭제] 버튼은 비활성화되며 "보관 후 삭제 가능" 툴팁이 표시된다.
- 삭제 클릭 시 확인 다이얼로그가 표시된 후 `DELETE /api/question-workbench/questions/{id}` 를 호출한다.
- 삭제 성공 후 해당 카드가 목록에서 제거되고 상세 패널이 초기화된다.

---

## Feature 5.3: Student Question Solver

### US-5.3.1 — 문제 탐색
**As** 학생  
**I want** 탐색 화면에서 Blueprint와 난이도로 필터링하여 풀고 싶은 문제를 직접 선택하고 싶다  
**So that** 내 취약 영역에 집중해서 자기주도적으로 학습할 수 있다.

**Acceptance Criteria:**
- Student Platform에 `/questions` 라우트가 존재한다.
- Blueprint, 난이도, 문제 타입 필터를 적용하여 published 문항만 목록에 표시된다.
- draft / archived 문항은 조회되지 않는다.
- 카드에는 지문 앞 50자, 난이도 배지, Blueprint 이름이 표시된다.

---

### US-5.3.2 — 문제 풀기
**As** 학생  
**I want** 선택한 문항의 지문을 읽고 답안을 제출하고 싶다  
**So that** 내 이해도를 즉각적으로 확인할 수 있다.

**Acceptance Criteria:**
- 카드 클릭 시 문제 풀기 화면으로 이동하며 지문 전체가 표시된다.
- MCQ: 라디오 버튼 A/B/C/D, O/X: 두 버튼, 단답형: 텍스트 입력으로 UI가 분기된다.
- 문제 풀기 화면에서 정답 필드(`correct_answer`)는 노출되지 않는다.

---

### US-5.3.3 — 채점 및 결과 확인
**As** 학생  
**I want** [제출] 버튼을 누르면 즉시 채점 결과와 해설을 확인하고 싶다  
**So that** 틀린 이유를 즉시 파악하고 학습 효율을 높일 수 있다.

**Acceptance Criteria:**
- [제출] 클릭 시 `POST /api/questions/{id}/submit` → Grader 에이전트 채점 흐름이 동작한다.
- 채점 후 정답 여부(O/X), 정답 선지 강조, 선택 선지의 rationale, 종합 해설이 표시된다.
- [다음 문제] 버튼으로 같은 Blueprint·난이도의 다음 문항으로 이동할 수 있다.

---

### US-5.3.4 — 학습 이력 기록
**As** 학생  
**I want** 내 풀이 결과가 자동으로 기록되어 마스터리 대시보드에 반영되길 원한다  
**So that** 시간 흐름에 따른 학습 진도를 추적할 수 있다.

**Acceptance Criteria:**
- 답안 제출 성공 시 정답 여부·소요 시간이 Student Platform 학습 이력 DB에 저장된다.
- 저장된 이력은 마스터리 대시보드에 반영된다.
