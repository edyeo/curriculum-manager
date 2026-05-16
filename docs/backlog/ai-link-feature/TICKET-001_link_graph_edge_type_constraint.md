# TICKET-001: link_graph — edge_type 제약 추가

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | agent-platform / curriculum-manager / graphs |
| 파일 | `agent-platform/agents/curriculum-manager/src/graphs/link_graph.py` |
| 의존 | 없음 (독립 작업) |
| 선행 조건 | 없음 |

---

## 배경

현재 `link_graph.py`의 `link_node`는 LLM이 edge type을 자유롭게 결정한다.
`linking_agent_skill.md`에 나열된 타입 중에서 LLM이 선택하는 구조.

AI Link 기능에서는 사용자가 edge 타입을 명시적으로 지정하므로,
LLM이 해당 타입의 엣지만 생성하도록 프롬프트 제약을 주입해야 한다.

---

## 작업 내용

### 1. `LinkState`에 필드 추가

```python
class LinkState(TypedDict):
    source_type: str
    target_type: str
    source_nodes: list[Entity]
    target_nodes: list[Entity]
    new_edges: list[Edge]
    edge_type_constraint: str | None   # 추가
```

### 2. `link_node` 프롬프트 조건부 주입

`HumanMessage` content 마지막에 추가:

```python
constraint_text = ""
if state.get("edge_type_constraint"):
    constraint_text = (
        f"\n\n[중요] 반드시 '{state['edge_type_constraint']}' 타입의 엣지만 생성하세요. "
        "다른 relation_type은 사용하지 마세요."
    )

HumanMessage(content=(
    f"## Source 노드 ({state['source_type']})\n{source_json}\n\n"
    f"## Target 노드 ({state['target_type']})\n{target_json}\n\n"
    "위 두 그룹 간의 논리적 관계를 추론하여 Edge 목록을 생성하세요."
    + constraint_text
))
```

### 3. `build_link_graph()` 기본값 보장

기존 호출부가 `edge_type_constraint` 없이 호출해도 동작하도록
`None` 기본값이 TypedDict에 명시되어 있으면 충분. 별도 수정 불필요.

---

## 완료 기준

- [ ] `LinkState`에 `edge_type_constraint: str | None` 필드 존재
- [ ] `edge_type_constraint`가 `None`이면 기존 동작과 동일
- [ ] `edge_type_constraint`가 지정되면 HumanMessage에 제약 문구 포함
- [ ] 기존 `trigger_link()` 호출 시 회귀 없음
