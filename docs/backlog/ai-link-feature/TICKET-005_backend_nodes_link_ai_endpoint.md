# TICKET-005: contents-manager backend — /curriculum/link-ai 엔드포인트 추가

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | contents-manager / backend / routes |
| 파일 | `contents-manager/backend/routes/nodes.py` |
| 의존 | TICKET-004 (gateway_client.link_ai_curriculum) |
| 선행 조건 | TICKET-004 완료 |

---

## 배경

프론트엔드가 호출하는 REST 엔드포인트.
agent-platform에서 생성된 신규 엣지 ID를 `SubjectEdge` 테이블에 등록하는 것이 핵심 역할.

기존 `expand` 엔드포인트(`POST /curriculum/expand`)와 동일한 패턴으로 구현.

---

## 작업 내용

### Request 모델 추가

```python
class AiLinkRequest(BaseModel):
    source_type: Optional[str] = None
    source_depth: Optional[int] = None
    source_node_id: Optional[str] = None
    target_type: Optional[str] = None
    target_depth: Optional[int] = None
    edge_type: Optional[str] = None
```

### 엔드포인트

```python
@router.post("/curriculum/link-ai")
async def link_ai(
    subject_id: str,
    req: AiLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.get_current_user),
):
    _get_subject_or_404(subject_id, db)

    before_edge_ids = {e["id"] for e in file_db.read_edges()}

    await gateway_client.link_ai_curriculum(req.model_dump(exclude_none=True))

    after_edge_ids = {e["id"] for e in file_db.read_edges()}
    new_edge_ids = after_edge_ids - before_edge_ids

    for eid in new_edge_ids:
        db.add(SubjectEdge(subject_id=subject_id, edge_id=eid))
    db.commit()

    return {"status": "success", "edges_added": len(new_edge_ids)}
```

### URL 패턴

기존 라우터 prefix: `/subjects/{subject_id}`
→ 최종 URL: `POST /subjects/{subject_id}/curriculum/link-ai`

---

## 완료 기준

- [ ] `POST /subjects/{subject_id}/curriculum/link-ai` 엔드포인트 존재
- [ ] `AiLinkRequest` 모델로 요청 파싱
- [ ] agent-platform 호출 전후 엣지 ID 스냅샷으로 신규 엣지 감지
- [ ] 신규 엣지 ID를 `SubjectEdge` 테이블에 등록
- [ ] response: `{ "status": "success", "edges_added": N }`
- [ ] subject 없을 시 404 반환
