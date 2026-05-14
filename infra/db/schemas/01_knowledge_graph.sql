-- Knowledge Graph DB Schema
-- 커리큘럼의 Entity와 Edge를 관리

CREATE SCHEMA IF NOT EXISTS kg;

-- Entity 테이블
CREATE TABLE kg.entity (
    id VARCHAR(50) PRIMARY KEY,
    type VARCHAR(50) NOT NULL,                 -- 'concept', 'skill', 'topic'
    name VARCHAR(255) NOT NULL,
    description TEXT,
    depth INT DEFAULT 0,                       -- 개념의 깊이 (0: 최상위)
    parent_id VARCHAR(50),                     -- 부모 entity
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES kg.entity(id) ON DELETE SET NULL
);

CREATE INDEX idx_entity_type ON kg.entity(type);
CREATE INDEX idx_entity_parent ON kg.entity(parent_id);
CREATE INDEX idx_entity_depth ON kg.entity(depth);
CREATE INDEX idx_entity_name ON kg.entity(name);
CREATE INDEX idx_entity_created ON kg.entity(created_at DESC);

-- Edge 테이블
CREATE TABLE kg.edge (
    id VARCHAR(50) PRIMARY KEY,
    source_id VARCHAR(50) NOT NULL,
    target_id VARCHAR(50) NOT NULL,
    relation_type VARCHAR(100) NOT NULL,      -- 'prerequisite', 'similar', 'extends'
    strength FLOAT DEFAULT 1.0,                -- 관계 강도 (0~1)
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES kg.entity(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES kg.entity(id) ON DELETE CASCADE,
    UNIQUE(source_id, target_id, relation_type)
);

CREATE INDEX idx_edge_source ON kg.edge(source_id);
CREATE INDEX idx_edge_target ON kg.edge(target_id);
CREATE INDEX idx_edge_type ON kg.edge(relation_type);
CREATE INDEX idx_edge_strength ON kg.edge(strength DESC);
CREATE INDEX idx_edge_created ON kg.edge(created_at DESC);

-- 함수: updated_at 자동 업데이트
CREATE OR REPLACE FUNCTION kg.update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 트리거: entity의 updated_at 업데이트
CREATE TRIGGER trg_entity_update BEFORE UPDATE ON kg.entity
FOR EACH ROW EXECUTE FUNCTION kg.update_timestamp();

-- 트리거: edge의 updated_at 업데이트
CREATE TRIGGER trg_edge_update BEFORE UPDATE ON kg.edge
FOR EACH ROW EXECUTE FUNCTION kg.update_timestamp();

-- 테스트 데이터 (선택사항)
-- INSERT INTO kg.entity (id, type, name, description, depth) VALUES
-- ('python_basics', 'concept', 'Python Basics', 'Python 언어 기초', 0),
-- ('variables', 'concept', 'Variables', '변수와 할당', 1),
-- ('data_types', 'concept', 'Data Types', '데이터 타입', 1);
