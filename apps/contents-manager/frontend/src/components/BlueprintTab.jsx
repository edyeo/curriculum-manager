import React, { useState, useEffect } from 'react'
import * as api from '../services/contentsApi.js'

const DEFAULT_MATRIX = [
  { layer: 'Seed',      stages: ['인식', '리스크', '통제'], stage_descriptions: {} },
  { layer: 'Concept',   stages: ['원리', '매핑', '대안'],   stage_descriptions: {} },
  { layer: 'TechStack', stages: ['스펙', '디버깅', '전환'], stage_descriptions: {} },
]

export default function BlueprintTab() {
  const [blueprints, setBlueprints] = useState([])
  const [selected, setSelected] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [creating, setCreating] = useState(false)
  const [showItemForm, setShowItemForm] = useState(false)
  const [itemName, setItemName] = useState('')
  const [itemDesc, setItemDesc] = useState('')
  const [itemCombos, setItemCombos] = useState([])
  // 매트릭스 편집 상태
  const [matrix, setMatrix] = useState([])          // 편집 중인 매트릭스
  const [matrixDirty, setMatrixDirty] = useState(false)
  const [matrixSaving, setMatrixSaving] = useState(false)
  const [addingStage, setAddingStage] = useState({}) // {layerName: inputValue}
  // Rubric 속성 편집 상태
  const [rubricWeight, setRubricWeight] = useState(1.0)
  const [rubricRequired, setRubricRequired] = useState(false)
  const [rubricDirty, setRubricDirty] = useState(false)
  const [rubricSaving, setRubricSaving] = useState(false)

  useEffect(() => {
    api.getBlueprints().then(d => setBlueprints(d.blueprints || []))
  }, [])

  const handleSelectBlueprint = async (bp) => {
    const detail = await api.getBlueprint(bp.id)
    setSelected(detail)
    const base = detail.matrix?.length ? detail.matrix : DEFAULT_MATRIX
    // stage_descriptions 필드 보정 (기존 데이터에 없을 수 있음)
    setMatrix(base.map(row => ({ ...row, stage_descriptions: row.stage_descriptions || {} })))
    setMatrixDirty(false)
    setAddingStage({})
    setRubricWeight(detail.weight ?? 1.0)
    setRubricRequired(detail.required ?? false)
    setRubricDirty(false)
  }

  // 인지 단계 추가
  const handleAddStage = (layer) => {
    const val = (addingStage[layer] || '').trim()
    if (!val) return
    setMatrix(prev => prev.map(row =>
      row.layer === layer ? { ...row, stages: [...row.stages, val] } : row
    ))
    setAddingStage(prev => ({ ...prev, [layer]: '' }))
    setMatrixDirty(true)
  }

  // 인지 단계 삭제
  const handleRemoveStage = (layer, stage) => {
    setMatrix(prev => prev.map(row => {
      if (row.layer !== layer) return row
      const descs = { ...(row.stage_descriptions || {}) }
      delete descs[stage]
      return { ...row, stages: row.stages.filter(s => s !== stage), stage_descriptions: descs }
    }))
    setMatrixDirty(true)
  }

  // stage 설명 수정
  const handleStageDesc = (layer, stage, value) => {
    setMatrix(prev => prev.map(row =>
      row.layer === layer
        ? { ...row, stage_descriptions: { ...(row.stage_descriptions || {}), [stage]: value } }
        : row
    ))
    setMatrixDirty(true)
  }

  // 매트릭스 저장
  const handleSaveMatrix = async () => {
    setMatrixSaving(true)
    try {
      const updated = await api.updateBlueprint(selected.id, { matrix })
      setSelected(prev => ({ ...prev, matrix: updated.matrix }))
      setMatrixDirty(false)
    } finally { setMatrixSaving(false) }
  }

  // Rubric 속성 저장
  const handleSaveRubric = async () => {
    setRubricSaving(true)
    try {
      const updated = await api.updateBlueprint(selected.id, { weight: rubricWeight, required: rubricRequired })
      setSelected(prev => ({ ...prev, weight: updated.weight, required: updated.required }))
      setBlueprints(prev => prev.map(b => b.id === selected.id ? { ...b, weight: updated.weight, required: updated.required } : b))
      setRubricDirty(false)
    } finally { setRubricSaving(false) }
  }

  const handleCreate = async () => {
    if (!newName.trim()) return
    setCreating(true)
    try {
      const bp = await api.createBlueprint({ name: newName, description: newDesc, matrix: DEFAULT_MATRIX })
      setBlueprints(prev => [bp, ...prev])
      setShowCreate(false)
      setNewName('')
      setNewDesc('')
    } finally { setCreating(false) }
  }

  const handleDelete = async (id) => {
    if (!confirm('이 Blueprint를 삭제할까요?')) return
    await api.deleteBlueprint(id)
    setBlueprints(prev => prev.filter(b => b.id !== id))
    if (selected?.id === id) setSelected(null)
  }

  const toggleCombo = (layer, stage) => {
    const key = `${layer}/${stage}`
    setItemCombos(prev => {
      const exists = prev.some(c => c.layer === layer && c.stage === stage)
      return exists ? prev.filter(c => !(c.layer === layer && c.stage === stage)) : [...prev, { layer, stage }]
    })
  }

  const handleAddItem = async () => {
    if (!itemName.trim() || !selected) return
    const item = await api.createIntegrationItem(selected.id, {
      name: itemName, description: itemDesc, required_combinations: itemCombos,
    })
    setSelected(prev => ({ ...prev, integration_items: [...(prev.integration_items || []), item] }))
    setShowItemForm(false)
    setItemName('')
    setItemDesc('')
    setItemCombos([])
  }

  const handleDeleteItem = async (itemId) => {
    if (!confirm('통합항목을 삭제할까요?')) return
    await api.deleteIntegrationItem(selected.id, itemId)
    setSelected(prev => ({
      ...prev,
      integration_items: prev.integration_items.filter(i => i.id !== itemId),
    }))
  }

  return (
    <div style={{ display: 'flex', height: '100%', gap: 0 }}>
      {/* 좌측: Blueprint 목록 */}
      <div style={{ width: 280, borderRight: '1px solid #2d3748', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '12px 16px', borderBottom: '1px solid #2d3748', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontWeight: 600, color: '#e2e8f0' }}>Blueprints</span>
          <button className="btn-primary" style={{ padding: '4px 10px', fontSize: 12 }} onClick={() => setShowCreate(true)}>+ 새 Blueprint</button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {blueprints.length === 0 && (
            <div style={{ padding: 16, color: '#718096', fontSize: 13 }}>Blueprint가 없습니다.</div>
          )}
          {blueprints.map(bp => (
            <div
              key={bp.id}
              onClick={() => handleSelectBlueprint(bp)}
              style={{
                padding: '10px 16px', cursor: 'pointer', borderBottom: '1px solid #1a202c',
                background: selected?.id === bp.id ? '#2d3748' : 'transparent',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              }}
            >
              <div>
                <div style={{ color: '#e2e8f0', fontSize: 13, fontWeight: 500 }}>{bp.name}</div>
                {bp.description && <div style={{ color: '#718096', fontSize: 11, marginTop: 2 }}>{bp.description.slice(0, 40)}</div>}
              </div>
              <button
                onClick={e => { e.stopPropagation(); handleDelete(bp.id) }}
                style={{ background: 'none', border: 'none', color: '#fc8181', cursor: 'pointer', fontSize: 14 }}
              >×</button>
            </div>
          ))}
        </div>
      </div>

      {/* 우측: Blueprint 상세 */}
      <div style={{ flex: 1, padding: 24, overflowY: 'auto' }}>
        {!selected ? (
          <div style={{ color: '#718096', fontSize: 14 }}>Blueprint를 선택하세요.</div>
        ) : (
          <>
            <h2 style={{ color: '#e2e8f0', marginBottom: 4 }}>{selected.name}</h2>
            {selected.description && <p style={{ color: '#a0aec0', marginBottom: 20 }}>{selected.description}</p>}

            {/* Rubric 속성 */}
            <section style={{ marginBottom: 24, background: '#1a202c', borderRadius: 8, padding: '14px 18px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <h3 style={{ color: '#90cdf4', fontSize: 14, margin: 0 }}>Rubric 속성</h3>
                {rubricDirty && (
                  <button className="btn-primary" onClick={handleSaveRubric} disabled={rubricSaving} style={{ padding: '4px 12px', fontSize: 12 }}>
                    {rubricSaving ? '저장 중...' : '저장'}
                  </button>
                )}
              </div>
              <div style={{ display: 'flex', gap: 24, alignItems: 'center' }}>
                <label style={{ color: '#a0aec0', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
                  가중치 (weight)
                  <input
                    type="number" min="0" max="10" step="0.1"
                    value={rubricWeight}
                    onChange={e => { setRubricWeight(parseFloat(e.target.value) || 1.0); setRubricDirty(true) }}
                    style={{ width: 64, background: '#2d3748', border: '1px solid #4a5568', borderRadius: 4, color: '#e2e8f0', padding: '3px 8px', fontSize: 13 }}
                  />
                </label>
                <label style={{ color: '#a0aec0', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={rubricRequired}
                    onChange={e => { setRubricRequired(e.target.checked); setRubricDirty(true) }}
                  />
                  필수 Blueprint (required)
                </label>
              </div>
            </section>

            {/* Matrix */}
            <section style={{ marginBottom: 28 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <h3 style={{ color: '#90cdf4', fontSize: 14, margin: 0 }}>인지 성숙도 매트릭스</h3>
                {matrixDirty && (
                  <button
                    className="btn-primary"
                    onClick={handleSaveMatrix}
                    disabled={matrixSaving}
                    style={{ padding: '4px 12px', fontSize: 12 }}
                  >
                    {matrixSaving ? '저장 중...' : '저장'}
                  </button>
                )}
              </div>
              <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                <thead>
                  <tr>
                    <th style={{ ...thStyle, width: 110 }}>레이어</th>
                    <th style={thStyle}>인지 단계</th>
                  </tr>
                </thead>
                <tbody>
                  {matrix.map(row => (
                    <tr key={row.layer}>
                      <td style={tdStyle}>
                        <span style={{ background: '#2d3748', padding: '2px 8px', borderRadius: 4, fontSize: 12 }}>{row.layer}</span>
                      </td>
                      <td style={tdStyle}>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center' }}>
                          {(row.stages || []).map(stage => (
                            <span key={stage} style={{
                              display: 'inline-flex', alignItems: 'center', gap: 4,
                              background: '#2d3748', color: '#e2e8f0',
                              padding: '3px 8px', borderRadius: 12, fontSize: 12,
                            }}>
                              {stage}
                              <button
                                onClick={() => handleRemoveStage(row.layer, stage)}
                                style={{ background: 'none', border: 'none', color: '#fc8181', cursor: 'pointer', fontSize: 11, padding: 0, lineHeight: 1 }}
                              >×</button>
                            </span>
                          ))}
                          {/* 단계 추가 인라인 입력 */}
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                            <input
                              value={addingStage[row.layer] || ''}
                              onChange={e => setAddingStage(prev => ({ ...prev, [row.layer]: e.target.value }))}
                              onKeyDown={e => e.key === 'Enter' && handleAddStage(row.layer)}
                              placeholder="+ 단계 추가"
                              style={{
                                background: 'transparent', border: 'none', borderBottom: '1px solid #4a5568',
                                color: '#a0aec0', fontSize: 12, width: 80, outline: 'none', padding: '2px 0',
                              }}
                            />
                            {(addingStage[row.layer] || '').trim() && (
                              <button
                                onClick={() => handleAddStage(row.layer)}
                                style={{ background: 'none', border: 'none', color: '#68d391', cursor: 'pointer', fontSize: 14, padding: 0 }}
                              >+</button>
                            )}
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            {/* Stage 설명 */}
            <section style={{ marginBottom: 28 }}>
              <h3 style={{ color: '#90cdf4', fontSize: 14, margin: '0 0 12px 0' }}>Stage 기준 설명</h3>
              <div style={{ display: 'flex', gap: 12 }}>
                {matrix.map(row => (
                  <div key={row.layer} style={{ flex: 1, background: '#1a202c', borderRadius: 8, padding: '12px 14px' }}>
                    <div style={{ color: '#a0aec0', fontSize: 12, fontWeight: 600, marginBottom: 10 }}>{row.layer}</div>
                    {(row.stages || []).map(stage => (
                      <div key={stage} style={{ marginBottom: 10 }}>
                        <div style={{ color: '#e2e8f0', fontSize: 12, marginBottom: 4 }}>{stage}</div>
                        <textarea
                          rows={2}
                          value={(row.stage_descriptions || {})[stage] || ''}
                          onChange={e => handleStageDesc(row.layer, stage, e.target.value)}
                          placeholder="이 단계의 평가 기준 설명..."
                          style={{
                            width: '100%', background: '#2d3748', border: '1px solid #4a5568',
                            borderRadius: 4, color: '#e2e8f0', fontSize: 12,
                            padding: '6px 8px', resize: 'vertical', outline: 'none',
                            boxSizing: 'border-box',
                          }}
                        />
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </section>

            {/* Integration Items */}
            <section>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <h3 style={{ color: '#90cdf4', fontSize: 14 }}>통합항목 (Z-Axis)</h3>
                <button className="btn-primary" style={{ padding: '4px 12px', fontSize: 12 }} onClick={() => setShowItemForm(true)}>+ 추가</button>
              </div>
              {(selected.integration_items || []).length === 0 && (
                <div style={{ color: '#718096', fontSize: 13 }}>통합항목이 없습니다.</div>
              )}
              {(selected.integration_items || []).map(item => (
                <div key={item.id} style={{ background: '#1a202c', borderRadius: 6, padding: '12px 16px', marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ color: '#e2e8f0', fontWeight: 500, marginBottom: 4 }}>{item.name}</div>
                    {item.description && <div style={{ color: '#a0aec0', fontSize: 12, marginBottom: 6 }}>{item.description}</div>}
                    {(item.required_combinations || []).length > 0 && (
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {item.required_combinations.map((c, i) => (
                          <span key={i} style={{ background: '#2d3748', color: '#90cdf4', fontSize: 11, padding: '2px 6px', borderRadius: 4 }}>
                            {c.layer}/{c.stage}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => handleDeleteItem(item.id)}
                    style={{ background: 'none', border: 'none', color: '#fc8181', cursor: 'pointer', fontSize: 14, alignSelf: 'flex-start' }}
                  >×</button>
                </div>
              ))}
            </section>
          </>
        )}
      </div>

      {/* Create Blueprint Modal */}
      {showCreate && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setShowCreate(false)}>
          <div className="modal-box">
            <h2>새 Blueprint 생성</h2>
            <label>이름 *</label>
            <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="예: 시니어 백엔드 평가 Blueprint" autoFocus />
            <label>설명 (선택)</label>
            <textarea value={newDesc} onChange={e => setNewDesc(e.target.value)} rows={3} placeholder="Blueprint 목적 설명..." />
            <p style={{ color: '#718096', fontSize: 12, marginTop: 4 }}>인지 단계 매트릭스는 기본값으로 생성됩니다 (나중에 수정 가능)</p>
            <div className="modal-actions">
              <button className="btn-cancel" onClick={() => setShowCreate(false)}>취소</button>
              <button className="btn-primary" onClick={handleCreate} disabled={creating || !newName.trim()}>
                {creating ? '생성 중...' : '생성'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Integration Item Modal */}
      {showItemForm && selected && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setShowItemForm(false)}>
          <div className="modal-box" style={{ maxWidth: 500 }}>
            <h2>통합항목 추가</h2>
            <label>이름 *</label>
            <input value={itemName} onChange={e => setItemName(e.target.value)} placeholder="예: 풀스택 아키텍팅" autoFocus />
            <label>설명 (선택)</label>
            <textarea value={itemDesc} onChange={e => setItemDesc(e.target.value)} rows={2} placeholder="통합항목 설명..." />
            <label>요구 인지 조합 (멀티 선택)</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
              {(selected.matrix || DEFAULT_MATRIX).map(row =>
                (row.stages || []).map(stage => {
                  const active = itemCombos.some(c => c.layer === row.layer && c.stage === stage)
                  return (
                    <button
                      key={`${row.layer}/${stage}`}
                      onClick={() => toggleCombo(row.layer, stage)}
                      style={{
                        padding: '4px 10px', borderRadius: 4, fontSize: 12, cursor: 'pointer',
                        background: active ? '#4299e1' : '#2d3748',
                        color: active ? '#fff' : '#a0aec0',
                        border: active ? '1px solid #4299e1' : '1px solid #4a5568',
                      }}
                    >
                      {row.layer}/{stage}
                    </button>
                  )
                })
              )}
            </div>
            <div className="modal-actions">
              <button className="btn-cancel" onClick={() => setShowItemForm(false)}>취소</button>
              <button className="btn-primary" onClick={handleAddItem} disabled={!itemName.trim()}>추가</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const thStyle = { textAlign: 'left', padding: '6px 12px', color: '#a0aec0', fontSize: 12, borderBottom: '1px solid #2d3748', fontWeight: 500 }
const tdStyle = { padding: '8px 12px', color: '#e2e8f0', fontSize: 13, borderBottom: '1px solid #1a202c' }
