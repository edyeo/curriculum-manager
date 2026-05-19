import { useState, useEffect } from 'react'
import {
  fetchFeatureDefinitions, createFeatureDefinition,
  updateFeatureDefinition, deleteFeatureDefinition,
} from '../api/client'

const CATEGORIES = ['숙련도', '학습특성', '기질', '답변 행동']
const VALUE_TYPES = ['categorical', 'numeric', 'text']

export default function Features() {
  const [features, setFeatures] = useState([])
  const [categoryTab, setCategoryTab] = useState('전체')
  const [showForm, setShowForm] = useState(false)
  const [editingFeature, setEditingFeature] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => { load() }, [])

  async function load() {
    try {
      setFeatures(await fetchFeatureDefinitions())
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleDelete(key, displayName) {
    if (!confirm(`'${displayName}' feature를 삭제하시겠습니까?`)) return
    try {
      await deleteFeatureDefinition(key)
      load()
    } catch (e) {
      alert(e.message)
    }
  }

  async function handleSave(formData) {
    if (editingFeature) {
      await updateFeatureDefinition(editingFeature.key, formData)
    } else {
      await createFeatureDefinition(formData)
    }
    setShowForm(false)
    setEditingFeature(null)
    load()
  }

  const filtered = features.filter(
    f => categoryTab === '전체' || f.category === categoryTab
  )

  return (
    <div>
      <div className="section-header">
        <h2>Feature Definition 관리</h2>
        <button
          className="btn-primary"
          onClick={() => { setEditingFeature(null); setShowForm(true) }}
        >
          + 새 Feature
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="tabs" style={{ marginBottom: 16 }}>
        {['전체', ...CATEGORIES].map(tab => (
          <button
            key={tab}
            className={`tab ${categoryTab === tab ? 'active' : ''}`}
            onClick={() => setCategoryTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Key</th><th>표시명</th><th>타입</th><th>카테고리</th><th>기본값</th><th>액션</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(fd => (
              <tr key={fd.key}>
                <td><code>{fd.key}</code></td>
                <td>{fd.display_name}</td>
                <td><span className="tag">{fd.value_type}</span></td>
                <td>{fd.category}</td>
                <td style={{ color: '#6b7280' }}>{fd.default_value || '—'}</td>
                <td>
                  <button
                    className="btn-sm"
                    onClick={() => { setEditingFeature(fd); setShowForm(true) }}
                  >
                    편집
                  </button>
                  <button
                    className="btn-sm btn-danger"
                    disabled={fd.is_builtin}
                    title={fd.is_builtin ? '기본 제공 feature는 삭제할 수 없습니다' : ''}
                    onClick={() => handleDelete(fd.key, fd.display_name)}
                  >
                    삭제
                  </button>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', color: '#999', padding: '24px' }}>
                  등록된 feature가 없습니다
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showForm && (
        <FeatureFormPanel
          feature={editingFeature}
          onSave={handleSave}
          onClose={() => { setShowForm(false); setEditingFeature(null) }}
        />
      )}
    </div>
  )
}

function FeatureFormPanel({ feature, onSave, onClose }) {
  const isEdit = !!feature
  const [key, setKey] = useState(feature?.key || '')
  const [displayName, setDisplayName] = useState(feature?.display_name || '')
  const [description, setDescription] = useState(feature?.description || '')
  const [valueType, setValueType] = useState(feature?.value_type || 'categorical')
  const [valueOptions, setValueOptions] = useState(
    feature?.value_options?.join(', ') || ''
  )
  const [rangeMin, setRangeMin] = useState(feature?.value_range?.min ?? 0)
  const [rangeMax, setRangeMax] = useState(feature?.value_range?.max ?? 1)
  const [defaultValue, setDefaultValue] = useState(feature?.default_value || '')
  const [category, setCategory] = useState(feature?.category || '기질')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const data = { display_name: displayName, description, default_value: defaultValue, category }
      if (!isEdit) {
        data.key = key
        data.value_type = valueType
      }
      if (valueType === 'categorical') {
        data.value_options = valueOptions.split(',').map(s => s.trim()).filter(Boolean)
      } else if (valueType === 'numeric') {
        data.value_range = { min: parseFloat(rangeMin), max: parseFloat(rangeMax) }
      }
      await onSave(data)
    } catch (e) {
      setError(e.message)
      setSaving(false)
    }
  }

  return (
    <div className="overlay">
      <div className="panel">
        <div className="panel-header">
          <h3>{isEdit ? 'Feature 편집' : '새 Feature 추가'}</h3>
          <button onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit} className="form">
          <label>
            Key *
            <input
              required
              value={key}
              onChange={e => setKey(e.target.value)}
              disabled={isEdit}
              placeholder="snake_case 형식"
            />
          </label>
          <label>
            표시명 *
            <input required value={displayName} onChange={e => setDisplayName(e.target.value)} />
          </label>
          <label>
            설명 *
            <textarea
              required
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={3}
            />
          </label>
          <label>
            타입 *
            <select
              value={valueType}
              onChange={e => setValueType(e.target.value)}
              disabled={isEdit}
            >
              {VALUE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>

          {valueType === 'categorical' && (
            <label>
              선택지 (쉼표로 구분)
              <input
                value={valueOptions}
                onChange={e => setValueOptions(e.target.value)}
                placeholder="낮음, 보통, 높음"
              />
            </label>
          )}

          {valueType === 'numeric' && (
            <div style={{ display: 'flex', gap: 12 }}>
              <label style={{ flex: 1 }}>
                최소값
                <input
                  type="number" step="0.1"
                  value={rangeMin}
                  onChange={e => setRangeMin(e.target.value)}
                />
              </label>
              <label style={{ flex: 1 }}>
                최대값
                <input
                  type="number" step="0.1"
                  value={rangeMax}
                  onChange={e => setRangeMax(e.target.value)}
                />
              </label>
            </div>
          )}

          <label>
            기본값
            <input value={defaultValue} onChange={e => setDefaultValue(e.target.value)} />
          </label>
          <label>
            카테고리 *
            <select value={category} onChange={e => setCategory(e.target.value)}>
              {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>

          {error && <div className="form-error">{error}</div>}
          <div className="form-actions">
            <button type="button" onClick={onClose}>취소</button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? '저장 중...' : '저장'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
