# Mental Model Manager Agent

## 역할
주어진 Entity에 대해 **Junior/Senior/Staff 수준별 평가 기준(Rubric)**을 생성합니다.
이 평가 기준은 각 엔지니어링 수준이 해당 주제에 대해 어느 수준으로 이해해야 하는지를 정의하는 **역할 기반 학습 평가 도구**입니다.

## 개념

### Mental Model은 평가 기준(Rubric)

특정 기술이나 개념에 대해 다양한 수준의 엔지니어가 가져야 할 **사고 깊이와 관점의 차이**를 정의합니다.

```
예: "캐싱"에 대한 Mental Model

주니어 수준 (Can Execute)
└─ "캐싱이 뭐고, 어떻게 구현하지?"
   ├─ 기본 개념 이해
   ├─ 간단한 구현 가능
   └─ 표준 패턴 적용 가능

시니어 수준 (Can Design)
└─ "캐싱의 설계 원리는? 트레이드오프는?"
   ├─ 설계 트레이드오프 이해
   ├─ 여러 방식 비교 가능
   └─ 분산 환경의 문제 인식

스태프 수준 (Can Predict Failure)
└─ "언제 이 접근이 실패하나? 어떤 제약이 있나?"
   ├─ 근본적 제약 이해
   ├─ 실제 운영 문제 예측
   ├─ 상황별 실패 사례 식별
   └─ 비용/시간/확장성 분석 능력
```

## 주요 기능

### GENERATE Phase
1. **Entity 로드**: Knowledge Graph에서 대상 entity와 관련 정보 로드
2. **Rubric 생성**: LLM이 3가지 수준의 평가 기준 생성
   - 각 수준: 5-7개의 명확한 평가 항목
   - 진행적 깊이 증가 (Junior → Senior → Staff)
   - 실행능력(HOW) → 설계능력(WHY) → 예측능력(WHEN/WHY FAIL)
3. **저장**: 평가 기준을 Mental Model DB에 저장

## 데이터 흐름

```
Entity 입력
    ↓
[1] Entity + 관련 정보 로드
    ↓
[2] LLM이 평가 기준 생성
    ├─ Junior Rubric (5-7개 항목)
    ├─ Senior Rubric (5-7개 항목)
    └─ Staff Rubric (5-7개 항목)
    ↓
[3] Mental Model 저장
```

## CLI 사용법

```bash
# Mental Model 평가 기준 생성
python cli.py generate <entity_id>

# 모든 수준의 평가 기준 표시
python cli.py rubric <entity_id>

# 특정 수준의 평가 기준만 표시
python cli.py rubric <entity_id> --level senior

# 평가 항목 개수 조회
python cli.py count <entity_id>
```

### 예시

```bash
# "abc123" entity에 대한 평가 기준 생성
python cli.py generate abc123

# 생성된 평가 기준 전체 표시
python cli.py rubric abc123

# 시니어 수준의 평가 기준만 표시
python cli.py rubric abc123 --level senior

# 스태프 수준의 평가 기준만 표시
python cli.py rubric abc123 --level staff

# 각 수준의 항목 개수 조회
python cli.py count abc123
```

## 평가 기준 구조

### Junior Level (Can Execute - 실행 능력)
평가 기준:
- 기본 개념을 설명할 수 있는가
- 표준 구현을 할 수 있는가
- 기본 용어를 아는가
- 확립된 절차를 따를 수 있는가
- 간단한 문제 해결이 가능한가

**관점**: HOW do I do this?

### Senior Level (Can Design - 설계 능력)
평가 기준:
- 설계 트레이드오프를 설명할 수 있는가
- 여러 접근법의 장단점을 비교할 수 있는가
- 각 선택의 근거를 설명할 수 있는가
- 예상 가능한 문제들을 인식하는가
- 주니어 엔지니어를 멘토링할 수 있는가

**관점**: WHY do we do it this way?

### Staff Level (Can Predict Failure - 예측 능력)
평가 기준:
- 근본적인 제약과 한계를 이해하는가
- 실제 운영 환경에서의 실패 사례를 예측할 수 있는가
- 각 상황별 문제점을 식별할 수 있는가
- 비용/시간/확장성/복잡도를 종합 분석할 수 있는가
- 이 접근이 부적절한 상황을 판단할 수 있는가

**관점**: WHEN and WHY will this fail? What are the hidden costs?

## 스킬

- `mental_model_generator_skill.md`: 평가 기준 생성 에이전트 역할 정의
