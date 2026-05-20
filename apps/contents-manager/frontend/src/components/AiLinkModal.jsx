import React, { useState } from 'react'

const TYPES = ['Seed', 'Concept', 'TechStack', 'System']
const DEPTHS = [1, 2, 3]
const EDGE_TYPES = ['has_subtopic', 'requires', 'implemented_by', 'relied_on']

export default function AiLinkModal({ nodes, onPreview, onConfirm, onClose }) {
  const [phase, setPhase] = useState('form')  // 'form' | 'review'
  const [mode, setMode] = useState('all')

  // 모드 1
  const [sourceType, setSourceType] = useState('Seed')
  const [sourceDepth, setSourceDepth] = useState(1)

  // 모드 2
  const [sourceNodeId, setSourceNodeId] = useState('')

  // 공통
  const [targetType, setTargetType] = useState('Concept')
  const [targetDepth, setTargetDepth] = useState(1)
  const [edgeType, setEdgeType] = useState('requires')

  const [loading, setLoading] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState(null)

  // review 단계
  const [candidateEdges, setCandidateEdges] = useState([])
  const [selected, setSelected] = useState(new Set())

  const canSubmit = mode === 'all' || (mode === 'node' && sourceNodeId)

  const handlePreview = async () => {
    setLoading(true)
    setError(null)
    try {
      const payload = mode === 'node'
        ? { source_node_id: sourceNodeId, target_type: targetType, target_depth: targetDepth, edge_type: edgeType }
        : { source_type: sourceType, source_depth: sourceDepth, target_type: targetType, target_depth: targetDepth, edge_type: edgeType }
      const res = await onPreview(payload)
      const edges = res.edges || []
      setCandidateEdges(edges)
      setSelected(new Set(edges.map(e => e.id)))
      setPhase('review')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const toggleAll = () => {
    if (selected.size === candidateEdges.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(candidateEdges.map(e => e.id)))
    }
  }

  const toggleOne = (id) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const handleConfirm = async () => {
    const toSave = candidateEdges.filter(e => selected.has(e.id))
    if (toSave.length === 0) return
    setConfirming(true)
    setError(null)
    try {
      await onConfirm(toSave)
      onClose()
    } catch (e) {
      setError(e.message)
    } finally {
      setConfirming(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-box" style={{ minWidth: phase === 'review' ? 760 : 420, maxWidth: '90vw' }}>
        <h2>{phase === 'form' ? 'link 추가 (AI)' : 'AI Link 검토'}</h2>

        {/* ── form 단계 ── */}
        {phase === 'form' && (
          <>
            <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
              {[['all', '전체 node 기준'], ['node', '특정 node 기준']].map(([val, label]) => (
                <button
                  key={val}
                  onClick={() => { setMode(val); setError(null) }}
                  style={{
                    flex: 1, padding: '7px 0', borderRadius: 6, border: 'none', cursor: 'pointer',
                    background: mode === val ? '#3b82f6' : '#1e2d3d',
                    color: mode === val ? '#fff' : '#64748b',
                    fontWeight: mode === val ? 600 : 400,
                    fontSize: 13,
                  }}
                >
                  {label}
                </button>
              ))}
            </div>

            <label>Source</label>
            {mode === 'all' ? (
              <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                <select value={sourceType} onChange={e => setSourceType(e.target.value)} style={{ flex: 1 }}>
                  {TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                <select value={sourceDepth} onChange={e => setSourceDepth(Number(e.target.value))} style={{ width: 100 }}>
                  {DEPTHS.map(d => <option key={d} value={d}>Depth {d}</option>)}
                </select>
              </div>
            ) : (
              <select
                value={sourceNodeId}
                onChange={e => setSourceNodeId(e.target.value)}
                style={{ width: '100%', marginBottom: 12 }}
              >
                <option value="">— 노드 선택 —</option>
                {nodes.map(n => (
                  <option key={n.id} value={n.id}>
                    [{n.type}·D{n.depth}] {n.name}
                  </option>
                ))}
              </select>
            )}

            <label>Target</label>
            <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
              <select value={targetType} onChange={e => setTargetType(e.target.value)} style={{ flex: 1 }}>
                {TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <select value={targetDepth} onChange={e => setTargetDepth(Number(e.target.value))} style={{ width: 100 }}>
                {DEPTHS.map(d => <option key={d} value={d}>Depth {d}</option>)}
              </select>
            </div>

            <label>Edge 타입</label>
            <select value={edgeType} onChange={e => setEdgeType(e.target.value)} style={{ width: '100%', marginBottom: 20 }}>
              {EDGE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>

            {error && <p style={{ color: '#f87171', fontSize: 13, marginBottom: 12 }}>❌ {error}</p>}

            <div className="modal-actions">
              <button className="btn-cancel" onClick={onClose}>취소</button>
              <button className="btn-primary" onClick={handlePreview} disabled={loading || !canSubmit}>
                {loading ? 'AI Link 생성 중...' : 'AI Link 생성'}
              </button>
            </div>
          </>
        )}

        {/* ── review 단계 ── */}
        {phase === 'review' && (
          <>
            {candidateEdges.length === 0 ? (
              <p style={{ color: '#64748b', fontSize: 14, padding: '24px 0', textAlign: 'center' }}>
                생성된 엣지가 없습니다.
              </p>
            ) : (
              <div style={{ overflowX: 'auto', marginBottom: 16 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #2d3748' }}>
                      <th style={{ width: 32, padding: '8px 4px', textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          checked={selected.size === candidateEdges.length && candidateEdges.length > 0}
                          onChange={toggleAll}
                        />
                      </th>
                      <th style={{ padding: '8px', textAlign: 'left', color: '#94a3b8' }}>Source</th>
                      <th style={{ padding: '8px', textAlign: 'left', color: '#94a3b8', width: 130 }}>Edge 타입</th>
                      <th style={{ padding: '8px', textAlign: 'left', color: '#94a3b8' }}>Target</th>
                      <th style={{ padding: '8px', textAlign: 'left', color: '#94a3b8' }}>근거</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidateEdges.map(e => (
                      <tr
                        key={e.id}
                        onClick={() => toggleOne(e.id)}
                        style={{
                          borderBottom: '1px solid #1e2d3d',
                          cursor: 'pointer',
                          background: selected.has(e.id) ? 'rgba(59,130,246,0.08)' : 'transparent',
                        }}
                      >
                        <td style={{ padding: '8px 4px', textAlign: 'center' }}>
                          <input
                            type="checkbox"
                            checked={selected.has(e.id)}
                            onChange={() => toggleOne(e.id)}
                            onClick={ev => ev.stopPropagation()}
                          />
                        </td>
                        <td style={{ padding: '8px', color: '#e2e8f0' }}>
                          <span style={{ fontSize: 11, color: '#64748b' }}>[{e.source_type}·D{e.source_depth}]</span><br />
                          {e.source_name}
                        </td>
                        <td style={{ padding: '8px' }}>
                          <span style={{ background: '#1e3a5f', color: '#60a5fa', fontSize: 11, padding: '2px 6px', borderRadius: 4 }}>
                            {e.relation_type}
                          </span>
                        </td>
                        <td style={{ padding: '8px', color: '#e2e8f0' }}>
                          <span style={{ fontSize: 11, color: '#64748b' }}>[{e.target_type}·D{e.target_depth}]</span><br />
                          {e.target_name}
                        </td>
                        <td style={{ padding: '8px', color: '#94a3b8', fontSize: 12, maxWidth: 200 }}>
                          <span title={e.logic_basis} style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                            {e.logic_basis}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {error && <p style={{ color: '#f87171', fontSize: 13, marginBottom: 12 }}>❌ {error}</p>}

            <div className="modal-actions">
              <button className="btn-cancel" onClick={onClose}>취소</button>
              {candidateEdges.length > 0 && (
                <button
                  className="btn-primary"
                  onClick={handleConfirm}
                  disabled={confirming || selected.size === 0}
                >
                  {confirming ? '저장 중...' : `${selected.size}개 엣지 승인`}
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
