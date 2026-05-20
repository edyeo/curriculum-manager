import React, { useState, useEffect } from 'react'
import MatrixGrid from './MatrixGrid.jsx'
import IntegrationPanel from './IntegrationPanel.jsx'
import * as api from '../services/contentsApi.js'

export default function BlueprintEditor({ blueprintId, onBack }) {
  const [blueprint, setBlueprint] = useState(null)
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)

  useEffect(() => {
    api.getBlueprint(blueprintId).then(setBlueprint).finally(() => setLoading(false))
  }, [blueprintId])

  const showToast = (msg, type = 'error') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }

  const handleAddCell = async (layer, label) => {
    try {
      const cell = await api.addMatrixCell(blueprintId, layer, label)
      setBlueprint(prev => ({
        ...prev,
        matrix: { ...prev.matrix, [layer]: [...(prev.matrix[layer] || []), cell] },
      }))
    } catch (e) { showToast(e.message) }
  }

  const handleUpdateCell = async (layer, cellId, label) => {
    try {
      const cell = await api.updateMatrixCell(blueprintId, cellId, label)
      setBlueprint(prev => ({
        ...prev,
        matrix: {
          ...prev.matrix,
          [layer]: prev.matrix[layer].map(c => c.id === cellId ? cell : c),
        },
      }))
    } catch (e) { showToast(e.message) }
  }

  const handleDeleteCell = async (layer, cellId) => {
    try {
      await api.deleteMatrixCell(blueprintId, cellId)
      setBlueprint(prev => ({
        ...prev,
        matrix: {
          ...prev.matrix,
          [layer]: prev.matrix[layer].filter(c => c.id !== cellId),
        },
      }))
    } catch (e) { showToast(e.message) }
  }

  const handleAddIntegration = async (name, combinations) => {
    const item = await api.addIntegration(blueprintId, name, combinations)
    setBlueprint(prev => ({ ...prev, integrations: [...prev.integrations, item] }))
  }

  const handleDeleteIntegration = async (itemId) => {
    try {
      await api.deleteIntegration(blueprintId, itemId)
      setBlueprint(prev => ({
        ...prev,
        integrations: prev.integrations.filter(i => i.id !== itemId),
      }))
    } catch (e) { showToast(e.message) }
  }

  if (loading) return <div className="blueprint-tab"><div className="empty-msg">로딩 중...</div></div>
  if (!blueprint) return <div className="blueprint-tab"><div className="empty-msg">Blueprint를 찾을 수 없습니다.</div></div>

  return (
    <div className="blueprint-tab">
      {toast && <div className={`bp-toast${toast.type === 'success' ? ' success' : ''}`}>{toast.msg}</div>}

      <div className="bp-editor-header">
        <button className="btn-back" onClick={onBack}>← 목록</button>
        <h2>{blueprint.name}</h2>
        {blueprint.description && <span className="bp-editor-desc">{blueprint.description}</span>}
      </div>

      <div className="bp-editor-body">
        <section className="bp-section">
          <h3 className="bp-section-title">인지 성숙도 매트릭스</h3>
          <MatrixGrid
            matrix={blueprint.matrix}
            onAddCell={handleAddCell}
            onUpdateCell={handleUpdateCell}
            onDeleteCell={handleDeleteCell}
          />
        </section>

        <section className="bp-section">
          <h3 className="bp-section-title">통합 항목 (Z-Axis)</h3>
          <IntegrationPanel
            integrations={blueprint.integrations}
            matrix={blueprint.matrix}
            onAdd={handleAddIntegration}
            onDelete={handleDeleteIntegration}
          />
        </section>
      </div>
    </div>
  )
}
