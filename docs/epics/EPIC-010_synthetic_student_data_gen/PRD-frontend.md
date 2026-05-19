# [PRD] EPIC-010 Frontend — Virtual Student Manager

> 핵심 개념·데이터 모델은 `PRD-synthetic_student_data_gen.md`,
> API 명세는 `PRD-backend.md` 참조.
> 이 문서는 신규 프론트엔드 앱의 UI/UX 명세를 다룬다.

---

## 1. 앱 개요

가상 학생 페르소나를 생성·관리하고, 생성된 학생들의 feature 분포를 시각화하는 **독립 관리자 웹앱**.

기존 `contents-manager/frontend`, `student-platform/frontend`와 완전히 분리된 신규 앱이다.

```
student-platform/
└── virtual-student-ui/          # 신규
    ├── src/
    │   ├── pages/
    │   │   ├── Dashboard.tsx    # 학생 목록 + 분포 대시보드
    │   │   ├── Students.tsx     # 가상 학생 CRUD
    │   │   └── Features.tsx     # Feature Definition 관리
    │   ├── components/
    │   ├── api/
    │   └── main.tsx
    ├── index.html
    ├── vite.config.ts
    └── package.json
```

**포트:** `3010`
**API 연결:** `http://localhost:8020` (virtual-student-api)

---

## 2. 기술 스택

| 항목 | 선택 |
|---|---|
| 번들러 | Vite |
| UI 프레임워크 | React + TypeScript |
| 스타일 | Tailwind CSS |
| 차트 | Recharts |
| 라우터 | React Router v6 |
| HTTP | fetch (또는 axios) |

---

## 3. 화면 구성

### 3-1. 공통 레이아웃

```
┌──────────────────────────────────────────────────────┐
│  [Virtual Student Manager]   Dashboard | Students | Features │
├──────────────────────────────────────────────────────┤
│                                                      │
│                  <페이지 콘텐츠>                       │
│                                                      │
└──────────────────────────────────────────────────────┘
```

상단 네비게이션 3개 탭: **Dashboard / Students / Features**

---

### 3-2. Dashboard 페이지 (`/`)

두 섹션으로 구성: 학생 목록 테이블 + Feature 분포 대시보드.

#### 섹션 A — 학생 목록 테이블

```
Subject 필터: [ cs-fundamentals ▼ ]      총 42명

┌──────┬──────────────────────────┬─────────────────┬──────────────┐
│  #   │  이름                    │  Subject        │  생성일      │
├──────┼──────────────────────────┼─────────────────┼──────────────┤
│  1   │  분석형 중급 학습자       │  cs-fundamentals │  2026-05-19  │
│  2   │  직관형 초급 학습자       │  cs-fundamentals │  2026-05-19  │
│  3   │  …                       │  …               │  …           │
└──────┴──────────────────────────┴─────────────────┴──────────────┘
                                          [ < 1 2 3 … > ]
```

- Subject 드롭다운으로 필터링 (전체 / 특정 subject)
- 행 클릭 → Students 페이지의 해당 학생 상세로 이동
- 페이지네이션: page_size=20

#### 섹션 B — Feature 분포 대시보드

Subject 필터와 연동. 선택된 subject(또는 전체)의 `GET /api/virtual-students/stats` 결과를 시각화.

**Categorical feature → Bar Chart (수평)**

```
자신감 수준 (기질)
낮음  ████████░░░░░░░░░░░░  8명  (19%)
보통  ████████████████████  20명 (48%)
높음  ██████████░░░░░░░░░░  10명 (24%)
과신  ████░░░░░░░░░░░░░░░░  4명  (10%)
```

**Numeric feature → Histogram (버킷별 막대)**

```
사전 지식 수준 (숙련도)
0.0–0.2 ██████░░░░  5명
0.2–0.4 ████████████  10명
0.4–0.6 ██████████████████  15명
0.6–0.8 ██████████  8명
0.8–1.0 █████░░░░░  4명
  평균: 0.51
```

**Text feature → 카드 표시만** (통계 불가, "자유 텍스트 feature" 안내)

레이아웃: feature 카드 그리드 (2열). category 탭(숙련도 / 학습특성 / 기질 / 답변 행동)으로 필터 가능.

---

### 3-3. Students 페이지 (`/students`)

가상 학생 CRUD.

#### 목록 뷰

Dashboard 테이블과 동일하나 **[+ 새 학생]** 버튼 추가.

#### 생성/편집 폼 (슬라이드오버 패널 또는 별도 페이지)

```
이름 *        [__________________________]
설명          [__________________________]
Subject *     [ cs-fundamentals         ▼]

── Feature 값 ──────────────────────────────
사전 지식 수준 (숙련도)   [0.5        ] (0~1)
개념 이해 깊이 (숙련도)   [ 보통      ▼]
학습 속도 (학습특성)      [ 보통      ▼]
오류 패턴 (학습특성)      [__________________________]
…
────────────────────────────────────────────
                          [취소]  [저장]
```

- feature 목록은 `GET /api/virtual-students/feature-definitions` 동적 로드
- `value_type`에 따라 입력 위젯 자동 변환:
  - `numeric` → 슬라이더 + 숫자 입력
  - `categorical` → 드롭다운
  - `text` → 텍스트 입력

#### 상세 뷰

학생 카드 + feature 값 목록 (description 포함 표시).

---

### 3-4. Features 페이지 (`/features`)

Feature Definition 관리.

#### 목록

```
[ + 새 Feature ]

카테고리 탭: 전체 | 숙련도 | 학습특성 | 기질 | 답변 행동

┌──────────────────────┬──────────┬───────────┬──────────┬────────┐
│  Key                 │  표시명  │  타입     │  카테고리 │  액션  │
├──────────────────────┼──────────┼───────────┼──────────┼────────┤
│  prior_knowledge_…   │  사전 지식 수준  │  numeric  │  숙련도  │  편집  │
│  reasoning_style     │  추론 스타일  │  categorical  │  답변 행동  │  편집  │
│  attention_span      │  집중력  │  categorical  │  기질   │  편집  삭제  │
└──────────────────────┴──────────┴───────────┴──────────┴────────┘
```

- `is_builtin: true` → 삭제 버튼 비활성화 (툴팁: "기본 제공 feature는 삭제할 수 없습니다")
- `is_builtin: true` → 편집 가능 (description, display_name, default_value만)

#### 생성/편집 폼

```
Key *               [______________]  (생성 시만 입력 가능, 편집 시 비활성)
표시명 *             [______________]
설명 *               [__________________________]
타입 *               [ categorical ▼]            (생성 시만 선택 가능)
  └ 선택지 (categorical) [낮음, 보통, 높음]  [+ 추가]
  └ 범위 (numeric)       최소 [0] 최대 [1]
기본값              [______________]
카테고리 *          [ 기질        ▼]
                    [취소]  [저장]
```

---

## 4. 상태 관리

별도 전역 상태 라이브러리 없이 React Query(또는 SWR)로 서버 상태 관리.

- Feature definitions: 앱 마운트 시 1회 로드, 캐시
- Students 목록: subject 필터 변경 시 재조회
- Stats: subject 필터 변경 시 재조회

---

## 5. 오류 처리

| 상황 | UI 처리 |
|---|---|
| API 연결 실패 | 각 섹션에 "데이터를 불러올 수 없습니다" + 재시도 버튼 |
| 학생 생성 실패 (422) | 폼 하단에 인라인 오류 메시지 |
| `is_builtin` feature 삭제 시도 | 삭제 버튼 비활성화로 선제 방지 |
| subject 검증 실패 | Subject 드롭다운 하단에 "유효하지 않은 subject" 표시 |
