# TICKET-003: KG API — questions 엔드포인트

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | contents-manager/backend |
| 파일 | `contents-manager/backend/routes/kg.py` |
| 의존 | TICKET-001, TICKET-002 |
| 선행 조건 | TICKET-002 완료 |

---

## 배경

학생이 특정 노드를 선택했을 때 해당 노드에 연결된 문제 목록이 필요하다. 현재 contents-manager의 questions 엔드포인트는 editor JWT가 필요하므로, KG API 경로에 서비스 토큰 기반 questions 엔드포인트를 별도 추가한다.

내부적으로는 기존 `gateway_client.get_questions(entity_id)`를 그대로 호출한다.

---

## 작업 내용

### `routes/kg.py`에 추가

```python
@router.get("/nodes/{node_id}/questions")
async def kg_questions(node_id: str, _=Depends(verify_service_token)):
    return await gateway_client.get_questions(node_id)
```

### 응답 스키마 (question-generator agent 기준)

```json
{
  "questions": [
    {
      "id": "q-001",
      "node_id": "abc-123",
      "type": "MULTIPLE_CHOICE",
      "difficulty": "MEDIUM",
      "content": {
        "question_text": "...",
        "choices": ["A", "B", "C", "D"]
      },
      "answer": "A",
      "explanation": "..."
    }
  ]
}
```

---

## 완료 기준

- [ ] `GET /kg/nodes/{node_id}/questions` — 해당 노드의 문제 목록 반환
- [ ] 서비스 토큰 없으면 401
- [ ] question-generator agent가 없거나 문제가 없으면 빈 배열 반환 (500 아님)
- [ ] 응답에 type, difficulty, content, answer, explanation 포함
