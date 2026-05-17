# TICKET-006: MasteryDashboard — 전체 이해도 현황

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | student-platform/frontend |
| 파일 | `src/components/MasteryDashboard.jsx` |
| 의존 | TICKET-003 |
| 선행 조건 | TICKET-003 완료 |

---

## 작업 내용

### 표시 방식

노드 타입별로 그룹화해 mastery 현황을 리스트로 표시.

```
Seed (3개)
  ▸ Throughput vs Latency Tradeoff   ████████░░  0.75
  ▸ State Divergence under Failures  ████░░░░░░  0.40
  ▸ ...

Concept (8개)
  ▸ Stream Processing Model          ██████████  0.90
  ▸ Event-Driven Architecture        ███░░░░░░░  0.30
  ▸ ...

TechStack (5개)
  ▸ Apache Kafka                     █████░░░░░  0.50
  ▸ ...
```

### 집계 지표

```
전체 평균 mastery: 0.62
학습한 노드: 12 / 16
취약 노드 (< 0.4): 3개
```

### 탭 배치

`App.jsx`의 상단 네비게이션에 "📊 이해도 현황" 탭으로 추가. ConceptMap과 별도 탭.

---

## 완료 기준

- [ ] 노드 타입(Seed/Concept/TechStack)별 그룹 표시
- [ ] 각 노드의 mastery 진행 바 표시
- [ ] 전체 평균, 학습 노드 수, 취약 노드 수 집계 표시
- [ ] 미학습 노드(mastery 기록 없음)는 "미학습"으로 표시
