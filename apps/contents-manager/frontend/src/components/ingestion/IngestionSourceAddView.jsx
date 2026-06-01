import React, { useEffect, useState } from 'react'
import * as api from '../../services/contentsApi.js'

function DropZone({ file, onFile }) {
  const [dragOver, setDragOver] = useState(false)
  const handleDrop = (e) => { e.preventDefault(); setDragOver(false); if (e.dataTransfer.files[0]) onFile(e.dataTransfer.files[0]) }
  const handleClick = () => {
    const inp = document.createElement('input')
    inp.type = 'file'; inp.accept = '.pdf,.txt,.md'
    inp.onchange = (e) => { if (e.target.files[0]) onFile(e.target.files[0]) }
    inp.click()
  }
  return (
    <div
      onDrop={handleDrop}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onClick={handleClick}
      style={{
        border: `2px dashed ${dragOver ? '#4f46e5' : '#1f2937'}`, borderRadius: 8,
        padding: '28px 16px', textAlign: 'center', cursor: 'pointer',
        background: dragOver ? '#1a1d3a' : '#111827',
      }}
    >
      {file ? (
        <div>
          <div style={{ fontSize: 13, color: '#e2e8f0', marginBottom: 4 }}>{file.name}</div>
          <div style={{ fontSize: 11, color: '#4b5563' }}>{(file.size / 1024).toFixed(1)} KB · 클릭하여 변경</div>
        </div>
      ) : (
        <div>
          <div style={{ fontSize: 22, marginBottom: 8 }}>📄</div>
          <div style={{ fontSize: 13, color: '#4b5563' }}>파일을 드래그하거나 클릭하여 선택</div>
          <div style={{ fontSize: 11, color: '#374151', marginTop: 4 }}>PDF · TXT · MD</div>
        </div>
      )}
    </div>
  )
}

export default function IngestionSourceAddView({ onSaved }) {
  const [sourceType, setSourceType] = useState('text')
  const [source, setSource] = useState('')
  const [dropFile, setDropFile] = useState(null)
  const [subjectId, setSubjectId] = useState('')
  const [subjects, setSubjects] = useState([])
  const [saving, setSaving] = useState(false)
  const [savedId, setSavedId] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getSubjects().then(d => setSubjects(d.subjects || [])).catch(() => {})
  }, [])

  const handleSave = async () => {
    if (sourceType === 'file' ? !dropFile : !source.trim()) return
    setSaving(true); setError(''); setSavedId(null)
    try {
      const r = sourceType === 'file'
        ? await api.saveIngestionSourceUpload(dropFile, subjectId || null)
        : await api.saveIngestionSource(sourceType, source, subjectId || null)
      setSavedId(r.id)
      setSource(''); setDropFile(null)
      onSaved?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const placeholder = { text: '분석할 텍스트를 입력하세요...', url: 'https://example.com/article' }[sourceType]

  return (
    <div style={{ maxWidth: 600, padding: 24 }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0', marginBottom: 20 }}>새 소스 추가</div>

      {/* Subject */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6 }}>대상 Subject <span style={{ color: '#374151' }}>(선택)</span></div>
        <select
          value={subjectId}
          onChange={e => setSubjectId(e.target.value)}
          style={{ width: '100%', fontSize: 12, background: '#1a1d2e', color: subjectId ? '#e2e8f0' : '#4b5563' }}
        >
          <option value="">-- Subject 미지정 --</option>
          {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </div>

      {/* Source Type */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6 }}>소스 타입</div>
        <div style={{ display: 'flex', gap: 6 }}>
          {['text', 'url', 'file'].map(t => (
            <button key={t} onClick={() => { setSourceType(t); setSource(''); setDropFile(null) }} style={{
              padding: '5px 14px', borderRadius: 5, fontSize: 12, border: 'none', cursor: 'pointer',
              background: sourceType === t ? '#4f46e5' : '#1e2130',
              color: sourceType === t ? '#fff' : '#94a3b8',
            }}>{t}</button>
          ))}
        </div>
      </div>

      {/* Source Input */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6 }}>
          {sourceType === 'text' ? '텍스트' : sourceType === 'url' ? 'URL' : '파일'}
        </div>
        {sourceType === 'text' ? (
          <textarea value={source} onChange={e => setSource(e.target.value)} placeholder={placeholder}
            rows={8} style={{ width: '100%', resize: 'vertical', fontSize: 12, boxSizing: 'border-box' }} />
        ) : sourceType === 'url' ? (
          <input value={source} onChange={e => setSource(e.target.value)} placeholder={placeholder}
            style={{ width: '100%', fontSize: 12, boxSizing: 'border-box' }} />
        ) : (
          <DropZone file={dropFile} onFile={setDropFile} />
        )}
      </div>

      <button
        onClick={handleSave}
        disabled={saving || (sourceType === 'file' ? !dropFile : !source.trim())}
        style={{
          width: '100%', padding: '10px', borderRadius: 6, fontSize: 13, fontWeight: 600, border: 'none',
          background: saving ? '#374151' : '#4f46e5',
          color: saving ? '#9ca3af' : '#fff',
          cursor: saving ? 'default' : 'pointer',
        }}
      >
        {saving ? '저장 중...' : '소스 저장'}
      </button>

      {error && (
        <div style={{ marginTop: 10, padding: '8px 12px', background: '#3b0764', borderRadius: 6, color: '#e879f9', fontSize: 12 }}>
          {error}
        </div>
      )}

      {savedId && (
        <div style={{ marginTop: 10, padding: '8px 12px', background: '#052e16', borderRadius: 6, color: '#4ade80', fontSize: 12 }}>
          저장 완료 — Source 조회에서 Dry-run 또는 파싱 등록을 진행하세요.
        </div>
      )}
    </div>
  )
}
