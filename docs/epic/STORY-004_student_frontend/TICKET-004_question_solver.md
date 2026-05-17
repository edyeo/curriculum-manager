# TICKET-004: QuestionSolver — 문제 풀기

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | student-platform/frontend |
| 파일 | `src/components/QuestionSolver.jsx` |
| 의존 | TICKET-003 |
| 선행 조건 | TICKET-003 완료 |

---

## 작업 내용

### 진입 경로

ConceptMap에서 노드 클릭 → 문제 목록 → 문제 선택 → QuestionSolver

### 문제 타입별 입력 UI

```
MULTIPLE_CHOICE
  → 선택지 라디오 버튼 (content.choices 배열 렌더링)

SHORT_ANSWER
  → 단답형 텍스트 input

DESCRIPTIVE
  → 여러 줄 textarea
```

### 제출 흐름

```js
const handleSubmit = async () => {
  const result = await api.submit({
    question_id, node_id, subject_id,
    question_type, question_text,
    correct_answer, user_answer,
    explanation,
    time_taken_seconds: elapsed
  })
  onSubmitSuccess(result)  // → ResultView로 전환
}
```

### 기타

- 제출 시작 시점부터 경과 시간(초) 측정 (`time_taken_seconds`)
- "이전으로" 버튼: ConceptMap으로 복귀

---

## 완료 기준

- [ ] MULTIPLE_CHOICE: 라디오 선택 후 제출
- [ ] SHORT_ANSWER / DESCRIPTIVE: 텍스트 입력 후 제출
- [ ] 빈 답안 제출 방지 (클라이언트 유효성 검사)
- [ ] 제출 중 로딩 상태 표시
- [ ] 제출 성공 시 ResultView로 전환
