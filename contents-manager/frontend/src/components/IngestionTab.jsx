import React, { useState, useEffect, useCallback } from 'react'
import * as api from '../services/contentsApi.js'

const TYPE_COLOR = {
  System:    { bg: '#1a1228', color: '#c084fc', border: '#a855f7' },
  Seed:      { bg: '#451a03', color: '#fbbf24', border: '#f59e0b' },
  Concept:   { bg: '#0c1a2e', color: '#7dd3fc', border: '#38bdf8' },
  TechStack: { bg: '#052e16', color: '#6ee7b7', border: '#34d399' },
}

function NodeBadge({ type, name, depth }) {
  const s = TYPE_COLOR[type] || { bg: '#1e2130', color: '#94a3b8', border: '#4a5568' }
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
      background: s.bg, color: s.color, borderLeft: `3px solid ${s.border}`,
    }}>
      {name}
      <span style={{ opacity: 0.6, fontWeight: 400 }}>D{depth}</span>
    </span>
  )
}

function DecisionBadge({ decision }) {
  const isAdd = decision === 'add'
  return (
    <span style={{
      padding: '1px 7px', borderRadius: 4, fontSize: 11, fontWeight: 600,
      background: isAdd ? '#052e16' : '#1c1917',
      color: isAdd ? '#4ade80' : '#78716c',
    }}>
      {isAdd ? '+ 추가' : '— 중복'}
    </span>
  )
}

function SummaryBar({ result }) {
  const items = [
    { label: '추출', value: result.extracted_nodes, sub: `노드 / ${result.extracted_edges} 엣지`, color: '#7dd3fc' },
    { label: '중복 skip', value: result.skipped_nodes, sub: `노드 / ${result.skipped_edges} 엣지`, color: '#fb923c' },
    { label: result.dry_run ? '추가 예정' : '반영 완료', value: result.added_nodes, sub: `노드 / ${result.added_edges} 엣지`, color: '#4ade80' },
  ]
  return (
    <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
      {items.map(({ label, value, sub, color }) => (
        <div key={label} style={{
          flex: 1, background: '#111827', border: '1px solid #1f2937',
          borderRadius: 8, padding: '12px 16px',
        }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4 }}>{label}</div>
          <div style={{ fontSize: 22, fontWeight: 700, color }}>{value}</div>
          <div style={{ fontSize: 11, color: '#4b5563', marginTop: 2 }}>{sub}</div>
        </div>
      ))}
    </div>
  )
}

function DedupTable({ nodes, edges }) {
  if (!nodes?.length && !edges?.length) return null
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {nodes?.length > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #1f2937', color: '#4b5563' }}>
              <th style={{ textAlign: 'left', padding: '4px 8px', fontWeight: 500 }}>노드</th>
              <th style={{ textAlign: 'left', padding: '4px 8px', fontWeight: 500 }}>타입</th>
              <th style={{ textAlign: 'left', padding: '4px 8px', fontWeight: 500 }}>결정</th>
            </tr>
          </thead>
          <tbody>
            {nodes.map((n, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #111827' }}>
                <td style={{ padding: '6px 8px', color: '#e2e8f0' }}>{n.name}</td>
                <td style={{ padding: '6px 8px' }}>
                  {n.type && <NodeBadge type={n.type} name={n.type} depth="" />}
                </td>
                <td style={{ padding: '6px 8px' }}><DecisionBadge decision={n.decision} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {edges?.length > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #1f2937', color: '#4b5563' }}>
              <th style={{ textAlign: 'left', padding: '4px 8px', fontWeight: 500 }}>소스</th>
              <th style={{ textAlign: 'left', padding: '4px 8px', fontWeight: 500 }}>관계</th>
              <th style={{ textAlign: 'left', padding: '4px 8px', fontWeight: 500 }}>타겟</th>
              <th style={{ textAlign: 'left', padding: '4px 8px', fontWeight: 500 }}>결정</th>
            </tr>
          </thead>
          <tbody>
            {edges.map((e, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #111827' }}>
                <td style={{ padding: '6px 8px', color: '#e2e8f0' }}>{e.source_name}</td>
                <td style={{ padding: '6px 8px' }}>
                  <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 3, background: '#0f172a', color: '#38bdf8', fontFamily: 'monospace' }}>
                    {e.relation}
                  </span>
                </td>
                <td style={{ padding: '6px 8px', color: '#e2e8f0' }}>{e.target_name}</td>
                <td style={{ padding: '6px 8px' }}><DecisionBadge decision={e.decision} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function ResultPanel({ result, detail }) {
  const [showNotes, setShowNotes] = useState(false)
  if (!result) return null

  const dedupNodes = detail?.dedup_report?.nodes || []
  const addedNodes = detail?.applied_diff?.added_nodes || []
  const addedEdges = detail?.applied_diff?.added_edges || []

  return (
    <div style={{ marginTop: 20 }}>
      {result.dry_run && (
        <div style={{
          marginBottom: 12, padding: '8px 14px', borderRadius: 6,
          background: '#1c1917', border: '1px solid #292524', color: '#a8a29e', fontSize: 12,
        }}>
          Dry-run 모드 — KG에 반영되지 않았습니다.
        </div>
      )}

      <SummaryBar result={result} />

      {result.extraction_notes && (
        <div style={{ marginBottom: 16 }}>
          <button
            onClick={() => setShowNotes(v => !v)}
            style={{ background: 'none', border: 'none', color: '#6366f1', fontSize: 12, cursor: 'pointer', padding: 0 }}
          >
            {showNotes ? '▾' : '▸'} LLM 추출 노트
          </button>
          {showNotes && (
            <div style={{
              marginTop: 6, padding: '10px 14px', background: '#0f172a',
              borderRadius: 6, fontSize: 12, color: '#94a3b8', lineHeight: 1.6,
            }}>
              {result.extraction_notes}
            </div>
          )}
        </div>
      )}

      {(dedupNodes.length > 0 || detail?.dedup_report?.edges?.length > 0) && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8 }}>중복 검사 결과</div>
          <DedupTable nodes={dedupNodes} edges={detail?.dedup_report?.edges} />
        </div>
      )}

      {!result.dry_run && (addedNodes.length > 0 || addedEdges.length > 0) && (
        <div>
          <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8 }}>반영된 항목</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {addedNodes.map(n => (
              <div key={n.id} style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '6px 10px', background: '#061911', borderRadius: 6, fontSize: 12,
              }}>
                <span style={{ color: '#4ade80', fontSize: 10 }}>●</span>
                <NodeBadge type={n.type} name={n.name} depth={n.depth} />
                <span style={{ color: '#6b7280', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {n.description}
                </span>
              </div>
            ))}
            {addedEdges.map(e => (
              <div key={e.id} style={{
                padding: '6px 10px', background: '#0a1628', borderRadius: 6, fontSize: 11, color: '#64748b',
              }}>
                <span style={{ color: '#38bdf8' }}>{e.relation_type}</span>
                <span style={{ margin: '0 6px' }}>·</span>
                <span style={{ fontFamily: 'monospace', fontSize: 10 }}>{e.source_id?.slice(0, 8)}… → {e.target_id?.slice(0, 8)}…</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function LogItem({ log, selected, onSelect }) {
  const ts = log.timestamp
  const date = `${ts.slice(0,4)}-${ts.slice(4,6)}-${ts.slice(6,8)} ${ts.slice(9,11)}:${ts.slice(11,13)}:${ts.slice(13,15)}`
  return (
    <div
      onClick={() => onSelect(log.timestamp)}
      style={{
        padding: '10px 14px', borderRadius: 6, cursor: 'pointer', marginBottom: 6,
        background: selected ? '#1e2130' : '#111827',
        border: `1px solid ${selected ? '#4f46e5' : '#1f2937'}`,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: '#64748b' }}>{date}</span>
        <div style={{ display: 'flex', gap: 6 }}>
          {log.dry_run && (
            <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 3, background: '#1c1917', color: '#78716c' }}>dry-run</span>
          )}
          <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 3, background: '#0c1a2e', color: '#7dd3fc' }}>
            {log.source_type}
          </span>
        </div>
      </div>
      <div style={{ fontSize: 12, color: '#94a3b8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {log.source_summary}
      </div>
      <div style={{ display: 'flex', gap: 12, marginTop: 6, fontSize: 11 }}>
        <span style={{ color: '#7dd3fc' }}>추출 {log.extracted_nodes}</span>
        <span style={{ color: '#fb923c' }}>skip {log.skipped_nodes}</span>
        <span style={{ color: '#4ade80' }}>추가 {log.added_nodes}</span>
      </div>
    </div>
  )
}

function SnapshotItem({ snap, selected, onSelect }) {
  const ts = snap.timestamp
  const date = `${ts.slice(0,4)}-${ts.slice(4,6)}-${ts.slice(6,8)} ${ts.slice(9,11)}:${ts.slice(11,13)}:${ts.slice(13,15)}`
  const triggerColor = snap.trigger === 'ROLLBACK' ? '#fb923c' : snap.trigger === 'INGESTION' ? '#4ade80' : '#7dd3fc'
  return (
    <div
      onClick={() => onSelect(snap.timestamp)}
      style={{
        padding: '10px 14px', borderRadius: 6, cursor: 'pointer', marginBottom: 6,
        background: selected ? '#1e2130' : '#111827',
        border: `1px solid ${selected ? '#4f46e5' : '#1f2937'}`,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: '#64748b' }}>{date}</span>
        <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 3, background: '#0d1117', color: triggerColor }}>
          {snap.trigger}
        </span>
      </div>
      <div style={{ display: 'flex', gap: 12, fontSize: 11 }}>
        <span style={{ color: '#7dd3fc' }}>노드 {snap.node_count}</span>
        <span style={{ color: '#a78bfa' }}>엣지 {snap.edge_count}</span>
        {snap.rolled_back_to && (
          <span style={{ color: '#78716c' }}>← {snap.rolled_back_to.slice(0, 15)}</span>
        )}
      </div>
    </div>
  )
}

function SnapshotDiffPanel({ diff, onRollback, rolling }) {
  if (!diff) return null
  const hasChanges = diff.added_nodes.length || diff.removed_nodes.length ||
                     diff.added_edges.length || diff.removed_edges.length

  return (
    <div style={{ marginTop: 12, padding: 12, background: '#111827', borderRadius: 8, border: '1px solid #1f2937' }}>
      <div style={{ fontSize: 11, color: '#64748b', marginBottom: 8 }}>현재 KG와의 차이</div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
        {[
          { label: '스냅샷 노드', val: diff.snapshot_node_count, color: '#7dd3fc' },
          { label: '현재 노드', val: diff.current_node_count, color: '#4ade80' },
          { label: '스냅샷 엣지', val: diff.snapshot_edge_count, color: '#a78bfa' },
          { label: '현재 엣지', val: diff.current_edge_count, color: '#c084fc' },
        ].map(({ label, val, color }) => (
          <div key={label} style={{ fontSize: 10, color: '#4b5563' }}>
            <span style={{ color, fontWeight: 600 }}>{val}</span> {label}
          </div>
        ))}
      </div>

      {!hasChanges && (
        <div style={{ fontSize: 11, color: '#374151', marginBottom: 8 }}>
          현재 KG와 동일합니다.
        </div>
      )}

      {diff.added_nodes.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <div style={{ fontSize: 10, color: '#4ade80', marginBottom: 4 }}>
            이후 추가된 노드 ({diff.added_nodes.length})
          </div>
          {diff.added_nodes.map(n => (
            <div key={n.id} style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 3 }}>
              <NodeBadge type={n.type} name={n.type} depth="" />
              <span style={{ fontSize: 11, color: '#6ee7b7' }}>{n.name}</span>
            </div>
          ))}
        </div>
      )}

      {diff.removed_nodes.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <div style={{ fontSize: 10, color: '#f87171', marginBottom: 4 }}>
            이후 삭제된 노드 ({diff.removed_nodes.length})
          </div>
          {diff.removed_nodes.map(n => (
            <div key={n.id} style={{ fontSize: 11, color: '#f87171', marginBottom: 3 }}>
              — {n.name} ({n.type})
            </div>
          ))}
        </div>
      )}

      {diff.added_edges.length > 0 && (
        <div style={{ marginBottom: 8, paddingTop: 8, borderTop: '1px solid #1f2937' }}>
          <div style={{ fontSize: 10, color: '#a78bfa', marginBottom: 4 }}>
            이후 추가된 엣지 ({diff.added_edges.length})
          </div>
          {diff.added_edges.map((e, i) => (
            <div key={i} style={{ fontSize: 10, color: '#7c3aed', marginBottom: 3, fontFamily: 'monospace' }}>
              {e.relation_type} · {e.source_id?.slice(0, 6)}→{e.target_id?.slice(0, 6)}
            </div>
          ))}
        </div>
      )}

      <button
        onClick={onRollback}
        disabled={rolling}
        style={{
          marginTop: 8, width: '100%', padding: '7px', borderRadius: 5, fontSize: 11, fontWeight: 600,
          background: rolling ? '#374151' : '#7f1d1d',
          color: rolling ? '#6b7280' : '#fca5a5',
          border: '1px solid #991b1b', cursor: rolling ? 'default' : 'pointer',
        }}
      >
        {rolling ? '롤백 중...' : '이 시점으로 KG 롤백'}
      </button>
    </div>
  )
}

function DropZone({ file, onFile }) {
  const [dragOver, setDragOver] = useState(false)

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) onFile(dropped)
  }

  const handleDragOver = (e) => { e.preventDefault(); setDragOver(true) }
  const handleDragLeave = () => setDragOver(false)

  const handleClick = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.pdf,.txt,.md'
    input.onchange = (e) => { if (e.target.files[0]) onFile(e.target.files[0]) }
    input.click()
  }

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={handleClick}
      style={{
        border: `2px dashed ${dragOver ? '#4f46e5' : '#1f2937'}`,
        borderRadius: 8,
        padding: '28px 16px',
        textAlign: 'center',
        cursor: 'pointer',
        background: dragOver ? '#1a1d3a' : '#111827',
        transition: 'border-color 0.15s, background 0.15s',
      }}
    >
      {file ? (
        <div>
          <div style={{ fontSize: 13, color: '#e2e8f0', marginBottom: 4 }}>{file.name}</div>
          <div style={{ fontSize: 11, color: '#4b5563' }}>{(file.size / 1024).toFixed(1)} KB · 클릭하여 변경</div>
        </div>
      ) : (
        <div>
          <div style={{ fontSize: 24, marginBottom: 8 }}>📄</div>
          <div style={{ fontSize: 13, color: '#4b5563' }}>파일을 여기에 드래그하거나 클릭하여 선택</div>
          <div style={{ fontSize: 11, color: '#374151', marginTop: 4 }}>PDF · TXT · MD</div>
        </div>
      )}
    </div>
  )
}

export default function IngestionTab() {
  const [sourceType, setSourceType] = useState('text')
  const [source, setSource]         = useState('')
  const [dropFile, setDropFile]     = useState(null)
  const [dryRun, setDryRun]         = useState(true)
  const [subjectId, setSubjectId]   = useState('')
  const [subjects, setSubjects]     = useState([])
  const [running, setRunning]       = useState(false)
  const [result, setResult]         = useState(null)
  const [detail, setDetail]         = useState(null)
  const [error, setError]           = useState('')

  const [rightTab, setRightTab]     = useState('logs') // 'logs' | 'snapshots'

  const [logs, setLogs]             = useState([])
  const [selectedTs, setSelectedTs] = useState(null)
  const [logDetail, setLogDetail]   = useState(null)
  const [logsLoading, setLogsLoading] = useState(false)

  const [snapshots, setSnapshots]       = useState([])
  const [selectedSnap, setSelectedSnap] = useState(null)
  const [snapDiff, setSnapDiff]         = useState(null)
  const [snapsLoading, setSnapsLoading] = useState(false)
  const [rolling, setRolling]           = useState(false)
  const [rollbackMsg, setRollbackMsg]   = useState('')

  const loadLogs = useCallback(async () => {
    setLogsLoading(true)
    try {
      const d = await api.getIngestionLogs()
      setLogs(d.logs || [])
    } catch { /* silent */ } finally {
      setLogsLoading(false)
    }
  }, [])

  const loadSnapshots = useCallback(async () => {
    setSnapsLoading(true)
    try {
      const d = await api.getIngestionSnapshots()
      setSnapshots(d.snapshots || [])
    } catch { /* silent */ } finally {
      setSnapsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadLogs()
    loadSnapshots()
    api.getSubjects().then(d => setSubjects(d.subjects || [])).catch(() => {})
  }, [loadLogs, loadSnapshots])

  const handleSelectLog = async (ts) => {
    setSelectedTs(ts)
    setLogDetail(null)
    try {
      const d = await api.getIngestionLogDetail(ts)
      setLogDetail(d)
    } catch { /* silent */ }
  }

  const handleSelectSnap = async (ts) => {
    setSelectedSnap(ts)
    setSnapDiff(null)
    setRollbackMsg('')
    try {
      const d = await api.getIngestionSnapshotDiff(ts)
      setSnapDiff(d)
    } catch { /* silent */ }
  }

  const handleRollback = async () => {
    if (!selectedSnap) return
    if (!window.confirm(`${selectedSnap} 시점으로 KG를 롤백합니다. 계속하시겠습니까?`)) return
    setRolling(true)
    setRollbackMsg('')
    try {
      const r = await api.rollbackIngestionSnapshot(selectedSnap)
      setRollbackMsg(`롤백 완료 → 스냅샷 ${r.new_snapshot} (노드 ${r.node_count} / 엣지 ${r.edge_count})`)
      await loadSnapshots()
      await handleSelectSnap(selectedSnap)
    } catch (e) {
      setRollbackMsg(`롤백 실패: ${e.message}`)
    } finally {
      setRolling(false)
    }
  }

  const handleRun = async () => {
    if (sourceType === 'file' ? !dropFile : !source.trim()) return
    setRunning(true)
    setResult(null)
    setDetail(null)
    setError('')
    try {
      const r = sourceType === 'file'
        ? await api.uploadIngestion(dropFile, dryRun, subjectId || null)
        : await api.runIngestion(sourceType, source, dryRun, subjectId || null)
      setResult(r)
      if (r.timestamp) {
        try {
          const d = await api.getIngestionLogDetail(r.timestamp)
          setDetail(d)
        } catch { /* silent */ }
      }
      await loadLogs()
      if (!dryRun) await loadSnapshots()
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(false)
    }
  }

  const sourcePlaceholder = {
    text: '분석할 텍스트를 입력하세요...',
    url:  'https://example.com/article',
    file: '/path/to/document.pdf',
  }[sourceType]

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>

      {/* ── 왼쪽: 실행 패널 ─────────────────────────────────── */}
      <div style={{ flex: 1, padding: 20, overflowY: 'auto', borderRight: '1px solid #1f2937' }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: '#e2e8f0' }}>
          Knowledge Ingestion
        </div>

        {/* Subject */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6 }}>
            대상 Subject
            <span style={{ marginLeft: 6, color: '#374151' }}>(선택 시 관련성 필터링 적용)</span>
          </div>
          <select
            value={subjectId}
            onChange={e => setSubjectId(e.target.value)}
            style={{ width: '100%', fontSize: 12, background: '#1a1d2e', color: subjectId ? '#e2e8f0' : '#4b5563' }}
          >
            <option value="">-- Subject 미지정 (전체 범위 추출) --</option>
            {subjects.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          {subjectId && (() => {
            const s = subjects.find(s => s.id === subjectId)
            return s?.description ? (
              <div style={{ marginTop: 4, fontSize: 11, color: '#4b5563', lineHeight: 1.5 }}>
                {s.description}
              </div>
            ) : null
          })()}
        </div>

        {/* Source Type */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6 }}>소스 타입</div>
          <div style={{ display: 'flex', gap: 6 }}>
            {['text', 'url', 'file'].map(t => (
              <button
                key={t}
                onClick={() => { setSourceType(t); setSource(''); setDropFile(null) }}
                style={{
                  padding: '5px 14px', borderRadius: 5, fontSize: 12,
                  background: sourceType === t ? '#4f46e5' : '#1e2130',
                  color: sourceType === t ? '#fff' : '#94a3b8',
                  border: 'none', cursor: 'pointer',
                }}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Source Input */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6 }}>
            {sourceType === 'text' ? '텍스트' : sourceType === 'url' ? 'URL' : '파일'}
          </div>
          {sourceType === 'text' ? (
            <textarea
              value={source}
              onChange={e => setSource(e.target.value)}
              placeholder={sourcePlaceholder}
              rows={8}
              style={{ width: '100%', resize: 'vertical', fontSize: 12, boxSizing: 'border-box' }}
            />
          ) : sourceType === 'url' ? (
            <input
              value={source}
              onChange={e => setSource(e.target.value)}
              placeholder={sourcePlaceholder}
              style={{ width: '100%', fontSize: 12, boxSizing: 'border-box' }}
            />
          ) : (
            <DropZone file={dropFile} onFile={setDropFile} />
          )}
        </div>

        {/* Dry-run toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12, color: '#94a3b8' }}>
            <input
              type="checkbox"
              checked={dryRun}
              onChange={e => setDryRun(e.target.checked)}
              style={{ accentColor: '#6366f1', width: 14, height: 14 }}
            />
            Dry-run (KG 미반영)
          </label>
          {!dryRun && (
            <span style={{ fontSize: 11, color: '#f97316', padding: '2px 8px', background: '#431407', borderRadius: 4 }}>
              실제 반영됩니다
            </span>
          )}
        </div>

        {/* Run button */}
        <button
          onClick={handleRun}
          disabled={running || (sourceType === 'file' ? !dropFile : !source.trim())}
          style={{
            width: '100%', padding: '10px', borderRadius: 6, fontSize: 13, fontWeight: 600,
            background: running ? '#374151' : '#4f46e5', color: running ? '#9ca3af' : '#fff',
            border: 'none', cursor: running ? 'default' : 'pointer',
          }}
        >
          {running ? '처리 중...' : dryRun ? '미리 보기 (Dry-run)' : 'KG에 반영'}
        </button>

        {error && (
          <div style={{ marginTop: 12, padding: '8px 12px', background: '#3b0764', borderRadius: 6, color: '#e879f9', fontSize: 12 }}>
            {error}
          </div>
        )}

        <ResultPanel result={result} detail={detail} />
      </div>

      {/* ── 오른쪽: 탭 패널 ──────────────────────────────────── */}
      <div style={{ width: 340, display: 'flex', flexDirection: 'column', background: '#0d1117' }}>

        {/* 탭 헤더 */}
        <div style={{ display: 'flex', borderBottom: '1px solid #1f2937', flexShrink: 0 }}>
          {[['logs', '실행 기록'], ['snapshots', 'KG 스냅샷']].map(([key, label]) => (
            <button
              key={key}
              onClick={() => setRightTab(key)}
              style={{
                flex: 1, padding: '10px', fontSize: 12, fontWeight: 500, border: 'none', cursor: 'pointer',
                background: rightTab === key ? '#111827' : 'transparent',
                color: rightTab === key ? '#e2e8f0' : '#4b5563',
                borderBottom: rightTab === key ? '2px solid #4f46e5' : '2px solid transparent',
              }}
            >
              {label}
            </button>
          ))}
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>

          {/* ── 실행 기록 탭 ── */}
          {rightTab === 'logs' && (
            <>
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 10 }}>
                <button
                  onClick={loadLogs}
                  disabled={logsLoading}
                  style={{ background: 'none', border: 'none', color: '#6366f1', fontSize: 11, cursor: 'pointer' }}
                >
                  {logsLoading ? '...' : '새로고침'}
                </button>
              </div>

              {logs.length === 0 && !logsLoading && (
                <div style={{ fontSize: 12, color: '#374151', textAlign: 'center', marginTop: 24 }}>
                  실행 기록이 없습니다
                </div>
              )}

              {logs.map(log => (
                <LogItem
                  key={log.timestamp}
                  log={log}
                  selected={selectedTs === log.timestamp}
                  onSelect={handleSelectLog}
                />
              ))}

              {selectedTs && logDetail && (
                <div style={{
                  marginTop: 12, padding: 12, background: '#111827',
                  borderRadius: 8, border: '1px solid #1f2937',
                }}>
                  <div style={{ fontSize: 11, color: '#64748b', marginBottom: 10 }}>상세 정보</div>
                  {logDetail.dedup_report?.nodes?.map((n, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                      <DecisionBadge decision={n.decision} />
                      {n.type && <NodeBadge type={n.type} name={n.type} depth="" />}
                      <span style={{ fontSize: 11, color: '#94a3b8' }}>{n.name}</span>
                    </div>
                  ))}
                  {logDetail.dedup_report?.edges?.length > 0 && (
                    <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #1f2937' }}>
                      <div style={{ fontSize: 10, color: '#64748b', marginBottom: 4 }}>엣지</div>
                      {logDetail.dedup_report.edges.map((e, i) => (
                        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 3 }}>
                          <DecisionBadge decision={e.decision} />
                          <span style={{ fontSize: 10, color: '#6b7280', fontFamily: 'monospace' }}>{e.relation}</span>
                          <span style={{ fontSize: 10, color: '#94a3b8' }}>{e.source_name} → {e.target_name}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {logDetail.applied_diff?.added_nodes?.length > 0 && (
                    <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #1f2937' }}>
                      <div style={{ fontSize: 10, color: '#4ade80', marginBottom: 4 }}>추가된 노드</div>
                      {logDetail.applied_diff.added_nodes.map(n => (
                        <div key={n.id} style={{ fontSize: 11, color: '#6ee7b7', marginBottom: 2 }}>
                          · {n.name} ({n.type} D{n.depth})
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {/* ── KG 스냅샷 탭 ── */}
          {rightTab === 'snapshots' && (
            <>
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 10 }}>
                <button
                  onClick={loadSnapshots}
                  disabled={snapsLoading}
                  style={{ background: 'none', border: 'none', color: '#6366f1', fontSize: 11, cursor: 'pointer' }}
                >
                  {snapsLoading ? '...' : '새로고침'}
                </button>
              </div>

              {snapshots.length === 0 && !snapsLoading && (
                <div style={{ fontSize: 12, color: '#374151', textAlign: 'center', marginTop: 24 }}>
                  스냅샷이 없습니다
                </div>
              )}

              {snapshots.map(snap => (
                <SnapshotItem
                  key={snap.timestamp}
                  snap={snap}
                  selected={selectedSnap === snap.timestamp}
                  onSelect={handleSelectSnap}
                />
              ))}

              {rollbackMsg && (
                <div style={{
                  marginTop: 8, padding: '8px 12px', borderRadius: 6, fontSize: 11,
                  background: rollbackMsg.startsWith('롤백 완료') ? '#052e16' : '#3b0764',
                  color: rollbackMsg.startsWith('롤백 완료') ? '#4ade80' : '#e879f9',
                }}>
                  {rollbackMsg}
                </div>
              )}

              {selectedSnap && (
                <SnapshotDiffPanel
                  diff={snapDiff}
                  onRollback={handleRollback}
                  rolling={rolling}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
