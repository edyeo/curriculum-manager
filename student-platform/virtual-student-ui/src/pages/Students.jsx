import { useState, useEffect } from 'react'
import {
  fetchStudents, fetchStudent, createStudent, updateStudent,
  deleteStudent, fetchFeatureDefinitions, generateStudents,
} from '../api/client'
import { useSubject } from '../context/SubjectContext'

export default function Students() {
  const { selectedId: subjectId, subjects } = useSubject()
  const [students, setStudents] = useState({ total: 0, items: [] })
  const [features, setFeatures] = useState([])
  const [page, setPage] = useState(1)
  const [showForm, setShowForm] = useState(false)
  const [showGenerate, setShowGenerate] = useState(false)
  const [editingStudent, setEditingStudent] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => { setPage(1) }, [subjectId])
  useEffect(() => { load() }, [subjectId, page])

  async function load() {
    try {
      const params = { page, page_size: 20 }
      if (subjectId) params.subject_id = subjectId
      const [data, fds] = await Promise.all([
        fetchStudents(params),
        fetchFeatureDefinitions(),
      ])
      setStudents(data)
      setFeatures(fds)
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleDelete(id, name) {
    if (!confirm(`'${name}' 학생을 삭제하시겠습니까?`)) return
    try {
      await deleteStudent(id)
      load()
    } catch (e) {
      alert(e.message)
    }
  }

  async function handleEdit(student) {
    try {
      const detail = await fetchStudent(student.id)
      setEditingStudent(detail)
      setShowForm(true)
    } catch (e) {
      alert(e.message)
    }
  }

  async function handleSave(formData) {
    if (editingStudent) {
      await updateStudent(editingStudent.id, formData)
    } else {
      await createStudent(formData)
    }
    setShowForm(false)
    setEditingStudent(null)
    load()
  }

  const totalPages = Math.ceil(students.total / 20)

  return (
    <div>
      <div className="section-header">
        <h2>가상 학생 관리</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn-secondary" onClick={() => setShowGenerate(true)}>
            학생 생성
          </button>
          <button className="btn-primary" onClick={() => { setEditingStudent(null); setShowForm(true) }}>
            + 새 학생
          </button>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>#</th><th>이름</th><th>설명</th><th>Subject</th><th>생성일</th><th>액션</th>
            </tr>
          </thead>
          <tbody>
            {students.items.map((s, i) => (
              <tr key={s.id}>
                <td>{(page - 1) * 20 + i + 1}</td>
                <td>{s.name}</td>
                <td style={{ color: '#6b7280', fontSize: '0.875rem' }}>{s.description || '—'}</td>
                <td><span className="tag">{s.subject_id}</span></td>
                <td>{new Date(s.created_at).toLocaleDateString('ko-KR')}</td>
                <td>
                  <button className="btn-sm" onClick={() => handleEdit(s)}>편집</button>
                  <button className="btn-sm btn-danger" onClick={() => handleDelete(s.id, s.name)}>
                    삭제
                  </button>
                </td>
              </tr>
            ))}
            {students.items.length === 0 && (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', color: '#999', padding: '24px' }}>
                  학생이 없습니다
                </td>
              </tr>
            )}
          </tbody>
        </table>
        {totalPages > 1 && (
          <div className="pagination">
            <button disabled={page === 1} onClick={() => setPage(p => p - 1)}>‹</button>
            <span>{page} / {totalPages}</span>
            <button disabled={page === totalPages} onClick={() => setPage(p => p + 1)}>›</button>
          </div>
        )}
      </div>

      {showForm && (
        <StudentFormPanel
          student={editingStudent}
          features={features}
          onSave={handleSave}
          onClose={() => { setShowForm(false); setEditingStudent(null) }}
        />
      )}

      {showGenerate && (
        <GenerateModal
          onGenerate={async (params) => {
            await generateStudents(params)
            setShowGenerate(false)
            load()
          }}
          onClose={() => setShowGenerate(false)}
        />
      )}
    </div>
  )
}

function StudentFormPanel({ student, features, onSave, onClose }) {
  const { selectedId: ctxSubjectId } = useSubject()
  const [name, setName] = useState(student?.name || '')
  const [description, setDescription] = useState(student?.description || '')
  const [subjectId, setSubjectId] = useState(student?.subject_id || ctxSubjectId)
  const [featureValues, setFeatureValues] = useState(() => {
    const map = {}
    if (student?.feature_values) {
      student.feature_values.forEach(fv => { map[fv.feature_key] = fv.value })
    } else {
      features.forEach(fd => { if (fd.default_value) map[fd.key] = fd.default_value })
    }
    return map
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const fvList = Object.entries(featureValues)
        .filter(([, v]) => v !== '')
        .map(([feature_key, value]) => ({ feature_key, value }))
      await onSave({ name, description, subject_id: subjectId, feature_values: fvList })
    } catch (e) {
      setError(e.message)
      setSaving(false)
    }
  }

  const setFv = (key, val) => setFeatureValues(prev => ({ ...prev, [key]: val }))

  return (
    <div className="overlay">
      <div className="panel">
        <div className="panel-header">
          <h3>{student ? '학생 편집' : '새 학생 생성'}</h3>
          <button onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit} className="form">
          <label>
            이름 *
            <input required value={name} onChange={e => setName(e.target.value)} />
          </label>
          <label>
            설명
            <input value={description} onChange={e => setDescription(e.target.value)} />
          </label>
          <label>
            Subject *
            <input required value={subjectId} onChange={e => setSubjectId(e.target.value)} />
          </label>

          <hr />
          <h4>Feature 값</h4>

          {features.map(fd => (
            <label key={fd.key}>
              {fd.display_name}
              <span className="badge-sm" style={{ marginLeft: 4 }}>{fd.category}</span>
              <FeatureValueInput
                fd={fd}
                value={featureValues[fd.key] ?? fd.default_value ?? ''}
                onChange={v => setFv(fd.key, v)}
              />
            </label>
          ))}

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

function FeatureValueInput({ fd, value, onChange }) {
  if (fd.value_type === 'categorical' && fd.value_options) {
    return (
      <select value={value} onChange={e => onChange(e.target.value)}>
        {fd.value_options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
      </select>
    )
  }

  if (fd.value_type === 'numeric') {
    const min = fd.value_range?.min ?? 0
    const max = fd.value_range?.max ?? 1
    const num = parseFloat(value) || min
    return (
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <input
          type="range" min={min} max={max} step={0.05}
          value={num}
          onChange={e => onChange(e.target.value)}
          style={{ flex: 1 }}
        />
        <span style={{ width: 36, textAlign: 'right', fontSize: '0.875rem' }}>
          {num.toFixed(2)}
        </span>
      </div>
    )
  }

  return <input value={value} onChange={e => onChange(e.target.value)} />
}

function GenerateModal({ onGenerate, onClose }) {
  const { selectedId: subjectId, selected } = useSubject()
  const [count, setCount] = useState(10)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setGenerating(true)
    setError(null)
    try {
      await onGenerate({ subject_id: subjectId, count: Number(count) })
    } catch (e) {
      setError(e.message)
      setGenerating(false)
    }
  }

  return (
    <div className="overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h3>학생 자동 생성</h3>
          <button onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body">
          <div className="modal-subject-badge">
            <span>Subject</span>
            <span className="tag">{selected?.name ?? subjectId}</span>
          </div>
          <label>
            생성 인원 *
            <input
              type="number"
              required
              min={1}
              max={200}
              value={count}
              onChange={e => setCount(e.target.value)}
            />
            <span className="input-hint">1~200명</span>
          </label>
          {error && <div className="form-error">{error}</div>}
          <div className="modal-actions">
            <button type="button" onClick={onClose}>취소</button>
            <button type="submit" className="btn-primary" disabled={generating || !subjectId}>
              {generating ? `생성 중...` : `${count}명 생성`}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
