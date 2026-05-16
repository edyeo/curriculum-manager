# TICKET-004: gateway_client — link_ai_curriculum() 추가

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | contents-manager / backend |
| 파일 | `contents-manager/backend/gateway_client.py` |
| 의존 | TICKET-003 (agent-platform 엔드포인트) |
| 선행 조건 | TICKET-003 완료 (또는 병렬 작업 후 통합 테스트) |

---

## 배경

contents-manager backend와 agent-platform 간의 HTTP 프록시 레이어.
기존 `generate_curriculum()`, `expand_curriculum()` 패턴과 동일한 구조로 추가.

---

## 작업 내용

### 함수 추가

```python
async def link_ai_curriculum(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            f"{GATEWAY_URL}/proxy/curriculum/api/curriculum/generate/link-ai",
            json=payload,
        )
        r.raise_for_status()
        return r.json()
```

### 참고: 기존 패턴

```python
async def expand_curriculum() -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{GATEWAY_URL}/proxy/curriculum/api/curriculum/generate/expand")
        r.raise_for_status()
        return r.json()
```

`expand_curriculum()`과 동일한 구조. `payload`를 JSON body로 전달하는 점만 다름.

---

## 완료 기준

- [ ] `link_ai_curriculum(payload: dict) -> dict` 함수 존재
- [ ] `GATEWAY_URL/proxy/curriculum/api/curriculum/generate/link-ai` 로 POST
- [ ] payload를 JSON body로 전달
- [ ] `TIMEOUT` 상수 재사용 (별도 timeout 설정 불필요)
