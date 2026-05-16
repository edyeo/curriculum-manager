# TICKET-003: agent-platform routes — /generate/link-ai 엔드포인트 추가

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | agent-platform / apps / curriculum_manager |
| 파일 | `agent-platform/apps/curriculum_manager/routes.py` |
| 의존 | TICKET-002 (trigger_link_ai) |
| 선행 조건 | TICKET-002 완료 |

---

## 배경

`PassIterationHarness.trigger_link_ai()`를 HTTP로 노출하는 엔드포인트.
contents-manager backend의 `gateway_client`가 이 엔드포인트를 프록시로 호출한다.

---

## 작업 내용

### Request 모델 추가

```python
class AiLinkRequest(BaseModel):
    # 모드 1: 전체 node 기준
    source_type: Optional[str] = None
    source_depth: Optional[int] = None
    # 모드 2: 특정 node 기준 (source_type/depth 대신)
    source_node_id: Optional[str] = None
    # 공통
    target_type: Optional[str] = None
    target_depth: Optional[int] = None
    edge_type: Optional[str] = None
```

### 엔드포인트

```python
@router.post("/generate/link-ai", response_model=GenerateResponse)
async def generate_link_ai(request: AiLinkRequest):
    """AI Link: 사용자 지정 조건으로 엣지 생성"""
    try:
        harness = PassIterationHarness()
        new_edges = harness.trigger_link_ai(
            source_type=request.source_type,
            source_depth=request.source_depth,
            target_type=request.target_type,
            target_depth=request.target_depth,
            edge_type=request.edge_type,
            source_node_id=request.source_node_id,
        )
        return GenerateResponse(
            status="success",
            message=f"{len(new_edges)}개 엣지 추가됨",
            data={
                "edges_added": len(new_edges),
                "total_edges": len(harness.edges),
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 입력 유효성 검사

- `source_node_id`와 `source_type` 중 하나는 반드시 있어야 함
- 없으면 400 반환

```python
if not request.source_node_id and not request.source_type:
    raise HTTPException(status_code=400, detail="source_node_id 또는 source_type 중 하나는 필수")
```

---

## 완료 기준

- [ ] `POST /api/curriculum/generate/link-ai` 엔드포인트 존재
- [ ] 모드 1 파라미터(source_type + source_depth)로 호출 성공
- [ ] 모드 2 파라미터(source_node_id)로 호출 성공
- [ ] source 미지정 시 400 반환
- [ ] response body에 `edges_added`, `total_edges` 포함
