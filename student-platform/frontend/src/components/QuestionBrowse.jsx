import { useState, useEffect, useCallback } from 'react'
import { api } from '../services/api'

const DIFF_LABEL = { easy: '쉬움', medium: '보통', hard: '어려움' }
const DIFF_COLOR = { easy: '#10b981', medium: '#f59e0b', hard: '#ef4444' }
const TYPE_LABEL = { MCQ: '객관식', OX: 'O/X', short_answer: '단답형' }

export default function QuestionBrowse({ onSelectQuestion, onBack }) {
  const [questions, setQuestions] = useState([])
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({ blueprint_id: '', difficulty: '', question_type: '' })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const active = Object.fromEntries(Object.entries(filters).filter(([, v]) => v))
      const res = await api.getPublishedQuestions(active)
      setQuestions(res.questions || [])
    } catch {
      setQuestions([])
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => { load() }, [load])

  return (
    <div style={S.root}>
      <div style={S.header}>
        <button onClick={onBack} style={S.backBtn}>← 개념 맵으로</button>
        <h2 style={S.title}>문제 탐색</h2>
      </div>

      {/* 필터 */}
      <div style={S.filters}>
        <select style={S.select} value={filters.difficulty} onChange={e => setFilters(f => ({ ...f, difficulty: e.target.value }))}>
          <option value="">전체 난이도</option>
          <option value="easy">쉬움</option>
          <option value="medium">보통</option>
          <option value="hard">어려움</option>
        </select>
        <select style={S.select} value={filters.question_type} onChange={e => setFilters(f => ({ ...f, question_type: e.target.value }))}>
          <option value="">전체 타입</option>
          <option value="MCQ">객관식</option>
          <option value="OX">O/X</option>
          <option value="short_answer">단답형</option>
        </select>
      </div>

      {/* 목록 */}
      {loading ? (
        <p style={S.hint}>불러오는 중…</p>
      ) : questions.length === 0 ? (
        <p style={S.hint}>출제된 문항이 없습니다.</p>
      ) : (
        <div style={S.grid}>
          {questions.map(q => (
            <div key={q.id} style={S.card} onClick={() => onSelectQuestion(q)}>
              <p style={S.cardText}>{q.question_text.slice(0, 50)}{q.question_text.length > 50 ? '…' : ''}</p>
              <div style={S.badges}>
                <span style={{ ...S.badge, background: DIFF_COLOR[q.difficulty] || '#ddd', color: '#fff' }}>
                  {DIFF_LABEL[q.difficulty] || q.difficulty}
                </span>
                <span style={{ ...S.badge, background: '#e2e8f0', color: '#555' }}>
                  {TYPE_LABEL[q.question_type] || q.question_type}
                </span>
                {q.entity_id && (
                  <span style={{ ...S.badge, background: '#eff6ff', color: '#3b82f6' }}>{q.entity_id}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const S = {
  root: { maxWidth: 800, margin: '0 auto' },
  header: { display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 },
  backBtn: { padding: '6px 12px', border: '1px solid #ddd', borderRadius: 6, cursor: 'pointer', background: '#fff', fontSize: 13 },
  title: { margin: 0, fontSize: 20, color: '#2d3748' },
  filters: { display: 'flex', gap: 8, marginBottom: 16 },
  select: { padding: '6px 10px', border: '1px solid #ddd', borderRadius: 6, fontSize: 13 },
  hint: { textAlign: 'center', color: '#888', padding: '40px 0' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 },
  card: { padding: '14px 16px', border: '1px solid #e2e8f0', borderRadius: 8, cursor: 'pointer', background: '#fff', transition: 'box-shadow 0.15s' },
  cardText: { fontSize: 14, color: '#333', lineHeight: 1.5, margin: '0 0 10px' },
  badges: { display: 'flex', gap: 6, flexWrap: 'wrap' },
  badge: { fontSize: 11, padding: '2px 8px', borderRadius: 10, fontWeight: 500 },
}
