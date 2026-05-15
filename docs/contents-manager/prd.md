# PRD: Contents Manager

**버전:** 0.1 (초안)  
**작성일:** 2026-05-15  
**상태:** 검토 중

---

## 1. 제품 개요

### 배경

`curriculum-manager` 플랫폼은 4개의 AI 에이전트(Curriculum, Researcher, Mental Model, Question Generator)와 API Gateway로 구성된 커리큘럼 생성 시스템이다. 현재 에이전트가 자동 생성한 커리큘럼 초안을 사람이 검토하고 편집할 수 있는 인터페이스가 없다.

### 목적

콘텐츠 작성자가 AI가 생성한 Subject·Curriculum을 브라우저에서 직접 조회·편집·관리할 수 있는 Admin Web Service를 제공한다.

### 대상 사용자

| 역할 | 설명 |
|------|------|
| Admin | 사용자 초대·권한 관리, 전체 Subject 접근 가능 |
| Editor | Subject 생성·편집, 리서치·문제 조회 |
| Viewer | 읽기 전용 (외부 검토자) |

---

## 2. 목표 및 성공 지표

| 목표 | 측정 지표 |
|------|-----------|
| AI 초안의 편집 가능성 확보 | 편집자가 노드 수정·추가·삭제를 UI에서 완료 가능 |
| 콘텐츠 완성도 가시화 | 문제 수·리서치 결과를 Subject 단위로 한눈에 파악 |
| 협업 지원 | 다수 편집자가 동일 Subject를 접근 가능 |

---

## 3. 핵심 기능 (MVP)

### P0: 기본 동작 필수

| 기능 | 설명 |
|------|------|
| 인증 | 이메일·패스워드 로그인, JWT 세션 (24h) |
| Subject 목록 | 전체 Subject 조회 (이름, 생성일, 노드 수, 상태) |
| Subject 생성 | 이름·설명 입력 → AI Draft 자동 생성 트리거 |
| Subject 삭제 | 확인 후 삭제 |
| 노드 테이블 조회 | 타입·depth별 필터, 이름·설명 검색 |
| 노드 편집 | 이름·설명 수정, 저장 |
| 노드 추가 | 인라인 행 입력 (이름, 타입, depth, 설명) |
| 노드 삭제 | 슬라이드 패널에서 삭제 |

### P1: MVP 완성도

| 기능 | 설명 |
|------|------|
| 관계(엣지) 관리 | 슬라이드 패널에서 관계 추가·삭제 |
| AI Expand | 그래프 자동 확장 트리거 |
| 그래프 탭 | SVG 시각화 (참조용, 편집 불가) |
| 리서치 탭 | Subject 단위 리서치 결과 조회·필터 |
| 문제 조회 | 노드별 문제 목록 조회 |
| 문제 생성 | 노드별 문제 생성 트리거 |

### P2: 이후 단계

| 기능 | 설명 |
|------|------|
| 사용자 초대 | 이메일 초대, 역할 설정 |
| Mental Model 조회 | 노드별 멘탈모델 열람 |
| 변경 이력 | 노드 편집 이력 추적 |

---

## 4. 비기능 요구사항

| 항목 | 요구사항 |
|------|----------|
| 보안 | JWT 인증 필수, CORS는 서비스 도메인만 허용 |
| 성능 | AI 작업(Draft 생성, 리서치 시작)은 비동기 처리 + 로딩 표시 |
| UI 언어 | 한국어 |
| 배포 | Docker Compose로 기존 인프라에 추가 |
| 포트 | Backend: 8010, Frontend: 3000 |
| DB | MVP: SQLite (사용자·Subject 메타데이터만), 운영: PostgreSQL |

---

## 5. 범위 외 (Out of Scope)

- 학습자(Student) 화면 — 별도 서비스로 분리
- 실시간 협업 편집 (WebSocket) — 추후 고려
- 노드 데이터의 이중 저장 — AI 에이전트 측 JSON DB를 직접 활용
- 커리큘럼 버전 관리 — 추후 고려

---

## 6. 시스템 맥락

```
Contents Manager (신규)
  ├── Frontend (React, port 3000)
  └── Backend (FastAPI, port 8010)
           │
           └── API Gateway (port 9000) ← 기존
                    ├── Curriculum Manager (8001)
                    ├── Mental Model Manager (8002)
                    ├── Researcher (8003)
                    └── Question Generator (8004)
```

Contents Manager Backend는 사용자 인증·Subject 메타데이터만 자체 DB에 저장하고,
노드·엣지·문제·리서치 데이터는 API Gateway를 통해 기존 에이전트에 위임한다.
