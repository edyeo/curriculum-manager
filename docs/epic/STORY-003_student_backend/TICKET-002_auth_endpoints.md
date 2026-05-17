# TICKET-002: 인증 엔드포인트 (register / login)

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | student-platform/backend |
| 파일 | `student-platform/backend/auth.py`, `routes/auth.py` |
| 의존 | TICKET-001 |
| 선행 조건 | TICKET-001 완료 |

---

## 작업 내용

### `auth.py`

```python
from passlib.context import CryptContext
from jose import jwt
import os, datetime

pwd_context = CryptContext(schemes=["bcrypt"])
SECRET = os.environ["STUDENT_JWT_SECRET"]
ALGORITHM = "HS256"

def hash_pw(pw: str) -> str: ...
def verify_pw(pw: str, hashed: str) -> bool: ...
def create_token(student_id: int) -> str: ...
def get_current_student(token: str = Depends(oauth2_scheme)) -> Student: ...
```

### `routes/auth.py`

```
POST /auth/register   { email, name, password } → { student_id, token }
POST /auth/login      { email, password }        → { student_id, token }
GET  /auth/me                                    → { id, email, name }
```

contents-manager의 User/auth와 완전히 독립된 별도 JWT secret 사용.

---

## 완료 기준

- [ ] `POST /auth/register` — 중복 이메일 409, 성공 시 JWT 반환
- [ ] `POST /auth/login` — 비밀번호 불일치 401, 성공 시 JWT 반환
- [ ] `GET /auth/me` — 토큰 없으면 401, 유효하면 학생 정보 반환
- [ ] 비밀번호는 bcrypt 해시 저장
