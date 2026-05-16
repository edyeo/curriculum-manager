# TICKET-002: harness — trigger_link_ai() 메서드 추가

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | agent-platform / curriculum-manager / harness |
| 파일 | `agent-platform/agents/curriculum-manager/src/harness.py` |
| 의존 | TICKET-001 (edge_type_constraint 필드) |
| 선행 조건 | TICKET-001 완료 |

---

## 배경

기존 `trigger_link(source_type, target_type)`는 타입 단위만 지원한다.
AI Link 기능은 depth 필터링과 단일 노드 지정(모드 2)을 추가로 지원해야 한다.

---

## 작업 내용

### 메서드 시그니처

```python
def trigger_link_ai(
    self,
    source_type: str | None = None,
    source_depth: int | None = None,
    target_type: str | None = None,
    target_depth: int | None = None,
    edge_type: str | None = None,
    source_node_id: str | None = None,
) -> list[Edge]:
```

### 로직

**source 노드 결정**

```python
if source_node_id:
    # 모드 2: 단일 노드
    source_nodes = [n for n in self.nodes if n.id == source_node_id]
    if not source_nodes:
        raise ValueError(f"source_node_id '{source_node_id}' 를 찾을 수 없음")
else:
    # 모드 1: type + depth 필터
    source_nodes = [
        n for n in self.nodes
        if (source_type is None or n.type.value == source_type)
        and (source_depth is None or n.depth == source_depth)
    ]
```

**target 노드 필터**

```python
target_nodes = [
    n for n in self.nodes
    if (target_type is None or n.type.value == target_type)
    and (target_depth is None or n.depth == target_depth)
]
```

**가드**

```python
if not source_nodes:
    print("⚠️  source 노드가 없습니다.")
    return []
if not target_nodes:
    print("⚠️  target 노드가 없습니다.")
    return []
```

**link_graph 호출**

```python
graph = build_link_graph()
result = graph.invoke({
    "source_type": source_type or "custom",
    "target_type": target_type or "custom",
    "source_nodes": source_nodes,
    "target_nodes": target_nodes,
    "new_edges": [],
    "edge_type_constraint": edge_type,
})
```

**중복 제거 및 저장**

```python
existing_pairs = {(e.source_id, e.target_id) for e in self.edges}
new_edges = [
    e for e in result["new_edges"]
    if (e.source_id, e.target_id) not in existing_pairs
]

self.edges.extend(new_edges)
save_edges(self.edges)
snapshot_work(self.nodes, self.edges, trigger="AI_LINK")

print(f"✅ AI LINK 완료: {len(new_edges)}개 엣지 추가 (총 {len(self.edges)}개)")
return new_edges
```

---

## 완료 기준

- [ ] `source_node_id` 지정 시 해당 단일 노드만 source로 사용
- [ ] `source_type` + `source_depth` 조합 필터링 동작
- [ ] `target_type` + `target_depth` 조합 필터링 동작
- [ ] 기존 엣지와 중복 (source_id, target_id) 쌍 제거
- [ ] `save_edges()` 호출로 영속화
- [ ] 신규 엣지 목록 반환
- [ ] source/target 노드 없을 시 빈 목록 반환 (예외 아님)
