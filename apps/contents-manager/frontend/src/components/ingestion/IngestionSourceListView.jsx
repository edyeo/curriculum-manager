import React, { useCallback, useEffect, useState } from 'react'
import * as api from '../../services/contentsApi.js'

const STATUS_STYLE = {
  saved:     { bg: '#1c1917', color: '#78716c', label: 'saved' },
  pending:   { bg: '#1c1917', color: '#fbbf24', label: 'pending' },
  approved:  { bg: '#052e16', color: '#4ade80', label: 'approved' },
  rejected:  { bg: '#2d1515', color: '#f87171', label: 'rejected' },
}

const TYPE_COLOR = {
  System: '#c084fc', Seed: '#fbbf24', Concept: '#7dd3fc', TechStack: '#6ee7b7',
}

function StatusBadge({ status }) {
  const s = STATUS_STYLE[status] || STATUS_STYLE.saved
  return (
    <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600, background: s.bg, color: s.color }}>
      {s.label}
    </span>
  )
}

function DryRunResult({ result }) {
  if (!result) return null
  const newNodes = result.nodes.filter(n => !n.db_exists)
  const dupNodes = result.nodes.filter(n => n.db_exists)
  const newEdges = result.edges.filter(e => !e.db_exists)
  const dupEdges = result.edges.filter(e => e.db_exists)

  return (
    <div style={{ marginTop: 16, borderTop: '1px solid #1f2937', paddingTop: 16 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8', marginBottom: 12 }}>Dry-run 결과</div>

      {/* 요약 */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 14, flexWrap: 'wrap' }}>
        {[
          { label: '신규 노드', val: newNodes.length, color: '#4ade80' },
          { label: '중복 노드', val: dupNodes.length, color: '#78716c' },
          { label: '신규 엣지', val: newEdges.length, color: '#a78bfa' },
          { label: '중복 엣지', val: dupEdges.length, color: '#4b5563' },
        ].map(({ label, val, color }) => (
          <div key={label} style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 6, padding: '8px 12px', minWidth: 70 }}>
            <div style={{ fontSize: 18, fontWeight: 700, color }}>{val}</div>
            <div style={{ fontSize: 10, color: '#4b5563', marginTop: 2 }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Entity 테이블 */}
      {result.nodes.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6 }}>Entity</div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #1f2937', color: '#4b5563' }}>
                <th style={{ textAlign: 'left', padding: '4px 8px', fontWeight: 500 }}>이름</th>
                <th style={{ textAlign: 'left', padding: '4px 8px', fontWeight: 500 }}>타입</th>
                <th style={{ textAlign: 'center', padding: '4px 8px', fontWeight: 500 }}>D</th>
                <th style={{ textAlign: 'left', padding: '4px 8px', fontWeight: 500 }}>DB존재</th>
              </tr>
            </thead>
            <tbody>
              {result.nodes.map((n, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #0d1117' }}>
                  <td style={{ padding: '5px 8px', color: '#e2e8f0' }}>{n.name}</td>
                  <td style={{ padding: '5px 8px' }}>
                    <span style={{ fontSize: 10, color: TYPE_COLOR[n.type] || '#94a3b8' }}>{n.type}</span>
                  </td>
                  <td style={{ padding: '5px 8px', textAlign: 'center', color: '#64748b' }}>{n.depth}</td>
                  <td style={{ padding: '5px 8px' }}>
                    {n.db_exists
                      ? <span style={{ color: '#78716c', fontSize: 10 }}>✓ 존재</span>
                      : <span style={{ color: '#4ade80', fontSize: 10 }}>✗ 신규</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Link 테이블 */}
      {result.edges.length > 0 && (
        <div>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6 }}>Link</div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #1f2937', color: '#4b5563' }}>
                <th style={{ textAlign: 'left', padding: '4px 8px', fontWeight: 500 }}>소스</th>
                <th style={{ textAlign: 'left', padding: '4px 8px', fontWeight: 500 }}>관계</th>
                <th style={{ textAlign: 'left', padding: '4px 8px', fontWeight: 500 }}>타겟</th>
                <th style={{ textAlign: 'left', padding: '4px 8px', fontWeight: 500 }}>DB존재</th>
              </tr>
            </thead>
            <tbody>
              {result.edges.map((e, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #0d1117' }}>
                  <td style={{ padding: '5px 8px', color: '#e2e8f0' }}>{e.source_name}</td>
                  <td style={{ padding: '5px 8px' }}>
                    <span style={{ fontSize: 10, background: '#0f172a', color: '#38bdf8', padding: '1px 5px', borderRadius: 3, fontFamily: 'monospace' }}>
                      {e.relation}
                    </span>
                  </td>
                  <td style={{ padding: '5px 8px', color: '#e2e8f0' }}>{e.target_name}</td>
                  <td style={{ padding: '5px 8px' }}>
                    {e.db_exists
                      ? <span style={{ color: '#78716c', fontSize: 10 }}>✓ 존재</span>
                      : <span style={{ color: '#a78bfa', fontSize: 10 }}>✗ 신규</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {result.extraction_notes && (
        <div style={{ marginTop: 10, padding: '8px 10px', background: '#0f172a', borderRadius: 5, fontSize: 11, color: '#64748b', lineHeight: 1.5 }}>
          {result.extraction_notes}
        </div>
      )}
    </div>
  )
}

export default function IngestionSourceListView({ onParsed }) {
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [dryRunResult, setDryRunResult] = useState(null)
  const [dryRunning, setDryRunning] = useState(false)
  const [parsing, setParsing] = useState(false)
  const [actionMsg, setActionMsg] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const d = await api.listIngestionSources()
      setSources(d.sources || [])
    } catch { /* silent */ } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const handleSelect = (id) => {
    if (selectedId === id) { setSelectedId(null); setDryRunResult(null); setActionMsg('') }
    else { setSelectedId(id); setDryRunResult(null); setActionMsg('') }
  }

  const handleDryRun = async () => {
    if (!selectedId) return
    setDryRunning(true); setDryRunResult(null); setActionMsg('')
    try {
      const r = await api.dryRunIngestionSource(selectedId)
      setDryRunResult(r)
    } catch (e) {
      setActionMsg(`Dry-run 실패: ${e.message}`)
    } finally { setDryRunning(false) }
  }

  const handleParse = async () => {
    if (!selectedId) return
    setParsing(true); setActionMsg('')
    try {
      const r = await api.parseIngestionSource(selectedId)
      setActionMsg(`파싱 등록 완료 — 노드 ${r.extracted_nodes}개, 엣지 ${r.extracted_edges}개`)
      await load()
      onParsed?.()
    } catch (e) {
      setActionMsg(`파싱 실패: ${e.message}`)
    } finally { setParsing(false) }
  }

  const selected = sources.find(s => s.id === selectedId)

  const fmtDate = (iso) => {
    if (!iso) return '-'
    const d = new Date(iso)
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
  }

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>

      {/* 소스 목록 */}
      <div style={{ flex: 1, padding: 20, overflowY: 'auto', borderRight: '1px solid #1f2937' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>Source 목록</div>
          <button onClick={load} disabled={loading}
            style={{ background: 'none', border: 'none', color: '#6366f1', fontSize: 11, cursor: 'pointer' }}>
            {loading ? '...' : '새로고침'}
          </button>
        </div>

        {sources.length === 0 && !loading && (
          <div style={{ fontSize: 12, color: '#374151', textAlign: 'center', marginTop: 40 }}>
            등록된 소스가 없습니다
          </div>
        )}

        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          {sources.length > 0 && (
            <thead>
              <tr style={{ borderBottom: '1px solid #1f2937', color: '#4b5563' }}>
                <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 500 }}>생성일시</th>
                <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 500 }}>타입</th>
                <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 500 }}>소스</th>
                <th style={{ textAlign: 'center', padding: '6px 8px', fontWeight: 500 }}>노드</th>
                <th style={{ textAlign: 'center', padding: '6px 8px', fontWeight: 500 }}>엣지</th>
                <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 500 }}>상태</th>
              </tr>
            </thead>
          )}
          <tbody>
            {sources.map(s => (
              <tr
                key={s.id}
                onClick={() => handleSelect(s.id)}
                style={{
                  borderBottom: '1px solid #111827', cursor: 'pointer',
                  background: selectedId === s.id ? '#1a1d3a' : 'transparent',
                  transition: 'background 0.1s',
                }}
              >
                <td style={{ padding: '8px 8px', color: '#64748b', whiteSpace: 'nowrap' }}>{fmtDate(s.created_at)}</td>
                <td style={{ padding: '8px 8px' }}>
                  <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 3, background: '#0c1a2e', color: '#7dd3fc' }}>{s.source_type}</span>
                </td>
                <td style={{ padding: '8px 8px', color: '#94a3b8', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {s.source_summary}
                </td>
                <td style={{ padding: '8px 8px', textAlign: 'center', color: '#7dd3fc' }}>{s.extracted_node_count || '-'}</td>
                <td style={{ padding: '8px 8px', textAlign: 'center', color: '#a78bfa' }}>{s.extracted_edge_count || '-'}</td>
                <td style={{ padding: '8px 8px' }}><StatusBadge status={s.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 액션 패널 (선택 시) */}
      {selectedId && (
        <div style={{ width: 400, padding: 20, overflowY: 'auto', background: '#0d1117' }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4 }}>선택된 소스</div>
          <div style={{ fontSize: 12, color: '#e2e8f0', marginBottom: 4, wordBreak: 'break-all' }}>
            {selected?.source_summary}
          </div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 16 }}>
            <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 3, background: '#0c1a2e', color: '#7dd3fc' }}>
              {selected?.source_type}
            </span>
            <StatusBadge status={selected?.status} />
          </div>

          {/* 액션 버튼 */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <button
              onClick={handleDryRun}
              disabled={dryRunning || parsing}
              style={{
                flex: 1, padding: '8px', borderRadius: 5, fontSize: 12, fontWeight: 600, border: '1px solid #1f2937',
                background: dryRunning ? '#1e2130' : '#111827',
                color: dryRunning ? '#4b5563' : '#94a3b8',
                cursor: (dryRunning || parsing) ? 'default' : 'pointer',
              }}
            >
              {dryRunning ? 'Dry-run 중...' : 'Dry-run'}
            </button>
            <button
              onClick={handleParse}
              disabled={parsing || dryRunning || !['saved', 'rejected'].includes(selected?.status)}
              style={{
                flex: 1, padding: '8px', borderRadius: 5, fontSize: 12, fontWeight: 600, border: 'none',
                background: (parsing || !['saved', 'rejected'].includes(selected?.status)) ? '#374151' : '#4f46e5',
                color: (parsing || !['saved', 'rejected'].includes(selected?.status)) ? '#6b7280' : '#fff',
                cursor: (parsing || dryRunning || !['saved', 'rejected'].includes(selected?.status)) ? 'default' : 'pointer',
              }}
            >
              {parsing ? '파싱 중...' : '파싱 등록'}
            </button>
          </div>

          {actionMsg && (
            <div style={{
              marginBottom: 12, padding: '7px 10px', borderRadius: 5, fontSize: 11,
              background: actionMsg.startsWith('파싱 등록 완료') ? '#052e16' : '#3b0764',
              color: actionMsg.startsWith('파싱 등록 완료') ? '#4ade80' : '#e879f9',
            }}>
              {actionMsg}
            </div>
          )}

          <DryRunResult result={dryRunResult} />
        </div>
      )}
    </div>
  )
}
