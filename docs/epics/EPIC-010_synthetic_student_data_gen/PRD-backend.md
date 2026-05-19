# [PRD] EPIC-010 Backend — Virtual Student API 서비스

> 핵심 개념·데이터 모델은 `PRD-synthetic_student_data_gen.md` 참조.
> 이 문서는 백엔드 서비스의 구현 상세를 다룬다.

---

## 1. 서비스 위치

신규 독립 FastAPI 서비스로 구현한다. `student-platform/backend`와 분리한다.

```
student-platform/
└── virtual-student-api/       # 신규
    ├── main.py
    ├── models.py
    ├── schemas.py
    ├── database.py
    ├── routes/
    │   ├── feature_definitions.py
    │   ├── virtual_students.py
    │   └── seed.py
    ├── seed_data/
    │   └── default_features.py   # 기본 10개 feature 정의
    ├── requirements.txt
    └── Dockerfile
```

**포트:** `8020` (기존 서비스와 충돌 없는 포트)

---

## 2. 기술 스택

| 항목 | 선택 |
|---|---|
| 프레임워크 | FastAPI |
| ORM | SQLAlchemy 2.x |
| DB (개발) | SQLite (`virtual_students.db`) |
| DB (운영) | PostgreSQL (환경변수로 전환) |
| 마이그레이션 | Alembic |
| 유효성 검사 | Pydantic v2 |

---

## 3. 환경 변수

```env
DATABASE_URL=sqlite:///./virtual_students.db   # dev 기본값
KG_API_URL=http://localhost:8010               # subject 검증용 Ontology API
```

---

## 4. DB 초기화 및 마이그레이션

### 4-1. 테이블 생성 순서

```
1. virtual_student_feature_definitions
2. virtual_students
3. virtual_student_feature_values
```

### 4-2. 기본 Feature Seed

서비스 최초 기동 시 `virtual_student_feature_definitions` 테이블이 비어 있으면 기본 10개 feature를 자동 삽입한다.

```python
# seed_data/default_features.py
DEFAULT_FEATURES = [
    {
        "key": "prior_knowledge_level",
        "display_name": "사전 지식 수준",
        "description": "해당 subject에 대한 학습 시작 전 지식 수준. "
                       "0.0은 완전 초보, 1.0은 전문가 수준.",
        "value_type": "numeric",
        "value_options": None,
        "value_range": {"min": 0.0, "max": 1.0},
        "default_value": "0.5",
        "category": "숙련도",
        "is_builtin": True,
    },
    {
        "key": "conceptual_depth",
        "display_name": "개념 이해 깊이",
        "description": "개념을 표면적으로 암기하는지, 원리까지 이해하는지를 나타낸다. "
                       "표면적은 정의 암기 수준, 깊은은 응용·연결 가능한 수준.",
        "value_type": "categorical",
        "value_options": ["표면적", "보통", "깊은"],
        "value_range": None,
        "default_value": "보통",
        "category": "숙련도",
        "is_builtin": True,
    },
    {
        "key": "learning_pace",
        "display_name": "학습 속도",
        "description": "새로운 개념을 습득하는 속도. "
                       "느린 학습자는 반복이 필요하고, 빠른 학습자는 적은 노출로 습득한다.",
        "value_type": "categorical",
        "value_options": ["느린", "보통", "빠른"],
        "value_range": None,
        "default_value": "보통",
        "category": "학습특성",
        "is_builtin": True,
    },
    {
        "key": "error_pattern",
        "display_name": "오류 패턴",
        "description": "이 학생이 주로 범하는 오류 유형에 대한 자유 텍스트 설명. "
                       "예: '절차를 건너뜀', '개념을 혼동함', '계산 실수가 잦음'.",
        "value_type": "text",
        "value_options": None,
        "value_range": None,
        "default_value": "특이 패턴 없음",
        "category": "학습특성",
        "is_builtin": True,
    },
    {
        "key": "question_interpretation_accuracy",
        "display_name": "문제 해석 정확도",
        "description": "문제 지문을 출제자의 의도대로 정확히 해석하는 정도. "
                       "0.0은 자주 잘못 해석, 1.0은 항상 정확히 해석.",
        "value_type": "numeric",
        "value_options": None,
        "value_range": {"min": 0.0, "max": 1.0},
        "default_value": "0.7",
        "category": "학습특성",
        "is_builtin": True,
    },
    {
        "key": "confidence_level",
        "display_name": "자신감 수준",
        "description": "자신의 답변에 대한 자신감 경향. "
                       "과신은 틀려도 확신하고, 낮음은 맞아도 불확실하게 표현한다.",
        "value_type": "categorical",
        "value_options": ["낮음", "보통", "높음", "과신"],
        "value_range": None,
        "default_value": "보통",
        "category": "기질",
        "is_builtin": True,
    },
    {
        "key": "persistence",
        "display_name": "끈기",
        "description": "어려운 문제에서 포기하지 않고 계속 시도하는 정도. "
                       "0.0은 조금만 막혀도 포기, 1.0은 끝까지 시도.",
        "value_type": "numeric",
        "value_options": None,
        "value_range": {"min": 0.0, "max": 1.0},
        "default_value": "0.5",
        "category": "기질",
        "is_builtin": True,
    },
    {
        "key": "risk_tolerance",
        "display_name": "위험 감수 성향",
        "description": "불확실한 상황에서 추측 답변을 제출하는 의향. "
                       "낮음은 모르면 빈칸, 높음은 추측해서라도 제출.",
        "value_type": "categorical",
        "value_options": ["낮음", "보통", "높음"],
        "value_range": None,
        "default_value": "보통",
        "category": "기질",
        "is_builtin": True,
    },
    {
        "key": "verbosity",
        "display_name": "답변 상세도",
        "description": "답변 작성 시 설명의 길이와 상세함 정도. "
                       "간략은 핵심만, 장문은 배경·근거까지 상세히 서술.",
        "value_type": "categorical",
        "value_options": ["간략", "보통", "장문"],
        "value_range": None,
        "default_value": "보통",
        "category": "답변 행동",
        "is_builtin": True,
    },
    {
        "key": "reasoning_style",
        "display_name": "추론 스타일",
        "description": "문제를 풀 때 사용하는 추론 방식. "
                       "직관적은 빠른 휴리스틱, 단계적은 절차 준수, 분석적은 분해 후 합성.",
        "value_type": "categorical",
        "value_options": ["직관적", "단계적", "분석적"],
        "value_range": None,
        "default_value": "단계적",
        "category": "답변 행동",
        "is_builtin": True,
    },
]
```

---

## 5. API 엔드포인트 상세

### 5-1. Feature Definition

#### `GET /api/virtual-students/feature-definitions`

응답:
```json
[
  {
    "key": "reasoning_style",
    "display_name": "추론 스타일",
    "description": "...",
    "value_type": "categorical",
    "value_options": ["직관적", "단계적", "분석적"],
    "value_range": null,
    "default_value": "단계적",
    "category": "답변 행동",
    "is_builtin": true,
    "created_at": "2026-05-19T00:00:00"
  }
]
```

#### `POST /api/virtual-students/feature-definitions`

요청:
```json
{
  "key": "attention_span",
  "display_name": "집중력 지속 시간",
  "description": "한 문제에 집중을 유지할 수 있는 시간 경향.",
  "value_type": "categorical",
  "value_options": ["짧음", "보통", "긺"],
  "value_range": null,
  "default_value": "보통",
  "category": "기질"
}
```

- `key` 중복 시 `409 Conflict`
- `value_type`이 `categorical`이면 `value_options` 필수

#### `PUT /api/virtual-students/feature-definitions/{key}`

수정 가능 필드: `display_name`, `description`, `value_options`, `value_range`, `default_value`, `category`

수정 불가 필드: `key`, `value_type`, `is_builtin`

#### `DELETE /api/virtual-students/feature-definitions/{key}`

- `is_builtin: true` → `403 Forbidden`
- 해당 key를 참조하는 `virtual_student_feature_values`가 있으면 `409 Conflict`

---

### 5-2. Virtual Students

#### `GET /api/virtual-students`

쿼리 파라미터:
- `subject_id` (optional): subject 필터
- `page` (default: 1), `page_size` (default: 20)

응답:
```json
{
  "total": 42,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": "uuid",
      "name": "분석형 중급 학습자",
      "description": "...",
      "subject_id": "cs-fundamentals",
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

> 목록 응답에는 `feature_values` 미포함 (성능). 상세 조회에서 포함.

#### `GET /api/virtual-students/{id}`

응답에 `feature_values` 포함. 각 값에 definition의 `description` 조인하여 반환.

```json
{
  "id": "uuid",
  "name": "분석형 중급 학습자",
  "subject_id": "cs-fundamentals",
  "feature_values": [
    {
      "feature_key": "reasoning_style",
      "display_name": "추론 스타일",
      "description": "문제를 풀 때 사용하는 추론 방식...",
      "category": "답변 행동",
      "value": "분석적"
    }
  ]
}
```

#### `POST /api/virtual-students`

- `subject_id` 유효성: `KG_API_URL/api/subjects/{subject_id}` 호출하여 404이면 `422 Unprocessable Entity`
- `feature_values` 미제출 feature는 definition의 `default_value`로 자동 채움
- 알 수 없는 `feature_key` 포함 시 `422`

#### `PUT /api/virtual-students/{id}`

- `feature_values` 부분 업데이트 지원: 포함된 key만 갱신, 나머지는 유지
- `subject_id` 변경 가능 (재검증)

#### `DELETE /api/virtual-students/{id}`

- Cascade: 연결된 `feature_values`도 삭제

---

### 5-3. Batch Seed

#### `POST /api/virtual-students/seed`

```json
{
  "subject_id": "cs-fundamentals",
  "templates": [
    {
      "name": "초급 자신감 낮은 학습자",
      "description": "기초 지식이 부족하고 자신감도 낮은 전형적인 입문자",
      "feature_values": {
        "prior_knowledge_level": "0.2",
        "confidence_level": "낮음",
        "learning_pace": "느린",
        "persistence": "0.3"
      }
    }
  ]
}
```

응답: 생성된 가상 학생 목록 (id 포함)

---

### 5-4. 통계 API (대시보드용)

#### `GET /api/virtual-students/stats`

쿼리 파라미터:
- `subject_id` (optional)

응답: feature별 값 분포 집계

```json
{
  "subject_id": "cs-fundamentals",
  "total_students": 42,
  "feature_distributions": [
    {
      "feature_key": "confidence_level",
      "display_name": "자신감 수준",
      "category": "기질",
      "value_type": "categorical",
      "distribution": [
        { "value": "낮음",  "count": 8,  "ratio": 0.19 },
        { "value": "보통",  "count": 20, "ratio": 0.48 },
        { "value": "높음",  "count": 10, "ratio": 0.24 },
        { "value": "과신",  "count": 4,  "ratio": 0.10 }
      ]
    },
    {
      "feature_key": "prior_knowledge_level",
      "display_name": "사전 지식 수준",
      "category": "숙련도",
      "value_type": "numeric",
      "distribution": {
        "min": 0.1,
        "max": 0.9,
        "mean": 0.51,
        "buckets": [
          { "range": "0.0–0.2", "count": 5 },
          { "range": "0.2–0.4", "count": 10 },
          { "range": "0.4–0.6", "count": 15 },
          { "range": "0.6–0.8", "count": 8 },
          { "range": "0.8–1.0", "count": 4 }
        ]
      }
    }
  ]
}
```

---

## 6. CORS

프론트엔드(신규 앱, `http://localhost:3010`)에서 호출 허용.

```python
origins = ["http://localhost:3010", "http://localhost:3000"]
```

---

## 7. Docker

```yaml
# docker-compose.local.yml에 추가
virtual-student-api:
  build: ./student-platform/virtual-student-api
  ports:
    - "8020:8020"
  environment:
    - DATABASE_URL=sqlite:///./data/virtual_students.db
    - KG_API_URL=http://contents-backend:8010
  volumes:
    - ./student-platform/virtual-student-api/data:/app/data
```
