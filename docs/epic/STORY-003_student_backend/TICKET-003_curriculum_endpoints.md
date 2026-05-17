# TICKET-003: curriculum 엔드포인트 (KG 프록시 + mastery overlay)

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | student-platform/backend |
| 파일 | `student-platform/backend/kg_client.py`, `routes/curriculum.py` |
| 의존 | TICKET-001, TICKET-002, STORY-001 완료 |
| 선행 조건 | KG API (STORY-001) 기동 상태 |

---

## 배경

student-platform/backend는 KG 데이터를 직접 보유하지 않는다. `kg_client.py`가 `KG_API_URL`에 HTTP 요청을 보내고, curriculum 엔드포인트에서 KG 데이터에 학생의 mastery 점수를 병합해 내려준다.

---

## 작업 내용

### `kg_client.py`

```python
import httpx, os

KG_API_URL = os.environ["KG_API_URL"]
SERVICE_TOKEN = os.environ["KG_SERVICE_TOKEN"]
HEADERS = {"X-Service-Token": SERVICE_TOKEN}

async def get_subjects(): ...
async def get_nodes(subject_id: str): ...
async def get_edges(subject_id: str): ...
async def get_questions(node_id: str): ...
```

### `routes/curriculum.py`

```
GET /curriculum/subjects
  → kg_client.get_subjects()

GET /curriculum/graph/{subject_id}
  → kg_client.get_nodes() + kg_client.get_edges()
  → NodeMastery DB에서 학생 mastery 조회
  → nodes에 mastery_score 병합 (없으면 기본값 0.5)
  응답: { nodes: [{id, type, name, depth, mastery_score}], edges: [{from, to, relation}] }

GET /curriculum/nodes/{node_id}/questions
  → kg_client.get_questions(node_id)
```

### mastery overlay 예시

```python
mastery_map = {m.node_id: m.mastery_score for m in db_masteries}
for node in nodes:
    node["mastery_score"] = mastery_map.get(node["id"], 0.5)
```

---

## 완료 기준

- [ ] `GET /curriculum/subjects` — 과목 목록 반환
- [ ] `GET /curriculum/graph/{subject_id}` — nodes(type 포함)와 edges, mastery_score 병합 반환
- [ ] `GET /curriculum/nodes/{node_id}/questions` — 문제 목록 반환
- [ ] KG API 미응답 시 503 반환 (student-platform 자체 500 아님)
- [ ] mastery 기록이 없는 노드는 0.5로 기본값 설정
