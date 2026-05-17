# TICKET-002: KG API — subjects / nodes / edges 엔드포인트

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | contents-manager/backend |
| 파일 | `contents-manager/backend/routes/kg.py` (신규) |
| 의존 | TICKET-001 (서비스 토큰 인증) |
| 선행 조건 | TICKET-001 완료 |

---

## 배경

student-platform이 과목 목록, 노드 목록(타입 포함), 엣지 목록을 읽어 ConceptMap을 구성할 수 있도록 read-only 엔드포인트를 제공한다. 데이터 소스는 기존 `file_db.py`(nodes.json / edges.json)와 `database.py`(subjects)를 그대로 사용한다.

---

## 작업 내용

### `routes/kg.py` 신규 생성

```python
from fastapi import APIRouter, Depends
from auth import verify_service_token
import file_db, database

router = APIRouter(prefix="/kg", tags=["kg"])

@router.get("/subjects")
async def kg_subjects(_=Depends(verify_service_token)):
    # database.py의 subjects 조회
    ...

@router.get("/subjects/{subject_id}/nodes")
async def kg_nodes(subject_id: str, _=Depends(verify_service_token)):
    # file_db에서 해당 subject의 nodes 반환
    # 반환 필드: id, type, name, depth, description
    ...

@router.get("/subjects/{subject_id}/edges")
async def kg_edges(subject_id: str, _=Depends(verify_service_token)):
    # file_db에서 해당 subject의 edges 반환
    # 반환 필드: id, from_node_id, to_node_id, relation
    ...
```

### 응답 스키마

**nodes 응답:**
```json
{
  "nodes": [
    {
      "id": "abc-123",
      "type": "Concept",
      "name": "Stream Processing Model",
      "depth": 1,
      "description": "..."
    }
  ]
}
```

**edges 응답:**
```json
{
  "edges": [
    {
      "id": "edge-456",
      "from_node_id": "seed-001",
      "to_node_id": "abc-123",
      "relation": "requires"
    }
  ]
}
```

---

## 완료 기준

- [ ] `GET /kg/subjects` — subject 목록 반환 (id, name)
- [ ] `GET /kg/subjects/{id}/nodes` — 노드 목록 반환 (id, **type**, name, depth, description)
- [ ] `GET /kg/subjects/{id}/edges` — 엣지 목록 반환 (from, to, relation)
- [ ] subject에 속하지 않는 노드/엣지는 필터링됨
- [ ] type 필드가 반드시 포함됨 (Seed / Concept / TechStack)
