# [PRD] EPIC-009 Knowledge Ingestion Agent

## 1. 개요 (Overview)

외부 소스(파일, URL, 텍스트)로부터 온톨로지 정의에 따라 **노드·엣지를 자동 추출**하고, 기존 Knowledge Graph와의 **중복·적합성 검증** 후 선택적으로 KG에 반영하는 에이전트를 구현한다.

커리큘럼 편집자가 참고 자료를 직접 입력하면, 에이전트가 온톨로지를 이해하고 새로운 개념을 추출·제안하여 KG를 점진적으로 풍부하게 만든다.

> **의존:** 기존 KG 구조 (nodes.json / edges.json), 온톨로지 (ontology.yaml), contents-manager backend가 구성된 상태에서 진행한다.

---

## 2. 제품 원칙 (Product Principles)

**온톨로지 우선:** 추출 결과는 반드시 ontology.yaml의 Entity·Relation 정의를 따른다. 온톨로지 위반 항목은 추출 단계에서 걸러낸다.

**검증 후 반영:** 추출된 후보를 즉시 KG에 넣지 않는다. 중복 검사 → 사용자 승인(또는 자동 임계값 판단) 후 반영한다.

**감사 가능성 (Auditability):** 추출·검증·반영 각 단계의 결과를 로그로 남긴다. "왜 이 노드가 추가/거부되었는지" 추적 가능해야 한다.

**비파괴적 확장:** 신규 항목 추가만 수행한다. 기존 노드·엣지 수정·삭제는 이 에이전트 범위 밖이다.

**버전 보존:** KG 변경 시 기존 snapshot 방식을 따라 변경 전·후 상태를 모두 기록한다.

---

## 3. 핵심 개념

### Source

에이전트가 처리할 입력 단위. 세 가지 형태를 지원한다:

| 형태 | 설명 |
|---|---|
| `file` | 로컬 파일 경로 (PDF, TXT, MD) |
| `url` | 웹 페이지 URL |
| `text` | 직접 입력한 raw 텍스트 |

### Extraction Result (후보 목록)

LLM이 소스로부터 추출한 **미검증** 노드·엣지 목록.

```json
{
  "nodes": [
    { "name": "...", "type": "Concept", "depth": 2, "description": "...", "parent_name": "..." }
  ],
  "edges": [
    { "source_name": "...", "target_name": "...", "relation": "implemented_by", "basis": "..." }
  ]
}
```

### Dedup Report (중복 검사 결과)

각 후보 노드·엣지에 대해 기존 KG와 비교한 결과.

```json
{
  "node_id_or_name": {
    "status": "new | exact_duplicate",
    "decision": "add | skip"
  }
}
```

### Ingestion Log

각 실행에 대한 감사 기록. `_work/ingestion/<timestamp>/` 에 저장.

```
ingestion_<timestamp>/
├── source_meta.json       # 소스 정보 (경로/URL/텍스트 요약, 처리 시각)
├── extraction_result.json # 원본 추출 결과
├── dedup_report.json      # 중복 검사 결과
├── applied_diff.json      # 실제 KG에 반영된 노드·엣지 목록 (dry_run=True면 생략)
└── manifest.json          # 처리 요약 (추출 N, 중복 skip M, 반영 add K)
```

### KG Version Snapshot

반영 완료 후 기존 `snapshot_work()` 방식으로 `_work/<timestamp>/` 에 KG 전체 상태 스냅샷 저장. 트리거명은 `INGESTION`.

---

## 4. 에이전트 파이프라인

```
[Source Input]
     │
     ▼
┌─────────────────┐
│  1. Loader      │  파일/URL/텍스트 → raw text
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. Extractor   │  LLM: ontology.yaml 컨텍스트 + text → 후보 노드·엣지
└────────┬────────┘
         │  extraction_result.json (logging)
         ▼
┌─────────────────┐
│  3. Dedup       │  기존 KG 대비 중복 검사
│  Checker        │  - 동일명 exact match
└────────┬────────┘
         │  dedup_report.json (logging)
         ▼
┌─────────────────┐
│  4. Merger      │  decision='add' 항목만 KG에 반영
│                 │  nodes.json / edges.json 업데이트
└────────┬────────┘
         │  applied_diff.json + KG snapshot (logging)
         ▼
┌─────────────────┐
│  5. Report      │  처리 결과 요약 반환
└─────────────────┘
```

---

## 5. 핵심 기능 명세

### Feature 9.1: Source Loader

**대상:** `agent-platform/agents/ingestion-agent/src/loader.py`

**지원 형태:**

| 입력 타입 | 처리 방식 |
|---|---|
| `file` (PDF) | PyMuPDF로 텍스트 추출 |
| `file` (TXT/MD) | 직접 읽기 |
| `url` | HTTP GET → BeautifulSoup HTML 파싱 → 텍스트 추출 |
| `text` | 그대로 사용 |

**출력:** `raw_text: str` (최대 32,000 토큰 길이 제한. 초과 시 청크 분할 처리)

---

### Feature 9.2: Ontology-Aware Extractor

**대상:** `agent-platform/agents/ingestion-agent/src/extractor.py`

**동작:**
1. `ontology.yaml` 전체를 시스템 프롬프트에 포함
2. raw text에서 Entity(노드)와 Relation(엣지) 후보 추출
3. Pydantic structured output으로 반환

**LLM 프롬프트 원칙:**
- 온톨로지에 정의된 Entity 타입만 추출 (System / Seed / Concept / TechStack)
- 온톨로지 위반 항목 자체 필터링 (예: Seed 이름에 기술 해결책 포함 시 제외)
- 부모-자식 계층(depth) 추론 포함
- 엣지는 ontology.yaml의 valid_pairs 규칙을 따름

**출력 스키마:**

```python
class ExtractionResult(BaseModel):
    nodes: list[ExtractedNode]
    edges: list[ExtractedEdge]
    extraction_notes: str  # 추출 시 특이사항, 온톨로지 위반으로 제외한 항목

class ExtractedNode(BaseModel):
    name: str
    type: str           # EntityType
    depth: int          # 1~3
    description: str
    parent_name: str | None
    source_excerpt: str # 추출 근거 원문 (감사용)

class ExtractedEdge(BaseModel):
    source_name: str    # 노드 이름 기반 (ID는 Dedup 후 해소)
    target_name: str
    relation: str       # RelationType
    basis: str
    source_excerpt: str
```

---

### Feature 9.3: Dedup Checker

**대상:** `agent-platform/agents/ingestion-agent/src/dedup.py`

**중복 판단 로직 (노드):**

```
Exact match: name.lower().strip() 동일 → status="exact_duplicate", decision="skip"
그 외              → status="new", decision="add"
```

> embedding 유사도 기반 검사는 이 PRD 범위에서 제외한다. 향후 Phase 2에서 검토.

**중복 판단 로직 (엣지):**

```
1. (source_name, target_name, relation) 3-tuple이 기존 엣지와 동일하면 skip
2. 신규 source/target 노드가 추가되는 경우, 해당 노드가 "add" 결정 후에만 엣지 처리
```

**`decision` 자동 결정 규칙:**

| status | decision | 비고 |
|---|---|---|
| `new` | `add` | 자동 반영 |
| `exact_duplicate` | `skip` | 자동 제외 |

---

### Feature 9.4: Merger

**대상:** `agent-platform/agents/ingestion-agent/src/merger.py`

**동작:**
1. decision=`add` 노드를 `Entity` 스키마로 변환 후 nodes.json에 추가
2. decision=`add` 엣지를 `Edge` 스키마로 변환 (source/target ID 해소) 후 edges.json에 추가
3. `created_by_trigger="INGESTION"` 태그
4. `snapshot_work()` 호출 → `_work/<timestamp>/` KG 전체 스냅샷 저장

**ID 해소:**
- 신규 추가된 노드는 UUID 신규 발급
- 기존 KG 노드를 참조하는 엣지는 기존 노드 ID 사용 (name → ID 매핑 테이블 활용)

---

### Feature 9.5: Ingestion Log

**대상:** `agent-platform/agents/ingestion-agent/src/logger.py`

각 실행마다 `_work/ingestion/<timestamp>/` 디렉토리 생성 후 아래 파일 저장:

| 파일 | 내용 |
|---|---|
| `source_meta.json` | 소스 타입, 경로/URL, 처리 시각, raw_text 글자 수 |
| `extraction_result.json` | Feature 9.2 출력 원본 |
| `dedup_report.json` | Feature 9.3 출력 원본 |
| `applied_diff.json` | 실제 반영된 노드·엣지 (dry_run=True면 생략) |
| `manifest.json` | 요약: 추출 N / 중복 skip M / 반영 add K / dry_run 여부 |

---

### Feature 9.6: Harness 통합

**대상:** `agent-platform/agents/ingestion-agent/src/harness.py`

기존 `PassIterationHarness` 패턴을 따르되 별도 에이전트로 구성.

```python
class IngestionHarness:
    def ingest(
        self,
        source_type: Literal["file", "url", "text"],
        source: str,           # 파일 경로 / URL / 텍스트 내용
        dry_run: bool = False, # True면 dedup_report까지만 출력, KG 미반영
    ) -> IngestionSummary:
        ...
```

**dry_run 모드:** 실제 KG 수정 없이 "이 소스를 넣으면 무엇이 추출되고 무엇이 추가될 것인가"를 미리 확인하는 안전 검토 경로.

---

### Feature 9.7: contents-manager API 통합

**대상:** `contents-manager/backend/routes/ingestion.py`

CLI 또는 외부 시스템에서 HTTP 호출로 ingestion을 실행할 수 있는 엔드포인트. frontend 없이도 동작해야 한다.

| Method | Path | 설명 |
|---|---|---|
| `POST` | `/ingestion/run` | 소스 ingestion 실행 (dry_run 옵션 포함) |
| `GET` | `/ingestion/logs` | 최근 ingestion 실행 목록 |
| `GET` | `/ingestion/logs/{timestamp}` | 특정 실행의 상세 로그 조회 |

**요청 예시:**
```bash
curl -X POST http://localhost:8010/ingestion/run \
  -H "Content-Type: application/json" \
  -d '{"source_type": "text", "source": "...", "dry_run": false}'
```

> frontend UI는 이 API를 사용하는 클라이언트로 Phase 2에서 구현한다.

---

## 6. (+) KG 버전 관리

기존 `snapshot_work()` 방식을 INGESTION 트리거에도 동일하게 적용한다.

- `_work/<timestamp>/` 디렉토리에 nodes.json + edges.json + manifest.json 저장
- 이는 각 T1 DRAFT / T2 LINK / T3 EXPAND 스냅샷과 동일한 구조

**향후 개선 방향 (현재 범위 외):**
- `_work/` 내 스냅샷 간 diff 뷰어
- 특정 스냅샷으로 KG 롤백 기능
- 변경 이력 타임라인 UI

---

## 7. 비기능 요건

| 항목 | 요건 |
|---|---|
| 처리 시간 | 단일 소스 (≤ 10,000자) 기준 60초 이내 |
| 토큰 한도 | raw_text 32,000 토큰 초과 시 청크 분할 (청크당 8,000 토큰) |
| Dry-run 안전성 | dry_run=True 시 nodes.json / edges.json 절대 수정 안 함 |
| 로그 보존 | `_work/ingestion/` 디렉토리는 자동 삭제 안 함 (수동 정리) |

---

## 8. 구현 범위

| Feature | Phase 1 | Phase 2 |
|---|---|---|
| Source Loader (file/text) | ✅ | |
| Source Loader (url) | ✅ | |
| Ontology-Aware Extractor | ✅ | |
| Dedup - Exact match | ✅ | |
| Merger | ✅ | |
| Ingestion Log | ✅ | |
| Dry-run 모드 | ✅ | |
| contents-manager API (`/ingestion/*`) | ✅ | |
| UI (ingestion 탭, 결과 확인·테스트용) | | ✅ |
| KG diff 뷰어 / 롤백 | | ✅ |
| Dedup - Embedding 유사도 | | ✅ |
| Mastery 재계산 | | ✅ |

---

## 9. 디렉토리 구조 (예상)

```
agent-platform/
└── agents/
    └── ingestion-agent/
        ├── src/
        │   ├── harness.py        # IngestionHarness 진입점
        │   ├── loader.py         # Feature 9.1
        │   ├── extractor.py      # Feature 9.2
        │   ├── dedup.py          # Feature 9.3
        │   ├── merger.py         # Feature 9.4
        │   └── logger.py         # Feature 9.5
        ├── tests/
        └── requirements.txt
```

---

## 10. 미결 사항 (Open Questions)

| # | 질문 | 현재 가정 |
|---|---|---|
| OQ-1 | 청크 분할 시 노드 추출 중복이 발생할 수 있는가? | Dedup exact match로 자체 해소 |
| OQ-2 | student-platform에 새 노드 ingestion 이벤트를 notify해야 하는가? | Phase 1 no. 향후 webhook 검토 |
