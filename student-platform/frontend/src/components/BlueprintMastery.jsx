import { useEffect, useState } from 'react'
import { api } from '../services/api'

const LAYER_COLORS = {
  Seed:       { bar: '#f6ad55', bg: '#fffaf0', border: '#fbd38d', text: '#c05621' },
  Concept:    { bar: '#68d391', bg: '#f0fff4', border: '#9ae6b4', text: '#276749' },
  TechStack:  { bar: '#76e4f7', bg: '#ebfcff', border: '#b2f5ea', text: '#086f83' },
}
const DEFAULT_COLOR = { bar: '#a0aec0', bg: '#f7fafc', border: '#cbd5e0', text: '#4a5568' }

function masteryColor(score) {
  if (score <= 0) return '#e2e8f0'
  if (score < 0.4) return '#fc8181'
  if (score < 0.7) return '#f6ad55'
  return '#68d391'
}

// 수직 막대 셀 — 높이가 mastery 비율에 비례
function MatrixCell({ layer, stage, mastery }) {
  const lc = LAYER_COLORS[layer] || DEFAULT_COLOR
  const pct = Math.round(mastery * 100)
  const barColor = pct === 0 ? '#e2e8f0' : masteryColor(mastery)
  const [hovered, setHovered] = useState(false)

  return (
    <div
      style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* 수직 막대 */}
      <div style={{ position: 'relative', width: 36, height: 80, background: '#f0f4f8', borderRadius: 4, overflow: 'hidden', border: '1px solid #e2e8f0' }}>
        <div style={{
          position: 'absolute', bottom: 0, left: 0, right: 0,
          height: `${pct}%`, background: barColor,
          transition: 'height 0.4s ease',
        }} />
        {hovered && (
          <div style={{
            position: 'absolute', top: 2, left: 0, right: 0,
            textAlign: 'center', fontSize: 10, fontWeight: 700,
            color: pct > 50 ? '#fff' : '#4a5568',
          }}>
            {pct}%
          </div>
        )}
      </div>
      {/* stage 라벨 */}
      <span style={{ fontSize: 11, color: '#718096', textAlign: 'center', lineHeight: 1.2, maxWidth: 48 }}>
        {stage}
      </span>
    </div>
  )
}

function BlueprintMatrix({ bp }) {
  const [open, setOpen] = useState(true)

  // 레이어별 최고 stage mastery 요약
  const layerSummaries = bp.matrix.map(ld => {
    const avg = ld.stages.length
      ? ld.stages.reduce((s, st) => s + st.mastery, 0) / ld.stages.length
      : 0
    return { layer: ld.layer, avg }
  })

  return (
    <div style={S.bpCard}>
      {/* 헤더 */}
      <div style={S.bpHeader} onClick={() => setOpen(o => !o)}>
        <div style={{ flex: 1 }}>
          <span style={S.bpTitle}>{bp.blueprint_name}</span>
          {bp.description && <span style={S.bpDesc}>{bp.description}</span>}
        </div>
        <div style={{ display: 'flex', gap: 8, marginRight: 12 }}>
          {layerSummaries.map(ls => {
            const lc = LAYER_COLORS[ls.layer] || DEFAULT_COLOR
            return (
              <span key={ls.layer} style={{
                fontSize: 11, padding: '2px 8px', borderRadius: 10,
                background: lc.bg, border: `1px solid ${lc.border}`, color: lc.text,
              }}>
                {ls.layer} {Math.round(ls.avg * 100)}%
              </span>
            )
          })}
        </div>
        <span style={{ color: '#a0aec0', fontSize: 12 }}>{open ? '▲' : '▼'}</span>
      </div>

      {open && (
        <>
          {/* Matrix grid: X축=layer, Y축=stage */}
          <div style={S.matrixWrap}>
            {bp.matrix.map(ld => {
              const lc = LAYER_COLORS[ld.layer] || DEFAULT_COLOR
              return (
                <div key={ld.layer} style={{ ...S.layerCol, borderTop: `3px solid ${lc.bar}` }}>
                  <div style={{ ...S.layerLabel, color: lc.text, background: lc.bg }}>
                    {ld.layer}
                  </div>
                  <div style={S.stageRow}>
                    {ld.stages.map(st => (
                      <MatrixCell key={st.stage} layer={ld.layer} stage={st.stage} mastery={st.mastery} />
                    ))}
                  </div>
                </div>
              )
            })}
          </div>

          {/* 범례 */}
          <div style={S.legend}>
            {[['#e2e8f0','미학습'], ['#fc8181','0–40%'], ['#f6ad55','40–70%'], ['#68d391','70%+']].map(([color, label]) => (
              <span key={label} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: '#718096' }}>
                <span style={{ width: 10, height: 10, borderRadius: 2, background: color, display: 'inline-block' }} />
                {label}
              </span>
            ))}
          </div>

          {/* 하단: layer 기준 stage 설명 */}
          <div style={S.stageDescSection}>
            <div style={S.stageDescTitle}>Stage 기준 설명</div>
            <div style={S.stageDescGrid}>
              {bp.matrix.map(ld => {
                const lc = LAYER_COLORS[ld.layer] || DEFAULT_COLOR
                return (
                  <div key={ld.layer} style={{ ...S.stageDescCol, borderTop: `2px solid ${lc.bar}` }}>
                    <div style={{ ...S.stageDescLayerLabel, color: lc.text }}>{ld.layer}</div>
                    {ld.stages.map((st, i) => (
                      <div key={st.stage} style={S.stageDescRow}>
                        <span style={{ ...S.stageDescBadge, background: lc.bg, color: lc.text, border: `1px solid ${lc.border}` }}>
                          {i + 1}. {st.stage}
                        </span>
                        <span style={S.stageDescText}>—</span>
                      </div>
                    ))}
                  </div>
                )
              })}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default function BlueprintMastery() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.getBlueprintMatrix()
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p style={S.hint}>Blueprint 로딩 중...</p>
  if (error) return <p style={{ ...S.hint, color: '#e53e3e' }}>{error}</p>
  if (!data) return null

  const blueprints = data.blueprints || []

  if (blueprints.length === 0) {
    return <p style={S.hint}>등록된 Blueprint(matrix 정의 포함)가 없습니다.</p>
  }

  // 전체 요약: 모든 셀 기준
  const allCells = blueprints.flatMap(bp => bp.matrix.flatMap(ld => ld.stages))
  const attempted = allCells.filter(st => st.mastery > 0)
  const avgMastery = attempted.length
    ? attempted.reduce((s, st) => s + st.mastery, 0) / attempted.length
    : 0

  return (
    <div style={{ padding: '1rem' }}>
      <div style={S.summary}>
        <div style={S.stat}>
          <span style={S.statNum}>{blueprints.length}</span>
          <span>Blueprint</span>
        </div>
        <div style={S.stat}>
          <span style={S.statNum}>{attempted.length}/{allCells.length}</span>
          <span>학습된 셀</span>
        </div>
        <div style={S.stat}>
          <span style={S.statNum}>{(avgMastery * 100).toFixed(0)}%</span>
          <span>학습 평균</span>
        </div>
      </div>

      {blueprints.map(bp => <BlueprintMatrix key={bp.blueprint_id} bp={bp} />)}
    </div>
  )
}

const S = {
  hint: { color: '#888', textAlign: 'center', paddingTop: '2rem' },
  summary: { display: 'flex', gap: '1rem', marginBottom: '1.5rem', justifyContent: 'center' },
  stat: { textAlign: 'center', background: '#f7fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: '0.75rem 1.5rem', display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12, color: '#666' },
  statNum: { fontSize: 22, fontWeight: 'bold', color: '#2d3748' },
  bpCard: { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 10, marginBottom: 16, overflow: 'hidden' },
  bpHeader: { display: 'flex', alignItems: 'center', padding: '12px 16px', cursor: 'pointer', borderBottom: '1px solid #f0f4f8' },
  bpTitle: { fontSize: 15, fontWeight: 600, color: '#2d3748', marginRight: 10 },
  bpDesc: { fontSize: 12, color: '#a0aec0' },
  matrixWrap: { display: 'flex', gap: 0, padding: '16px', borderBottom: '1px solid #f0f4f8', overflowX: 'auto' },
  layerCol: { flex: 1, minWidth: 120, borderRadius: 6, overflow: 'hidden', margin: '0 6px', border: '1px solid #e2e8f0' },
  layerLabel: { textAlign: 'center', fontWeight: 600, fontSize: 13, padding: '8px 4px' },
  stageRow: { display: 'flex', justifyContent: 'center', gap: 8, padding: '12px 8px', flexWrap: 'wrap' },
  legend: { display: 'flex', gap: 16, padding: '8px 16px', background: '#fafafa', justifyContent: 'flex-end', borderBottom: '1px solid #f0f4f8' },
  stageDescSection: { padding: '16px' },
  stageDescTitle: { fontSize: 13, fontWeight: 600, color: '#4a5568', marginBottom: 10 },
  stageDescGrid: { display: 'flex', gap: 12 },
  stageDescCol: { flex: 1, paddingTop: 8 },
  stageDescLayerLabel: { fontSize: 12, fontWeight: 600, marginBottom: 8 },
  stageDescRow: { display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 },
  stageDescBadge: { fontSize: 11, padding: '2px 8px', borderRadius: 10, fontWeight: 500, whiteSpace: 'nowrap' },
  stageDescText: { fontSize: 11, color: '#a0aec0', flex: 1 },
}
