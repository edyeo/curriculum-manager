# [PRD] Synthetic Student Data Generation Engine

## 1. 개요 (Overview)

학습 시뮬레이션, 시스템 개발·테스트, 가상 학생 기반 답변 생성에 활용할 **가상 학생 페르소나를 생성하고 DB에 저장·관리하는 엔진**을 구현한다.

가상 학생은 subject 단위로 생성되며, 숙련도·학습특성·기질·답변 행동 등을 표현하는 **사용자 정의 편집 가능한 feature 집합**을 보유한다. DB에 저장된 페르소나는 별도의 Virtual Student Agent가 문제에 대한 가상 답변을 생성할 때 persona 컨텍스트로 참조한다.

> **이 PRD의 범위:** 페르소나 정의·생성·저장·관리만 다룬다. 가상 답변 생성 로직(Virtual Student Agent)은 별도 에픽에서 다룬다.

> **의존:** EPIC-004 Ontology API(subject 목록), EPIC-001 Student Platform(학생 DB 인프라)

---

## 2. 제품 원칙 (Product Principles)

**Subject 단위 페르소나:** 가상 학생은 반드시 특정 subject에 귀속된다. 동일 학생 archetype도 subject마다 별도 인스턴스를 갖는다.

**편집 가능한 Feature 스키마:** Feature 정의(키·설명·타입·기본값)는 시스템에 고정되지 않는다. 관리자가 feature를 추가·수정·삭제할 수 있으며, 기본 10개 feature는 초기값으로 제공된다.

**설명과 값의 분리:** 각 feature는 "이 feature가 무엇인지 설명하는 메타데이터"와 "이 학생의 해당 feature 값"을 명확히 구분하여 저장한다. Virtual Student Agent가 프롬프트를 조립할 때 두 정보를 함께 활용한다.

**페르소나 전용 테이블:** 가상 학생은 실제 학생 테이블과 분리된 전용 테이블에 저장한다. 운영 데이터 오염 방지와 명확한 데이터 출처 구분이 목적이다.

---

## 3. 핵심 개념

### Virtual Student

subject에 귀속된 가상 학생 레코드. 이름·설명과 함께 feature 값 집합을 보유한다.

```
{
  id: uuid,
  name: "분석형 중급 학습자",
  description: "체계적으로 접근하지만 시간이 걸리는 스타일",
  subject_id: "...",
  feature_values: [
    { feature_key: "prior_knowledge_level", value: "0.6" },
    { feature_key: "reasoning_style",       value: "단계적" },
    ...
  ]
}
```

### Feature Definition

페르소나를 구성하는 특성 항목의 메타데이터. 시스템 전체에서 공유되며 관리자가 편집 가능하다.

```
{
  key: "reasoning_style",
  display_name: "추론 스타일",
  description: "문제를 풀 때 사용하는 추론 방식. \
    직관적(빠르고 휴리스틱), 단계적(절차 준수), 분석적(분해 후 합성) 중 하나.",
  value_type: "categorical",        // categorical | numeric | text
  value_options: ["직관적", "단계적", "분석적"],  // categorical일 때
  value_range: null,                // numeric일 때 { min, max }
  default_value: "단계적",
  category: "답변 행동",            // 숙련도 | 학습특성 | 기질 | 답변 행동
  is_builtin: true                  // 기본 제공 feature 여부
}
```

### Feature Value

특정 가상 학생이 보유한 feature 값. Feature Definition과 분리 저장되어, 정의 변경 시 기존 값에 영향을 주지 않는다.

---

## 4. 기본 Feature 목록 (10개)

| key | display_name | category | value_type | 설명 |
|---|---|---|---|---|
| `prior_knowledge_level` | 사전 지식 수준 | 숙련도 | numeric (0~1) | 해당 subject에 대한 학습 시작 전 지식 수준 |
| `conceptual_depth` | 개념 이해 깊이 | 숙련도 | categorical (표면적/보통/깊은) | 개념을 암기 수준으로 아는지, 원리까지 이해하는지 |
| `learning_pace` | 학습 속도 | 학습특성 | categorical (느린/보통/빠른) | 새로운 개념을 습득하는 속도 |
| `error_pattern` | 오류 패턴 | 학습특성 | text | 주로 범하는 오류 유형 (예: "절차를 건너뜀", "개념을 혼동") |
| `question_interpretation_accuracy` | 문제 해석 정확도 | 학습특성 | numeric (0~1) | 문제 지문을 의도대로 정확히 해석하는 정도 |
| `confidence_level` | 자신감 수준 | 기질 | categorical (낮음/보통/높음/과신) | 자신의 답변에 대한 자신감 경향 |
| `persistence` | 끈기 | 기질 | numeric (0~1) | 어려운 문제에서 포기하지 않고 시도하는 정도 |
| `risk_tolerance` | 위험 감수 성향 | 기질 | categorical (낮음/보통/높음) | 불확실할 때 추측 답변을 제출하는 의향 |
| `verbosity` | 답변 상세도 | 답변 행동 | categorical (간략/보통/장문) | 답변 작성 시 설명의 길이와 상세함 정도 |
| `reasoning_style` | 추론 스타일 | 답변 행동 | categorical (직관적/단계적/분석적) | 문제 풀이 시 사용하는 추론 방식 |

---

## 5. 핵심 기능 명세

### Feature 10.1: Feature Definition 관리 API

**대상:** `contents-manager/backend` 또는 `student-platform/backend` (구현 시 결정)

**엔드포인트:**

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/api/virtual-students/feature-definitions` | 전체 feature 정의 목록 조회 |
| `POST` | `/api/virtual-students/feature-definitions` | 신규 feature 정의 추가 |
| `PUT` | `/api/virtual-students/feature-definitions/{key}` | feature 정의 수정 (description, display_name, default_value 등) |
| `DELETE` | `/api/virtual-students/feature-definitions/{key}` | feature 정의 삭제 (is_builtin=true이면 거부) |

**제약:**
- `is_builtin: true`인 기본 10개 feature는 삭제 불가. 수정은 가능.
- `key`는 생성 후 변경 불가 (외래 참조 무결성).

---

### Feature 10.2: Virtual Student CRUD API

**엔드포인트:**

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/api/virtual-students` | 전체 가상 학생 목록 (subject_id 필터 지원) |
| `GET` | `/api/virtual-students/{id}` | 가상 학생 상세 (feature_values 포함) |
| `POST` | `/api/virtual-students` | 가상 학생 생성 |
| `PUT` | `/api/virtual-students/{id}` | 가상 학생 정보 수정 |
| `DELETE` | `/api/virtual-students/{id}` | 가상 학생 삭제 |

**생성 요청 본문:**
```json
{
  "name": "분석형 중급 학습자",
  "description": "체계적이지만 속도가 느린 스타일",
  "subject_id": "cs-fundamentals",
  "feature_values": [
    { "feature_key": "prior_knowledge_level", "value": "0.5" },
    { "feature_key": "reasoning_style", "value": "단계적" }
  ]
}
```

**응답:** feature_values에 feature 정의의 `description`을 포함하여 반환 (Virtual Student Agent가 프롬프트 조립 시 바로 사용 가능하도록).

```json
{
  "id": "uuid",
  "name": "분석형 중급 학습자",
  "subject_id": "cs-fundamentals",
  "feature_values": [
    {
      "feature_key": "prior_knowledge_level",
      "display_name": "사전 지식 수준",
      "description": "해당 subject에 대한 학습 시작 전 지식 수준",
      "value": "0.5"
    },
    ...
  ]
}
```

---

### Feature 10.3: 가상 학생 일괄 생성 (Batch Seed)

**엔드포인트:**

| Method | Path | 설명 |
|---|---|---|
| `POST` | `/api/virtual-students/seed` | 정의된 템플릿 기반으로 여러 학생 일괄 생성 |

**용도:** 개발·테스트 환경에서 다양한 타입의 가상 학생을 빠르게 구성할 때 사용.

**요청 본문:**
```json
{
  "subject_id": "cs-fundamentals",
  "templates": [
    {
      "name": "초급 자신감 낮은 학습자",
      "description": "...",
      "feature_values": { "prior_knowledge_level": "0.2", "confidence_level": "낮음" }
    }
  ]
}
```

---

## 6. 데이터 모델

### `virtual_student_feature_definitions`

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `key` | VARCHAR PK | feature 식별자 (불변) |
| `display_name` | VARCHAR | UI 표시명 |
| `description` | TEXT | feature 의미 설명 (LLM 프롬프트용) |
| `value_type` | ENUM | `categorical` / `numeric` / `text` |
| `value_options` | JSONB | categorical 선택지 목록 |
| `value_range` | JSONB | numeric 범위 `{min, max}` |
| `default_value` | VARCHAR | 미입력 시 기본값 |
| `category` | VARCHAR | 숙련도 / 학습특성 / 기질 / 답변 행동 |
| `is_builtin` | BOOLEAN | 기본 제공 여부 (삭제 보호) |
| `created_at` | TIMESTAMP | |

### `virtual_students`

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | UUID PK | |
| `name` | VARCHAR | 페르소나 이름 |
| `description` | TEXT | 페르소나 설명 |
| `subject_id` | VARCHAR | 귀속 subject |
| `created_at` | TIMESTAMP | |
| `updated_at` | TIMESTAMP | |

### `virtual_student_feature_values`

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | UUID PK | |
| `virtual_student_id` | UUID FK → `virtual_students` | |
| `feature_key` | VARCHAR FK → `virtual_student_feature_definitions` | |
| `value` | TEXT | 모든 타입을 문자열로 저장 (해석은 definition의 value_type 기준) |

---

## 7. 구현 제약

- **미입력 feature 처리:** 생성 시 누락된 feature는 definition의 `default_value`로 자동 채운다. `default_value`도 없으면 레코드를 생성하지 않는다 (nullable 허용 안 함).
- **definition 변경 영향:** feature definition 수정은 기존 feature_values에 소급 적용하지 않는다. 값의 의미가 바뀌어도 기존 값은 보존된다.
- **subject 검증:** 가상 학생 생성 시 `subject_id`가 실제 존재하는 subject인지 Ontology API를 통해 검증한다.
- **실제 학생 테이블 분리:** `virtual_students`는 `students` 테이블과 완전히 분리된다. 공유 FK 없음.
