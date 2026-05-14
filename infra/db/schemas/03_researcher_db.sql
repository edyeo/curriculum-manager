-- Researcher DB Schema
-- Researcher 에이전트의 조사 결과 저장

CREATE SCHEMA IF NOT EXISTS res;

-- Research Result 테이블
CREATE TABLE res.research_result (
    id VARCHAR(50) PRIMARY KEY,
    entity_id VARCHAR(50) NOT NULL,
    keyword VARCHAR(255),
    source VARCHAR(100),                       -- 'blog', 'linkedin', 'paper', 'github', etc.
    title VARCHAR(255),
    url TEXT,
    summary TEXT,                              -- LLM이 생성한 요약
    full_content TEXT,                         -- 원본 내용
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (entity_id) REFERENCES kg.entity(id) ON DELETE CASCADE
);

CREATE INDEX idx_research_entity ON res.research_result(entity_id);
CREATE INDEX idx_research_keyword ON res.research_result(keyword);
CREATE INDEX idx_research_source ON res.research_result(source);
CREATE INDEX idx_research_entity_keyword ON res.research_result(entity_id, keyword);
CREATE INDEX idx_research_created ON res.research_result(created_at DESC);

-- 뷰: 조사 결과 요약 (entity별)
CREATE OR REPLACE VIEW res.vw_research_summary AS
SELECT
    rr.entity_id,
    COUNT(*) as total_results,
    COUNT(DISTINCT rr.keyword) as keyword_count,
    COUNT(CASE WHEN rr.source = 'blog' THEN 1 END) as blog_count,
    COUNT(CASE WHEN rr.source = 'linkedin' THEN 1 END) as linkedin_count,
    COUNT(CASE WHEN rr.source = 'paper' THEN 1 END) as paper_count,
    COUNT(CASE WHEN rr.source = 'github' THEN 1 END) as github_count,
    MAX(rr.created_at) as last_updated
FROM res.research_result rr
GROUP BY rr.entity_id;

-- 테스트 데이터 (선택사항)
-- INSERT INTO res.research_result (id, entity_id, keyword, source, title, summary) VALUES
-- ('res1', 'python_basics', 'python', 'blog', 'Python 101 Guide', 'Python 기초 완벽 가이드...');
