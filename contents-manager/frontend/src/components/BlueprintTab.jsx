import React, { useState, useEffect } from 'react'
import BlueprintEditor from './BlueprintEditor.jsx'
import * as api from '../services/contentsApi.js'

function BlueprintList({ blueprints, loading, onSelect, onCreate, onDelete }) {
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [creating, setCreating] = useState(false)

  const handleCreate = async () => {
    if (!name.trim()) return
    setCreating(true)
    try {
      await onCreate(name.trim(), desc.trim())
      setShowCreate(false)
      setName('')
      setDesc('')
    } finally { setCreating(false) }
  }

  return (
    <div className="blueprint-tab">
      <div className="bp-list-header">
        <h2>Blueprint 워크스페이스</h2>
        <button className="btn-primary" onClick={() => setShowCreate(true)}>+ 새 Blueprint</button>
      </div>

      {loading ? (
        <div className="empty-msg">로딩 중...</div>
      ) : blueprints.length === 0 ? (
        <div className="empty-msg">Blueprint가 없습니다. 새로 만들어보세요.</div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '8px 10px', background: '#1a1d2e', color: '#94a3b8', borderBottom: '1px solid #2d3748' }}>이름</th>
              <th style={{ textAlign: 'left', padding: '8px 10px', background: '#1a1d2e', color: '#94a3b8', borderBottom: '1px solid #2d3748' }}>설명</th>
              <th style={{ textAlign: 'left', padding: '8px 10px', background: '#1a1d2e', color: '#94a3b8', borderBottom: '1px solid #2d3748' }}>생성일</th>
              <th style={{ background: '#1a1d2e', borderBottom: '1px solid #2d3748' }}></th>
            </tr>
          </thead>
          <tbody>
            {blueprints.map(bp => (
              <tr
                key={bp.id}
                onClick={() => onSelect(bp.id)}
                style={{ cursor: 'pointer' }}
                onMouseEnter={e => e.currentTarget.querySelectorAll('td').forEach(td => td.style.background = '#1a1d2e')}
                onMouseLeave={e => e.currentTarget.querySelectorAll('td').forEach(td => td.style.background = '')}
              >
                <td style={{ padding: '8px 10px', borderBottom: '1px solid #1e2130', fontWeight: 500 }}>{bp.name}</td>
                <td style={{ padding: '8px 10px', borderBottom: '1px solid #1e2130', color: '#94a3b8', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {bp.description || '-'}
                </td>
                <td style={{ padding: '8px 10px', borderBottom: '1px solid #1e2130', color: '#64748b', fontSize: 12, whiteSpace: 'nowrap' }}>
                  {new Date(bp.created_at).toLocaleDateString('ko-KR')}
                </td>
                <td style={{ padding: '8px 10px', borderBottom: '1px solid #1e2130' }}>
                  <button
                    className="btn-danger"
                    style={{ padding: '3px 8px', fontSize: 12 }}
                    onClick={e => {
                      e.stopPropagation()
                      if (confirm(`"${bp.name}" Blueprint를 삭제할까요?`)) onDelete(bp.id)
                    }}
                  >삭제</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {showCreate && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setShowCreate(false)}>
          <div className="modal-box">
            <h2>새 Blueprint 생성</h2>
            <label>이름 *</label>
            <input
              value={name}
              autoFocus
              placeholder="예: 백엔드 엔지니어링 v1"
              onChange={e => setName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCreate()}
            />
            <label>설명 (선택)</label>
            <textarea value={desc} rows={3} placeholder="평가 기준 설명..." onChange={e => setDesc(e.target.value)} />
            <div className="modal-actions">
              <button className="btn-cancel" onClick={() => setShowCreate(false)}>취소</button>
              <button className="btn-primary" onClick={handleCreate} disabled={creating || !name.trim()}>
                {creating ? '생성 중...' : '생성'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function BlueprintTab() {
  const [blueprints, setBlueprints] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getBlueprints()
      .then(d => setBlueprints(d.blueprints || []))
      .finally(() => setLoading(false))
  }, [])

  const handleCreate = async (name, description) => {
    const bp = await api.createBlueprint(name, description)
    setBlueprints(prev => [{ id: bp.id, name: bp.name, description: bp.description, created_at: bp.created_at }, ...prev])
    setSelectedId(bp.id)
  }

  const handleDelete = async (id) => {
    await api.deleteBlueprint(id)
    setBlueprints(prev => prev.filter(b => b.id !== id))
    if (selectedId === id) setSelectedId(null)
  }

  if (selectedId) {
    return <BlueprintEditor blueprintId={selectedId} onBack={() => setSelectedId(null)} />
  }

  return (
    <BlueprintList
      blueprints={blueprints}
      loading={loading}
      onSelect={setSelectedId}
      onCreate={handleCreate}
      onDelete={handleDelete}
    />
  )
}
