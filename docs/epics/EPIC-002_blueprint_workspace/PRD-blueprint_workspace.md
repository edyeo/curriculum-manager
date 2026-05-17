# [PRD] Blueprint Workspace

## 1. 개요 (Overview)

출제 관리자가 엔지니어링 실무 숙련도 평가에 특화된 출제 기준(Blueprint)을 독립적으로 설계하고 관리하는 워크스페이스. 레이어별 맞춤형 인지 단계 매트릭스와 복합 통합 항목(Z-Axis)을 정의하여, 이후 문항 생성([EPIC-003](../EPIC-003_question_generator_workbench/PRD-question_generator_workbench.md))의 기반 데이터를 제공한다.

기존 `contents-manager/frontend`에 새 탭으로 추가된다.

---

## 2. 제품 원칙 (Product Principles)

**Decoupling:** Blueprint 설계와 문제 생성(EPIC-003)은 UI 및 생명주기가 완전히 분리된 독립된 환경으로 동작한다.

**Traceability:** 생성된 모든 Blueprint는 고유한 Blueprint_ID로 식별되며, 이후 출제된 문항과 완전한 추적성을 유지해야 한다.

---

## 3. 핵심 기능 명세 (Feature Specifications)

### Feature 1.1: 커스텀 인지 성숙도 매트릭스 설정기 (Custom Matrix Configurator)

**상세 설명:** 내용 레이어(Seed, Concept, Tech Stack)별로 고정된 교육학적 기준이 아닌, 엔지니어링 실무 숙련도에 특화된 맞춤형 인지 단계(Enum)를 격자(Grid) 형태로 정의하고 관리하는 기능.

**비즈니스 가치:** 도메인과 직무 성격에 맞는 정교한 평가 체계의 뼈대를 자유롭게 설계할 수 있음.

**인수 조건 (Acceptance Criteria):**

- 출제 관리자는 Seed(인식-리스크-통제), Concept(원리-매핑-대안), Tech(스펙-디버깅-전환) 등 레이어별로 다른 인지 단계 이름을 수정/추가할 수 있어야 한다.
- 완성된 매트릭스는 고유한 Blueprint_ID를 가진 상태로 DB에 정적 JSON 레코드로 저장되어야 한다.

---

### Feature 1.2: 통합 항목(Z-Axis) 정의 관리자 (Integration Item Manager)

**상세 설명:** 단일 지식 노드가 아닌, 복수의 레이어와 인지 단계가 결합된 포괄적 문제 출제 기준(예: "제약-개념 정렬", "풀스택 아키텍팅")을 Blueprint 내에 명시적으로 추가하는 기능.

**비즈니스 가치:** 시니어 레벨을 변별하기 위한 종합 아키텍처 문제의 출제 가이드라인을 정형화함.

**인수 조건 (Acceptance Criteria):**

- 하나의 통합 항목 생성 시, 필수적으로 만족해야 하는 내용 레이어와 인지 단계의 조합 목록을 멀티 셀렉트할 수 있어야 한다.
- 통합 항목은 Blueprint에 종속되며, Blueprint와 함께 저장/삭제된다.

---

## 4. 제약사항 및 비기능 요구사항 (Technical Constraints)

**Data Integrity:** Blueprint가 삭제될 경우, 해당 Blueprint_ID를 참조하는 문항 데이터(EPIC-003)가 깨지지 않도록 soft delete 또는 참조 무결성 보호 정책을 적용한다.

**컴포넌트 위치:** `contents-manager/frontend` 내 새 탭으로 추가. 백엔드는 `contents-manager/backend`에 Blueprint CRUD 라우터를 추가한다.
