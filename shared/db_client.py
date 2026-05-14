"""
Database Client - Adapter Pattern
Abstract interfaces for different database implementations.

Design:
  - Abstract base classes define the API
  - Implementations in shared/db/{postgres,neo4j}/
  - Factory function returns concrete implementation
  - Agents use only abstract interfaces
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
import os


# ── Exceptions ──────────────────────────────────────────────────

class DatabaseError(Exception):
    """Base exception for database errors"""
    pass


class EntityNotFoundError(DatabaseError):
    """Entity not found in database"""
    pass


class DuplicateEntityError(DatabaseError):
    """Duplicate entity already exists"""
    pass


class InvalidParentError(DatabaseError):
    """Parent entity does not exist"""
    pass


class DuplicateEdgeError(DatabaseError):
    """Duplicate edge already exists"""
    pass


class ValidationError(DatabaseError):
    """Input validation failed"""
    pass


# ── Abstract Interfaces ─────────────────────────────────────────

class KnowledgeGraphDB(ABC):
    """Abstract interface for Knowledge Graph database operations"""

    # ========== Entity Operations ==========

    @abstractmethod
    def query_entity(self, entity_id: str) -> Dict:
        """Query single entity by ID"""
        pass

    @abstractmethod
    def query_entities(
        self,
        subject: str = None,
        entity_type: str = None,
        depth: int = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query entities with optional filters"""
        pass

    @abstractmethod
    def query_children(self, parent_id: str) -> List[Dict]:
        """Query child entities of given parent"""
        pass

    @abstractmethod
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
        """Create new entity"""
        pass

    @abstractmethod
    def update_entity(self, entity_id: str, **kwargs) -> Dict:
        """Update entity fields"""
        pass

    @abstractmethod
    def upsert_entities(self, entities: List[Dict]) -> List[Dict]:
        """Create or update multiple entities (batch operation)"""
        pass

    # ========== Edge Operations ==========

    @abstractmethod
    def query_edges(
        self,
        source_id: str = None,
        target_id: str = None,
        relation_type: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query edges with optional filters"""
        pass

    @abstractmethod
    def query_connected_entities(
        self,
        entity_id: str,
        relation_type: str = None,
        direction: str = "both"
    ) -> List[Dict]:
        """Query entities connected to given entity"""
        pass

    @abstractmethod
    def create_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        strength: float = 1.0,
        metadata: Dict = None
    ) -> Dict:
        """Create new edge (relationship)"""
        pass

    @abstractmethod
    def update_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        **kwargs
    ) -> Dict:
        """Update edge"""
        pass

    @abstractmethod
    def upsert_edges(self, edges: List[Dict]) -> List[Dict]:
        """Create or update multiple edges (batch operation)"""
        pass

    # ========== Convenience Methods ==========

    @abstractmethod
    def get_curriculum_graph(
        self,
        root_entity_id: str,
        max_depth: int = 3
    ) -> Dict:
        """Get curriculum graph as tree structure"""
        pass


class QuestionBankDB(ABC):
    """Abstract interface for Question Bank operations"""

    # ========== Question Operations ==========

    @abstractmethod
    def query_questions(
        self,
        entity_id: str = None,
        difficulty_level: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query questions with optional filters"""
        pass

    @abstractmethod
    def create_question(
        self,
        entity_id: str,
        question_text: str,
        options: List[Dict],
        correct_answer: str = None,
        difficulty_level: str = None,
        explanation: str = None,
        metadata: Dict = None
    ) -> Dict:
        """Create new question"""
        pass

    @abstractmethod
    def upsert_questions(self, questions: List[Dict]) -> List[Dict]:
        """Create or update multiple questions (batch operation)"""
        pass

    # ========== Statistics ==========

    @abstractmethod
    def get_question_stats(self, entity_id: str) -> Dict:
        """Get question statistics for entity"""
        pass

    # ========== User Response ==========

    @abstractmethod
    def record_response(
        self,
        question_id: str,
        response: str,
        is_correct: bool,
        user_id: str = None,
        response_time_sec: int = None,
        metadata: Dict = None
    ) -> Dict:
        """Record user's response to question"""
        pass

    @abstractmethod
    def get_user_performance(
        self,
        user_id: str,
        entity_id: str = None
    ) -> Dict:
        """Get user's performance metrics"""
        pass


class ResearcherDB(ABC):
    """Abstract interface for Researcher database operations"""

    @abstractmethod
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
        """Save research result"""
        pass

    @abstractmethod
    def query_research_results(
        self,
        entity_id: str = None,
        keyword: str = None,
        source: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query research results with optional filters"""
        pass

    @abstractmethod
    def get_research_summary(self, entity_id: str) -> Dict:
        """Get research summary for entity"""
        pass


# ── Factory Function ────────────────────────────────────────────

def get_db_client(
    db_type: str = None,
    config: Dict = None
) -> Tuple[KnowledgeGraphDB, QuestionBankDB, ResearcherDB]:
    """
    Factory function to get database client implementations.

    Args:
        db_type: 'postgres' or 'neo4j' (default from env var DB_TYPE)
        config: Connection configuration dict

    Returns:
        Tuple of (KnowledgeGraphDB, QuestionBankDB, ResearcherDB)

    Environment Variables:
        DB_TYPE: Database type ('postgres' or 'neo4j')
        DB_HOST: Database host (default: localhost)
        DB_PORT: Database port
        DB_NAME: Database name
        DB_USER: Database user
        DB_PASSWORD: Database password
    """
    if db_type is None:
        db_type = os.getenv("DB_TYPE", "postgres")

    if config is None:
        config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "curriculum_db"),
            "user": os.getenv("DB_USER", "curriculum_user"),
            "password": os.getenv("DB_PASSWORD", "curriculum_password"),
        }

    if db_type == "postgres":
        from shared.db.postgres.knowledge_graph_postgres import KnowledgeGraphPostgres
        from shared.db.postgres.question_bank_postgres import QuestionBankPostgres
        from shared.db.postgres.researcher_db_postgres import ResearcherDBPostgres

        return (
            KnowledgeGraphPostgres(config),
            QuestionBankPostgres(config),
            ResearcherDBPostgres(config),
        )

    elif db_type == "neo4j":
        from shared.db.neo4j.knowledge_graph_neo4j import KnowledgeGraphNeo4j
        from shared.db.neo4j.question_bank_neo4j import QuestionBankNeo4j
        from shared.db.neo4j.researcher_db_neo4j import ResearcherDBNeo4j

        return (
            KnowledgeGraphNeo4j(config),
            QuestionBankNeo4j(config),
            ResearcherDBNeo4j(config),
        )

    else:
        raise ValueError(f"Unknown db_type: {db_type}. Choose 'postgres' or 'neo4j'")
