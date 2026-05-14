"""
PostgreSQL implementation of KnowledgeGraphDB
"""
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from typing import Dict, List, Optional
import json
from uuid import uuid4

from shared.db_client import (
    KnowledgeGraphDB,
    EntityNotFoundError,
    DuplicateEntityError,
    InvalidParentError,
    DuplicateEdgeError,
    ValidationError,
)


class KnowledgeGraphPostgres(KnowledgeGraphDB):
    """PostgreSQL implementation of Knowledge Graph database"""

    def __init__(self, config: Dict):
        """
        Initialize PostgreSQL connection

        Args:
            config: Dictionary with keys:
                - host: Database host
                - port: Database port
                - database: Database name
                - user: Database user
                - password: Database password
        """
        self.config = config
        self._connect()

    def _connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(
                host=self.config["host"],
                port=self.config["port"],
                database=self.config["database"],
                user=self.config["user"],
                password=self.config["password"],
            )
            self.conn.autocommit = False
        except psycopg2.Error as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}")

    def _get_cursor(self):
        """Get database cursor with dict output"""
        return self.conn.cursor(cursor_factory=RealDictCursor)

    def _close_cursor(self, cursor):
        """Close cursor and commit"""
        if cursor:
            cursor.close()
        self.conn.commit()

    # ========== Entity Operations ==========

    def query_entity(self, entity_id: str) -> Dict:
        """Query single entity by ID"""
        cursor = self._get_cursor()
        try:
            cursor.execute("SELECT * FROM kg.entity WHERE id = %s", (entity_id,))
            row = cursor.fetchone()
            if not row:
                raise EntityNotFoundError(f"Entity not found: {entity_id}")
            return dict(row)
        finally:
            self._close_cursor(cursor)

    def query_entities(
        self,
        subject: str = None,
        entity_type: str = None,
        depth: int = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query entities with optional filters"""
        cursor = self._get_cursor()
        try:
            query = "SELECT * FROM kg.entity WHERE 1=1"
            params = []

            if subject:
                query += " AND name ILIKE %s"
                params.append(f"%{subject}%")

            if entity_type:
                query += " AND type = %s"
                params.append(entity_type)

            if depth is not None:
                query += " AND depth = %s"
                params.append(depth)

            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            self._close_cursor(cursor)

    def query_children(self, parent_id: str) -> List[Dict]:
        """Query child entities of given parent"""
        cursor = self._get_cursor()
        try:
            cursor.execute(
                "SELECT * FROM kg.entity WHERE parent_id = %s ORDER BY created_at",
                (parent_id,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            self._close_cursor(cursor)

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
        if not entity_id:
            entity_id = str(uuid4())[:8]

        metadata = metadata or {}

        # Validate parent_id if provided
        if parent_id:
            try:
                self.query_entity(parent_id)
            except EntityNotFoundError:
                raise InvalidParentError(f"Parent entity not found: {parent_id}")

        cursor = self._get_cursor()
        try:
            cursor.execute(
                """
                INSERT INTO kg.entity (id, type, name, description, parent_id, depth, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (entity_id, entity_type, name, description, parent_id, depth, json.dumps(metadata))
            )
            row = cursor.fetchone()
            self.conn.commit()
            return dict(row)
        except psycopg2.IntegrityError as e:
            self.conn.rollback()
            if "duplicate key" in str(e).lower():
                raise DuplicateEntityError(f"Entity already exists: {entity_id}")
            raise
        finally:
            self._close_cursor(cursor)

    def update_entity(self, entity_id: str, **kwargs) -> Dict:
        """Update entity fields"""
        cursor = self._get_cursor()
        try:
            # Build dynamic UPDATE query
            allowed_fields = ["name", "description", "metadata", "parent_id", "type"]
            set_clauses = []
            params = []

            for field, value in kwargs.items():
                if field in allowed_fields:
                    if field == "metadata" and isinstance(value, dict):
                        set_clauses.append(f"{field} = %s")
                        params.append(json.dumps(value))
                    else:
                        set_clauses.append(f"{field} = %s")
                        params.append(value)

            if not set_clauses:
                raise ValidationError("No valid fields to update")

            query = f"UPDATE kg.entity SET {', '.join(set_clauses)} WHERE id = %s RETURNING *"
            params.append(entity_id)

            cursor.execute(query, params)
            row = cursor.fetchone()

            if not row:
                raise EntityNotFoundError(f"Entity not found: {entity_id}")

            self.conn.commit()
            return dict(row)
        finally:
            self._close_cursor(cursor)

    def upsert_entities(self, entities: List[Dict]) -> List[Dict]:
        """Create or update multiple entities (batch operation)"""
        cursor = self._get_cursor()
        try:
            results = []
            for entity in entities:
                entity_id = entity.get("id", str(uuid4())[:8])
                try:
                    # Try update first
                    result = self.update_entity(entity_id, **entity)
                    results.append(result)
                except EntityNotFoundError:
                    # If not found, create
                    result = self.create_entity(**entity)
                    results.append(result)
            return results
        finally:
            self._close_cursor(cursor)

    # ========== Edge Operations ==========

    def query_edges(
        self,
        source_id: str = None,
        target_id: str = None,
        relation_type: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query edges with optional filters"""
        cursor = self._get_cursor()
        try:
            query = "SELECT * FROM kg.edge WHERE 1=1"
            params = []

            if source_id:
                query += " AND source_id = %s"
                params.append(source_id)

            if target_id:
                query += " AND target_id = %s"
                params.append(target_id)

            if relation_type:
                query += " AND relation_type = %s"
                params.append(relation_type)

            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            self._close_cursor(cursor)

    def query_connected_entities(
        self,
        entity_id: str,
        relation_type: str = None,
        direction: str = "both"
    ) -> List[Dict]:
        """Query entities connected to given entity"""
        cursor = self._get_cursor()
        try:
            if direction == "outgoing":
                query = """
                    SELECT DISTINCT e.* FROM kg.entity e
                    INNER JOIN kg.edge ed ON e.id = ed.target_id
                    WHERE ed.source_id = %s
                """
                params = [entity_id]
            elif direction == "incoming":
                query = """
                    SELECT DISTINCT e.* FROM kg.entity e
                    INNER JOIN kg.edge ed ON e.id = ed.source_id
                    WHERE ed.target_id = %s
                """
                params = [entity_id]
            else:  # both
                query = """
                    SELECT DISTINCT e.* FROM kg.entity e
                    WHERE e.id IN (
                        SELECT target_id FROM kg.edge WHERE source_id = %s
                        UNION
                        SELECT source_id FROM kg.edge WHERE target_id = %s
                    )
                """
                params = [entity_id, entity_id]

            if relation_type:
                query += " AND ed.relation_type = %s"
                params.append(relation_type)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            self._close_cursor(cursor)

    def create_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        strength: float = 1.0,
        metadata: Dict = None
    ) -> Dict:
        """Create new edge"""
        edge_id = str(uuid4())[:8]
        metadata = metadata or {}

        # Validate entities exist
        try:
            self.query_entity(source_id)
            self.query_entity(target_id)
        except EntityNotFoundError as e:
            raise ValidationError(f"Entity not found: {e}")

        cursor = self._get_cursor()
        try:
            cursor.execute(
                """
                INSERT INTO kg.edge (id, source_id, target_id, relation_type, strength, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (edge_id, source_id, target_id, relation_type, strength, json.dumps(metadata))
            )
            row = cursor.fetchone()
            self.conn.commit()
            return dict(row)
        except psycopg2.IntegrityError as e:
            self.conn.rollback()
            if "duplicate" in str(e).lower():
                raise DuplicateEdgeError(
                    f"Edge already exists: {source_id} -> {target_id} ({relation_type})"
                )
            raise
        finally:
            self._close_cursor(cursor)

    def update_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        **kwargs
    ) -> Dict:
        """Update edge"""
        cursor = self._get_cursor()
        try:
            allowed_fields = ["strength", "metadata"]
            set_clauses = []
            params = []

            for field, value in kwargs.items():
                if field in allowed_fields:
                    if field == "metadata" and isinstance(value, dict):
                        set_clauses.append(f"{field} = %s")
                        params.append(json.dumps(value))
                    else:
                        set_clauses.append(f"{field} = %s")
                        params.append(value)

            if not set_clauses:
                raise ValidationError("No valid fields to update")

            query = """
                UPDATE kg.edge SET {}
                WHERE source_id = %s AND target_id = %s AND relation_type = %s
                RETURNING *
            """.format(", ".join(set_clauses))

            params.extend([source_id, target_id, relation_type])
            cursor.execute(query, params)
            row = cursor.fetchone()

            if not row:
                raise DuplicateEdgeError(
                    f"Edge not found: {source_id} -> {target_id} ({relation_type})"
                )

            self.conn.commit()
            return dict(row)
        finally:
            self._close_cursor(cursor)

    def upsert_edges(self, edges: List[Dict]) -> List[Dict]:
        """Create or update multiple edges"""
        results = []
        for edge in edges:
            source_id = edge["source_id"]
            target_id = edge["target_id"]
            relation_type = edge["relation_type"]

            try:
                # Try update first
                result = self.update_edge(source_id, target_id, relation_type, **edge)
                results.append(result)
            except (DuplicateEdgeError, ValidationError):
                # If not found or validation fails, create
                result = self.create_edge(
                    source_id,
                    target_id,
                    relation_type,
                    strength=edge.get("strength", 1.0),
                    metadata=edge.get("metadata")
                )
                results.append(result)

        return results

    # ========== Convenience Methods ==========

    def get_curriculum_graph(
        self,
        root_entity_id: str,
        max_depth: int = 3
    ) -> Dict:
        """Get curriculum graph as tree structure"""
        root = self.query_entity(root_entity_id)

        def build_tree(entity_id: str, current_depth: int) -> Dict:
            if current_depth >= max_depth:
                return None

            entity = self.query_entity(entity_id)
            children = self.query_children(entity_id)
            edges = self.query_edges(source_id=entity_id)

            return {
                "entity": entity,
                "edges": edges,
                "children": [
                    build_tree(child["id"], current_depth + 1)
                    for child in children
                    if build_tree(child["id"], current_depth + 1) is not None
                ]
            }

        return build_tree(root_entity_id, 0)

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __del__(self):
        """Ensure connection is closed on object deletion"""
        self.close()
