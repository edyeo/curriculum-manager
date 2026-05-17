# TICKET-005: ResultView — 채점 결과 + mastery 변화

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | student-platform/frontend |
| 파일 | `src/components/ResultView.jsx` |
| 의존 | TICKET-004 |
| 선행 조건 | TICKET-004 완료 |

---

## 작업 내용

### 표시 항목

```
정오 여부       → ✅ 정답 / ❌ 오답
점수            → score (0.0~1.0)
AI 피드백       → feedback 텍스트
이해도 변화     → mastery_before → mastery_after (진행 바)
```

### mastery 변화 시각화

```
이전: ████████░░  0.60
이후: ██████████  0.72  (+0.12)
```

정답이면 초록 상승, 오답이면 빨강 하강으로 표시.

### 하단 액션 버튼

```
[다음 추천 문제 풀기]  → api.getRecommend() 호출 후 QuestionSolver 진입
[ConceptMap으로 돌아가기]
```

---

## 완료 기준

- [ ] 정오 여부, 점수, 피드백 표시
- [ ] mastery before/after 진행 바 시각화
- [ ] "다음 추천 문제 풀기" 버튼 동작
- [ ] "ConceptMap으로 돌아가기" 버튼 동작
