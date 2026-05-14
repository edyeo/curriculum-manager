# Curriculum Manager API - 통합 테스트 가이드

## 📋 개요

이 문서는 Curriculum Manager의 DB API를 Docker Compose를 사용하여 테스트하고 검증하는 방법을 설명합니다.

작성된 테스트 코드:
- **10개의 통합 테스트 케이스** - API의 주요 기능 검증
- **Docker Compose 자동화** - 서비스 관리 및 헬스 체크
- **데이터 지속성 검증** - JSON 파일 저장 확인

## 🧪 테스트 구성

### 테스트 파일 구조
```
tests/
├── __init__.py
├── conftest.py                      # pytest 설정 및 fixture
├── test_curriculum_api_simple.py    # 간단한 직접 테스트
└── test_curriculum_api_integration.py # 통합 테스트
```

### 테스트 케이스 목록

| Test # | 설명 | 엔드포인트 | 검증 항목 |
|--------|------|-----------|---------|
| 1 | 헬스 체크 | GET /health | 서버 상태 |
| 2 | DRAFT 생성 | POST /api/curriculum/generate/draft | 노드 생성 |
| 3 | STATUS 조회 | GET /api/curriculum/status | 노드/엣지 개수 |
| 4 | LINK 생성 | POST /api/curriculum/generate/link | 관계 생성 |
| 5 | EXPAND 확장 | POST /api/curriculum/generate/expand | 그래프 확장 |
| 6 | 순차 처리 | 여러 DRAFT | 대량 데이터 생성 |
| 7 | 응답 스키마 | 모든 엔드포인트 | JSON 구조 검증 |
| 8 | nodes.json | 파일 확인 | 데이터 지속성 |
| 9 | edges.json | 파일 확인 | 엣지 데이터 저장 |
| 10 | 완전한 워크플로우 | DRAFT→STATUS→LINK | 종단간 검증 |

## 🚀 테스트 실행

### 방법 1: Docker Compose + pytest

```bash
# 1. 의존성 설치
pip install pytest requests

# 2. Docker Compose 시작
docker-compose -f infra/docker-compose.test.yml up -d

# 3. 테스트 실행
pytest tests/test_curriculum_api_simple.py -v

# 4. 테스트 완료 후 정리
docker-compose -f infra/docker-compose.test.yml down
```

### 방법 2: curl을 사용한 직접 테스트

```bash
# 1. Docker Compose 시작
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local.yml up -d

# 2. API 테스트
bash test_api_direct.sh

# 또는 수동으로:
curl http://localhost:8001/health | jq .

curl -X POST http://localhost:8001/api/curriculum/generate/draft \
  -H "Content-Type: application/json" \
  -d '{"subject": "Machine Learning", "description": "ML basics"}'
```

### 방법 3: 자동화 테스트 스크립트

```bash
# 포트 8010에서 실행되는 테스트 환경
docker-compose -f infra/docker-compose.test.yml up -d
bash run_tests.sh
```

## 📊 테스트 데이터

### DRAFT 생성 예제
```json
{
  "subject": "Machine Learning Basics",
  "description": "Introduction to ML concepts and algorithms"
}
```

**응답:**
```json
{
  "status": "success",
  "message": "Draft generated for subject: Machine Learning Basics",
  "data": {
    "nodes_count": 12
  }
}
```

### LINK 생성 예제
```json
{
  "source_type": "Concept",
  "target_type": "Skill"
}
```

**응답:**
```json
{
  "status": "success",
  "message": "Edges created between Concept and Skill",
  "data": {
    "edges_count": 24
  }
}
```

### STATUS 조회 예제

**응답:**
```json
{
  "status": "ready",
  "nodes_count": 45,
  "edges_count": 120
}
```

## 📁 데이터 지속성

### 파일 저장 위치
- **nodes.json** - 모든 노드 데이터
- **edges.json** - 모든 엣지(관계) 데이터

### 데이터 구조

**Node (nodes.json)**
```json
{
  "id": "uuid-string",
  "type": "Concept",
  "depth": 1,
  "name": "Basic Concept",
  "description": "Description of the concept",
  "metadata": {},
  "created_at": "2026-05-15T00:00:00Z",
  "created_by_trigger": "T1_DRAFT"
}
```

**Edge (edges.json)**
```json
{
  "source_id": "uuid-string",
  "target_id": "uuid-string",
  "relation_type": "prerequisite",
  "logic_basis": "Reason for the relationship",
  "created_at": "2026-05-15T00:00:00Z",
  "created_by_trigger": "T2_LINK"
}
```

## 🔧 설정 파일

### docker-compose.test.yml
- PostgreSQL (포트 5433)
- Redis (포트 6380)
- Curriculum Manager API (포트 8010)
- 자동 헬스 체크

### pyproject.toml 업데이트
추가된 의존성:
```toml
dependencies = [
  "fastapi>=0.100.0",
  "uvicorn>=0.23.0",
  "requests>=2.31.0",
  # ... 기존 의존성
]
```

### Dockerfile 수정
- PYTHONPATH 설정
- uvicorn 직접 실행
- 포트 8001 노출

## ✅ 테스트 체크리스트

- [ ] Docker가 설치되고 실행 중인가?
- [ ] Docker Compose가 설치되어 있는가?
- [ ] 포트 8001, 8010이 사용 중이 아닌가?
- [ ] Python 3.11+ 설치되어 있는가?
- [ ] 의존성이 설치되었는가? (`pip install -e ".[dev]"`)
- [ ] Docker 이미지가 빌드되었는가?
- [ ] 모든 서비스가 healthy 상태인가?

## 🐛 트러블슈팅

### 포트 충돌
```bash
# 사용 중인 포트 확인
lsof -i :8001
lsof -i :8010

# 충돌하는 프로세스 종료
kill -9 <PID>
```

### 데이터 초기화
```bash
# 전체 정리
docker-compose -f infra/docker-compose.test.yml down -v
rm -f nodes.json edges.json

# 다시 시작
docker-compose -f infra/docker-compose.test.yml up -d
```

### 로그 확인
```bash
# 컨테이너 로그
docker logs curriculum-manager-test

# 전체 로그
docker-compose -f infra/docker-compose.test.yml logs
```

## 📈 다음 단계

1. **CI/CD 통합** - GitHub Actions 워크플로우 추가
2. **성능 테스트** - 대량 데이터 처리 테스트
3. **부하 테스트** - 동시 요청 처리 검증
4. **API 문서** - Swagger/OpenAPI 자동 생성

## 📝 참고사항

- 테스트는 file-based DB 사용 (DB_TYPE=file)
- PostgreSQL/Redis는 optional (향후 확장용)
- 각 테스트는 독립적으로 실행 가능
- 테스트 데이터는 nodes.json, edges.json에 누적됨

## 👤 Author

생성일: 2026-05-15
테스트 작성자: Claude AI
