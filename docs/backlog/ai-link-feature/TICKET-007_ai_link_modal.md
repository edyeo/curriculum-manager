# TICKET-007: AiLinkModal.jsx — 모달 컴포넌트 신규 생성

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | contents-manager / frontend / components |
| 파일 | `contents-manager/frontend/src/components/AiLinkModal.jsx` (신규) |
| 의존 | TICKET-006 (aiLinkCurriculum API 함수) |
| 선행 조건 | 없음 (UI 독립 작업 가능) |

---

## 배경

편집 탭에서 사용자가 AI 링크 조건을 직접 지정하는 모달.
두 가지 모드를 탭/토글로 전환하며, 완료 후 결과를 부모로 전달한다.

---

## 작업 내용

### Props

```js
AiLinkModal({
  nodes,          // 현재 subject의 전체 노드 목록 (모드 2 source 선택용)
  onConfirm,      // (payload) => Promise<void> — AI link 실행 + edges 갱신
  onClose,        // () => void — 모달 닫기
})
```

### 상태

```js
const [mode, setMode] = useState('all')        // 'all' | 'node'
const [sourceType, setSourceType] = useState('Seed')
const [sourceDepth, setSourceDepth] = useState(1)
const [sourceNodeId, setSourceNodeId] = useState('')
const [targetType, setTargetType] = useState('Concept')
const [targetDepth, setTargetDepth] = useState(1)
const [edgeType, setEdgeType] = useState('requires')
const [loading, setLoading] = useState(false)
const [result, setResult] = useState(null)     // { edges_added: N }
```

### UI 구조

```
┌─────────────────────────────────────────┐
│  link 추가 (AI)                    [×]  │
├─────────────────────────────────────────┤
│  [전체 node 기준]  [특정 node 기준]      │  ← 모드 토글
├─────────────────────────────────────────┤
│  모드 1                                  │
│  Source  [타입 ▾]  [Depth ▾]            │
│  Target  [타입 ▾]  [Depth ▾]            │
│  Edge    [타입 ▾]                        │
│                                          │
│  모드 2                                  │
│  Source  [노드 선택 ▾]                   │  ← [타입·D{depth}] 이름 형식
│  Target  [타입 ▾]  [Depth ▾]            │
│  Edge    [타입 ▾]                        │
├─────────────────────────────────────────┤
│  {결과 표시: "3개 엣지 추가됨"}           │  ← 완료 후 표시
│                    [취소]  [AI Link 생성] │
└─────────────────────────────────────────┘
```

### 상수

```js
const TYPES = ['Seed', 'Concept', 'TechStack', 'System']
const DEPTHS = [1, 2, 3]
const EDGE_TYPES = ['has_subtopic', 'requires', 'implemented_by', 'relied_on']
```

### 실행 흐름

```js
const handleSubmit = async () => {
  setLoading(true)
  setResult(null)
  try {
    const payload = mode === 'node'
      ? { source_node_id: sourceNodeId, target_type: targetType, target_depth: targetDepth, edge_type: edgeType }
      : { source_type: sourceType, source_depth: sourceDepth, target_type: targetType, target_depth: targetDepth, edge_type: edgeType }

    const res = await onConfirm(payload)   // App이 edges 갱신 처리
    setResult(res)
  } finally {
    setLoading(false)
  }
}
```

완료 후 결과 메시지 표시, 닫기는 사용자가 [×] 또는 [취소] 클릭 시.

### 유효성 검사

- 모드 2에서 `sourceNodeId` 미선택 시 버튼 비활성화

---

## 완료 기준

- [ ] 모드 토글 동작 (전체 node 기준 / 특정 node 기준)
- [ ] 모드 1: 타입+depth select 렌더링 및 값 수집
- [ ] 모드 2: nodes 목록 기반 source 노드 select (`[타입·D{depth}] 이름` 형식)
- [ ] 모드 2: source 미선택 시 실행 버튼 비활성화
- [ ] loading 중 버튼 비활성화 및 "생성 중..." 텍스트
- [ ] 완료 후 `edges_added` 수 표시
- [ ] 모달 오버레이 클릭 시 닫힘
- [ ] 기존 모달(Create Subject)과 동일한 스타일 클래스 사용
