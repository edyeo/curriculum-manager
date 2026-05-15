"""
Neo4j implementation of KnowledgeGraphDB (stub for future implementation)
"""
from shared.db_client import KnowledgeGraphDB


class KnowledgeGraphNeo4j(KnowledgeGraphDB):
    """Neo4j implementation of Knowledge Graph database"""

    def __init__(self, config):
        raise NotImplementedError("Neo4j implementation coming in Phase 3")

    def query_entity(self, entity_id):
        raise NotImplementedError()

    def query_entities(self, subject=None, entity_type=None, depth=None, limit=100):
        raise NotImplementedError()

    def query_children(self, parent_id):
        raise NotImplementedError()

    def create_entity(self, entity_id, name, entity_type, description=None, parent_id=None, depth=0, metadata=None):
        raise NotImplementedError()

    def update_entity(self, entity_id, **kwargs):
        raise NotImplementedError()

    def upsert_entities(self, entities):
        raise NotImplementedError()

    def query_edges(self, source_id=None, target_id=None, relation_type=None, limit=100):
        raise NotImplementedError()

    def query_connected_entities(self, entity_id, relation_type=None, direction="both"):
        raise NotImplementedError()

    def create_edge(self, source_id, target_id, relation_type, strength=1.0, metadata=None):
        raise NotImplementedError()

    def update_edge(self, source_id, target_id, relation_type, **kwargs):
        raise NotImplementedError()

    def upsert_edges(self, edges):
        raise NotImplementedError()

    def get_curriculum_graph(self, root_entity_id, max_depth=3):
        raise NotImplementedError()
