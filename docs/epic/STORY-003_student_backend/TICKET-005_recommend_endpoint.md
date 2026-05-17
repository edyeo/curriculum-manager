# TICKET-005: 다음 학습 추천 엔드포인트

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | student-platform/backend |
| 파일 | `student-platform/backend/routes/study.py` |
| 의존 | TICKET-003, TICKET-004 |
| 선행 조건 | TICKET-004 완료 |

---

## 배경

학생의 NodeMastery와 KG 엣지 구조를 조합해 다음에 학습할 노드를 추천한다. Phase 1은 규칙 기반(LLM 없음)으로 구현한다.

---

## 추천 전략 (규칙 기반)

```
1. mastery < 0.4  → 취약 노드 우선 추천 (REMEDIATION)
2. 0.4 ≤ mastery < 0.7 → 연결 노드 중 미학습 노드 추천 (EXPLORATION)
   - edges에서 현재 노드와 연결된 노드 탐색
   - requires: Seed → 연결 Concept 추천
   - implemented_by: Concept → 연결 TechStack 추천
3. mastery ≥ 0.7 → 동일 타입의 형제 노드 또는 상위 노드 추천 (CHALLENGE)
```

---

## 작업 내용

### `GET /study/recommend`

```python
# 파라미터
subject_id: str
current_node_id: str = None   # 현재 보고 있는 노드 (선택)

# 흐름:
# 1. kg_client.get_nodes(subject_id) + get_edges(subject_id)
# 2. 학생 NodeMastery 전체 조회
# 3. 전략 결정 → 추천 node_id 선정
# 4. kg_client.get_questions(node_id)에서 미풀이 문제 선택
```

### 응답

```json
{
  "strategy": "REMEDIATION",
  "reason": "mastery 0.3으로 취약한 'Stream Processing Model' 노드 학습 권장",
  "recommended_node": { "id": "...", "type": "Concept", "name": "...", "mastery_score": 0.3 },
  "recommended_question": { "id": "...", "type": "MULTIPLE_CHOICE", ... }
}
```

---

## 완료 기준

- [ ] `GET /study/recommend` — strategy, reason, recommended_node, recommended_question 반환
- [ ] mastery 기록이 없는 학생은 depth=1 노드부터 추천
- [ ] 모든 노드 mastery ≥ 0.7이면 CHALLENGE 전략 적용
- [ ] 추천 문제가 없으면 recommended_question: null 반환 (에러 아님)
