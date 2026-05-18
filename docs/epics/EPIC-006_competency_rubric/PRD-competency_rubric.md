# [PRD] Competency Rubric

## 1. 개요 (Overview)

[EPIC-005](../EPIC-005_question_bank/PRD-question_bank.md)에서 구현된 문제은행과 NodeMastery 점수 체계를 확장하여, **Blueprint를 Competency Rubric 단위로 재정의**하고 학생의 이해도를 입체적으로 평가하는 EPIC.

현재 시스템은 노드 단위 mastery_score를 단순 EMA로 산출하지만, 이는 "어떤 측면을 얼마나 이해했는가"라는 shape 정보를 지운다. Blueprint는 이미 "이 개념을 이해했다면 풀 수 있어야 하는 문제 시나리오"를 정의하고 있으므로, Blueprint를 Rubric 단위로 삼아 **Blueprint 달성도 기반 Competency 점수**를 산출한다.

> **의존:** EPIC-005 Question Bank가 완성된 이후 진행한다.

---

## 2. 제품 원칙 (Product Principles)

**Blueprint = Rubric:** 별도 Rubric 엔티티를 만들지 않는다. Blueprint가 이미 "이 개념의 이해를 검증하는 문제 시나리오"를 정의하므로, Blueprint에 `weight`와 `required` 속성을 추가해 Rubric 역할을 겸하도록 한다.

**Shape 보존:** 단순 평균 대신 Blueprint별 달성도를 유지한다. "5개 노드 중 3개 완전 이해 + 2개 미달"과 "5개 모두 60%"는 다른 프로파일이다.

**점진적 도입:** 기존 NodeMastery EMA 점수는 유지한다. Competency 점수는 Blueprint 달성도를 추가 레이어로 얹는 방식으로, 하위 호환성을 깨지 않는다.

---

## 3. 핵심 개념

### Blueprint Clearance

학생이 특정 Blueprint에 속한 문항들을 통해 일정 수준 이상의 성취를 보였을 때 "Blueprint를 달성(clear)했다"고 정의한다.

```
blueprint_clearance(student, blueprint) =
  정답 문항 수 / 해당 blueprint 문항 수  ≥  threshold (예: 0.7)
```

### Competency Score

노드에 연결된 Blueprint들의 weighted clearance 합산:

```
competency(student, node) =
  Σ(blueprint.weight × cleared(student, blueprint)) / Σ(blueprint.weight)
```

- `required=True`인 Blueprint를 미달성 시 전체 competency를 일정 수준 이상으로 인정하지 않음 (상한 0.5 적용)

---

## 4. 핵심 기능 명세

### Feature 6.1: Blueprint Rubric 속성 추가

**대상:** `contents-manager/backend` — Blueprint 모델 및 API

**변경 사항:**
- `Blueprint` 모델에 `weight: Float (default=1.0)`, `required: Boolean (default=False)` 필드 추가
- DB 마이그레이션: `ALTER TABLE blueprints ADD COLUMN weight`, `required`
- CM Backend `PUT /api/blueprints/{id}` 에 해당 필드 업데이트 지원
- CM Frontend Blueprint 편집 UI에 weight / required 필드 노출

---

### Feature 6.2: Blueprint Attempt 이력 (기존 활용)

**대상:** `student-platform/backend`

`StudyAttempt` 에 `blueprint_id`가 이미 기록되어 있으므로 (EPIC-005), 신규 테이블 없이 기존 쿼리로 blueprint별 정답률 산출 가능.

---

### Feature 6.3: Competency Score 산출 API

**대상:** `student-platform/backend`

**신규 엔드포인트:**

```
GET /study/competency?subject_id={id}
```

**응답:**
```json
{
  "nodes": [
    {
      "node_id": "...",
      "node_name": "...",
      "competency_score": 0.83,
      "blueprints": [
        {
          "blueprint_id": "...",
          "blueprint_name": "...",
          "weight": 1.0,
          "required": false,
          "clearance": 0.9,
          "cleared": true,
          "attempt_count": 5,
          "correct_count": 4
        }
      ],
      "required_blueprint_cleared": true
    }
  ]
}
```

**산출 로직:**
1. `subject_id`의 KG 노드 목록 조회 (CM API 프록시)
2. 각 노드에 연결된 Blueprint 목록 조회 (CM API)
3. `StudyAttempt` 집계: blueprint별 attempt_count, correct_count
4. clearance = correct_count / published_question_count (최소 1회 시도 기준)
5. competency = weighted avg of clearance
6. required Blueprint 미달성 시 competency 상한 0.5 적용

---

### Feature 6.4: Student Competency Dashboard

**대상:** `student-platform/frontend`

**이해도 현황 탭 개편:**
- 기존: NodeMastery EMA 점수 단순 나열
- 변경: Blueprint 달성 현황 포함한 노드별 competency 카드

**컴포넌트:**
- `CompetencyDashboard` (기존 `MasteryDashboard` 대체)
- 노드 카드: competency_score 게이지 + blueprint 달성 배지 목록
- required blueprint 미달성 시 경고 표시

---

## 5. 기술 스택 및 제약

| 항목 | 결정 |
|------|------|
| 신규 모델 | 없음 (Blueprint 필드 추가만) |
| 하위 호환 | NodeMastery EMA 유지, competency는 별도 엔드포인트 |
| Blueprint 조회 | CM API 프록시 (기존 `_cm_get` 패턴) |
| DB 마이그레이션 | `ALTER TABLE blueprints ADD COLUMN weight`, `required` |

---

## 6. 범위 외 (Out of Scope)

- Rubric 기반 자동 학습 추천 (별도 Epic)
- 교사/관리자용 학생 competency 리포트
- 코스 수료 인증 (Certificate)
