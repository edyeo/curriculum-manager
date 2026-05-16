import React, { useState } from 'react'

const TYPES = ['Seed', 'Concept', 'TechStack', 'System']
const DEPTHS = [1, 2, 3]
const EDGE_TYPES = ['has_subtopic', 'requires', 'implemented_by', 'relied_on']

export default function AiLinkModal({ nodes, onConfirm, onClose }) {
  const [mode, setMode] = useState('all')  // 'all' | 'node'

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
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const canSubmit = mode === 'all' || (mode === 'node' && sourceNodeId)

  const handleSubmit = async () => {
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const payload = mode === 'node'
        ? { source_node_id: sourceNodeId, target_type: targetType, target_depth: targetDepth, edge_type: edgeType }
        : { source_type: sourceType, source_depth: sourceDepth, target_type: targetType, target_depth: targetDepth, edge_type: edgeType }
      const res = await onConfirm(payload)
      setResult(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-box" style={{ minWidth: 420 }}>
        <h2>link 추가 (AI)</h2>

        {/* 모드 토글 */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          {[['all', '전체 node 기준'], ['node', '특정 node 기준']].map(([val, label]) => (
            <button
              key={val}
              onClick={() => { setMode(val); setResult(null); setError(null) }}
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

        {/* Source */}
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

        {/* Target */}
        <label>Target</label>
        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          <select value={targetType} onChange={e => setTargetType(e.target.value)} style={{ flex: 1 }}>
            {TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <select value={targetDepth} onChange={e => setTargetDepth(Number(e.target.value))} style={{ width: 100 }}>
            {DEPTHS.map(d => <option key={d} value={d}>Depth {d}</option>)}
          </select>
        </div>

        {/* Edge 타입 */}
        <label>Edge 타입</label>
        <select value={edgeType} onChange={e => setEdgeType(e.target.value)} style={{ width: '100%', marginBottom: 20 }}>
          {EDGE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>

        {/* 결과 / 에러 */}
        {result && (
          <p style={{ color: '#22c55e', fontSize: 13, marginBottom: 12 }}>
            ✅ {result.edges_added ?? 0}개 엣지 추가됨
          </p>
        )}
        {error && (
          <p style={{ color: '#f87171', fontSize: 13, marginBottom: 12 }}>
            ❌ {error}
          </p>
        )}

        <div className="modal-actions">
          <button className="btn-cancel" onClick={onClose}>취소</button>
          <button
            className="btn-primary"
            onClick={handleSubmit}
            disabled={loading || !canSubmit}
          >
            {loading ? 'AI Link 생성 중...' : 'AI Link 생성'}
          </button>
        </div>
      </div>
    </div>
  )
}
