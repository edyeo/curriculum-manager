import React, { useState } from 'react'

const LAYER_COLORS = {
  System:    { bg: '#1a1a2e', border: '#6366f1', text: '#a5b4fc' },
  Seed:      { bg: '#451a03', border: '#f59e0b', text: '#fbbf24' },
  Concept:   { bg: '#0c1a2e', border: '#38bdf8', text: '#7dd3fc' },
  TechStack: { bg: '#052e16', border: '#34d399', text: '#6ee7b7' },
}
const DEFAULT_COLOR = { bg: '#1e2130', border: '#4a5568', text: '#94a3b8' }

function CellChip({ cell, layer, onUpdate, onDelete }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(cell.label)
  const colors = LAYER_COLORS[layer] || DEFAULT_COLOR

  const handleSave = () => {
    const trimmed = value.trim()
    if (!trimmed) { setValue(cell.label); setEditing(false); return }
    if (trimmed !== cell.label) onUpdate(layer, cell.id, trimmed)
    setEditing(false)
  }

  if (editing) {
    return (
      <input
        className="matrix-cell-input"
        value={value}
        autoFocus
        style={{ borderColor: colors.border, width: Math.max(60, value.length * 9 + 20) + 'px' }}
        onChange={e => setValue(e.target.value)}
        onBlur={handleSave}
        onKeyDown={e => {
          if (e.key === 'Enter') handleSave()
          if (e.key === 'Escape') { setValue(cell.label); setEditing(false) }
        }}
      />
    )
  }

  return (
    <div
      className="matrix-cell"
      style={{ background: colors.bg, borderColor: colors.border, color: colors.text }}
      onClick={() => setEditing(true)}
    >
      {cell.label}
      <button
        className="matrix-cell-del"
        onClick={e => { e.stopPropagation(); onDelete(layer, cell.id) }}
      >×</button>
    </div>
  )
}

function AddCellInput({ layer, onAdd }) {
  const [adding, setAdding] = useState(false)
  const [value, setValue] = useState('')
  const colors = LAYER_COLORS[layer] || DEFAULT_COLOR

  const handleSave = () => {
    const trimmed = value.trim()
    if (trimmed) onAdd(layer, trimmed)
    setValue('')
    setAdding(false)
  }

  if (!adding) {
    return (
      <button className="matrix-cell-add" onClick={() => setAdding(true)}>+ 단계 추가</button>
    )
  }

  return (
    <input
      className="matrix-cell-input"
      value={value}
      autoFocus
      placeholder="단계 이름..."
      style={{ borderColor: colors.border }}
      onChange={e => setValue(e.target.value)}
      onBlur={handleSave}
      onKeyDown={e => {
        if (e.key === 'Enter') handleSave()
        if (e.key === 'Escape') { setValue(''); setAdding(false) }
      }}
    />
  )
}

export default function MatrixGrid({ matrix, onAddCell, onUpdateCell, onDeleteCell }) {
  const layers = Object.keys(matrix)
  if (layers.length === 0) return <div className="empty-msg">매트릭스 데이터가 없습니다.</div>

  return (
    <div className="matrix-grid">
      {layers.map(layer => (
        <div key={layer} className="matrix-row">
          <div className="matrix-layer-label">{layer}</div>
          <div className="matrix-cells">
            {matrix[layer].map(cell => (
              <CellChip
                key={cell.id}
                cell={cell}
                layer={layer}
                onUpdate={onUpdateCell}
                onDelete={onDeleteCell}
              />
            ))}
            <AddCellInput layer={layer} onAdd={onAddCell} />
          </div>
        </div>
      ))}
    </div>
  )
}
