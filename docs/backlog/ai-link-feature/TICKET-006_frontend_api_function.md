# TICKET-006: contentsApi.js — aiLinkCurriculum() 추가

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | contents-manager / frontend / services |
| 파일 | `contents-manager/frontend/src/services/contentsApi.js` |
| 의존 | TICKET-005 (backend 엔드포인트) |
| 선행 조건 | 없음 (독립 작업 가능, 통합은 TICKET-005 필요) |

---

## 배경

프론트엔드의 모든 API 호출은 `contentsApi.js`를 통한다.
기존 `generateCurriculum()`, `expandCurriculum()` 패턴과 동일하게 추가.

---

## 작업 내용

### 함수 추가

```js
export const aiLinkCurriculum = (subjectId, payload) =>
  fetch(`${BASE}/subjects/${subjectId}/curriculum/link-ai`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(payload),
  }).then(handle)
```

### payload 구조

```js
// 모드 1
{
  source_type: 'Seed',
  source_depth: 1,
  target_type: 'Concept',
  target_depth: 1,
  edge_type: 'requires',
}

// 모드 2
{
  source_node_id: 'uuid-...',
  target_type: 'Concept',
  target_depth: 2,
  edge_type: 'implemented_by',
}
```

### 참고: 기존 패턴

```js
export const expandCurriculum = (subjectId) =>
  fetch(`${BASE}/subjects/${subjectId}/curriculum/expand`, {
    method: 'POST', headers: headers()
  }).then(handle)
```

---

## 완료 기준

- [ ] `aiLinkCurriculum(subjectId, payload)` 함수 export
- [ ] `POST /subjects/{subjectId}/curriculum/link-ai` 로 요청
- [ ] payload를 JSON body로 전달
- [ ] `handle()` 통해 에러 처리 일관성 유지
