# TICKET-008: NodeTable + App — UI 연결

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | contents-manager / frontend |
| 파일 | `contents-manager/frontend/src/components/NodeTable.jsx`<br>`contents-manager/frontend/src/App.jsx` |
| 의존 | TICKET-006 (aiLinkCurriculum), TICKET-007 (AiLinkModal) |
| 선행 조건 | TICKET-006, TICKET-007 완료 |

---

## 배경

`AiLinkModal`과 `aiLinkCurriculum` API를 편집 탭에 연결하는 마지막 단계.
버튼 추가 → 모달 오픈 → 실행 → edges state 갱신의 전체 흐름을 완성한다.

---

## 작업 내용

### NodeTable.jsx

**props 추가**

```js
export default function NodeTable({
  nodes, onSelectNode, selectedNodeId,
  onAddNode, onGenerate, generating,
  onExpand, expanding,
  onAiLink, aiLinking,    // 추가
})
```

**툴바에 버튼 추가**

기존 버튼 순서: `AI 초안 생성` → `AI 확장` → `+ 노드 추가`

변경 후: `AI 초안 생성` → `AI 확장` → **`link 추가(AI)`** → `+ 노드 추가`

```jsx
<button
  className="btn-ai-link"
  onClick={onAiLink}
  disabled={aiLinking || generating || expanding}
>
  {aiLinking ? 'Link 생성 중...' : 'link 추가(AI)'}
</button>
```

---

### App.jsx

**import 추가**

```js
import AiLinkModal from './components/AiLinkModal.jsx'
import * as api from './services/contentsApi.js'
```

**state 추가**

```js
const [showAiLink, setShowAiLink] = useState(false)
const [aiLinking, setAiLinking] = useState(false)
```

**핸들러 추가**

```js
const handleAiLink = async (payload) => {
  setAiLinking(true)
  try {
    const res = await api.aiLinkCurriculum(selectedSubjectId, payload)
    // edges 갱신
    const ed = await api.getEdges(selectedSubjectId)
    setEdges(ed.edges || [])
    return res   // { edges_added: N } — 모달에서 결과 표시용
  } finally {
    setAiLinking(false)
  }
}
```

**NodeTable props 연결**

```jsx
<NodeTable
  ...
  onAiLink={() => setShowAiLink(true)}
  aiLinking={aiLinking}
/>
```

**AiLinkModal 렌더링**

기존 Create Subject Modal 아래에 추가:

```jsx
{showAiLink && (
  <AiLinkModal
    nodes={nodes}
    onConfirm={handleAiLink}
    onClose={() => setShowAiLink(false)}
  />
)}
```

---

## 완료 기준

- [ ] 편집 탭 툴바에 "link 추가(AI)" 버튼 표시
- [ ] 버튼 클릭 시 `AiLinkModal` 오픈
- [ ] 모달 실행 시 `aiLinking` true → 버튼 비활성화
- [ ] 실행 완료 후 `edges` state 즉시 갱신 (GraphView 반영)
- [ ] AI 초안 생성 / AI 확장 진행 중에는 link 추가(AI) 버튼 비활성화 (역방향도 동일)
- [ ] 모달 닫기(`onClose`) 시 `showAiLink` false로 전환
