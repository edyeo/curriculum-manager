# STORY-003: Student Platform Backend

## 개요

| 항목 | 내용 |
|---|---|
| Epic | [EPIC-001](../EPIC-001_student_platform.md) |
| 컴포넌트 | student-platform/backend |
| 목표 | 학생 인증, KG 데이터 중계, 문제 풀이·채점·mastery 관리 API 구축 |

---

## 배경

student-platform/backend는 LLM을 직접 호출하지 않는 순수 비즈니스 로직 서버다. KG 데이터는 `KG_API_URL`에서 읽고, 주관식 채점은 `GATEWAY_URL/grade`에 위임한다. 자체 DB에는 학습 상태(Student, NodeMastery, StudySession)만 보관한다.

---

## 디렉토리 구조

```
student-platform/backend/
├── main.py
├── database.py
├── models.py
├── auth.py
├── kg_client.py          # KG_API_URL 호출
├── grader_client.py      # GATEWAY_URL/grade 호출
├── routes/
│   ├── auth.py
│   ├── curriculum.py     # KG 프록시 + mastery overlay
│   └── study.py          # 문제 제출, mastery, 추천
├── requirements.txt
└── Dockerfile
```

---

## 자체 DB 모델

```
Student: id, email, name, hashed_pw, created_at
NodeMastery: student_id, node_id*, subject_id*, mastery_score, attempt_count, updated_at
StudySession: id, student_id, question_id*, node_id*, subject_id*, user_answer,
              is_correct, score, feedback, time_taken_seconds, created_at

* 외부 참조 ID (FK 제약 없음)
```

---

## Tickets

| Ticket | 제목 |
|---|---|
| [TICKET-001](TICKET-001_scaffold_db_models.md) | 프로젝트 구조 및 DB 모델 |
| [TICKET-002](TICKET-002_auth_endpoints.md) | 인증 엔드포인트 (register / login) |
| [TICKET-003](TICKET-003_curriculum_endpoints.md) | curriculum 엔드포인트 (KG 프록시 + mastery overlay) |
| [TICKET-004](TICKET-004_study_submit_mastery.md) | 문제 제출·채점·mastery 업데이트 |
| [TICKET-005](TICKET-005_recommend_endpoint.md) | 다음 학습 추천 엔드포인트 |
| [TICKET-006](TICKET-006_docker_compose.md) | docker-compose student-backend 추가 |

---

## 완료 기준

- [ ] 학생 가입/로그인, JWT 발급
- [ ] `/curriculum/subjects`, `/curriculum/graph/{subject_id}` — KG + mastery 병합 반환
- [ ] `/curriculum/nodes/{node_id}/questions` — 문제 목록 반환
- [ ] `POST /study/submit` — 채점 + NodeMastery 업데이트 + StudySession 저장
- [ ] `GET /study/mastery` — 학생 전체 이해도 현황
- [ ] `GET /study/recommend` — mastery 기반 다음 노드/문제 추천
