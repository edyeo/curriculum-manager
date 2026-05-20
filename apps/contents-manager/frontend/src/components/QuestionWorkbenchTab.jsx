import React, { useState, useEffect, useRef } from 'react'
import * as api from '../services/contentsApi.js'

// ── SubgraphMiniMap (Feature 2.2 시각화) ──────────────────────────────────────
function SubgraphMiniMap({ candidate, onSelect, isSelected }) {
  const typeColor = { Seed: '#f6ad55', Concept: '#68d391', TechStack: '#63b3ed' }
  return (
    <div
      onClick={() => onSelect(candidate)}
      style={{
        border: `2px solid ${isSelected ? '#4299e1' : '#2d3748'}`,
        borderRadius: 8, padding: 12, cursor: 'pointer', marginBottom: 8,
        background: isSelected ? '#1a2744' : '#1a202c',
      }}
    >
      <div style={{ color: '#a0aec0', fontSize: 11, marginBottom: 6 }}>
        점수: {(candidate.score * 100).toFixed(0)}% · {candidate.nodes.length}개 노드 · {candidate.rationale}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
        {candidate.nodes.slice(0, 8).map(n => (
          <span
            key={n.id}
            style={{
              background: typeColor[n.type] || '#4a5568', color: '#1a202c',
              fontSize: 10, padding: '2px 6px', borderRadius: 12, fontWeight: 600,
            }}
          >
            {n.name}
          </span>
        ))}
        {candidate.nodes.length > 8 && (
          <span style={{ color: '#718096', fontSize: 10 }}>+{candidate.nodes.length - 8}개</span>
        )}
      </div>
    </div>
  )
}

// ── QuestionPreviewEditor (Feature 2.4) ───────────────────────────────────────
function QuestionPreviewEditor({ question, entityId, blueprintId, onSaved, onDiscard }) {
  const [q, setQ] = useState(question)
  const [saving, setSaving] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [savedId, setSavedId] = useState(null)

  const handleSaveDraft = async () => {
    setSaving(true)
    try {
      const body = {
        entity_id: entityId,
        blueprint_id: blueprintId || null,
        question_text: q.question_text,
        options: q.options,
        correct_answer: q.correct_answer,
        explanation: q.explanation,
        node_snapshot: q.node_snapshot,
      }
      const saved = await api.saveWorkbenchQuestion(body)
      setSavedId(saved.id)
    } finally { setSaving(false) }
  }

  const handlePublish = async () => {
    if (!savedId) {
      alert('먼저 저장하세요.')
      return
    }
    setPublishing(true)
    try {
      await api.publishWorkbenchQuestion(savedId)
      onSaved()
    } finally { setPublishing(false) }
  }

  const updateOption = (idx, field, value) => {
    setQ(prev => ({
      ...prev,
      options: prev.options.map((o, i) => i === idx ? { ...o, [field]: value } : o),
    }))
  }

  return (
    <div style={{ background: '#1a202c', borderRadius: 8, padding: 20, marginBottom: 16, border: '1px solid #2d3748' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <span style={{ color: '#90cdf4', fontSize: 12, fontWeight: 600 }}>
          {q.difficulty_level?.toUpperCase()}
          {savedId && <span style={{ color: '#68d391', marginLeft: 8 }}>저장됨</span>}
        </span>
        <button onClick={onDiscard} style={{ background: 'none', border: 'none', color: '#718096', cursor: 'pointer', fontSize: 12 }}>제거</button>
      </div>

      {/* 지문 */}
      <textarea
        value={q.question_text}
        onChange={e => setQ(prev => ({ ...prev, question_text: e.target.value }))}
        rows={3}
        style={textareaStyle}
        placeholder="지문..."
      />

      {/* 선지 */}
      <div style={{ marginTop: 12 }}>
        {(q.options || []).map((opt, i) => (
          <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'flex-start' }}>
            <span style={{
              minWidth: 22, height: 22, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 11, fontWeight: 700,
              background: opt.is_correct ? '#276749' : '#2d3748',
              color: opt.is_correct ? '#68d391' : '#a0aec0',
            }}>
              {opt.label}
            </span>
            <div style={{ flex: 1 }}>
              <input
                value={opt.text}
                onChange={e => updateOption(i, 'text', e.target.value)}
                style={{ ...inputStyle, marginBottom: 4 }}
                placeholder={`선지 ${opt.label}`}
              />
              <input
                value={opt.rationale || ''}
                onChange={e => updateOption(i, 'rationale', e.target.value)}
                style={{ ...inputStyle, fontSize: 11, color: '#a0aec0' }}
                placeholder="rationale (KG 근거)"
              />
            </div>
            <input
              type="checkbox"
              checked={opt.is_correct || false}
              onChange={e => updateOption(i, 'is_correct', e.target.checked)}
              title="정답"
            />
          </div>
        ))}
      </div>

      {/* 해설 */}
      <textarea
        value={q.explanation || ''}
        onChange={e => setQ(prev => ({ ...prev, explanation: e.target.value }))}
        rows={2}
        style={{ ...textareaStyle, marginTop: 12, color: '#a0aec0', fontSize: 12 }}
        placeholder="종합 해설 (트레이드오프 포함)..."
      />

      {/* 액션 */}
      <div style={{ display: 'flex', gap: 8, marginTop: 14, justifyContent: 'flex-end' }}>
        <button className="btn-cancel" onClick={handleSaveDraft} disabled={saving} style={{ fontSize: 12 }}>
          {saving ? '저장 중...' : '초안 저장'}
        </button>
        <button
          className="btn-primary"
          onClick={handlePublish}
          disabled={publishing || !savedId}
          style={{ fontSize: 12, background: publishing ? '#2d6a4f' : '#276749' }}
        >
          {publishing ? '등록 중...' : '최종 등록'}
        </button>
      </div>
    </div>
  )
}

// ── Main QuestionWorkbenchTab ─────────────────────────────────────────────────
export default function QuestionWorkbenchTab({ nodes }) {
  const [blueprints, setBlueprints] = useState([])
  const [selectedBlueprint, setSelectedBlueprint] = useState('')
  const [blueprintDetail, setBlueprintDetail] = useState(null)  // {matrix, integration_items}
  const [selectedCogTarget, setSelectedCogTarget] = useState(null)  // {layer, stage}
  const [selectedItem, setSelectedItem] = useState('')
  const [pathMode, setPathMode] = useState('A')  // 'A' | 'B'
  const [questionType, setQuestionType] = useState('MCQ')

  // Path A
  const [selectedEntityId, setSelectedEntityId] = useState('')

  // Path B subgraph search
  const [searchLoading, setSearchLoading] = useState(false)
  const [subgraphCandidates, setSubgraphCandidates] = useState([])
  const [selectedSubgraph, setSelectedSubgraph] = useState(null)

  // Generation
  const [generating, setGenerating] = useState(false)
  const [genError, setGenError] = useState('')
  const [progress, setProgress] = useState('')
  const [generatedQuestions, setGeneratedQuestions] = useState([])
  const [discardedIdx, setDiscardedIdx] = useState(new Set())

  // Published list
  const [publishedList, setPublishedList] = useState([])
  const [showPublished, setShowPublished] = useState(false)
  const pollRef = useRef(null)

  useEffect(() => {
    api.getBlueprints().then(d => setBlueprints(d.blueprints || []))
  }, [])

  useEffect(() => {
    if (!selectedBlueprint) {
      setBlueprintDetail(null)
      setSelectedItem('')
      setSelectedCogTarget(null)
      setSubgraphCandidates([])
      return
    }
    api.getBlueprint(selectedBlueprint).then(d => setBlueprintDetail(d))
  }, [selectedBlueprint])

  const integrationItems = blueprintDetail?.integration_items || []
  const matrix = blueprintDetail?.matrix || []

  const toggleCogTarget = (layer, stage) => {
    setSelectedCogTarget(prev =>
      prev?.layer === layer && prev?.stage === stage ? null : { layer, stage }
    )
  }

  const handleSubgraphSearch = async () => {
    if (!selectedItem) return
    setSearchLoading(true)
    setSubgraphCandidates([])
    setSelectedSubgraph(null)
    try {
      const res = await api.subgraphSearch(selectedItem)
      setSubgraphCandidates(res.candidates || [])
    } finally { setSearchLoading(false) }
  }

  const handleSelectSubgraph = (candidate) => {
    setSelectedSubgraph(candidate)
    if (candidate.nodes.length > 0) setSelectedEntityId(candidate.nodes[0].id)
  }

  const pollJob = (jobId) => {
    pollRef.current = setInterval(async () => {
      const job = await api.getGenerationJob(jobId)
      setProgress(job.status)
      if (job.status === 'completed') {
        clearInterval(pollRef.current)
        setGenerating(false)
        setGeneratedQuestions(job.result || [])
      } else if (job.status === 'failed') {
        clearInterval(pollRef.current)
        setGenerating(false)
        setGenError(`생성 실패: ${job.error || '알 수 없는 오류'}`)
      }
    }, 2000)
  }

  const handleGenerate = async () => {
    const entityId = pathMode === 'A' ? selectedEntityId : (selectedSubgraph?.nodes[0]?.id || '')
    if (!entityId) { alert('Entity를 선택하세요.'); return }
    setGenerating(true)
    setGenError('')
    setProgress('pending')
    setGeneratedQuestions([])
    setDiscardedIdx(new Set())
    try {
      const { job_id } = await api.startGeneration(
        entityId,
        selectedBlueprint || null,
        pathMode === 'B' ? selectedItem || null : null,
        questionType,
      )
      pollJob(job_id)
    } catch (e) {
      setGenerating(false)
      setGenError(`생성 요청 실패: ${e.message || e}`)
    }
  }

  const handleSaved = () => {
    api.listWorkbenchQuestions({ status: 'published' }).then(d => setPublishedList(d.questions || []))
    setShowPublished(true)
  }

  const activeEntity = pathMode === 'A'
    ? nodes.find(n => n.id === selectedEntityId)
    : (selectedSubgraph?.nodes[0] || null)

  const canGenerate = !generating && (
    pathMode === 'A' ? !!selectedEntityId : !!selectedSubgraph
  )

  return (
    <div style={{ display: 'flex', height: '100%', gap: 0 }}>
      {/* 좌측: 파라미터 패널 */}
      <div style={{ width: 340, borderRight: '1px solid #2d3748', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
        <div style={{ padding: '14px 16px', borderBottom: '1px solid #2d3748' }}>
          <span style={{ fontWeight: 600, color: '#e2e8f0', fontSize: 14 }}>문제 생성 파라미터</span>
        </div>

        <div style={{ padding: 16, flex: 1 }}>

          {/* ── STEP 1: Blueprint 선택 ── */}
          <div style={stepLabel}>1 · Blueprint</div>
          <select
            value={selectedBlueprint}
            onChange={e => { setSelectedBlueprint(e.target.value); setPathMode('A') }}
            style={selectStyle}
          >
            <option value="">-- Blueprint 없이 생성 --</option>
            {blueprints.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>

          {/* ── STEP 2: 인지 단계 목표 선택 (Blueprint 선택 시) ── */}
          {matrix.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={stepLabel}>2 · 인지 단계 목표 <span style={{ color: '#718096', fontWeight: 400 }}>(선택)</span></div>
              {matrix.map(row => (
                <div key={row.layer} style={{ marginBottom: 8 }}>
                  <div style={{ color: '#718096', fontSize: 10, marginBottom: 4 }}>{row.layer}</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {(row.stages || []).map(stage => {
                      const active = selectedCogTarget?.layer === row.layer && selectedCogTarget?.stage === stage
                      return (
                        <button
                          key={stage}
                          onClick={() => toggleCogTarget(row.layer, stage)}
                          style={{
                            padding: '3px 10px', borderRadius: 12, fontSize: 11, cursor: 'pointer', border: 'none',
                            background: active ? '#4299e1' : '#2d3748',
                            color: active ? '#fff' : '#a0aec0',
                            fontWeight: active ? 600 : 400,
                          }}
                        >
                          {stage}
                        </button>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ── STEP 3: 진입 경로 ── */}
          <div style={{ marginTop: 16 }}>
            <div style={stepLabel}>{matrix.length > 0 ? '3' : '2'} · 진입 경로</div>
            <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
              <button
                onClick={() => { setPathMode('A'); setSelectedItem(''); setSubgraphCandidates([]) }}
                style={{
                  flex: 1, padding: '8px 0', borderRadius: 6, fontSize: 12, cursor: 'pointer', fontWeight: 600, border: 'none',
                  background: pathMode === 'A' ? '#4299e1' : '#2d3748',
                  color: pathMode === 'A' ? '#fff' : '#a0aec0',
                }}
              >
                Entity 직접 선택
              </button>
              <button
                onClick={() => setPathMode('B')}
                disabled={!selectedBlueprint}
                style={{
                  flex: 1, padding: '8px 0', borderRadius: 6, fontSize: 12, fontWeight: 600, border: 'none',
                  cursor: selectedBlueprint ? 'pointer' : 'not-allowed',
                  background: pathMode === 'B' ? '#805ad5' : '#2d3748',
                  color: pathMode === 'B' ? '#fff' : '#a0aec0',
                  opacity: selectedBlueprint ? 1 : 0.4,
                }}
              >
                통합항목 기반
              </button>
            </div>

            {/* Path A: Entity 선택 */}
            {pathMode === 'A' && (
              <select value={selectedEntityId} onChange={e => setSelectedEntityId(e.target.value)} style={selectStyle}>
                <option value="">-- Entity 선택 --</option>
                {nodes.map(n => (
                  <option key={n.id} value={n.id}>{n.name} ({n.type})</option>
                ))}
              </select>
            )}

            {/* Path B: 통합항목 카드 + 서브그래프 탐색 */}
            {pathMode === 'B' && (
              <>
                {integrationItems.length === 0 ? (
                  <div style={{ color: '#718096', fontSize: 12, padding: '10px 0' }}>
                    통합항목이 없습니다.<br />
                    <span style={{ color: '#4299e1', fontSize: 11 }}>출제기준 탭에서 먼저 추가하세요.</span>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {integrationItems.map(item => {
                      const active = selectedItem === item.id
                      return (
                        <div
                          key={item.id}
                          onClick={() => { setSelectedItem(active ? '' : item.id); setSubgraphCandidates([]); setSelectedSubgraph(null) }}
                          style={{
                            padding: '10px 12px', borderRadius: 6, cursor: 'pointer',
                            border: `1px solid ${active ? '#805ad5' : '#2d3748'}`,
                            background: active ? '#1d1235' : '#1a202c',
                          }}
                        >
                          <div style={{ color: '#e2e8f0', fontSize: 12, fontWeight: active ? 600 : 400 }}>{item.name}</div>
                          {item.description && <div style={{ color: '#718096', fontSize: 11, marginTop: 2 }}>{item.description}</div>}
                          {(item.required_combinations || []).length > 0 && (
                            <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap', marginTop: 6 }}>
                              {item.required_combinations.map((c, i) => (
                                <span key={i} style={{ background: '#2d3748', color: '#90cdf4', fontSize: 10, padding: '1px 6px', borderRadius: 8 }}>
                                  {c.layer}/{c.stage}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}

                {selectedItem && (
                  <button
                    onClick={handleSubgraphSearch}
                    disabled={searchLoading}
                    className="btn-primary"
                    style={{ width: '100%', marginTop: 10, fontSize: 12 }}
                  >
                    {searchLoading ? '탐색 중...' : '서브그래프 탐색'}
                  </button>
                )}

                {subgraphCandidates.length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <div style={{ color: '#a0aec0', fontSize: 11, marginBottom: 6 }}>서브그래프 후보 선택</div>
                    {subgraphCandidates.map((c, i) => (
                      <SubgraphMiniMap key={i} candidate={c} onSelect={handleSelectSubgraph} isSelected={selectedSubgraph === c} />
                    ))}
                  </div>
                )}
              </>
            )}
          </div>

          {/* 선택된 Entity 요약 */}
          {activeEntity && (
            <div style={{ marginTop: 14, padding: 10, background: '#1a202c', borderRadius: 6, border: '1px solid #2d3748' }}>
              <div style={{ color: '#68d391', fontSize: 10, marginBottom: 3 }}>선택된 Entity</div>
              <div style={{ color: '#e2e8f0', fontWeight: 600, fontSize: 12 }}>{activeEntity.name || activeEntity.id}</div>
              {activeEntity.type && <div style={{ color: '#718096', fontSize: 11 }}>{activeEntity.type}</div>}
            </div>
          )}

          {/* ── 문제 타입 ── */}
          <div style={{ marginTop: 16 }}>
            <div style={stepLabel}>{matrix.length > 0 ? '4' : '3'} · 문제 타입</div>
            <div style={{ display: 'flex', gap: 6 }}>
              {[
                { key: 'MCQ', label: '선다형', desc: '4지선다' },
                { key: 'OX', label: 'O/X', desc: '참/거짓' },
                { key: 'short_answer', label: '단답형', desc: '키워드' },
              ].map(({ key, label, desc }) => (
                <button
                  key={key}
                  onClick={() => setQuestionType(key)}
                  style={{
                    flex: 1, padding: '7px 0', borderRadius: 6, fontSize: 11, cursor: 'pointer', border: 'none',
                    background: questionType === key ? '#2b6cb0' : '#2d3748',
                    color: questionType === key ? '#fff' : '#a0aec0',
                    fontWeight: questionType === key ? 600 : 400,
                  }}
                >
                  <div>{label}</div>
                  <div style={{ fontSize: 9, opacity: 0.7, marginTop: 1 }}>{desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* 생성 버튼 */}
          <button
            className="btn-primary"
            onClick={handleGenerate}
            disabled={!canGenerate}
            style={{ width: '100%', marginTop: 20, padding: '10px 0', fontSize: 13, fontWeight: 600 }}
          >
            {generating ? `생성 중... (${progress})` : '문제 생성'}
          </button>

          {generating && (
            <div style={{ marginTop: 8, textAlign: 'center', color: '#a0aec0', fontSize: 12 }}>
              {progress === 'running' ? '에이전트 실행 중...' : '대기 중...'}
            </div>
          )}

          {genError && (
            <div style={{ marginTop: 10, padding: '8px 12px', background: '#2d1515', border: '1px solid #fc8181', borderRadius: 6, color: '#fc8181', fontSize: 12 }}>
              {genError}
            </div>
          )}
        </div>
      </div>

      {/* 우측: 생성 결과 + 편집 */}
      <div style={{ flex: 1, padding: 20, overflowY: 'auto' }}>
        {/* 등록된 문항 목록 토글 */}
        {showPublished && (
          <div style={{ marginBottom: 20, background: '#1a202c', borderRadius: 8, padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
              <span style={{ color: '#68d391', fontWeight: 600, fontSize: 13 }}>등록된 문항 ({publishedList.length}개)</span>
              <button onClick={() => setShowPublished(false)} style={{ background: 'none', border: 'none', color: '#718096', cursor: 'pointer' }}>닫기</button>
            </div>
            {publishedList.map(q => (
              <div key={q.id} style={{ padding: '8px 0', borderBottom: '1px solid #2d3748', color: '#e2e8f0', fontSize: 13 }}>
                [{q.entity_id}] {q.question_text.slice(0, 60)}...
              </div>
            ))}
          </div>
        )}

        {generatedQuestions.length === 0 && !generating && (
          <div style={{ color: '#718096', fontSize: 14, paddingTop: 40, textAlign: 'center' }}>
            파라미터를 설정하고 문제를 생성하세요.
          </div>
        )}

        {generatedQuestions.length > 0 && (
          <>
            <div style={{ color: '#a0aec0', fontSize: 12, marginBottom: 16 }}>
              총 {generatedQuestions.length}개 생성됨 — 인라인 편집 후 최종 등록하세요.
            </div>
            {generatedQuestions.map((q, i) => (
              discardedIdx.has(i) ? null : (
                <QuestionPreviewEditor
                  key={i}
                  question={q}
                  entityId={pathMode === 'A' ? selectedEntityId : (selectedSubgraph?.nodes[0]?.id || '')}
                  blueprintId={selectedBlueprint || null}
                  onSaved={handleSaved}
                  onDiscard={() => setDiscardedIdx(prev => new Set([...prev, i]))}
                />
              )
            ))}
          </>
        )}
      </div>
    </div>
  )
}

const stepLabel = { color: '#a0aec0', fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }
const labelStyle = { display: 'block', color: '#a0aec0', fontSize: 11, marginBottom: 4, fontWeight: 500 }
const selectStyle = { width: '100%', background: '#2d3748', border: '1px solid #4a5568', color: '#e2e8f0', padding: '7px 10px', borderRadius: 6, fontSize: 13 }
const inputStyle = { width: '100%', background: '#2d3748', border: '1px solid #4a5568', color: '#e2e8f0', padding: '6px 8px', borderRadius: 4, fontSize: 13, boxSizing: 'border-box' }
const textareaStyle = { width: '100%', background: '#2d3748', border: '1px solid #4a5568', color: '#e2e8f0', padding: '8px', borderRadius: 4, fontSize: 13, resize: 'vertical', boxSizing: 'border-box' }
