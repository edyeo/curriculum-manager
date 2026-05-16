import React, { useState, useEffect } from 'react'
import LoginPage from './LoginPage.jsx'
import NodeTable from './components/NodeTable.jsx'
import NodePanel from './components/NodePanel.jsx'
import GraphView from './components/GraphView.jsx'
import ResearchTab from './components/ResearchTab.jsx'
import AiLinkModal from './components/AiLinkModal.jsx'
import * as api from './services/contentsApi.js'

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('cm_token'))
  const [subjects, setSubjects] = useState([])
  const [selectedSubjectId, setSelectedSubjectId] = useState(null)
  const [currentTab, setCurrentTab] = useState('editor')
  const [nodes, setNodes] = useState([])
  const [edges, setEdges] = useState([])
  const [selectedNodeId, setSelectedNodeId] = useState(null)
  const [expanding, setExpanding] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [aiLinking, setAiLinking] = useState(false)
  const [showAiLink, setShowAiLink] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [creating, setCreating] = useState(false)

  const handleLogin = () => setToken(localStorage.getItem('cm_token'))
  const handleLogout = () => { localStorage.removeItem('cm_token'); setToken(null) }

  useEffect(() => {
    if (!token) return
    api.getSubjects().then(d => {
      const list = d.subjects || []
      setSubjects(list)
      if (list.length > 0) setSelectedSubjectId(list[0].id)
    }).catch(() => handleLogout())
  }, [token])

  useEffect(() => {
    if (!selectedSubjectId) { setNodes([]); setEdges([]); return }
    setSelectedNodeId(null)
    api.getNodes(selectedSubjectId).then(d => setNodes(d.nodes || [])).catch(() => setNodes([]))
    api.getEdges(selectedSubjectId).then(d => setEdges(d.edges || [])).catch(() => setEdges([]))
  }, [selectedSubjectId])

  const handleCreateSubject = async () => {
    if (!newName.trim()) return
    setCreating(true)
    try {
      const s = await api.createSubject(newName, newDesc)
      setSubjects(prev => [...prev, s])
      setSelectedSubjectId(s.id)
      setShowCreate(false)
      setNewName('')
      setNewDesc('')
    } finally { setCreating(false) }
  }

  const handleDeleteSubject = async () => {
    if (!selectedSubjectId) return
    const s = subjects.find(s => s.id === selectedSubjectId)
    if (!confirm(`"${s?.name}" Subject를 삭제할까요?`)) return
    await api.deleteSubject(selectedSubjectId)
    const next = subjects.filter(s => s.id !== selectedSubjectId)
    setSubjects(next)
    setSelectedSubjectId(next[0]?.id || null)
  }

  const handleAddNode = async (nodeData) => {
    const n = await api.createNode(selectedSubjectId, nodeData)
    setNodes(prev => [...prev, { ...n, edge_count: 0 }])
  }

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      await api.generateCurriculum(selectedSubjectId)
      const [nd, ed] = await Promise.all([
        api.getNodes(selectedSubjectId),
        api.getEdges(selectedSubjectId),
      ])
      setNodes(nd.nodes || [])
      setEdges(ed.edges || [])
    } finally { setGenerating(false) }
  }

  const handleExpand = async () => {
    setExpanding(true)
    try {
      await api.expandCurriculum(selectedSubjectId)
      const d = await api.getNodes(selectedSubjectId)
      setNodes(d.nodes || [])
    } finally { setExpanding(false) }
  }

  const handleAiLink = async (payload) => {
    setAiLinking(true)
    try {
      const res = await api.aiLinkCurriculum(selectedSubjectId, payload)
      const ed = await api.getEdges(selectedSubjectId)
      setEdges(ed.edges || [])
      return res
    } finally {
      setAiLinking(false)
    }
  }

  const handleNodeUpdated = (updated) => {
    setNodes(prev => prev.map(n => n.id === updated.id ? { ...n, ...updated } : n))
  }

  const handleNodeDeleted = (nodeId) => {
    setNodes(prev => prev.filter(n => n.id !== nodeId))
    setEdges(prev => prev.filter(e => e.source_id !== nodeId && e.target_id !== nodeId))
  }

  const handleEdgeCreated = (edge) => setEdges(prev => [...prev, edge])
  const handleEdgeDeleted = (edgeId) => setEdges(prev => prev.filter(e => e.id !== edgeId))

  if (!token) return <LoginPage onLogin={handleLogin} />

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header className="app-header">
        <h1>Contents Manager</h1>
        <select className="subject-select" value={selectedSubjectId || ''} onChange={e => setSelectedSubjectId(e.target.value)}>
          {subjects.length === 0 && <option value="">Subject 없음</option>}
          {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <button className="btn-new-subject" onClick={() => setShowCreate(true)}>+ 새 Subject</button>
        {selectedSubjectId && (
          <button className="btn-cancel" onClick={handleDeleteSubject} style={{ background: '#2d3748', color: '#94a3b8' }}>삭제</button>
        )}
        <button className="btn-logout" onClick={handleLogout}>로그아웃</button>
      </header>

      {/* Tabs */}
      <nav className="tab-nav">
        {['editor', 'graph', 'research'].map(t => (
          <button key={t} className={`tab-btn ${currentTab === t ? 'active' : ''}`} onClick={() => setCurrentTab(t)}>
            {t === 'editor' ? '편집' : t === 'graph' ? '그래프' : '리서치'}
          </button>
        ))}
      </nav>

      {/* Main */}
      <main className="app-main">
        {!selectedSubjectId ? (
          <div className="no-subject">Subject를 선택하거나 새로 만드세요.</div>
        ) : (
          <>
            {currentTab === 'editor' && (
              <div className="editor-tab">
                <div className="table-area">
                  <NodeTable
                    nodes={nodes}
                    selectedNodeId={selectedNodeId}
                    onSelectNode={id => setSelectedNodeId(prev => prev === id ? null : id)}
                    onAddNode={handleAddNode}
                    onGenerate={handleGenerate}
                    generating={generating}
                    onExpand={handleExpand}
                    expanding={expanding}
                    onAiLink={() => setShowAiLink(true)}
                    aiLinking={aiLinking}
                  />
                </div>
                {selectedNodeId && (
                  <NodePanel
                    subjectId={selectedSubjectId}
                    nodeId={selectedNodeId}
                    nodes={nodes}
                    edges={edges}
                    onClose={() => setSelectedNodeId(null)}
                    onNodeUpdated={handleNodeUpdated}
                    onNodeDeleted={handleNodeDeleted}
                    onEdgeCreated={handleEdgeCreated}
                    onEdgeDeleted={handleEdgeDeleted}
                  />
                )}
              </div>
            )}
            {currentTab === 'graph' && <GraphView nodes={nodes} edges={edges} />}
            {currentTab === 'research' && <ResearchTab subjectId={selectedSubjectId} />}
          </>
        )}
      </main>

      {/* AI Link Modal */}
      {showAiLink && (
        <AiLinkModal
          nodes={nodes}
          onConfirm={handleAiLink}
          onClose={() => setShowAiLink(false)}
        />
      )}

      {/* Create Subject Modal */}
      {showCreate && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setShowCreate(false)}>
          <div className="modal-box">
            <h2>새 Subject 생성</h2>
            <label>이름 *</label>
            <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="예: Distributed Systems" autoFocus />
            <label>설명 (선택)</label>
            <textarea value={newDesc} onChange={e => setNewDesc(e.target.value)} rows={3} placeholder="커리큘럼 주제 설명..." />
            <div className="modal-actions">
              <button className="btn-cancel" onClick={() => setShowCreate(false)}>취소</button>
              <button className="btn-primary" onClick={handleCreateSubject} disabled={creating || !newName.trim()}>
                {creating ? '생성 중...' : '생성'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
