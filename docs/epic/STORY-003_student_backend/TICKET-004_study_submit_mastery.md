# TICKET-004: 문제 제출·채점·mastery 업데이트

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | student-platform/backend |
| 파일 | `student-platform/backend/grader_client.py`, `routes/study.py` |
| 의존 | TICKET-001, TICKET-002, STORY-002 완료 |
| 선행 조건 | grader agent 기동 상태 |

---

## 작업 내용

### `grader_client.py`

```python
import httpx, os

GATEWAY_URL = os.environ["GATEWAY_URL"]

async def grade(question_type, question_text, correct_answer, user_answer, explanation=""):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{GATEWAY_URL}/grade", json={...})
        r.raise_for_status()
        return r.json()  # { is_correct, score, feedback }
```

### `POST /study/submit`

```python
class SubmitRequest(BaseModel):
    question_id: str
    node_id: str
    subject_id: str
    question_type: str
    question_text: str
    correct_answer: str
    user_answer: str
    explanation: str = ""
    time_taken_seconds: int = 0

# 흐름:
# 1. grader_client.grade() 호출
# 2. NodeMastery 업데이트 (EMA)
# 3. StudySession 저장
# 4. 결과 반환
```

### Mastery 업데이트 (EMA)

```python
def update_mastery(current: float, is_correct: bool, score: float) -> float:
    if is_correct:
        return min(1.0, current + (1 - current) * 0.3 * score)
    else:
        return max(0.0, current - current * 0.2)
```

### 응답

```json
{
  "is_correct": true,
  "score": 0.9,
  "feedback": "...",
  "mastery_before": 0.5,
  "mastery_after": 0.65
}
```

---

## 완료 기준

- [ ] `POST /study/submit` — 채점 결과 반환
- [ ] NodeMastery upsert (없으면 생성, 있으면 갱신)
- [ ] StudySession 저장
- [ ] mastery_before / mastery_after 응답에 포함
- [ ] grader agent 미응답 시 503 반환
