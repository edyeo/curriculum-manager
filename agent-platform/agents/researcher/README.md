# Researcher Agent

## 역할
Knowledge Graph의 엔터티를 분석하여 필요한 강화 키워드를 자동으로 추출하고, 웹 검색을 통해 정보를 수집합니다. 수집된 원본 정보와 LLM 요약을 Research DB에 저장하여 Knowledge Graph를 점진적으로 강화합니다.

## 주요 기능

### RESEARCH Phase
1. **Entity 분석**: Knowledge Graph에서 대상 entity 로드
2. **Keyword 추출**: LLM이 entity 정보를 분석하여 강화 필요 키워드 도출
3. **웹 검색**: 각 키워드에 대해 WebSearch 수행 → 원본 콘텐츠 수집
4. **요약 생성**: LLM으로 검색 결과 요약
5. **저장**: 원본 + 요약 → Research DB

## 데이터 흐름

```
Entity ID 입력
    ↓
[1] KG에서 Entity 로드
    ↓
[2] Agent가 키워드 자동 추출
    ↓
[3] For each keyword: WebSearch 실행
    ↓
[4] 원본 콘텐츠 수집
    ↓
[5] LLM이 요약 생성
    ↓
[6] 원본 + 요약 저장 (Research DB)
```

## CLI 사용법

```bash
# Entity 조사 시작 (자동 키워드 추출)
python cli.py research <entity_id>

# 조사 결과 조회
python cli.py query --entity-id <entity_id> [--keyword <keyword>] [--source <source>]

# Entity별 조사 요약
python cli.py summary <entity_id>

# Entity 조사 결과 표시
python cli.py show <entity_id>
```

### 예시

```bash
# "abc123" entity 조사 시작
python cli.py research abc123

# 조사 결과 조회
python cli.py query --entity-id abc123 --limit 10

# 특정 키워드 결과만 조회
python cli.py query --entity-id abc123 --keyword "distributed"

# Entity 조사 요약
python cli.py summary abc123

# 조사 결과 표시
python cli.py show abc123
```

## 저장 구조

Research DB에는 다음이 저장됩니다:
- `keyword`: 검색 키워드
- `raw_content`: 웹 검색 원본 결과
- `summary`: LLM이 생성한 요약 (2-3줄)
- `source`: 검색 출처 (web_search 등)
- `metadata`: 우선순위, 결과 수, 타임스탐프 등
