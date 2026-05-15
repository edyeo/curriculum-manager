# DB Client API Specification - 2026-05-14

## 개요

`shared/db_client.py`에 정의될 **추상 인터페이스** 스펙입니다.

**설계 원칙:**
- **API는 불변**: 모든 에이전트가 같은 인터페이스 사용
- **구현은 교체 가능**: PostgreSQL → Neo4j/Graph DB로 변경 가능
- **Adapter 패턴**: DB별 구현을 분리

**폴더 구조:**
```
shared/
├── db_client.py              # 추상 인터페이스 (Base Classes)
└── db/
    ├── __init__.py
    ├── postgres/             # PostgreSQL 구현
    │   ├── __init__.py
    │   ├── knowledge_graph_postgres.py
    │   ├── question_bank_postgres.py
    │   └── researcher_db_postgres.py
    └── neo4j/                # 향후 Neo4j 구현
        ├── __init__.py
        ├── knowledge_graph_neo4j.py
        └── ...
```

**사용 예시:**
```python
# agents/curriculum-manager/src/harness.py
from shared.db_client import get_db_client

# 설정으로 DB 타입 선택 (PostgreSQL 또는 Neo4j)
db = get_db_client(db_type="postgres")  # or "neo4j"

# API는 동일하게 사용
entities = db.knowledge_graph.query_entities(subject="Python")
```

---

## 1. KnowledgeGraphDB

**목적**: 커리큘럼의 entity와 edge(관계)를 관리

**데이터 구조:**
```
Entity:
  id: string (unique)
  type: string ('concept', 'skill', 'topic', etc)
  name: string
  description: string
  depth: int (hierarchical depth)
  parent_id: string (parent entity)
  metadata: object
  created_at: timestamp
  updated_at: timestamp

Edge:
  id: string (unique)
  source_id: string (entity id)
  target_id: string (entity id)
  relation_type: string ('prerequisite', 'similar', 'extends', etc)
  strength: float (0~1, relationship strength)
  metadata: object
  created_at: timestamp
  updated_at: timestamp
```

**PostgreSQL 구현 스키마:**
```sql
CREATE TABLE entity (
    id VARCHAR(50) PRIMARY KEY,
    type VARCHAR(50),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    depth INT DEFAULT 0,
    parent_id VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (parent_id) REFERENCES entity(id)
);

CREATE TABLE edge (
    id VARCHAR(50) PRIMARY KEY,
    source_id VARCHAR(50) NOT NULL,
    target_id VARCHAR(50) NOT NULL,
    relation_type VARCHAR(100),
    strength FLOAT DEFAULT 1.0,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (source_id) REFERENCES entity(id),
    FOREIGN KEY (target_id) REFERENCES entity(id),
    UNIQUE(source_id, target_id, relation_type)
);
```

**Neo4j 구현 스키마 (향후):**
```cypher
CREATE (e:Entity {
  id: string,
  type: string,
  name: string,
  description: string,
  depth: int,
  metadata: object,
  created_at: datetime,
  updated_at: datetime
})

CREATE (e1:Entity)-[r:RELATION_TYPE {
  strength: float,
  metadata: object,
  created_at: datetime
}]->(e2:Entity)
```

### API (추상 인터페이스)

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class KnowledgeGraphDB(ABC):
    
    # ========== Entity 조회 ==========
    
    def query_entity(self, entity_id: str) -> Dict:
        """
        단일 entity 조회
        
        Args:
            entity_id: entity의 unique id
        
        Returns:
            {
                "id": "python_basics",
                "type": "concept",
                "name": "Python Basics",
                "description": "...",
                "depth": 0,
                "parent_id": None,
                "metadata": {},
                "created_at": "2026-05-14T...",
                "updated_at": "2026-05-14T..."
            }
        
        Raises:
            EntityNotFoundError: entity가 없을 때
        """
        pass
    
    def query_entities(
        self,
        subject: str = None,
        entity_type: str = None,
        depth: int = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        entity 목록 조회 (필터 가능)
        
        Args:
            subject: 주제 필터 (name에 포함되는 문자열)
            entity_type: entity 타입 필터
            depth: 특정 깊이 필터
            limit: 최대 반환 개수
        
        Returns:
            [
                {...entity1...},
                {...entity2...},
            ]
        
        Examples:
            # Python 관련 모든 entity
            db.query_entities(subject="Python")
            
            # 모든 concept 타입
            db.query_entities(entity_type="concept")
            
            # 깊이가 0인 최상위 개념
            db.query_entities(depth=0)
        """
        pass
    
    def query_children(self, parent_id: str) -> List[Dict]:
        """
        특정 entity의 자식 entity 조회
        
        Args:
            parent_id: 부모 entity id
        
        Returns:
            [child1, child2, ...]
        """
        pass
    
    # ========== Entity 생성/수정 ==========
    
    def create_entity(
        self,
        entity_id: str,
        name: str,
        entity_type: str,
        description: str = None,
        parent_id: str = None,
        depth: int = 0,
        metadata: Dict = None
    ) -> Dict:
        """
        새로운 entity 생성
        
        Args:
            entity_id: unique id (생성되지 않으면 slug 자동생성)
            name: entity 이름
            entity_type: 'concept', 'skill', 'topic' 등
            description: 설명
            parent_id: 부모 entity id (계층 구조)
            depth: 깊이 (자동 계산 가능)
            metadata: 추가 정보 (JSON)
        
        Returns:
            생성된 entity dict
        
        Raises:
            DuplicateEntityError: 같은 id가 이미 존재
            InvalidParentError: parent_id가 존재하지 않음
        """
        pass
    
    def update_entity(
        self,
        entity_id: str,
        **kwargs
    ) -> Dict:
        """
        entity 수정 (name, description, metadata 등)
        
        Args:
            entity_id: 대상 entity id
            **kwargs: 수정할 필드들
                - name: str
                - description: str
                - metadata: Dict (merge)
                - parent_id: str
        
        Returns:
            수정된 entity dict
        
        Raises:
            EntityNotFoundError: entity가 없을 때
        """
        pass
    
    def upsert_entities(self, entities: List[Dict]) -> List[Dict]:
        """
        여러 entity를 한 번에 생성/수정 (batch operation)
        
        Args:
            entities: [
                {
                    "id": "...",
                    "name": "...",
                    "type": "...",
                    ...
                },
                ...
            ]
        
        Returns:
            저장된 entities
        
        Note:
            - id가 존재하면 update, 없으면 create
            - 트랜잭션으로 처리 (모두 성공 또는 모두 실패)
        """
        pass
    
    # ========== Edge 조회 ==========
    
    def query_edges(
        self,
        source_id: str = None,
        target_id: str = None,
        relation_type: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        edge 목록 조회
        
        Args:
            source_id: source entity 필터
            target_id: target entity 필터
            relation_type: 관계 타입 필터
            limit: 최대 반환 개수
        
        Returns:
            [
                {
                    "id": "edge_1",
                    "source_id": "python_basics",
                    "target_id": "variables",
                    "relation_type": "prerequisite",
                    "strength": 0.9,
                    "metadata": {},
                    "created_at": "...",
                    "updated_at": "..."
                },
                ...
            ]
        
        Examples:
            # Python Basics에서 출발하는 모든 관계
            db.query_edges(source_id="python_basics")
            
            # prerequisite 관계만
            db.query_edges(relation_type="prerequisite")
        """
        pass
    
    def query_connected_entities(
        self,
        entity_id: str,
        relation_type: str = None,
        direction: str = "both"  # 'outgoing', 'incoming', 'both'
    ) -> List[Dict]:
        """
        특정 entity와 연결된 entity들 조회
        
        Args:
            entity_id: 기준 entity
            relation_type: 특정 관계 타입만 (None이면 모두)
            direction: 'outgoing'(출발), 'incoming'(도착), 'both'(양쪽)
        
        Returns:
            연결된 entity 목록
        """
        pass
    
    # ========== Edge 생성/수정 ==========
    
    def create_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        strength: float = 1.0,
        metadata: Dict = None
    ) -> Dict:
        """
        새로운 edge 생성
        
        Args:
            source_id: source entity id
            target_id: target entity id
            relation_type: 'prerequisite', 'similar', 'extends', 'related' 등
            strength: 관계 강도 (0~1, 기본값 1.0)
            metadata: 추가 정보
        
        Returns:
            생성된 edge dict
        
        Raises:
            EntityNotFoundError: source 또는 target이 없을 때
            DuplicateEdgeError: 같은 source-target-type 조합이 이미 존재
        """
        pass
    
    def update_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        **kwargs
    ) -> Dict:
        """
        edge 수정
        
        Args:
            source_id: source entity id
            target_id: target entity id
            relation_type: relation type
            **kwargs: 수정할 필드들
                - strength: float
                - metadata: Dict (merge)
        
        Returns:
            수정된 edge dict
        """
        pass
    
    def upsert_edges(self, edges: List[Dict]) -> List[Dict]:
        """
        여러 edge를 한 번에 생성/수정 (batch operation)
        
        Args:
            edges: [
                {
                    "source_id": "...",
                    "target_id": "...",
                    "relation_type": "...",
                    "strength": 0.9,
                    ...
                },
                ...
            ]
        
        Returns:
            저장된 edges
        """
        pass
    
    # ========== 편의 메소드 ==========
    
    def get_curriculum_graph(
        self,
        root_entity_id: str,
        max_depth: int = 3
    ) -> Dict:
        """
        특정 entity를 루트로 하는 curriculum graph 반환
        (트리 구조로 entities + edges 포함)
        
        Returns:
            {
                "root": {...entity...},
                "children": [
                    {
                        "entity": {...},
                        "edges": [...],
                        "children": [...]
                    },
                    ...
                ]
            }
        """
        pass
```

---

## 2. QuestionBankDB

**목적**: 문제는행 관리 (생성된 문제, 통계, 사용자 응답)

### Schema

#### QUESTION 테이블
```sql
CREATE TABLE question (
    id VARCHAR(50) PRIMARY KEY,
    entity_id VARCHAR(50) NOT NULL,
    difficulty_level VARCHAR(20),     -- 'easy', 'medium', 'hard'
    question_text TEXT NOT NULL,
    options JSONB,                    -- [{text, is_correct}, ...]
    correct_answer VARCHAR(255),
    explanation TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (entity_id) REFERENCES entity(id)
);

CREATE INDEX idx_question_entity_difficulty 
ON question(entity_id, difficulty_level);
```

#### QUESTION_RESPONSE 테이블
```sql
CREATE TABLE question_response (
    id VARCHAR(50) PRIMARY KEY,
    question_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50),              -- nullable (익명 사용자)
    response VARCHAR(255),
    is_correct BOOLEAN,
    response_time_sec INT,            -- 응답 소요 시간
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (question_id) REFERENCES question(id)
);
```

### API

```python
class QuestionBankDB:
    
    # ========== Question 조회 ==========
    
    def query_questions(
        self,
        entity_id: str = None,
        difficulty_level: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        문제 목록 조회
        
        Args:
            entity_id: 특정 entity 관련 문제만
            difficulty_level: 'easy', 'medium', 'hard'
            limit: 최대 반환 개수
        
        Returns:
            [
                {
                    "id": "q1",
                    "entity_id": "python_basics",
                    "difficulty_level": "easy",
                    "question_text": "...",
                    "options": [
                        {"text": "A", "is_correct": True},
                        {"text": "B", "is_correct": False},
                        ...
                    ],
                    "explanation": "...",
                    "created_at": "..."
                },
                ...
            ]
        """
        pass
    
    # ========== Question 생성/수정 ==========
    
    def create_question(
        self,
        entity_id: str,
        question_text: str,
        options: List[Dict],          # [{text, is_correct}, ...]
        correct_answer: str = None,   # option text or id
        difficulty_level: str = None,
        explanation: str = None,
        metadata: Dict = None
    ) -> Dict:
        """
        새로운 문제 생성
        
        Args:
            entity_id: 연관된 entity id
            question_text: 문제 텍스트
            options: [
                {"text": "Option A", "is_correct": True},
                {"text": "Option B", "is_correct": False},
                ...
            ]
            correct_answer: 정답 (option의 text)
            difficulty_level: 'easy', 'medium', 'hard'
            explanation: 설명
            metadata: 추가 정보
        
        Returns:
            생성된 question dict
        """
        pass
    
    def upsert_questions(self, questions: List[Dict]) -> List[Dict]:
        """
        여러 문제를 한 번에 생성/수정
        
        Args:
            questions: question dict 리스트
        
        Returns:
            저장된 questions
        """
        pass
    
    # ========== 통계 조회 ==========
    
    def get_question_stats(self, entity_id: str) -> Dict:
        """
        entity의 문제 통계
        
        Returns:
            {
                "total_questions": 50,
                "by_difficulty": {
                    "easy": 15,
                    "medium": 20,
                    "hard": 15
                },
                "avg_correct_rate": 0.75,  # 평균 정답률
                "total_responses": 1000
            }
        """
        pass
    
    # ========== 사용자 응답 기록 ==========
    
    def record_response(
        self,
        question_id: str,
        response: str,
        is_correct: bool,
        user_id: str = None,
        response_time_sec: int = None,
        metadata: Dict = None
    ) -> Dict:
        """
        사용자의 답변 기록
        
        Args:
            question_id: 문제 id
            response: 사용자가 선택한 답
            is_correct: 정답 여부
            user_id: 사용자 id (익명이면 None)
            response_time_sec: 응답 소요 시간
            metadata: 추가 정보 (선택지 클릭 순서 등)
        
        Returns:
            기록된 response dict
        """
        pass
    
    def get_user_performance(
        self,
        user_id: str,
        entity_id: str = None
    ) -> Dict:
        """
        사용자의 학습 성과 조회
        
        Returns:
            {
                "user_id": "user123",
                "total_attempts": 100,
                "correct_count": 75,
                "correct_rate": 0.75,
                "by_entity": {
                    "python_basics": {
                        "attempts": 20,
                        "correct_rate": 0.8
                    },
                    ...
                }
            }
        """
        pass
```

---

## 3. ResearcherDB

**목적**: Researcher 에이전트가 조사한 결과 저장/조회

### Schema

```sql
CREATE TABLE research_result (
    id VARCHAR(50) PRIMARY KEY,
    entity_id VARCHAR(50) NOT NULL,
    keyword VARCHAR(255),
    source VARCHAR(100),             -- 'blog', 'linkedin', 'paper' 등
    title VARCHAR(255),
    url TEXT,
    summary TEXT,
    full_content TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (entity_id) REFERENCES entity(id)
);

CREATE INDEX idx_research_entity_keyword 
ON research_result(entity_id, keyword);
```

### API

```python
class ResearcherDB:
    
    def create_research_result(
        self,
        entity_id: str,
        keyword: str,
        source: str,
        title: str,
        url: str = None,
        summary: str = None,
        full_content: str = None,
        metadata: Dict = None
    ) -> Dict:
        """
        조사 결과 저장
        
        Args:
            entity_id: entity id
            keyword: 검색 키워드
            source: 'blog', 'linkedin', 'paper', 'github' 등
            title: 제목
            url: URL (선택사항)
            summary: 요약 (LLM이 생성한 요약)
            full_content: 전문
            metadata: 추가 정보
        
        Returns:
            저장된 research_result dict
        """
        pass
    
    def query_research_results(
        self,
        entity_id: str = None,
        keyword: str = None,
        source: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        조사 결과 조회
        
        Args:
            entity_id: 특정 entity 관련 결과만
            keyword: 특정 키워드만
            source: 특정 소스만
            limit: 최대 반환 개수
        
        Returns:
            research_result dict 리스트
        """
        pass
    
    def get_research_summary(self, entity_id: str) -> Dict:
        """
        entity의 모든 조사 결과 요약
        
        Returns:
            {
                "entity_id": "python_basics",
                "total_results": 50,
                "by_source": {
                    "blog": 20,
                    "linkedin": 15,
                    "paper": 15
                },
                "keywords": ["python", "basics", ...],
                "last_updated": "2026-05-14T..."
            }
        """
        pass
```

---

## 에러 처리

모든 메소드에서 다음 예외를 발생시킬 수 있습니다:

```python
class DatabaseError(Exception):
    """DB 연결 또는 쿼리 에러"""
    pass

class EntityNotFoundError(DatabaseError):
    """entity를 찾을 수 없음"""
    pass

class DuplicateEntityError(DatabaseError):
    """같은 id의 entity가 이미 존재"""
    pass

class InvalidParentError(DatabaseError):
    """parent_id가 존재하지 않음"""
    pass

class DuplicateEdgeError(DatabaseError):
    """같은 source-target-type 조합이 이미 존재"""
    pass

class ValidationError(DatabaseError):
    """입력값 검증 실패"""
    pass
```

---

## 사용 예시

```python
from shared.db_client import KnowledgeGraphDB, QuestionBankDB

# curriculum 생성
db = KnowledgeGraphDB()
entities = db.query_entities(subject="Python")
new_entity = db.create_entity(
    entity_id="python_variables",
    name="Variables",
    entity_type="concept",
    parent_id="python_basics"
)
db.create_edge(
    source_id="python_basics",
    target_id="python_variables",
    relation_type="prerequisite"
)

# 문제 생성
qdb = QuestionBankDB()
qdb.create_question(
    entity_id="python_variables",
    question_text="What is a variable?",
    options=[
        {"text": "A container for data", "is_correct": True},
        {"text": "A function", "is_correct": False},
    ],
    difficulty_level="easy"
)

# 통계 조회
stats = qdb.get_question_stats("python_variables")
```

---

## 구현 아키텍처

### 1. 추상 인터페이스 (shared/db_client.py)
```python
from abc import ABC, abstractmethod

class KnowledgeGraphDB(ABC):
    @abstractmethod
    def query_entity(self, entity_id: str) -> Dict:
        pass
    
    @abstractmethod
    def query_entities(self, subject: str = None, ...) -> List[Dict]:
        pass
    
    # ... 모든 메소드는 추상 메소드

class QuestionBankDB(ABC):
    # ...
    pass

class ResearcherDB(ABC):
    # ...
    pass
```

### 2. PostgreSQL 구현 (shared/db/postgres/)
```python
# shared/db/postgres/knowledge_graph_postgres.py
from shared.db_client import KnowledgeGraphDB
import psycopg2

class KnowledgeGraphPostgres(KnowledgeGraphDB):
    def __init__(self, connection_string: str):
        self.conn = psycopg2.connect(connection_string)
    
    def query_entity(self, entity_id: str) -> Dict:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM entity WHERE id = %s", (entity_id,))
        # ...
        return entity_dict
    
    def query_entities(self, subject: str = None, ...) -> List[Dict]:
        # SQL JOIN 등으로 구현
        pass
```

### 3. Neo4j 구현 (shared/db/neo4j/) - 향후
```python
# shared/db/neo4j/knowledge_graph_neo4j.py
from shared.db_client import KnowledgeGraphDB
from neo4j import GraphDatabase

class KnowledgeGraphNeo4j(KnowledgeGraphDB):
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def query_entity(self, entity_id: str) -> Dict:
        with self.driver.session() as session:
            result = session.run("MATCH (e:Entity {id: $id}) RETURN e", id=entity_id)
            # ...
        return entity_dict
    
    def query_entities(self, subject: str = None, ...) -> List[Dict]:
        # Cypher 쿼리로 구현
        pass
```

### 4. Factory 패턴 (shared/db_client.py)
```python
def get_db_client(
    db_type: str = "postgres",
    config: Dict = None
) -> Tuple[KnowledgeGraphDB, QuestionBankDB, ResearcherDB]:
    """
    DB 타입에 따라 적절한 구현 반환
    
    Args:
        db_type: "postgres" or "neo4j"
        config: DB 연결 설정
    
    Returns:
        (knowledge_graph_db, question_bank_db, researcher_db)
    """
    if db_type == "postgres":
        from shared.db.postgres import (
            KnowledgeGraphPostgres,
            QuestionBankPostgres,
            ResearcherDBPostgres
        )
        return (
            KnowledgeGraphPostgres(config),
            QuestionBankPostgres(config),
            ResearcherDBPostgres(config)
        )
    
    elif db_type == "neo4j":
        from shared.db.neo4j import (
            KnowledgeGraphNeo4j,
            QuestionBankNeo4j,
            ResearcherDBNeo4j
        )
        return (
            KnowledgeGraphNeo4j(config),
            QuestionBankNeo4j(config),
            ResearcherDBNeo4j(config)
        )
    
    else:
        raise ValueError(f"Unknown db_type: {db_type}")
```

### 5. 에이전트에서 사용
```python
# agents/curriculum-manager/src/harness.py
from shared.db_client import get_db_client
import os

# 환경 변수로 DB 타입 선택
db_type = os.getenv("DB_TYPE", "postgres")
db_config = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

kg_db, qb_db, res_db = get_db_client(db_type, db_config)

def generate(subject: str, depth: int, scope: str) -> dict:
    # API는 동일하게 사용
    entities = kg_db.query_entities(subject=subject)
    # ...
    return result
```

---

## 마이그레이션 경로

### Phase 1: PostgreSQL로 시작
- shared/db_client.py: 추상 인터페이스
- shared/db/postgres/: PostgreSQL 구현
- 모든 에이전트가 동일 API 사용

### Phase 2: Neo4j 추가 (향후)
- shared/db/neo4j/: Neo4j 구현
- 추상 인터페이스는 변경 없음
- 환경 변수로 DB 선택만 변경

### 변경 최소화
```
Before: db_type="postgres"  ← 환경 변수만 변경
After:  db_type="neo4j"
```

---

## 다음 단계

1. ✅ 이 스펙 리뷰 (API, 데이터 구조, 마이그레이션 경로)
2. 승인 후:
   - shared/db_client.py: 추상 인터페이스 작성
   - shared/db/postgres/: PostgreSQL 구현
   - infra/db/schemas/: PostgreSQL 스크립트
   - docker-compose.yml: DB 설정
