import { useEffect, useState } from 'react'
import { api } from '../services/api'

function CellScore({ score }) {
  const pct = (score ?? 0) * 100
  const bg = pct < 40 ? '#fff5f5' : pct < 70 ? '#fffaf0' : '#f0fff4'
  const color = pct < 40 ? '#e53e3e' : pct < 70 ? '#c05621' : '#276749'
  const border = pct < 40 ? '#fed7d7' : pct < 70 ? '#fbd38d' : '#9ae6b4'
  return (
    <div style={{ background: bg, border: `1px solid ${border}`, borderRadius: 6, padding: '6px 10px', textAlign: 'center', minWidth: 70 }}>
      <div style={{ fontSize: 15, fontWeight: 700, color }}>{pct.toFixed(0)}%</div>
    </div>
  )
}

function IntegrationItemCard({ item }) {
  const [open, setOpen] = useState(false)
  const pct = (item.mastery_score ?? 0) * 100
  const color = pct < 40 ? '#e53e3e' : pct < 70 ? '#c05621' : '#276749'
  const hasCells = item.required_combinations?.length > 0
  return (
    <div style={S.itemCard}>
      <div style={S.itemHeader} onClick={() => hasCells && setOpen(o => !o)}>
        <span style={S.itemName}>{item.item_name}</span>
        <span style={{ fontSize: 13, fontWeight: 600, color }}>{pct.toFixed(0)}%</span>
        {hasCells && <span style={S.chevron}>{open ? '▲' : '▼'}</span>}
      </div>
      {open && hasCells && (
        <div style={S.cellGrid}>
          {item.required_combinations.map((c, i) => (
            <div key={i} style={S.cellEntry}>
              <div style={S.cellLabel}>{c.layer}<br />{c.stage}</div>
              <CellScore score={c.cell_mastery} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function BlueprintCard({ bp }) {
  const [open, setOpen] = useState(false)
  const hasItems = bp.integration_items?.length > 0
  const statusColor = bp.cleared ? '#38a169' : bp.required ? '#e53e3e' : '#a0aec0'
  const statusLabel = bp.cleared ? '달성' : bp.required ? '필수 미달' : '미달'
  return (
    <div style={S.bpCard}>
      <div style={S.bpHeader} onClick={() => setOpen(o => !o)}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={S.bpName}>{bp.blueprint_name}</span>
            {bp.required && <span style={S.requiredBadge}>필수</span>}
          </div>
          <span style={{ fontSize: 11, color: '#718096' }}>
            정답 {bp.correct_count}/{bp.attempt_count}회 · clearance {(bp.clearance * 100).toFixed(0)}%
          </span>
        </div>
        <span style={{ fontSize: 13, fontWeight: 600, color: statusColor }}>{statusLabel}</span>
        <span style={S.chevron}>{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div style={S.bpBody}>
          {hasItems
            ? bp.integration_items.map(item => (
                <IntegrationItemCard key={item.item_id} item={item} />
              ))
            : <p style={{ fontSize: 12, color: '#a0aec0', margin: 0 }}>IntegrationItem 없음</p>
          }
        </div>
      )}
    </div>
  )
}

function NodeSection({ node }) {
  const [open, setOpen] = useState(false)
  const pct = node.competency_score * 100
  const color = pct < 40 ? '#e53e3e' : pct < 70 ? '#c05621' : '#276749'
  return (
    <div style={S.nodeSection}>
      <div style={S.nodeSectionHeader} onClick={() => setOpen(o => !o)}>
        <div style={{ flex: 1 }}>
          <span style={S.nodeName}>{node.node_name}</span>
          {!node.required_blueprint_cleared && (
            <span style={S.failBadge}>필수 미달</span>
          )}
        </div>
        <span style={{ fontSize: 14, fontWeight: 700, color }}>{pct.toFixed(0)}%</span>
        <span style={S.chevron}>{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div style={S.nodeSectionBody}>
          {node.blueprints.map(bp => (
            <BlueprintCard key={bp.blueprint_id} bp={bp} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function BlueprintMastery({ subjectId }) {
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
  if (loading) return <p style={S.hint}>Blueprint 역량 로딩 중...</p>
  if (error) return <p style={{ ...S.hint, color: '#e53e3e' }}>{error}</p>
  if (!data) return null

  const nodes = (data.nodes || []).filter(n => n.blueprints.length > 0)
  const totalItems = nodes.flatMap(n => n.blueprints.flatMap(b => b.integration_items || []))
  const masteredItems = totalItems.filter(i => i.mastery_score >= 0.7)
  const requiredFail = nodes.filter(n => !n.required_blueprint_cleared).length

  return (
    <div style={{ padding: '1rem' }}>
      <div style={S.summary}>
        <div style={S.stat}>
          <span style={S.statNum}>{nodes.length}</span>
          <span>평가 노드</span>
        </div>
        <div style={S.stat}>
          <span style={S.statNum}>{masteredItems.length}/{totalItems.length}</span>
          <span>숙달 항목 (70%+)</span>
        </div>
        <div style={S.stat}>
          <span style={{ ...S.statNum, color: requiredFail ? '#fc8181' : '#68d391' }}>{requiredFail}</span>
          <span>필수 미달 노드</span>
        </div>
      </div>

      {nodes.length === 0
        ? <p style={S.hint}>Blueprint가 연결된 노드가 없습니다.</p>
        : nodes.map(node => <NodeSection key={node.node_id} node={node} />)
      }
    </div>
  )
}

const S = {
  summary: { display: 'flex', gap: '1rem', marginBottom: '1.5rem', justifyContent: 'center' },
  stat: { textAlign: 'center', background: '#f7fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: '0.75rem 1.5rem', display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12, color: '#666' },
  statNum: { fontSize: 22, fontWeight: 'bold', color: '#2d3748' },
  hint: { color: '#888', textAlign: 'center', paddingTop: '2rem' },
  nodeSection: { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, marginBottom: 10, overflow: 'hidden' },
  nodeSectionHeader: { display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px', cursor: 'pointer' },
  nodeSectionBody: { borderTop: '1px solid #e2e8f0', padding: '10px 16px', display: 'flex', flexDirection: 'column', gap: 8 },
  nodeName: { fontSize: 14, fontWeight: 600, color: '#2d3748', marginRight: 8 },
  failBadge: { fontSize: 10, background: '#fff5f5', border: '1px solid #fc8181', color: '#e53e3e', borderRadius: 4, padding: '1px 5px' },
  chevron: { marginLeft: 6, color: '#a0aec0', fontSize: 12 },
  bpCard: { background: '#f7fafc', border: '1px solid #e8edf2', borderRadius: 6, overflow: 'hidden' },
  bpHeader: { display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', cursor: 'pointer' },
  bpName: { fontSize: 13, fontWeight: 500, color: '#2d3748' },
  bpBody: { borderTop: '1px solid #e8edf2', padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: 6 },
  requiredBadge: { fontSize: 10, background: '#fff5f5', border: '1px solid #fc8181', color: '#e53e3e', borderRadius: 4, padding: '1px 5px' },
  itemCard: { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 6, overflow: 'hidden' },
  itemHeader: { display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px', cursor: 'pointer' },
  itemName: { flex: 1, fontSize: 12, color: '#4a5568' },
  cellGrid: { display: 'flex', flexWrap: 'wrap', gap: 8, padding: '8px 10px', borderTop: '1px solid #f0f4f8' },
  cellEntry: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 },
  cellLabel: { fontSize: 10, color: '#718096', textAlign: 'center', lineHeight: 1.3 },
}
