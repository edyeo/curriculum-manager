# TICKET-003: ConceptMap — 노드/엣지/mastery 시각화

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | student-platform/frontend |
| 파일 | `src/components/ConceptMap.jsx` |
| 의존 | TICKET-001, TICKET-002 |
| 선행 조건 | TICKET-002 완료 |

---

## 배경

KG의 Seed / Concept / TechStack 노드와 requires / implemented_by / has_subtopic 엣지를 그래프로 시각화한다. 기존 contents-manager의 GraphView.jsx를 참고하되 학생용 read-only 뷰로 구현한다.

노드 클릭 시 해당 노드의 문제 목록을 사이드 패널에 표시한다.

---

## 작업 내용

### 데이터 흐름

```js
useEffect(() => {
  const { nodes, edges } = await api.getGraph(subjectId)
  // nodes에 mastery_score 포함됨
}, [subjectId])
```

### 노드 색상 (mastery_score 기반)

```
0.0 ~ 0.4  →  빨강  (취약)
0.4 ~ 0.7  →  노랑  (보통)
0.7 ~ 1.0  →  초록  (숙달)
기록 없음  →  회색  (미학습)
```

### 노드 형태 (type 기반)

```
Seed       →  원형 (○)
Concept    →  사각형 (□)
TechStack  →  다이아몬드 (◇)
```

### 엣지 표시 (relation 기반)

```
requires         →  실선 화살표
implemented_by   →  점선 화살표
has_subtopic     →  얇은 실선
```

### 클릭 이벤트

노드 클릭 → `onNodeSelect(node)` 콜백 → QuestionSolver 진입 또는 사이드 패널

---

## 완료 기준

- [ ] 노드 타입별 형태 구분 (Seed/Concept/TechStack)
- [ ] 노드별 mastery 색상 표시
- [ ] 엣지 relation별 선 스타일 구분
- [ ] 노드 클릭 시 onNodeSelect 콜백 호출
- [ ] 노드 hover 시 name, type, mastery_score 툴팁 표시
