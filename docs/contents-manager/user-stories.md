# User Stories: Contents Manager

**버전:** 0.1 (초안)  
**작성일:** 2026-05-15

---

## Epic 1: 인증

### US-01 로그인

```
As a 콘텐츠 작성자
I want to 이메일·패스워드로 로그인하고 싶다
So that 내 작업 내역을 안전하게 관리할 수 있다
```

**Acceptance Criteria:**
- 이메일·패스워드 입력 폼 제공
- 로그인 성공 시 JWT 토큰 발급 → Subject 목록 화면으로 이동
- 로그인 실패 시 "이메일 또는 패스워드가 올바르지 않습니다" 표시
- 토큰 만료(24h) 시 자동 로그아웃 → 로그인 화면으로 리다이렉트

---

### US-02 로그아웃

```
As a 로그인된 사용자
I want to 로그아웃하고 싶다
So that 공용 PC에서 안전하게 세션을 종료할 수 있다
```

**Acceptance Criteria:**
- 헤더 우측에 로그아웃 버튼 상시 노출
- 클릭 시 localStorage 토큰 삭제 → 로그인 화면으로 이동

---

## Epic 2: Subject 관리

### US-03 Subject 목록 조회

```
As a 콘텐츠 작성자
I want to Subject 목록을 보고 싶다
So that 전체 작업 현황을 한눈에 파악할 수 있다
```

**Acceptance Criteria:**
- 로그인 직후 Subject 목록 표시
- 각 항목: Subject 이름, 생성일, 노드 수, 상태 (draft/active/archived)
- Subject 클릭 시 해당 Subject의 편집 화면으로 전환

---

### US-04 Subject 생성

```
As a 콘텐츠 작성자
I want to 새 Subject를 생성하고 싶다
So that AI가 커리큘럼 초안을 자동으로 만들어 줄 수 있다
```

**Acceptance Criteria:**
- "새 Subject" 버튼 클릭 → 이름(필수), 설명(선택) 입력 폼 표시
- 저장 시 Backend에 Subject 생성 + API Gateway `POST /curriculum/generate` 자동 호출
- AI Draft 생성 중 로딩 스피너 표시 (수십 초 소요 가능)
- 완료 후 해당 Subject의 편집 탭(노드 테이블)으로 자동 이동

---

### US-05 Subject 삭제

```
As a 콘텐츠 작성자
I want to 불필요한 Subject를 삭제하고 싶다
So that 목록이 정돈된 상태로 유지된다
```

**Acceptance Criteria:**
- Subject 항목에 삭제 버튼 제공
- 삭제 전 "정말 삭제하시겠습니까?" 확인 다이얼로그
- 확인 후 목록에서 즉시 제거

---

## Epic 3: Curriculum 편집 (편집 탭)

### US-06 노드 테이블 조회

```
As a 콘텐츠 작성자
I want to Subject의 모든 노드를 테이블로 보고 싶다
So that 커리큘럼 구성 요소 전체를 한번에 파악하고 편집할 수 있다
```

**Acceptance Criteria:**
- 컬럼: 이름, 타입 (Seed/Concept/TechStack), Depth (1-3), 설명 (요약), 관계 수, 문제 수
- 타입·Depth 필터, 이름/설명 키워드 검색 지원
- 행 클릭 시 우측 슬라이드 패널 열림

---

### US-07 노드 편집

```
As a 콘텐츠 작성자
I want to 노드의 이름과 설명을 수정하고 싶다
So that AI가 생성한 내용을 사람이 다듬을 수 있다
```

**Acceptance Criteria:**
- 행 클릭 → 우측 슬라이드 패널에서 이름·설명 전체 편집 가능
- "저장" 버튼 클릭 시 `PATCH /subjects/{id}/nodes/{node_id}` 호출
- 저장 성공 시 테이블 해당 행 즉시 반영

---

### US-08 노드 추가

```
As a 콘텐츠 작성자
I want to 새 노드를 커리큘럼에 추가하고 싶다
So that AI가 빠뜨린 개념을 직접 보완할 수 있다
```

**Acceptance Criteria:**
- 테이블 상단 "+ 노드 추가" 버튼 클릭 → 테이블 하단에 인라인 입력 행 삽입
- 입력 필드: 이름(필수), 타입 선택, Depth 선택, 설명(선택)
- "저장" 클릭 시 `POST /subjects/{id}/nodes` 호출
- 저장 후 인라인 행이 일반 행으로 전환되어 테이블에 추가됨

---

### US-09 노드 삭제

```
As a 콘텐츠 작성자
I want to 불필요한 노드를 삭제하고 싶다
So that 커리큘럼을 정제된 상태로 유지할 수 있다
```

**Acceptance Criteria:**
- 슬라이드 패널 하단 "노드 삭제" 버튼
- 삭제 확인 후 `DELETE /subjects/{id}/nodes/{node_id}` 호출
- 삭제 후 패널 닫힘, 테이블에서 행 제거

---

### US-10 관계(엣지) 관리

```
As a 콘텐츠 작성자
I want to 노드 간의 관계를 추가하거나 삭제하고 싶다
So that 학습 순서와 개념 연결 구조를 올바르게 표현할 수 있다
```

**Acceptance Criteria:**
- 슬라이드 패널 내 "관계" 섹션: 현재 관계 목록 표시 (대상 노드명, 관계 타입)
- 관계 타입: requires / implemented_by / evolves_to
- "관계 추가" → 대상 노드 검색 + 관계 타입 선택 → 저장
- 기존 관계 항목 옆 삭제 버튼

---

### US-11 AI Expand

```
As a 콘텐츠 작성자
I want to AI에게 커리큘럼 그래프를 확장해달라고 요청하고 싶다
So that 누락된 개념이나 기술을 자동으로 보완받을 수 있다
```

**Acceptance Criteria:**
- 편집 탭 상단 "AI 확장" 버튼
- 클릭 시 `POST /subjects/{id}/curriculum/expand` 호출 (비동기)
- 완료 후 테이블에 새 노드 추가, "NEW" 배지 표시 (세션 내 유지)

---

## Epic 4: 그래프 탭

### US-12 그래프 시각화

```
As a 콘텐츠 작성자
I want to 커리큘럼의 노드·관계를 그래프로 보고 싶다
So that 전체 구조와 연결 흐름을 시각적으로 파악할 수 있다
```

**Acceptance Criteria:**
- 노드: 타입별 색상 구분 (Seed: amber, Concept: sky, TechStack: emerald)
- 엣지: 관계 타입 라벨 표시 (requires / implemented_by / evolves_to)
- 그래프는 참조용 — 이 탭에서 직접 편집 불가
- 노드 클릭 시 이름·설명 툴팁 표시

---

## Epic 5: 리서치 탭

### US-13 리서치 결과 조회

```
As a 콘텐츠 작성자
I want to Subject의 리서치 결과를 보고 싶다
So that AI가 자동 조사한 자료를 콘텐츠 작성 레퍼런스로 활용할 수 있다
```

**배경:** Researcher 에이전트는 curriculum 전체를 분석해 keyword를 자체 도출하고 조사한다.
결과는 Subject 단위로 조회한다. Entity별 조회가 아님.

**Acceptance Criteria:**
- "리서치 시작" 버튼 → `POST /subjects/{id}/research/start` 호출 (비동기)
- 결과 목록: keyword, source (blog/linkedin/paper/github), title, summary, url
- keyword 검색 및 source 필터 지원
- url 클릭 시 새 탭으로 외부 링크 열기

---

## Epic 6: 문제 관리 (편집 탭 슬라이드 패널)

### US-14 문제 조회

```
As a 콘텐츠 작성자
I want to 각 노드에 연결된 문제를 확인하고 싶다
So that 평가 자료 완성도를 노드별로 파악할 수 있다
```

**Acceptance Criteria:**
- 슬라이드 패널 내 "Questions" 탭
- 문제 목록: 난이도 (easy/medium/hard) 배지, 질문 텍스트 요약
- 문제가 없으면 "문제 없음 — 생성하기" 안내

---

### US-15 문제 생성

```
As a 콘텐츠 작성자
I want to 특정 노드의 문제를 AI에게 생성 요청하고 싶다
So that 평가 자료를 빠르게 확보할 수 있다
```

**Acceptance Criteria:**
- "문제 생성" 버튼 클릭 → `POST /subjects/{id}/nodes/{node_id}/questions` 호출
- 생성 중 로딩 표시
- 완료 후 문제 목록 즉시 갱신

---

## Epic 7: 사용자 관리 — P2

### US-16 사용자 초대

```
As a Admin
I want to 팀원을 이메일로 초대하고 싶다
So that 함께 커리큘럼을 작성할 수 있다
```

**Acceptance Criteria:**
- Admin 탭 → 이메일 입력 + 역할 선택 (editor/viewer) → "초대" 클릭
- 초대된 사용자는 임시 패스워드로 최초 로그인 후 변경

---

### US-17 권한 관리

```
As a Admin
I want to 사용자별 역할을 변경하고 싶다
So that 필요에 따라 편집·열람 권한을 조정할 수 있다
```

**Acceptance Criteria:**
- 사용자 목록에서 역할 드롭다운으로 즉시 변경 가능
- Viewer 역할은 노드 편집·추가·삭제 버튼이 비활성화됨
