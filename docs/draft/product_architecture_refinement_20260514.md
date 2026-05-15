# Stage1: Contents Management

# Agents

## curriculum-manager

- role v1
    - 커리큘럼 초안 작성
    - linker
    - enricher: 특정 entity를 강화
    - enhancer: 상호 연관관계에서 추가 추출대상 선별하여, 추가
- tools
    - graph DB 조회

## Mental Model manager

- role1
    - 초안 작성

## Researcher

- Roles
    - 기존 보유중인 지식을 토대로 조사
    - research keyword from blog and linked in and save to DB
- Tools
    - graph DB 조회

## Question Generator

- Roles
    - 현 entity, link, 난이도를 반영한 질문 통계 정보 조회
    - 주어진 entity를 이용한 질문 생성
    - 보완 질문 영역 도출 및 신규 문제 등록
    - 사용자 입력, domain 영역을 반영한 질문 생성
- Tools
    - 문제은행 통계 조회 API
    - 문제은행 CRUD API

# Service API

- Backend
    - 각 Agent를 API를 통해 호출 가능하며, agent의 역할 수행 가능
- Frontend
    - Agent와 관련된 DB 정보의 조회/편집 기능
    - Agent 지시 후 Human in the loop가 필요한 경우 기능 지원

# Infra

## DB (Graph 관계 유지)

### DB: Knowledge Graph

- subject 등록
- entity, link 업데이트
- API 제공 (타 component 답변 제공)

DB: Researcher 조사 결과 저장 및 조회

- curriculum-manager agent의 knowledge graph 강화 시 활용
- 원본 저장
- parsing 되어 활용 가능형태로 저장

DB: 문제은행

- 생성된 문제의 기록