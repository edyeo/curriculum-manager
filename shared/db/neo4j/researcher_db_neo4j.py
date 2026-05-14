"""
Neo4j implementation of ResearcherDB (stub for future implementation)
"""
from shared.db_client import ResearcherDB


class ResearcherDBNeo4j(ResearcherDB):
    """Neo4j implementation of Researcher database"""

    def __init__(self, config):
        raise NotImplementedError("Neo4j implementation coming in Phase 3")

    def create_research_result(self, entity_id, keyword, source, title, url=None, summary=None, full_content=None, metadata=None):
        raise NotImplementedError()

    def query_research_results(self, entity_id=None, keyword=None, source=None, limit=100):
        raise NotImplementedError()

    def get_research_summary(self, entity_id):
        raise NotImplementedError()
