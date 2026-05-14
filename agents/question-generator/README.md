# Question Generator Agent

## 역할
Knowledge Graph의 엔터티를 분석하여 다양한 난이도의 교육 평가 문제를 자동으로 생성합니다.
Entity의 깊이, 관련 개념, 학습 수준을 반영한 맞춤형 문제를 생성하여 Question Bank에 저장합니다.

## 주요 기능

### GENERATE Phase
1. **Entity 분석**: Knowledge Graph에서 대상 entity와 관련 정보 로드
2. **난이도 분석**: Entity depth에 따른 난이도 분포 결정
   - `depth=1` (기초): 쉬운 문제 중심 (easy:4, medium:2, hard:0)
   - `depth=2` (중간): 다양한 난이도 (easy:2, medium:3, hard:1)
   - `depth=3` (구체): 어려운 문제 중심 (easy:1, medium:2, hard:3)
3. **문제 생성**: LLM이 난이도별 문제 생성
   - 객관식 문제 (4개 선택지)
   - 명확한 정답과 해설 포함
   - 관련 개념 반영
4. **저장**: Question Bank DB에 문제 저장

## 데이터 흐름

```
Entity ID 입력
    ↓
[1] Entity + 관련 정보 로드
    ↓
[2] 난이도 분포 분석 (depth 기반)
    ↓
[3] LLM이 문제 생성
    ↓
[4] 문제 저장 (Question DB)
```

## CLI 사용법

```bash
# Entity에 대한 문제 생성 (자동 난이도 분배)
python cli.py generate <entity_id>

# 문제 조회
python cli.py query --entity-id <entity_id> [--difficulty easy|medium|hard] [--limit 20]

# Entity의 문제 통계
python cli.py stats <entity_id>

# 통계 표시 (정리된 형식)
python cli.py show <entity_id>
```

### 예시

```bash
# "abc123" entity에 대해 문제 생성
python cli.py generate abc123

# 생성된 모든 문제 조회
python cli.py query --entity-id abc123 --limit 50

# 중간 난이도 문제만 조회
python cli.py query --entity-id abc123 --difficulty medium

# Entity의 문제 통계 조회
python cli.py stats abc123

# 정리된 통계 표시
python cli.py show abc123
```

## 생성되는 문제 구조

Question DB에는 다음 정보가 저장됩니다:
- `question_text`: 문제 텍스트
- `options`: 4개의 선택지 (정답 1개, 오답 3개)
- `correct_answer`: 정답 텍스트
- `explanation`: 2-3줄의 상세 해설
- `difficulty_level`: 난이도 (easy, medium, hard)
- `metadata`: 문제 생성 일시, 타입 등

## 스킬

- `question_generator_skill.md`: 문제 생성 에이전트 역할 정의
