"""
File-based implementation of KnowledgeGraphDB
Uses nodes.json and edges.json for storage (development/prototyping)
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4
from datetime import datetime

from shared.db_client import (
    KnowledgeGraphDB,
    EntityNotFoundError,
    DuplicateEntityError,
    InvalidParentError,
    DuplicateEdgeError,
    ValidationError,
)


class KnowledgeGraphFile(KnowledgeGraphDB):
    """File-based implementation using JSON files"""

    def __init__(self, config: Dict = None):
        """
        Initialize file-based storage

        Args:
            config: Dictionary with optional keys:
                - nodes_file: Path to nodes.json (default: nodes.json)
                - edges_file: Path to edges.json (default: edges.json)
        """
        self.config = config or {}
        self.nodes_file = Path(self.config.get("nodes_file", "nodes.json"))
        self.edges_file = Path(self.config.get("edges_file", "edges.json"))

        # Initialize files if they don't exist
        self._init_files()

        # Load into memory
        self._load()

    def _init_files(self):
        """Initialize JSON files if they don't exist"""
        if not self.nodes_file.exists():
            with open(self.nodes_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

        if not self.edges_file.exists():
            with open(self.edges_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def _load(self):
        """Load entities and edges from files"""
        try:
            with open(self.nodes_file, "r", encoding="utf-8") as f:
                self.entities = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self.entities = []

        try:
            with open(self.edges_file, "r", encoding="utf-8") as f:
                self.edges_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self.edges_data = []

    def _save(self):
        """Save entities and edges to files"""
        with open(self.nodes_file, "w", encoding="utf-8") as f:
            json.dump(self.entities, f, ensure_ascii=False, indent=2)

        with open(self.edges_file, "w", encoding="utf-8") as f:
            json.dump(self.edges_data, f, ensure_ascii=False, indent=2)

    # ========== Entity Operations ==========

    def query_entity(self, entity_id: str) -> Dict:
        """Query single entity by ID"""
        for entity in self.entities:
            if entity.get("id") == entity_id:
                return entity
        raise EntityNotFoundError(f"Entity not found: {entity_id}")

    def query_entities(
        self,
        subject: str = None,
        entity_type: str = None,
        depth: int = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query entities with optional filters"""
        results = self.entities

        if subject:
            results = [
                e for e in results
                if subject.lower() in e.get("name", "").lower()
            ]

        if entity_type:
            results = [e for e in results if e.get("type") == entity_type]

        if depth is not None:
            results = [e for e in results if e.get("depth") == depth]

        return results[:limit]

    def query_children(self, parent_id: str) -> List[Dict]:
        """Query child entities of given parent"""
        return [
            e for e in self.entities
            if e.get("parent_id") == parent_id
        ]

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

        # Check for duplicates
        for entity in self.entities:
            if entity.get("id") == entity_id:
                raise DuplicateEntityError(f"Entity already exists: {entity_id}")

        # Validate parent_id if provided
        if parent_id:
            try:
                self.query_entity(parent_id)
            except EntityNotFoundError:
                raise InvalidParentError(f"Parent entity not found: {parent_id}")

        entity = {
            "id": entity_id,
            "type": entity_type,
            "name": name,
            "description": description,
            "depth": depth,
            "parent_id": parent_id,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        self.entities.append(entity)
        self._save()
        return entity

    def update_entity(self, entity_id: str, **kwargs) -> Dict:
        """Update entity fields"""
        for entity in self.entities:
            if entity.get("id") == entity_id:
                allowed_fields = ["name", "description", "metadata", "parent_id", "type"]
                for field, value in kwargs.items():
                    if field in allowed_fields:
                        entity[field] = value
                entity["updated_at"] = datetime.now().isoformat()
                self._save()
                return entity

        raise EntityNotFoundError(f"Entity not found: {entity_id}")

    def upsert_entities(self, entities: List[Dict]) -> List[Dict]:
        """Create or update multiple entities"""
        results = []
        for entity in entities:
            entity_id = entity.get("id", str(uuid4())[:8])
            try:
                result = self.update_entity(entity_id, **entity)
                results.append(result)
            except EntityNotFoundError:
                result = self.create_entity(**entity)
                results.append(result)
        return results

    # ========== Edge Operations ==========

    def query_edges(
        self,
        source_id: str = None,
        target_id: str = None,
        relation_type: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query edges with optional filters"""
        results = self.edges_data

        if source_id:
            results = [e for e in results if e.get("source_id") == source_id]

        if target_id:
            results = [e for e in results if e.get("target_id") == target_id]

        if relation_type:
            results = [e for e in results if e.get("relation_type") == relation_type]

        return results[:limit]

    def query_connected_entities(
        self,
        entity_id: str,
        relation_type: str = None,
        direction: str = "both"
    ) -> List[Dict]:
        """Query entities connected to given entity"""
        connected_ids = set()

        for edge in self.edges_data:
            if direction in ["outgoing", "both"] and edge.get("source_id") == entity_id:
                if relation_type is None or edge.get("relation_type") == relation_type:
                    connected_ids.add(edge.get("target_id"))

            if direction in ["incoming", "both"] and edge.get("target_id") == entity_id:
                if relation_type is None or edge.get("relation_type") == relation_type:
                    connected_ids.add(edge.get("source_id"))

        results = []
        for entity_id_str in connected_ids:
            try:
                results.append(self.query_entity(entity_id_str))
            except EntityNotFoundError:
                pass

        return results

    def create_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        strength: float = 1.0,
        metadata: Dict = None
    ) -> Dict:
        """Create new edge"""
        # Validate entities exist
        try:
            self.query_entity(source_id)
            self.query_entity(target_id)
        except EntityNotFoundError as e:
            raise ValidationError(f"Entity not found: {e}")

        # Check for duplicates
        for edge in self.edges_data:
            if (edge.get("source_id") == source_id and
                edge.get("target_id") == target_id and
                edge.get("relation_type") == relation_type):
                raise DuplicateEdgeError(
                    f"Edge already exists: {source_id} -> {target_id} ({relation_type})"
                )

        edge_id = str(uuid4())[:8]
        edge = {
            "id": edge_id,
            "source_id": source_id,
            "target_id": target_id,
            "relation_type": relation_type,
            "strength": strength,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        self.edges_data.append(edge)
        self._save()
        return edge

    def update_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        **kwargs
    ) -> Dict:
        """Update edge"""
        for edge in self.edges_data:
            if (edge.get("source_id") == source_id and
                edge.get("target_id") == target_id and
                edge.get("relation_type") == relation_type):

                allowed_fields = ["strength", "metadata"]
                for field, value in kwargs.items():
                    if field in allowed_fields:
                        edge[field] = value

                edge["updated_at"] = datetime.now().isoformat()
                self._save()
                return edge

        raise DuplicateEdgeError(
            f"Edge not found: {source_id} -> {target_id} ({relation_type})"
        )

    def upsert_edges(self, edges: List[Dict]) -> List[Dict]:
        """Create or update multiple edges"""
        results = []
        for edge in edges:
            source_id = edge["source_id"]
            target_id = edge["target_id"]
            relation_type = edge["relation_type"]

            try:
                result = self.update_edge(source_id, target_id, relation_type, **edge)
                results.append(result)
            except (DuplicateEdgeError, ValidationError):
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
        try:
            root = self.query_entity(root_entity_id)
        except EntityNotFoundError:
            return {}

        def build_tree(entity_id: str, current_depth: int) -> Optional[Dict]:
            if current_depth >= max_depth:
                return None

            try:
                entity = self.query_entity(entity_id)
            except EntityNotFoundError:
                return None

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

        return build_tree(root_entity_id, 0) or {}
