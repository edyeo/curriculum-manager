# TICKET-002: Claude API 기반 채점 로직

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | agent-platform/agents/grader |
| 파일 | `agent-platform/agents/grader/main.py` |
| 의존 | TICKET-001 |
| 선행 조건 | TICKET-001 완료 |

---

## 배경

MULTIPLE_CHOICE는 정답 문자열 비교로 처리하고, SHORT_ANSWER / DESCRIPTIVE는 Claude API를 호출해 채점한다. 채점 결과는 is_correct(bool), score(0.0~1.0), feedback(str)으로 통일한다.

---

## 작업 내용

### 객관식 채점 (LLM 없음)

```python
def grade_multiple_choice(correct: str, user: str) -> GradeResponse:
    is_correct = correct.strip().upper() == user.strip().upper()
    return GradeResponse(
        is_correct=is_correct,
        score=1.0 if is_correct else 0.0,
        feedback="정답입니다." if is_correct else f"오답입니다. 정답: {correct}"
    )
```

### 주관식/서술형 채점 (Claude API)

```python
import anthropic, json, os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

async def grade_with_llm(req: GradeRequest) -> GradeResponse:
    prompt = f"""
다음 문제의 학생 답안을 채점하세요.

문제: {req.question_text}
모범 답안: {req.correct_answer}
참고 해설: {req.explanation}
학생 답안: {req.user_answer}

JSON으로만 응답하세요:
{{"is_correct": bool, "score": 0.0~1.0, "feedback": "채점 근거 1~2문장"}}
"""
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}]
    )
    result = json.loads(message.content[0].text)
    return GradeResponse(**result)
```

### `POST /grade` 라우터 완성

```python
@app.post("/grade", response_model=GradeResponse)
async def grade(req: GradeRequest) -> GradeResponse:
    if req.question_type == "MULTIPLE_CHOICE":
        return grade_multiple_choice(req.correct_answer, req.user_answer)
    return await grade_with_llm(req)
```

---

## 완료 기준

- [ ] MULTIPLE_CHOICE: LLM 호출 없이 정답 비교
- [ ] SHORT_ANSWER / DESCRIPTIVE: Claude API 호출, JSON 파싱
- [ ] score 범위 0.0~1.0 보장
- [ ] LLM 응답 파싱 실패 시 500 대신 fallback 처리 (score=0, feedback="채점 오류")
- [ ] `ANTHROPIC_API_KEY` 환경변수 미설정 시 명확한 에러 메시지
