import React, { useState } from 'react'

function IntegrationCard({ item, allCells, onDelete }) {
  const enriched = item.combinations.map(c => ({
    ...c,
    label: allCells.find(ac => ac.id === c.cell_id)?.label || '?',
  }))

  return (
    <div className="integration-card">
      <div className="integration-card-header">
        <span className="integration-name">{item.name}</span>
        <button className="btn-del-relation" onClick={() => onDelete(item.id)}>삭제</button>
      </div>
      <div className="integration-combinations">
        {enriched.map((c, i) => (
          <span key={i} className="combination-tag">
            <span className="combination-layer">{c.layer}·</span>{c.label}
          </span>
        ))}
      </div>
    </div>
  )
}

export default function IntegrationPanel({ integrations, matrix, onAdd, onDelete }) {
  const [showModal, setShowModal] = useState(false)
  const [name, setName] = useState('')
  const [selected, setSelected] = useState([])
  const [saving, setSaving] = useState(false)

  const allCells = Object.entries(matrix).flatMap(([layer, cells]) =>
    cells.map(c => ({ ...c, layer }))
  )

  const isSelected = (layer, cellId) =>
    selected.some(s => s.layer === layer && s.cell_id === cellId)

  const toggleCell = (layer, cell) => {
    setSelected(prev => {
      if (prev.some(s => s.layer === layer && s.cell_id === cell.id)) {
        return prev.filter(s => !(s.layer === layer && s.cell_id === cell.id))
      }
      return [...prev, { layer, cell_id: cell.id, label: cell.label }]
    })
  }

  const handleSave = async () => {
    if (!name.trim() || selected.length < 2) return
    setSaving(true)
    try {
      await onAdd(name.trim(), selected.map(({ layer, cell_id }) => ({ layer, cell_id })))
      handleClose()
    } catch {
      // error handled by parent
    } finally {
      setSaving(false)
    }
  }

  const handleClose = () => {
    setShowModal(false)
    setName('')
    setSelected([])
  }

  return (
    <div className="integration-panel">
      <div className="integration-toolbar">
        <button className="btn-primary" onClick={() => setShowModal(true)}>+ 통합 항목 추가</button>
      </div>

      {integrations.length === 0 ? (
        <div className="empty-msg" style={{ padding: '12px 0' }}>통합 항목이 없습니다.</div>
      ) : (
        integrations.map(item => (
          <IntegrationCard key={item.id} item={item} allCells={allCells} onDelete={onDelete} />
        ))
      )}

      {showModal && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && handleClose()}>
          <div className="modal-box" style={{ width: 520 }}>
            <h2>통합 항목 추가</h2>
            <label>이름 *</label>
            <input
              value={name}
              autoFocus
              placeholder="예: 풀스택 아키텍팅"
              onChange={e => setName(e.target.value)}
            />
            <label style={{ marginTop: 12 }}>조합 선택 (최소 2개) *</label>
            <div className="integration-matrix-select">
              {Object.entries(matrix).map(([layer, cells]) => (
                <div key={layer} className="integration-matrix-row">
                  <span className="matrix-layer-label" style={{ fontSize: 11, minWidth: 80 }}>{layer}</span>
                  <div className="matrix-cells">
                    {cells.map(cell => (
                      <button
                        key={cell.id}
                        type="button"
                        className={`matrix-cell-select${isSelected(layer, cell.id) ? ' selected' : ''}`}
                        onClick={() => toggleCell(layer, cell)}
                      >
                        {cell.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            {selected.length > 0 && (
              <div className="selected-preview">
                선택: {selected.map(s => `${s.layer}·${s.label}`).join(', ')}
              </div>
            )}
            <div className="modal-actions" style={{ marginTop: 16 }}>
              <button className="btn-cancel" onClick={handleClose}>취소</button>
              <button
                className="btn-primary"
                onClick={handleSave}
                disabled={saving || !name.trim() || selected.length < 2}
              >
                {saving ? '저장 중...' : '저장'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
