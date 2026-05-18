import { useEffect, useState } from 'react'
import { api } from '../services/api'

function MasteryBar({ score }) {
  const pct = (score ?? 0) * 100
  const color = pct < 40 ? '#fc8181' : pct < 70 ? '#f6ad55' : '#68d391'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 8, background: '#e2e8f0', borderRadius: 4 }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 4 }} />
      </div>
      <span style={{ fontSize: 12, color: '#555', width: 40, textAlign: 'right' }}>
        {pct.toFixed(0)}%
      </span>
    </div>
  )
}

export default function MasteryDashboard({ subjectId, graphData }) {
  const [mastery, setMastery] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!subjectId) return
    setLoading(true)
    setError(null)
    api.getMastery(subjectId)
      .then(setMastery)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [subjectId])

  if (!subjectId) return <p style={S.hint}>과목을 선택하세요.</p>
  if (loading) return <p style={S.hint}>이해도 로딩 중...</p>
  if (error) return <p style={{ ...S.hint, color: '#e53e3e' }}>{error}</p>

  const records = mastery?.mastery || []
  const masteryMap = Object.fromEntries(records.map(r => [r.node_id, r]))

  const nodes = graphData?.nodes || []
  const nodesWithMastery = nodes.map(n => ({
    ...n,
    mastery: masteryMap[n.id] ?? null,
  }))

  const attempted = nodesWithMastery.filter(n => n.mastery)
  const avgScore = attempted.length
    ? attempted.reduce((s, n) => s + n.mastery.mastery_score, 0) / attempted.length
    : 0

  return (
    <div style={{ padding: '1rem' }}>
      <div style={S.summary}>
        <div style={S.stat}>
          <span style={S.statNum}>{(avgScore * 100).toFixed(0)}%</span>
          <span>평균 이해도</span>
        </div>
        <div style={S.stat}>
          <span style={S.statNum}>{attempted.length}/{nodes.length}</span>
          <span>학습한 노드</span>
        </div>
        <div style={S.stat}>
          <span style={S.statNum}>{attempted.filter(n => n.mastery.mastery_score >= 0.7).length}</span>
          <span>숙달 노드 (70%+)</span>
        </div>
      </div>

      <div style={S.list}>
        {nodesWithMastery.length === 0 && (
          <p style={S.hint}>그래프 데이터를 불러오는 중...</p>
        )}
        {nodesWithMastery.map(node => (
          <div key={node.id} style={S.row}>
            <div style={S.nodeInfo}>
              <span style={S.nodeName}>{node.name}</span>
              <span style={S.nodeType}>{node.type}</span>
            </div>
            <div style={S.barWrap}>
              {node.mastery
                ? <MasteryBar score={node.mastery.mastery_score} />
                : <span style={S.unlearned}>미학습</span>
              }
            </div>
            {node.mastery && (
              <span style={S.attempts}>{node.mastery.attempt_count}회</span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

const S = {
  summary: { display: 'flex', gap: '1rem', marginBottom: '1.5rem', justifyContent: 'center' },
  stat: { textAlign: 'center', background: '#f7fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: '0.75rem 1.5rem', display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12, color: '#666' },
  statNum: { fontSize: 22, fontWeight: 'bold', color: '#2d3748' },
  hint: { color: '#888', textAlign: 'center', paddingTop: '2rem' },
  list: { display: 'flex', flexDirection: 'column', gap: 6 },
  row: { display: 'flex', alignItems: 'center', gap: 12, background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '10px 16px' },
  nodeInfo: { display: 'flex', alignItems: 'center', gap: 8, width: 220 },
  nodeName: { fontSize: 13, fontWeight: 500, color: '#2d3748' },
  nodeType: { fontSize: 10, color: '#a0aec0', background: '#f7fafc', border: '1px solid #e2e8f0', borderRadius: 4, padding: '1px 5px' },
  barWrap: { flex: 1 },
  unlearned: { fontSize: 11, color: '#cbd5e0' },
  attempts: { fontSize: 11, color: '#a0aec0', width: 32, textAlign: 'right' },
}
