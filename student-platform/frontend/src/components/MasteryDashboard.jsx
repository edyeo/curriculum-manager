import { useEffect, useState } from 'react'
import { api } from '../services/api'

function MasteryBar({ score }) {
  const pct = score !== null && score !== undefined ? score * 100 : null
  const color = pct === null ? '#b0b0b0' : pct < 40 ? '#fc8181' : pct < 70 ? '#f6ad55' : '#68d391'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 8, background: '#e2e8f0', borderRadius: 4 }}>
        {pct !== null && <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 4 }} />}
      </div>
      <span style={{ fontSize: 12, color: '#555', width: 40, textAlign: 'right' }}>
        {pct !== null ? `${pct.toFixed(0)}%` : '미학습'}
      </span>
    </div>
  )
}

export default function MasteryDashboard({ subjectId, graphData }) {
  const [masteryMap, setMasteryMap] = useState({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!subjectId) return
    setLoading(true)
    api.getMastery(subjectId)
      .then(res => {
        const map = {}
        for (const r of res.mastery) map[r.node_id] = r.mastery_score
        setMasteryMap(map)
      })
      .finally(() => setLoading(false))
  }, [subjectId])

  if (!graphData?.nodes?.length) return <p style={{ color: '#888', textAlign: 'center' }}>그래프 데이터를 불러오는 중...</p>
  if (loading) return <p style={{ color: '#888', textAlign: 'center' }}>이해도 로딩 중...</p>

  const nodes = graphData.nodes.map(n => ({ ...n, mastery_score: masteryMap[n.id] ?? null }))
  const byType = {}
  for (const n of nodes) {
    if (!byType[n.type]) byType[n.type] = []
    byType[n.type].push(n)
  }

  const learned = nodes.filter(n => n.mastery_score !== null)
  const avgMastery = learned.length ? learned.reduce((s, n) => s + n.mastery_score, 0) / learned.length : 0
  const weak = learned.filter(n => n.mastery_score < 0.4)

  return (
    <div style={{ padding: '1rem' }}>
      <div style={styles.summary}>
        <div style={styles.stat}><span style={styles.statNum}>{(avgMastery * 100).toFixed(0)}%</span><span>전체 평균</span></div>
        <div style={styles.stat}><span style={styles.statNum}>{learned.length}/{nodes.length}</span><span>학습 완료</span></div>
        <div style={styles.stat}><span style={{ ...styles.statNum, color: '#fc8181' }}>{weak.length}</span><span>취약 노드</span></div>
      </div>

      {['Seed', 'Concept', 'TechStack'].map(type => byType[type] && (
        <div key={type} style={styles.group}>
          <h4 style={styles.groupTitle}>{type} ({byType[type].length}개)</h4>
          {byType[type].map(n => (
            <div key={n.id} style={styles.nodeRow}>
              <span style={{ fontSize: 13, flex: 1, color: '#333' }}>{n.name}</span>
              <div style={{ width: 200 }}><MasteryBar score={n.mastery_score} /></div>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

const styles = {
  summary: { display: 'flex', gap: '1rem', marginBottom: '1.5rem', justifyContent: 'center' },
  stat: { textAlign: 'center', background: '#f7fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: '0.75rem 1.5rem', display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12, color: '#666' },
  statNum: { fontSize: 22, fontWeight: 'bold', color: '#2d3748' },
  group: { marginBottom: '1.5rem' },
  groupTitle: { fontSize: 14, color: '#555', borderBottom: '1px solid #e2e8f0', paddingBottom: 6, marginBottom: 10 },
  nodeRow: { display: 'flex', alignItems: 'center', gap: 12, padding: '4px 0' },
}
