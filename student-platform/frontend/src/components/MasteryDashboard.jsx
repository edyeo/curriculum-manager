import { useEffect, useState } from 'react'
import { api } from '../services/api'

function CompetencyGauge({ score }) {
  const pct = score * 100
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

function BlueprintBadge({ bp }) {
  const color = bp.cleared ? '#68d391' : bp.required ? '#fc8181' : '#cbd5e0'
  const bg = bp.cleared ? '#f0fff4' : bp.required ? '#fff5f5' : '#f7fafc'
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      border: `1px solid ${color}`, background: bg,
      borderRadius: 12, padding: '2px 8px', fontSize: 11, color: '#4a5568',
    }}>
      <span style={{ color, fontWeight: 700 }}>{bp.cleared ? '✓' : bp.required ? '!' : '○'}</span>
      {bp.blueprint_name}
      <span style={{ color: '#a0aec0' }}>{(bp.clearance * 100).toFixed(0)}%</span>
    </span>
  )
}

function NodeCard({ node }) {
  const [open, setOpen] = useState(false)
  const hasRequired = node.blueprints.some(b => b.required)
  return (
    <div style={S.card}>
      <div style={S.cardHeader} onClick={() => setOpen(o => !o)}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 500, color: '#2d3748' }}>{node.node_name}</span>
            {hasRequired && !node.required_blueprint_cleared && (
              <span style={{ fontSize: 10, background: '#fff5f5', border: '1px solid #fc8181', color: '#e53e3e', borderRadius: 4, padding: '1px 5px' }}>필수 미달</span>
            )}
          </div>
          <div style={{ marginTop: 4, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {node.blueprints.map(bp => <BlueprintBadge key={bp.blueprint_id} bp={bp} />)}
          </div>
        </div>
        <div style={{ width: 180, marginLeft: 16 }}>
          <CompetencyGauge score={node.competency_score} />
        </div>
        <span style={{ marginLeft: 8, color: '#a0aec0', fontSize: 14 }}>{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div style={S.cardBody}>
          {node.blueprints.map(bp => (
            <div key={bp.blueprint_id} style={S.bpRow}>
              <div style={{ flex: 1 }}>
                <span style={{ fontSize: 12, color: '#4a5568' }}>{bp.blueprint_name}</span>
                {bp.required && <span style={{ marginLeft: 6, fontSize: 10, color: '#e53e3e' }}>필수</span>}
              </div>
              <span style={{ fontSize: 11, color: '#718096' }}>
                정답 {bp.correct_count}/{bp.attempt_count}회 시도 · {(bp.clearance * 100).toFixed(0)}% 달성
              </span>
              <span style={{ marginLeft: 8, fontWeight: 600, fontSize: 12, color: bp.cleared ? '#38a169' : '#a0aec0' }}>
                {bp.cleared ? '달성' : '미달'}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function MasteryDashboard({ subjectId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!subjectId) return
    setLoading(true)
    setError(null)
    api.getCompetency(subjectId)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [subjectId])

  if (!subjectId) return <p style={S.hint}>과목을 선택하세요.</p>
  if (loading) return <p style={S.hint}>이해도 로딩 중...</p>
  if (error) return <p style={{ ...S.hint, color: '#e53e3e' }}>{error}</p>
  if (!data) return null

  const nodes = data.nodes || []
  const withBp = nodes.filter(n => n.blueprints.length > 0)
  const noBp = nodes.filter(n => n.blueprints.length === 0)
  const avgComp = withBp.length
    ? withBp.reduce((s, n) => s + n.competency_score, 0) / withBp.length
    : 0
  const clearedCount = withBp.filter(n => n.competency_score >= 0.7).length
  const requiredFail = withBp.filter(n => !n.required_blueprint_cleared).length

  return (
    <div style={{ padding: '1rem' }}>
      <div style={S.summary}>
        <div style={S.stat}>
          <span style={S.statNum}>{(avgComp * 100).toFixed(0)}%</span>
          <span>전체 평균</span>
        </div>
        <div style={S.stat}>
          <span style={S.statNum}>{clearedCount}/{withBp.length}</span>
          <span>달성 노드</span>
        </div>
        <div style={S.stat}>
          <span style={{ ...S.statNum, color: requiredFail ? '#fc8181' : '#68d391' }}>{requiredFail}</span>
          <span>필수 미달</span>
        </div>
      </div>

      {withBp.map(node => <NodeCard key={node.node_id} node={node} />)}

      {noBp.length > 0 && (
        <div style={S.noBpGroup}>
          <span style={{ fontSize: 12, color: '#a0aec0' }}>Blueprint 미연결 노드: </span>
          {noBp.map(n => (
            <span key={n.node_id} style={{ fontSize: 12, color: '#cbd5e0', marginLeft: 8 }}>{n.node_name}</span>
          ))}
        </div>
      )}
    </div>
  )
}

const S = {
  summary: { display: 'flex', gap: '1rem', marginBottom: '1.5rem', justifyContent: 'center' },
  stat: { textAlign: 'center', background: '#f7fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: '0.75rem 1.5rem', display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12, color: '#666' },
  statNum: { fontSize: 22, fontWeight: 'bold', color: '#2d3748' },
  hint: { color: '#888', textAlign: 'center' },
  card: { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, marginBottom: 8, overflow: 'hidden' },
  cardHeader: { display: 'flex', alignItems: 'center', padding: '12px 16px', cursor: 'pointer' },
  cardBody: { borderTop: '1px solid #e2e8f0', padding: '8px 16px' },
  bpRow: { display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', fontSize: 12 },
  noBpGroup: { marginTop: 12, padding: '8px 12px', background: '#f7fafc', borderRadius: 6 },
}
