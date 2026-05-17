# [PRD] Question Generator Workbench

## 1. 개요 (Overview)

출제위원이 [EPIC-002](../EPIC-002_blueprint_workspace/PRD-blueprint_workspace.md)에서 정의된 Blueprint를 기반으로, Knowledge Graph 노드를 조합하고 AI 에이전트의 지원을 받아 고품질의 실무 시나리오 문제를 생산하는 독립 워크벤치.

수동 노드 매핑과 에이전트 기반 서브그래프 추천을 병행 지원하며, AI 생성 결과를 인간 전문가가 최종 검수·편집한 후 DB에 등록하는 전 과정을 커버한다.

> **의존:** EPIC-002 Blueprint API가 완성된 이후 진행한다.

---

## 2. 제품 원칙 (Product Principles)

**Agent as a Co-Pilot:** 에이전트는 출제 과정을 독점하지 않으며, 복잡한 종합 문제 설계 시 연관 지식을 탐색해 주는 '지능형 비서'의 역할에 충실한다.

**Traceability:** 생성된 모든 문항은 Knowledge Graph의 특정 노드 ID 및 Blueprint_ID와 완전한 추적성을 유지해야 한다.

---

## 3. 핵심 기능 명세 (Feature Specifications)

### Feature 2.1: 매뉴얼 서브그래프 조립 UI (Manual Subgraph Assembly UI)

**상세 설명:** 출제위원이 화면에서 직접 Blueprint를 선택한 후, 시스템 내장 지식 그래프 브라우저를 통해 문제에 바인딩할 특정 노드들을 검색하고 직접 수동으로 매핑(Pinning)하는 기능.

**비즈니스 가치:** 출제위원의 명확한 의도에 기반한 타깃형 문제를 빠르고 직관적으로 설계할 수 있음.

**인수 조건 (Acceptance Criteria):**

- EPIC-002에서 생성된 Blueprint 목록을 동적으로 동기화하여 선택할 수 있어야 한다.
- 선택된 노드들의 메타데이터(Description, 속성 등)가 화면에 가시화되어 출제위원이 인지할 수 있어야 한다.

---

### Feature 2.2: 에이전트 기반 지능형 서브그래프 검색 엔진 (Agentic Smart-Search Engine)

**상세 설명:** 출제위원이 Blueprint의 '통합 항목'을 선택하고 검색을 요청하면, 에이전트가 Knowledge Graph를 자율적으로 탐색하여 이에 부합하는 연관 노드 클러스터(Seed-Concept-Tech 뭉치)를 찾아내어 UI에 추천하는 기능.

**비즈니스 가치:** 복잡한 융합 문제를 출제할 때 사람이 일일이 연관 노드를 찾는 리서치 공수를 획기적으로 줄여줌.

**인수 조건 (Acceptance Criteria):**

- 에이전트는 주어진 통합 항목의 컨텍스트를 해석하여 최적의 연결 경로(Path)를 가진 서브그래프 후보군을 최소 3개 이상 추천해야 한다.
- 추천된 서브그래프는 UI 상에 노드 간의 관계선이 포함된 미니 맵 형태로 시각화되어야 하며, 사용자가 이를 채택할 수 있어야 한다.

---

### Feature 2.3: 다차원 문항 및 트레이드오프 해설 생성기 (Multi-Agent Item & Rationale Factory)

**상세 설명:** 확정된 지식 조합(수동 선택 또는 에이전트 추천)과 인지 단계 가이드라인을 파이프라인에 주입하여, 실무 시나리오 지문, 선지, 정답, 그리고 아키텍처적 트레이드오프가 녹아난 해설을 생성하는 기능.

**비즈니스 가치:** 단순 지식 검증을 넘어 "왜 이 기술을 써야 하고 다른 기술은 안 되는지"에 대한 시니어급 해설서를 자동 생산함.

**인수 조건 (Acceptance Criteria):**

- 객관식(MCQ)의 경우, 정답 노드의 형제 노드(Sibling) 또는 안티패턴 노드를 추적하여 매력적인 오답 선지 3개를 반드시 생성해야 한다.
- 해설(Rationale) 데이터는 각 선지별로 지식 그래프 상의 제약조건(Seed)을 충족하는지 혹은 위배하는지에 대한 논리적 근거를 포함해야 한다.

---

### Feature 2.4: 인라인 프리뷰 및 인간 협업 편집기 (Preview & Human-in-the-loop Editor)

**상세 설명:** AI 에이전트가 생성한 문항의 아웃풋을 최종 등록 전 단계에서 화면에 프리뷰하고, 출제위원이 지문, 정답, 해설 텍스트를 자유롭게 수동 편집(Fine-tuning)할 수 있는 UI 컴포넌트.

**비즈니스 가치:** AI의 환각(Hallucination)이나 어색한 문맥을 인간 전문가가 최종 검수하여 문항의 가치를 완벽하게 담보함.

**인수 조건 (Acceptance Criteria):**

- 생성된 문항 객체의 모든 텍스트 필드(지문, 선지, 해설 등)는 UI 상에서 인라인 에디팅이 가능해야 한다.
- [최종 등록] 버튼 클릭 시, 편집된 내용과 함께 엮인 Blueprint_ID 및 Node_ID들이 매핑 테이블 형태의 데이터 구조로 서비스 DB에 영구 적재되어야 한다.

---

## 4. 제약사항 및 비기능 요구사항 (Technical Constraints)

**Performance:** 에이전트 지능형 검색(Feature 2.2) 및 문항 생성(Feature 2.3)은 전형적인 High-Latency 작업이므로, UI 블로킹을 방지하기 위해 반드시 비동기 워커 큐(Asynchronous Worker Queue) 패턴으로 백엔드를 처리하며 UI 상에 Progress State를 명시한다.

**Data Integrity:** 지식 그래프 상에서 노드가 삭제되거나 ID가 변경될 경우, 기존에 출제되어 등록된 문항 데이터가 깨지지 않도록 문항 DB 적재 시 관련 노드의 스냅샷 메타데이터를 함께 보관(De-normalization)한다.
