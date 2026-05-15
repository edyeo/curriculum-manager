import React, { useState, useEffect } from 'react'
import * as api from '../services/contentsApi.js'

const RELATION_TYPES = ['requires', 'implemented_by', 'evolves_to']

export default function NodePanel({ subjectId, nodeId, nodes, edges, onClose, onNodeUpdated, onNodeDeleted, onEdgeCreated, onEdgeDeleted }) {
  const node = nodes.find(n => n.id === nodeId)
  const [tab, setTab] = useState('detail')
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [saving, setSaving] = useState(false)

  const [questions, setQuestions] = useState([])
  const [loadingQ, setLoadingQ] = useState(false)
  const [generatingQ, setGeneratingQ] = useState(false)

  const [addRelSource, setAddRelSource] = useState('')
  const [addRelType, setAddRelType] = useState('requires')
  const [addingRel, setAddingRel] = useState(false)

  const nodeEdges = edges.filter(e => e.source_id === nodeId || e.target_id === nodeId)

  useEffect(() => {
    if (!node) return
    setName(node.name)
    setDesc(node.description || '')
    setTab('detail')
  }, [nodeId])

  useEffect(() => {
    if (tab === 'questions' && nodeId) loadQuestions()
  }, [tab, nodeId])

  const loadQuestions = async () => {
    setLoadingQ(true)
    try {
      const data = await api.getQuestions(subjectId, nodeId)
      setQuestions(data?.data?.questions || data?.questions || [])
    } catch { setQuestions([]) } finally { setLoadingQ(false) }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await api.updateNode(subjectId, nodeId, { name, description: desc })
      onNodeUpdated(updated)
    } finally { setSaving(false) }
  }

  const handleDelete = async () => {
    if (!confirm(`"${node.name}" 노드를 삭제할까요?`)) return
    await api.deleteNode(subjectId, nodeId)
    onNodeDeleted(nodeId)
    onClose()
  }

  const handleAddRelation = async () => {
    if (!addRelSource) return
    setAddingRel(true)
    try {
      const edge = await api.createEdge(subjectId, { source_id: nodeId, target_id: addRelSource, relation_type: addRelType, logic_basis: '' })
      onEdgeCreated(edge)
      setAddRelSource('')
    } finally { setAddingRel(false) }
  }

  const handleDeleteEdge = async (edgeId) => {
    await api.deleteEdge(subjectId, edgeId)
    onEdgeDeleted(edgeId)
  }

  const handleGenerateQ = async () => {
    setGeneratingQ(true)
    try {
      await api.generateQuestions(subjectId, nodeId)
      await loadQuestions()
    } finally { setGeneratingQ(false) }
  }

  if (!node) return null

  return (
    <div className="node-panel">
      <div className="panel-header">
        <h3>{node.name}</h3>
        <button className="btn-close" onClick={onClose}>✕</button>
      </div>
      <div className="panel-tabs">
        {['detail', 'relations', 'questions'].map(t => (
          <button key={t} className={`panel-tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {t === 'detail' ? '상세' : t === 'relations' ? '관계' : '문제'}
          </button>
        ))}
      </div>

      <div className="panel-body">
        {tab === 'detail' && (
          <>
            <label>이름</label>
            <input value={name} onChange={e => setName(e.target.value)} />
            <label>타입</label>
            <div><span className={`type-badge type-${node.type}`}>{node.type}</span></div>
            <label>Depth</label>
            <div style={{ color: '#94a3b8', fontSize: 13 }}>{node.depth}</div>
            <label>설명</label>
            <textarea value={desc} onChange={e => setDesc(e.target.value)} rows={4} />
            {nodeEdges.length > 0 && (
              <div className="detail-links">
                <label>연결 ({nodeEdges.length})</label>
                {nodeEdges.map(e => {
                  const isSource = e.source_id === nodeId
                  const otherId = isSource ? e.target_id : e.source_id
                  const other = nodes.find(n => n.id === otherId)
                  return (
                    <div key={e.id} className="detail-link-item">
                      <span className="detail-link-arrow">{isSource ? '→' : '←'}</span>
                      <span className="detail-link-rel">{e.relation_type}</span>
                      <span className="detail-link-name">{other?.name || otherId}</span>
                    </div>
                  )
                })}
              </div>
            )}
          </>
        )}

        {tab === 'relations' && (
          <>
            {nodeEdges.length === 0 && <p className="empty-msg">관계 없음</p>}
            {nodeEdges.map(e => {
              const isSource = e.source_id === nodeId
              const otherId = isSource ? e.target_id : e.source_id
              const other = nodes.find(n => n.id === otherId)
              return (
                <div key={e.id} className="relation-item">
                  <div>
                    <span style={{ color: '#e2e8f0' }}>{other?.name || otherId}</span>
                    <br />
                    <span className="relation-type">{isSource ? '→' : '←'} {e.relation_type}</span>
                  </div>
                  <button className="btn-del-relation" onClick={() => handleDeleteEdge(e.id)}>삭제</button>
                </div>
              )
            })}
            <div className="add-relation">
              <label style={{ marginTop: 16 }}>관계 추가</label>
              <select value={addRelSource} onChange={e => setAddRelSource(e.target.value)}>
                <option value="">노드 선택...</option>
                {nodes.filter(n => n.id !== nodeId).map(n => (
                  <option key={n.id} value={n.id}>{n.name}</option>
                ))}
              </select>
              <select value={addRelType} onChange={e => setAddRelType(e.target.value)}>
                {RELATION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <button className="btn-primary" onClick={handleAddRelation} disabled={!addRelSource || addingRel}>
                {addingRel ? '추가 중...' : '추가'}
              </button>
            </div>
          </>
        )}

        {tab === 'questions' && (
          <>
            <button className="btn-primary" onClick={handleGenerateQ} disabled={generatingQ} style={{ marginBottom: 12 }}>
              {generatingQ ? '생성 중...' : '문제 생성'}
            </button>
            {loadingQ && <p className="empty-msg">로딩 중...</p>}
            {!loadingQ && questions.length === 0 && <p className="empty-msg">문제 없음 — 생성하기</p>}
            {questions.map((q, i) => (
              <div key={q.id || i} className="question-item">
                <span className={`q-difficulty q-${q.difficulty_level}`}>{q.difficulty_level}</span>
                {q.question_text}
              </div>
            ))}
          </>
        )}
      </div>

      <div className="panel-footer">
        {tab === 'detail' && (
          <>
            <button className="btn-primary" onClick={handleSave} disabled={saving}>{saving ? '저장 중...' : '저장'}</button>
            <button className="btn-danger" onClick={handleDelete}>노드 삭제</button>
          </>
        )}
      </div>
    </div>
  )
}
