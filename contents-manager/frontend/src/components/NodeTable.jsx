import React, { useState } from 'react'

const TYPES = ['Seed', 'Concept', 'TechStack']
const DEPTHS = [1, 2, 3]

export default function NodeTable({ nodes, onSelectNode, selectedNodeId, onAddNode, onExpand, expanding }) {
  const [typeFilter, setTypeFilter] = useState('')
  const [depthFilter, setDepthFilter] = useState('')
  const [search, setSearch] = useState('')
  const [adding, setAdding] = useState(false)
  const [newNode, setNewNode] = useState({ name: '', type: 'Concept', depth: 1, description: '' })
  const [saving, setSaving] = useState(false)

  const filtered = nodes.filter(n => {
    if (typeFilter && n.type !== typeFilter) return false
    if (depthFilter && n.depth !== Number(depthFilter)) return false
    if (search) {
      const q = search.toLowerCase()
      if (!n.name.toLowerCase().includes(q) && !(n.description || '').toLowerCase().includes(q)) return false
    }
    return true
  })

  const handleSaveNew = async () => {
    if (!newNode.name.trim()) return
    setSaving(true)
    try {
      await onAddNode(newNode)
      setAdding(false)
      setNewNode({ name: '', type: 'Concept', depth: 1, description: '' })
    } finally { setSaving(false) }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="table-toolbar">
        <button className="btn-expand" onClick={onExpand} disabled={expanding}>
          {expanding ? 'AI 확장 중...' : 'AI 확장'}
        </button>
        <button className="btn-add-node" onClick={() => setAdding(true)} disabled={adding}>+ 노드 추가</button>
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
          <option value="">전체 타입</option>
          {TYPES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <select value={depthFilter} onChange={e => setDepthFilter(e.target.value)}>
          <option value="">전체 Depth</option>
          {DEPTHS.map(d => <option key={d} value={d}>Depth {d}</option>)}
        </select>
        <input placeholder="이름·설명 검색..." value={search} onChange={e => setSearch(e.target.value)} />
        <span style={{ color: '#64748b', fontSize: 12 }}>{filtered.length}개</span>
      </div>

      <div style={{ flex: 1, overflow: 'auto' }}>
        <table>
          <thead>
            <tr>
              <th style={{ width: 220 }}>이름</th>
              <th style={{ width: 110 }}>타입</th>
              <th style={{ width: 70 }}>Depth</th>
              <th>설명</th>
              <th style={{ width: 60 }}>관계</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(n => (
              <tr key={n.id} className={selectedNodeId === n.id ? 'selected' : ''} onClick={() => onSelectNode(n.id)}>
                <td>{n.name}</td>
                <td><span className={`type-badge type-${n.type}`}>{n.type}</span></td>
                <td className="count-cell">{n.depth}</td>
                <td className="desc-cell">{n.description}</td>
                <td className="count-cell">{n.edge_count ?? 0}</td>
              </tr>
            ))}
            {adding && (
              <tr className="inline-add-row">
                <td><input value={newNode.name} onChange={e => setNewNode(p => ({ ...p, name: e.target.value }))} placeholder="노드 이름 (필수)" autoFocus /></td>
                <td>
                  <select value={newNode.type} onChange={e => setNewNode(p => ({ ...p, type: e.target.value }))}>
                    {TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </td>
                <td>
                  <select value={newNode.depth} onChange={e => setNewNode(p => ({ ...p, depth: Number(e.target.value) }))}>
                    {DEPTHS.map(d => <option key={d} value={d}>{d}</option>)}
                  </select>
                </td>
                <td><input value={newNode.description} onChange={e => setNewNode(p => ({ ...p, description: e.target.value }))} placeholder="설명 (선택)" /></td>
                <td>
                  <button className="btn-save-inline" onClick={handleSaveNew} disabled={saving}>{saving ? '...' : '저장'}</button>
                  <button className="btn-cancel-inline" onClick={() => setAdding(false)}>취소</button>
                </td>
              </tr>
            )}
          </tbody>
        </table>
        {filtered.length === 0 && !adding && (
          <p style={{ color: '#4a5568', fontSize: 13, textAlign: 'center', padding: 24 }}>노드가 없습니다.</p>
        )}
      </div>
    </div>
  )
}
