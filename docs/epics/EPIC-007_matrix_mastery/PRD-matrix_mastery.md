# [PRD] Blueprint Matrix Mastery

## 1. 개요 (Overview)

[EPIC-006](../EPIC-006_competency_rubric/PRD-competency_rubric.md)에서 구현된 Blueprint 달성도 체계를 확장하여, **학생의 역량을 matrix 셀(layer/stage) 단위까지 분해·추적**한다.

문제는 KG entity + Blueprint matrix 요소의 조합으로 생성된다. 따라서 답안 제출 시 단일 점수가 아닌 **해당 문제가 테스트한 matrix 셀별 점수**를 Grader가 분해 산출하고, 이를 바탕으로 NodeMastery·CellMastery·IntegrationItemMastery 세 레벨이 동시에 업데이트된다.

> **의존:** EPIC-006 Competency Rubric이 완성된 이후 진행한다.

---

## 2. 핵심 설계 원칙

**Question = KG ↔ Blueprint 조인 포인트**
문제 생성 시 사용된 KG entity 목록과 matrix 셀 목록을 링크 테이블에 기록한다. 이 링크가 제출 시 양측 점수 업데이트의 기준이 된다.

**3-레벨 동시 업데이트**
1회 채점 결과로 NodeMastery(KG) / CellMastery(matrix 셀) / IntegrationItemMastery 세 레벨이 동시에 반영된다.

**IntegrationItem mastery = min(required_combinations 셀 점수)**
IntegrationItem이 요구하는 모든 셀 중 가장 낮은 점수가 해당 Item의 mastery가 된다.

**Blueprint clearance는 여전히 derived**
IntegrationItem mastery에서 on-demand 집계 (EPIC-006 로직 유지).

---

## 3. 핵심 개념

### Matrix 셀 점수 (CellMastery)

```
cell_mastery(student, blueprint, layer, stage)
```

Grader가 답안을 평가할 때 문제가 커버하는 각 셀에 대해 개별 점수(0.0~1.0)를 반환한다.

### IntegrationItem Mastery

```
integration_item_mastery(student, item) =
  min( cell_mastery(student, blueprint, c.layer, c.stage)
       for c in item.required_combinations )
```

### NodeMastery (기존 유지)

문제에 연결된 각 KG entity에 대해 기존 EMA 방식으로 업데이트된다.

---

## 4. 핵심 기능 명세

### Feature 7.1: 문제-링크 테이블 (CM Backend)

**신규 테이블:**

```sql
-- 문제 ↔ KG entity 연결
CREATE TABLE question_entity_links (
  question_id TEXT REFERENCES question_items(id) ON DELETE CASCADE,
  entity_id   TEXT NOT NULL,
  PRIMARY KEY (question_id, entity_id)
);

-- 문제 ↔ Blueprint matrix 셀 연결
CREATE TABLE question_matrix_links (
  question_id          TEXT REFERENCES question_items(id) ON DELETE CASCADE,
  blueprint_id         TEXT REFERENCES blueprints(id) ON DELETE CASCADE,
  layer                TEXT NOT NULL,
  stage                TEXT NOT NULL,
  integration_item_id  TEXT REFERENCES blueprint_integration_items(id) ON DELETE SET NULL,
  PRIMARY KEY (question_id, blueprint_id, layer, stage)
);
```

**CM Agent 파이프라인 변경:**
- 문제 생성 완료 후 사용된 entity 목록 → `question_entity_links` 저장
- 사용된 matrix 셀 목록 → `question_matrix_links` 저장
- 셀이 속하는 `integration_item_id` 매핑도 함께 저장

**KG API 확장:**
- `GET /kg/nodes/{node_id}/questions` 응답에 `entity_links`, `matrix_links` 포함

---

### Feature 7.2: Grader matrix 셀 분해 (Grader Agent)

**현재:** `{is_correct, score, feedback}` 단일 점수 반환

**변경:** `matrix_cells` 컨텍스트를 입력으로 받아 셀별 점수 분해 반환

```python
# 입력 추가
matrix_cells: list[dict]  # [{"layer": "Concept", "stage": "원리"}, ...]

# 출력 추가
"cell_scores": {
  "Concept/원리": 0.9,
  "TechStack/스펙": 0.7
}
```

Grader 프롬프트: 각 셀의 정의(layer/stage 의미)를 컨텍스트로 제공하고, 답안이 해당 역량을 얼마나 충족했는지 0.0~1.0으로 평가.

---

### Feature 7.3: Mastery 테이블 신설 (SP Backend)

```python
class BlueprintCellMastery(Base):
    __tablename__ = "blueprint_cell_mastery"
    id            = Column(Integer, primary_key=True)
    student_id    = Column(Integer, ForeignKey("students.id"), nullable=False)
    blueprint_id  = Column(Text, nullable=False)
    layer         = Column(Text, nullable=False)
    stage         = Column(Text, nullable=False)
    mastery_score = Column(Float, default=0.0)
    attempt_count = Column(Integer, default=0)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("student_id", "blueprint_id", "layer", "stage"),)


class BlueprintItemMastery(Base):
    __tablename__ = "blueprint_item_mastery"
    id                  = Column(Integer, primary_key=True)
    student_id          = Column(Integer, ForeignKey("students.id"), nullable=False)
    integration_item_id = Column(Text, nullable=False)
    mastery_score       = Column(Float, default=0.0)
    attempt_count       = Column(Integer, default=0)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("student_id", "integration_item_id"),)
```

---

### Feature 7.4: 제출 시 3-레벨 동시 업데이트 (SP Backend)

**대상:** `POST /questions/{id}/submit`

**변경 흐름:**

```
1. CM API에서 question의 entity_links + matrix_links 조회
2. Grader 호출 (matrix_cells 포함)
3. StudyAttempt 기록 (기존)
4. NodeMastery 업데이트 — entity_links의 각 entity_id (기존 EMA)
5. BlueprintCellMastery 업데이트 — matrix_links의 각 (blueprint_id, layer, stage)
6. BlueprintItemMastery 업데이트 — cell 점수로 required_combinations min 계산
```

**BlueprintCellMastery 업데이트 (EMA 방식):**
```python
cell_mastery_new = cell_mastery_old + (cell_score - cell_mastery_old) * 0.3
```

**BlueprintItemMastery 업데이트:**
```python
item_score = min(cell_scores[f"{c.layer}/{c.stage}"] for c in item.required_combinations)
item_mastery_new = item_mastery_old + (item_score - item_mastery_old) * 0.3
```

---

### Feature 7.5: Competency API 개편 (SP Backend)

**`GET /study/competency`** 응답에 cell mastery 및 item mastery 추가:

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
          "integration_items": [
            {
              "item_id": "...",
              "item_name": "...",
              "mastery_score": 0.85,
              "required_combinations": [
                {"layer": "Concept", "stage": "원리", "cell_mastery": 0.9},
                {"layer": "TechStack", "stage": "스펙", "cell_mastery": 0.8}
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

---

### Feature 7.6: CompetencyDashboard 개편 (SP Frontend)

- 노드 카드 → Blueprint → IntegrationItem → 셀 점수 드릴다운
- 셀별 히트맵 또는 배지 표시

---

## 5. 기술 제약

| 항목 | 결정 |
|------|------|
| IntegrationItem mastery 집계 | `min(required_combinations 셀 점수)` |
| CellMastery 업데이트 방식 | EMA (α=0.3, NodeMastery와 동일) |
| Blueprint clearance | on-demand derived (EPIC-006 유지) |
| Grader 셀 평가 | LLM 프롬프트에 matrix 셀 정의 포함 |
| 링크 기록 주체 | CM Agent 파이프라인 |

---

## 6. 범위 외 (Out of Scope)

- matrix 셀 mastery 기반 자동 학습 추천 개편
- Blueprint/셀 mastery 리포트 (교사용)
- 셀 가중치 (현재는 단순 min)
