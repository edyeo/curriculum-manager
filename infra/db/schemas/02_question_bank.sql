-- Question Bank DB Schema
-- 생성된 문제 및 사용자 응답 관리

CREATE SCHEMA IF NOT EXISTS qb;

-- Question 테이블
CREATE TABLE qb.question (
    id VARCHAR(50) PRIMARY KEY,
    entity_id VARCHAR(50) NOT NULL,
    difficulty_level VARCHAR(20),              -- 'easy', 'medium', 'hard'
    question_text TEXT NOT NULL,
    options JSONB NOT NULL,                    -- [{text, is_correct}, ...]
    correct_answer VARCHAR(255),
    explanation TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (entity_id) REFERENCES kg.entity(id) ON DELETE CASCADE
);

CREATE INDEX idx_question_entity ON qb.question(entity_id);
CREATE INDEX idx_question_difficulty ON qb.question(difficulty_level);
CREATE INDEX idx_question_entity_difficulty ON qb.question(entity_id, difficulty_level);
CREATE INDEX idx_question_created ON qb.question(created_at DESC);

-- Question Response 테이블 (사용자 답변 기록)
CREATE TABLE qb.question_response (
    id VARCHAR(50) PRIMARY KEY,
    question_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50),                       -- nullable (익명 사용자)
    response VARCHAR(255),
    is_correct BOOLEAN,
    response_time_sec INT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES qb.question(id) ON DELETE CASCADE
);

CREATE INDEX idx_response_question ON qb.question_response(question_id);
CREATE INDEX idx_response_user ON qb.question_response(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_response_correct ON qb.question_response(is_correct);
CREATE INDEX idx_response_created ON qb.question_response(created_at DESC);

-- 함수: updated_at 자동 업데이트
CREATE OR REPLACE FUNCTION qb.update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 트리거: question의 updated_at 업데이트
CREATE TRIGGER trg_question_update BEFORE UPDATE ON qb.question
FOR EACH ROW EXECUTE FUNCTION qb.update_timestamp();

-- 뷰: 문제 통계 (entity별)
CREATE OR REPLACE VIEW qb.vw_question_stats AS
SELECT
    q.entity_id,
    COUNT(*) as total_questions,
    COUNT(CASE WHEN q.difficulty_level = 'easy' THEN 1 END) as easy_count,
    COUNT(CASE WHEN q.difficulty_level = 'medium' THEN 1 END) as medium_count,
    COUNT(CASE WHEN q.difficulty_level = 'hard' THEN 1 END) as hard_count,
    COUNT(qr.id) as total_responses,
    ROUND(100.0 * COUNT(CASE WHEN qr.is_correct THEN 1 END)::NUMERIC / NULLIF(COUNT(qr.id), 0), 2) as avg_correct_rate
FROM qb.question q
LEFT JOIN qb.question_response qr ON q.id = qr.question_id
GROUP BY q.entity_id;

-- 뷰: 사용자 성과 (user별)
CREATE OR REPLACE VIEW qb.vw_user_performance AS
SELECT
    qr.user_id,
    COUNT(*) as total_attempts,
    COUNT(CASE WHEN qr.is_correct THEN 1 END) as correct_count,
    ROUND(100.0 * COUNT(CASE WHEN qr.is_correct THEN 1 END)::NUMERIC / COUNT(*), 2) as correct_rate,
    ROUND(AVG(qr.response_time_sec)::NUMERIC, 2) as avg_response_time_sec
FROM qb.question_response qr
WHERE qr.user_id IS NOT NULL
GROUP BY qr.user_id;

-- 테스트 데이터 (선택사항)
-- INSERT INTO qb.question (id, entity_id, difficulty_level, question_text, options, correct_answer) VALUES
-- ('q1', 'python_basics', 'easy',
--  'Python은 어떤 종류의 언어인가?',
--  '[{"text": "인터프리터 언어", "is_correct": true}, {"text": "컴파일 언어", "is_correct": false}]',
--  '인터프리터 언어');
