# [PRD] Pass-Iteration: 트리거 기반 지능형 커리큘럼 생성기 (PoC)

## 1. 개요 및 목적

본 제품은 데이터 엔지니어링의 핵심 고려사항(Seed)을 중심으로 지식을 구조화하는 AI 엔진이다. 모든 엔터티를 파편화(Decoupling)하여 생성하고, 명시적인 트리거를 통해 단계별로 연결 및 확장함으로써 지식의 정합성과 진화 가능성을 검증한다.

## 2. 사용자 가이드 (User Flow)

1. **Drafting:** 사용자가 주제(Subject)를 입력하여 각 분야의 독립적인 노드 풀을 생성한다.
2. **Linking:** 사용자가 연결할 두 타입을 지정하여 수평적 관계(Edge)를 맺는다.
3. **Expansion:** 시스템이 구축된 뼈대를 바탕으로 상세화(Depth 3) 및 역방향 고려사항을 도출한다.
4. **Review:** 사용자는 중간 단계마다 생성된 `state.json`을 확인하고 필요 시 해당 단계를 재실행한다.

## 3. 핵심 기능 (Functional Requirements)

- **[F1] 상태 격리 보존:** 각 트리거 실행 후 결과는 즉시 로컬 파일에 저장되어 다음 단계의 입력값이 된다.
- **[F2] 수평적 계층 연결:** 동일 Depth 내의 엔터티끼리만 연결을 허용하는 가드레일을 적용한다.
- **[F3] Pairwise 매핑:** 한 번에 모든 관계를 맺지 않고, 지정된 두 타입 간의 관계만 집중적으로 추론한다.

---

# [Technical Spec] Pass-Iteration 하네스 및 에이전트 사양

## 1. 데이터 스키마 및 상태 관리

외부 DB 없이 로컬 `state.json`을 **Global Blackboard**로 사용한다.

### 1.1. Entity Schema

JSON

`{
  "id": "UUID",
  "type": "Seed | Concept | TechStack",
  "depth": 1 | 2 | 3,
  "name": "String",
  "description": "String",
  "metadata": {}
}`

### 1.2. Edge Schema

JSON

`{
  "source_id": "UUID",
  "target_id": "UUID",
  "relation_type": "requires | implemented_by | evolves_to",
  "logic_basis": "에이전트가 연결한 논리적 근거"
}`

---

## 2. 트리거 주입(Trigger Injection) 아키텍처

명령행 인터페이스(CLI)를 통해 특정 함수(Node)를 호출하고, 인자를 주입한다.

### 2.1. T1: `DRAFT [subject]`

- **작동:** `skill_drafting.md`를 가진 에이전트들이 병렬 실행되어 노드 생성.
- **결과:** `state.json`의 `nodes` 리스트 채움.

### 2.2. T2: `LINK [source_type] [target_type]`

- **작동:** 지정된 두 타입의 노드들만 메모리에 로드하여 `skill_linking.md` 기반으로 엣지 생성.
- **규칙:** `if source.depth == target.depth: create_edge()`
- **명령 예시:** `python cli.py link --source Seed --target Concept`

### 2.3. T3: `EXPAND`

- **작동:** `skill_debate.md`를 통해 기존 그래프의 빈틈 분석.
- **로직:** Tech(D2) → 새로운 Seed(D3) 생성 및 기존 Tech(D3)와 연결.

---

## 3. 에이전트 스킬 설계 (Skill-based Logic)

각 에이전트는 `skill.md`에 정의된 페르소나와 제약 조건을 시스템 프롬프트로 주입받는다.

- **`seed_agent_skill.md`**: 문제 공간 정의 전문가. "어떤 기술적 난제가 존재하는가?"에 집중.
- **`concept_agent_skill.md`**: 논리 설계 전문가. "이 문제를 풀기 위한 원자적 단위(Primitive)는 무엇인가?"에 집중.
- **`tech_agent_skill.md`**: 구현 전문가. "이 개념을 지원하는 실제 모듈과 그 제약은 무엇인가?"에 집중.

---

## 4. 상세 구현 전략 (Python Dispatcher)

Python

`class PassIterationHarness:
    def __init__(self, state_path="state.json"):
        self.state_path = state_path
        self.state = self.load_state()

    def load_state(self):
        # JSON 로드 로직 (파일 없을 시 초기화)
        pass

    def save_state(self):
        # JSON 저장 로직
        pass

    def trigger_draft(self, subject):
        """Phase 1: Skeleton Drafting"""
        # 에이전트 실행 및 노드 생성
        self.save_state()

    def trigger_link(self, source_type, target_type):
        """Phase 2: Pairwise Connectivity"""
        # 지정된 타입 간의 엣지 형성 로직
        self.save_state()

    def trigger_expand(self):
        """Phase 3: Evolutionary Expansion"""
        # D3 생성 및 역방향 노드 도출
        self.save_state()`

---

## 5. PoC 성공 지표 (Success Metrics)

1. **독립성 검증:** `DRAFT` 이후 `nodes` 리스트만 존재하고 `edges`가 비어있는가?
2. **정합성 검증:** `LINK` 결과물 중 Depth가 서로 다른 노드끼리 연결된 사례가 0건인가?
3. **진화성 검증:** `EXPAND` 실행 후, 초안에 없던 새로운 `Seed` 노드가 `Tech` 노드의 역방향 추론을 통해 생성되었는가?