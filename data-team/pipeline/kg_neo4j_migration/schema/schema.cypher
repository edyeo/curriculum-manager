// KG Neo4j Schema — constraint & index 정의
// 실행: python schema/apply_schema.py --neo4j-uri bolt://localhost:7687
// (idempotent: IF NOT EXISTS로 중복 실행 안전)

// ── Node uniqueness constraints ──────────────────────────────────
CREATE CONSTRAINT subject_id  IF NOT EXISTS FOR (n:Subject)   REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT seed_id     IF NOT EXISTS FOR (n:Seed)      REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT concept_id  IF NOT EXISTS FOR (n:Concept)   REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT tech_id     IF NOT EXISTS FOR (n:TechStack) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT system_id   IF NOT EXISTS FOR (n:System)    REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT question_id IF NOT EXISTS FOR (n:Question)  REQUIRE n.id IS UNIQUE;

// ── Indexes for common lookups ────────────────────────────────────
CREATE INDEX subject_name IF NOT EXISTS FOR (n:Subject) ON (n.name);
CREATE INDEX seed_name     IF NOT EXISTS FOR (n:Seed)     ON (n.name);
CREATE INDEX concept_name  IF NOT EXISTS FOR (n:Concept)  ON (n.name);
