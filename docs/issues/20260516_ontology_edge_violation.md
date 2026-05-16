# 온톨로지 위반 및 데이터 정합성 점검 (2026-05-16)

## 발견된 문제

### 1. 온톨로지 정의 미흡

기존 `ontology.yaml`의 relation 정의가 depth 기반 계층 구조를 반영하지 못했다.

- `evolves_to` 관계가 의미적으로 부정확 — 실제 의도는 심화/발전이 아닌 선수지식(prerequisite) 또는 계층 구조
- 동일 타입(Seed→Seed, Concept→Concept, TechStack→TechStack) 간 부모-자식 관계를 표현하는 relation 없음
- `requires` valid_pairs가 과도하게 허용됨 (Concept→Concept, TechStack→Concept 포함)
- `System` entity 미정의

### 2. edges.json 온톨로지 위반 (7건)

| # | 원본 source→target | 원본 relation | 위반 내용 |
|---|---|---|---|
| 1 | Data Encryption (Seed) → Security and Privacy (Seed) | `requires` | Seed→Seed `requires` 미허용 |
| 2 | Streaming Data Visualization (Concept) → Stream Processing (Concept) | `requires` | Concept→Concept `requires` 미허용, 방향 역전 필요 |
| 3 | Authentication Mechanisms (Seed) → Security and Privacy (Seed) | `requires` | Seed→Seed `requires` 미허용 |
| 4 | GDPR Compliance (Seed) → Security and Privacy (Seed) | `requires` | Seed→Seed `requires` 미허용 |
| 5 | Apache Storm (TechStack) → Stream Processing (Concept) | `implemented_by` | TechStack→Concept 방향 역전 필요 |
| 6 | Asynchronous Processing (Concept) → Stream Processing (Concept) | `evolves_to` | 삭제된 relation 사용, 방향 역전 필요 |
| 7 | Stream Monitoring Tools (TechStack) → Stream Processing (Concept) | `requires` | TechStack→Concept `requires` 미허용, 방향 역전 필요 |

### 3. Parent없는 Child 노드 다수

전체 37개 노드 중 26개(depth ≥ 2)가 incoming edge 없이 고립 상태.
edge가 8개에 불과해 T1_DRAFT로 생성된 대부분 노드가 그래프에 연결되지 않음.

---

## 수정 내용

### ontology.yaml 개정

- `evolves_to` 삭제
- `requires` → Seed→Concept 단일 쌍으로 제한
- `has_subtopic` 추가: 동일 타입 내 부모→자식 계층 (Seed→Seed, Concept→Concept, TechStack→TechStack)
- `prerequisite` 추가: 선수지식 의미, valid_pairs 향후 정의 예정
- `System` entity 추가 (depth_range [1,3])
- `relied_on` 추가: System→Seed (현재 데이터 미반영)

### edges.json 수정 (7건)

| # | 수정 후 source→target | 수정 후 relation |
|---|---|---|
| 1 | Security and Privacy (Seed, d1) → Data Encryption (Seed, d2) | `has_subtopic` |
| 2 | Stream Processing (Concept, d1) → Streaming Data Visualization (Concept, d2) | `has_subtopic` |
| 3 | Security and Privacy (Seed, d1) → Authentication Mechanisms (Seed, d2) | `has_subtopic` |
| 4 | Security and Privacy (Seed, d1) → GDPR Compliance (Seed, d2) | `has_subtopic` |
| 5 | Stream Processing (Concept, d1) → Apache Storm (TechStack, d2) | `implemented_by` |
| 6 | Stream Processing (Concept, d1) → Asynchronous Processing (Concept, d2) | `has_subtopic` |
| 7 | Stream Processing (Concept, d1) → Stream Monitoring Tools (TechStack, d2) | `implemented_by` |

---

## 미해결 사항

- depth ≥ 2인 고립 노드 26개에 대한 `has_subtopic` edge 추가 필요 (별도 작업)
- `prerequisite` relation의 valid_pairs 정의 필요
- `System` entity 데이터 생성 필요
