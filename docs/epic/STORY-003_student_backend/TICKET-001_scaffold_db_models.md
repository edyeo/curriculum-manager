# TICKET-001: 프로젝트 구조 및 DB 모델

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | student-platform/backend |
| 파일 | `student-platform/backend/` (신규) |
| 의존 | 없음 |
| 선행 조건 | 없음 |

---

## 작업 내용

### 디렉토리 초기화

```
student-platform/backend/
├── main.py
├── database.py
├── models.py
├── auth.py
├── kg_client.py
├── grader_client.py
├── routes/__init__.py
├── requirements.txt
└── Dockerfile
```

### `database.py`

SQLite (개발) / PostgreSQL (프로덕션) 전환 가능한 구조.

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./student_platform.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
```

### `models.py`

```python
class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_pw = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class NodeMastery(Base):
    __tablename__ = "node_mastery"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    node_id = Column(String, nullable=False)       # KG 외부 참조
    subject_id = Column(String, nullable=False)    # KG 외부 참조
    mastery_score = Column(Float, default=0.5)
    attempt_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("student_id", "node_id"),)

class StudySession(Base):
    __tablename__ = "study_sessions"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    question_id = Column(String, nullable=False)   # question-generator 외부 참조
    node_id = Column(String, nullable=False)
    subject_id = Column(String, nullable=False)
    user_answer = Column(Text)
    is_correct = Column(Boolean)
    score = Column(Float)
    feedback = Column(Text)
    time_taken_seconds = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### `main.py`

```python
app = FastAPI(title="Student Platform API")
# routes 등록은 각 TICKET에서 추가
```

---

## 완료 기준

- [ ] `python -c "from models import Student, NodeMastery, StudySession"` 오류 없음
- [ ] `Base.metadata.create_all(engine)` 으로 테이블 생성 확인
- [ ] FastAPI app 기동 (`uvicorn main:app --port 8020`)
