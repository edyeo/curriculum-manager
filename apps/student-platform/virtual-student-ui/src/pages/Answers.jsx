import { useState, useEffect } from 'react'
import { fetchVirtualAnswers } from '../api/client'
import { useSubject } from '../context/SubjectContext'

export default function Answers() {
  const { selectedId: subjectId } = useSubject()
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    setSelected(null)
    load()
  }, [subjectId])

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchVirtualAnswers(subjectId)
      setRows(Array.isArray(data) ? data : [])
    } catch (e) {
      setError(e.message)
      setRows([])
    } finally {
      setLoading(false)
    }
  }

  const scoreColor = (s) => s >= 0.7 ? '#16a34a' : s >= 0.4 ? '#ca8a04' : '#dc2626'

  return (
    <div>
      <div className="section-header">
        <h2>Answers</h2>
        <button className="btn-secondary" onClick={load} disabled={loading}>
          {loading ? '로딩 중...' : '새로고침'}
        </button>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      <div className="card" style={{ padding: 0 }}>
        <table className="table">
          <thead>
            <tr>
              <th>학생</th>
              <th>Session ID</th>
              <th>문제</th>
              <th style={{ textAlign: 'center' }}>점수</th>
              <th style={{ textAlign: 'center' }}>정오</th>
              <th>일시</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={6} style={{ textAlign: 'center', color: '#9ca3af', padding: 32 }}>불러오는 중...</td></tr>
            )}
            {!loading && rows.length === 0 && (
              <tr><td colSpan={6} style={{ textAlign: 'center', color: '#9ca3af', padding: 32 }}>답변 데이터가 없습니다. 데이터 파이프라인을 먼저 실행하세요.</td></tr>
            )}
            {rows.map((r) => {
              const isSelected = selected?.id === r.id
              return [
                <tr
                  key={r.id}
                  style={{
                    cursor: 'pointer',
                    background: isSelected ? '#eef2ff' : undefined,
                    borderLeft: isSelected ? '3px solid #6366f1' : '3px solid transparent',
                  }}
                  onClick={() => setSelected(isSelected ? null : r)}
                >
                  <td style={{ fontWeight: 600 }}>{r.student_name}</td>
                  <td style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: '#6b7280' }}>
                    {r.student_id.slice(0, 8)}…
                  </td>
                  <td style={{ maxWidth: 360 }}>
                    <span style={{ fontSize: '0.875rem', color: '#374151' }}>
                      {r.question_text && r.question_text !== r.question_id
                        ? (r.question_text.length > 70 ? r.question_text.slice(0, 70) + '…' : r.question_text)
                        : <span style={{ color: '#9ca3af', fontFamily: 'monospace', fontSize: '0.78rem' }}>{r.question_id.slice(0, 16)}…</span>
                      }
                    </span>
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    {r.score != null
                      ? <span style={{ fontWeight: 700, color: scoreColor(r.score) }}>{(r.score * 100).toFixed(0)}점</span>
                      : <span style={{ color: '#9ca3af' }}>—</span>
                    }
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    {r.is_correct != null
                      ? <span style={{
                          fontSize: '0.75rem', padding: '2px 8px', borderRadius: 4, fontWeight: 600,
                          background: r.is_correct ? '#dcfce7' : '#fee2e2',
                          color: r.is_correct ? '#16a34a' : '#dc2626',
                        }}>
                          {r.is_correct ? '정답' : '오답'}
                        </span>
                      : <span style={{ color: '#9ca3af' }}>—</span>
                    }
                  </td>
                  <td style={{ fontSize: '0.8rem', color: '#6b7280', whiteSpace: 'nowrap' }}>
                    {r.created_at ? new Date(r.created_at).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'}
                  </td>
                </tr>,

                isSelected && (
                  <tr key={`${r.id}-detail`} style={{ background: '#f5f3ff' }}>
                    <td colSpan={6} style={{ padding: 0 }}>
                      <DetailPanel row={r} />
                    </td>
                  </tr>
                ),
              ]
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function DetailPanel({ row }) {
  const scoreColor = (s) => s >= 0.7 ? '#16a34a' : s >= 0.4 ? '#ca8a04' : '#dc2626'

  return (
    <div style={{ padding: '20px 24px', borderTop: '1px solid #c7d2fe' }}>
      <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', marginBottom: 16 }}>
        <MetaItem label="학생" value={row.student_name} bold />
        <MetaItem label="Session ID" value={row.student_id} mono />
        <MetaItem label="Question ID" value={row.question_id} mono />
        {row.score != null && (
          <MetaItem label="점수" value={
            <span style={{ fontWeight: 700, color: scoreColor(row.score) }}>{(row.score * 100).toFixed(0)}점</span>
          } />
        )}
        {row.is_correct != null && (
          <MetaItem label="정오" value={
            <span style={{
              fontSize: '0.8rem', padding: '2px 8px', borderRadius: 4, fontWeight: 600,
              background: row.is_correct ? '#dcfce7' : '#fee2e2',
              color: row.is_correct ? '#16a34a' : '#dc2626',
            }}>
              {row.is_correct ? '정답' : '오답'}
            </span>
          } />
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ background: '#eef2ff', border: '1px solid #c7d2fe', borderRadius: 8, padding: '12px 16px' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#4f46e5', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>문제</div>
          <div style={{ fontSize: '0.875rem', color: '#1f2937', lineHeight: 1.6 }}>
            {row.question_text && row.question_text !== row.question_id ? row.question_text : row.question_id}
          </div>
        </div>

        <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8, padding: '12px 16px' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#15803d', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>학생 답변</div>
          <div style={{ fontSize: '0.875rem', color: '#1f2937', lineHeight: 1.6 }}>{row.user_answer || '—'}</div>
        </div>

        {row.feedback && (
          <div style={{ background: '#fafafa', border: `1px solid #e5e7eb`, borderLeft: `3px solid ${scoreColor(row.score ?? 0.5)}`, borderRadius: 6, padding: '10px 14px' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#6b7280', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>피드백</div>
            <div style={{ fontSize: '0.8rem', color: '#4b5563', lineHeight: 1.6 }}>{row.feedback}</div>
          </div>
        )}
      </div>
    </div>
  )
}

function MetaItem({ label, value, bold, mono }) {
  return (
    <div>
      <div style={{ fontSize: '0.72rem', color: '#6b7280', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 2 }}>{label}</div>
      <div style={{ fontWeight: bold ? 700 : 400, fontFamily: mono ? 'monospace' : undefined, fontSize: mono ? '0.78rem' : '0.875rem', color: '#1f2937' }}>
        {value}
      </div>
    </div>
  )
}
