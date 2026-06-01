import React, { useCallback, useEffect, useState } from 'react'
import * as api from '../../services/contentsApi.js'

const TYPE_COLOR = {
  System: { color: '#c084fc', bg: '#1a1228' },
  Seed: { color: '#fbbf24', bg: '#451a03' },
  Concept: { color: '#7dd3fc', bg: '#0c1a2e' },
  TechStack: { color: '#6ee7b7', bg: '#052e16' },
}

function ExistBadge({ exists }) {
  return exists
    ? <span style={{ fontSize: 10, color: '#78716c' }}>✓ 존재</span>
    : <span style={{ fontSize: 10, color: '#4ade80' }}>✗ 신규</span>
}

function TypeBadge({ type }) {
  const s = TYPE_COLOR[type] || { color: '#94a3b8', bg: '#1e2130' }
  return (
    <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 3, background: s.bg, color: s.color, fontWeight: 600 }}>
      {type}
    </span>
  )
}

export default function IngestionAuditView() {
  const [sources, setSources] = useState([])
  const [sessionId, setSessionId] = useState('')
  const [nodes, setNodes] = useState([])
  const [edges, setEdges] = useState([])
  const [loading, setLoading] = useState(false)
  const [approving, setApproving] = useState(false)
  const [rejecting, setRejecting] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    api.listIngestionSources()
      .then(d => setSources((d.sources || []).filter(s => s.status === 'pending')))
      .catch(() => {})
  }, [])

  const loadAudit = useCallback(async (sid) => {
    setLoading(true); setMsg('')
    try {
      const d = await api.getIngestionAudit(sid || null)
      setNodes(d.nodes || [])
      setEdges(d.edges || [])
    } catch { /* silent */ } finally { setLoading(false) }
  }, [])

  const handleSessionChange = (sid) => {
    setSessionId(sid)
    setNodes([]); setEdges([])
    if (sid) loadAudit(sid)
  }

  const handleApprove = async () => {
    if (!sessionId) return
    if (!window.confirm('선택된 소스를 KG에 반영합니다. 계속하시겠습니까?')) return
    setApproving(true); setMsg('')
    try {
      const r = await api.approveIngestionSource(sessionId)
      setMsg(`승인 완료 — 노드 ${r.added_nodes}개, 엣지 ${r.added_edges}개 추가됨`)
      setSources(prev => prev.filter(s => s.id !== sessionId))
      setSessionId(''); setNodes([]); setEdges([])
    } catch (e) {
      setMsg(`승인 실패: ${e.message}`)
    } finally { setApproving(false) }
  }

  const handleReject = async () => {
    if (!sessionId) return
    if (!window.confirm('선택된 소스를 거부합니다. 계속하시겠습니까?')) return
    setRejecting(true); setMsg('')
    try {
      await api.rejectIngestionSource(sessionId)
      setMsg('거부 처리 완료')
      setSources(prev => prev.filter(s => s.id !== sessionId))
      setSessionId(''); setNodes([]); setEdges([])
    } catch (e) {
      setMsg(`거부 실패: ${e.message}`)
    } finally { setRejecting(false) }
  }

  const newNodes = nodes.filter(n => !n.db_exists)
  const dupNodes = nodes.filter(n => n.db_exists)
  const newEdges = edges.filter(e => !e.db_exists)
  const dupEdges = edges.filter(e => e.db_exists)

  return (
    <div style={{ padding: 20, overflowY: 'auto', height: '100%', boxSizing: 'border-box' }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0', marginBottom: 16 }}>Audit</div>

      {/* Source 필터 */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6 }}>소스 선택 (pending 상태만 표시)</div>
        <select
          value={sessionId}
          onChange={e => handleSessionChange(e.target.value)}
          style={{ width: '100%', maxWidth: 480, fontSize: 12, background: '#1a1d2e', color: sessionId ? '#e2e8f0' : '#4b5563' }}
        >
          <option value="">-- 소스를 선택하세요 --</option>
          {sources.map(s => (
            <option key={s.id} value={s.id}>
              {s.source_summary?.slice(0, 60)} ({s.source_type}) — 노드 {s.extracted_node_count}, 엣지 {s.extracted_edge_count}
            </option>
          ))}
        </select>
        {sources.length === 0 && (
          <div style={{ fontSize: 11, color: '#374151', marginTop: 6 }}>
            파싱 등록된 소스가 없습니다. Source &gt; 조회에서 파싱 등록을 진행하세요.
          </div>
        )}
      </div>

      {loading && <div style={{ fontSize: 12, color: '#4b5563' }}>로딩 중...</div>}

      {sessionId && !loading && (
        <>
          {/* 요약 카드 */}
          <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
            {[
              { label: '신규 노드', val: newNodes.length, color: '#4ade80' },
              { label: '중복 노드', val: dupNodes.length, color: '#78716c' },
              { label: '신규 엣지', val: newEdges.length, color: '#a78bfa' },
              { label: '중복 엣지', val: dupEdges.length, color: '#4b5563' },
            ].map(({ label, val, color }) => (
              <div key={label} style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 8, padding: '10px 14px', minWidth: 80 }}>
                <div style={{ fontSize: 20, fontWeight: 700, color }}>{val}</div>
                <div style={{ fontSize: 10, color: '#4b5563', marginTop: 2 }}>{label}</div>
              </div>
            ))}
          </div>

          {/* Entity 테이블 */}
          {nodes.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8', marginBottom: 8 }}>Entity ({nodes.length})</div>
              <div style={{ background: '#111827', borderRadius: 8, border: '1px solid #1f2937', overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #1f2937', background: '#0d1117' }}>
                      {['이름', '타입', 'D', '설명', 'DB존재'].map(h => (
                        <th key={h} style={{ textAlign: 'left', padding: '8px 10px', fontWeight: 500, color: '#4b5563', fontSize: 11 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {nodes.map((n, i) => (
                      <tr key={n.id || i} style={{ borderBottom: '1px solid #0d1117', background: n.db_exists ? 'transparent' : '#050d14' }}>
                        <td style={{ padding: '7px 10px', color: '#e2e8f0', fontWeight: 500 }}>{n.name}</td>
                        <td style={{ padding: '7px 10px' }}><TypeBadge type={n.type} /></td>
                        <td style={{ padding: '7px 10px', color: '#64748b', textAlign: 'center' }}>{n.depth}</td>
                        <td style={{ padding: '7px 10px', color: '#64748b', maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {n.description}
                        </td>
                        <td style={{ padding: '7px 10px' }}><ExistBadge exists={n.db_exists} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Link 테이블 */}
          {edges.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8', marginBottom: 8 }}>Link ({edges.length})</div>
              <div style={{ background: '#111827', borderRadius: 8, border: '1px solid #1f2937', overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #1f2937', background: '#0d1117' }}>
                      {['소스', '관계', '타겟', 'DB존재'].map(h => (
                        <th key={h} style={{ textAlign: 'left', padding: '8px 10px', fontWeight: 500, color: '#4b5563', fontSize: 11 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {edges.map((e, i) => (
                      <tr key={e.id || i} style={{ borderBottom: '1px solid #0d1117', background: e.db_exists ? 'transparent' : '#050d14' }}>
                        <td style={{ padding: '7px 10px', color: '#e2e8f0' }}>{e.source_name}</td>
                        <td style={{ padding: '7px 10px' }}>
                          <span style={{ fontSize: 10, background: '#0f172a', color: '#38bdf8', padding: '1px 6px', borderRadius: 3, fontFamily: 'monospace' }}>
                            {e.relation}
                          </span>
                        </td>
                        <td style={{ padding: '7px 10px', color: '#e2e8f0' }}>{e.target_name}</td>
                        <td style={{ padding: '7px 10px' }}><ExistBadge exists={e.db_exists} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 승인/거부 버튼 */}
          <div style={{ display: 'flex', gap: 10, paddingTop: 8 }}>
            <button
              onClick={handleReject}
              disabled={rejecting || approving}
              style={{
                padding: '9px 20px', borderRadius: 6, fontSize: 13, fontWeight: 600,
                background: rejecting ? '#374151' : '#1c1917',
                color: rejecting ? '#6b7280' : '#a8a29e',
                border: '1px solid #292524', cursor: (rejecting || approving) ? 'default' : 'pointer',
              }}
            >
              {rejecting ? '처리 중...' : '거부'}
            </button>
            <button
              onClick={handleApprove}
              disabled={approving || rejecting}
              style={{
                flex: 1, padding: '9px', borderRadius: 6, fontSize: 13, fontWeight: 600,
                background: approving ? '#374151' : '#166534',
                color: approving ? '#6b7280' : '#4ade80',
                border: '1px solid #15803d', cursor: (approving || rejecting) ? 'default' : 'pointer',
              }}
            >
              {approving ? '처리 중...' : 'KG에 승인 반영'}
            </button>
          </div>

          {msg && (
            <div style={{
              marginTop: 10, padding: '8px 12px', borderRadius: 6, fontSize: 12,
              background: msg.includes('완료') ? '#052e16' : '#3b0764',
              color: msg.includes('완료') ? '#4ade80' : '#e879f9',
            }}>
              {msg}
            </div>
          )}
        </>
      )}
    </div>
  )
}
