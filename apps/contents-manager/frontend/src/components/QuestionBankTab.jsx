import { useState, useEffect, useCallback } from 'react'
import {
  listWorkbenchQuestions,
  updateWorkbenchQuestion,
  publishWorkbenchQuestion,
  unpublishWorkbenchQuestion,
  archiveWorkbenchQuestion,
  deleteWorkbenchQuestion,
  getBlueprints,
} from '../services/contentsApi'

const STATUS_LABEL = { draft: '초안', published: '출제됨', archived: '보관됨' }
const STATUS_COLOR = { draft: '#f59e0b', published: '#10b981', archived: '#6b7280' }
const TYPE_LABEL   = { MCQ: '객관식', OX: 'O/X', short_answer: '단답형' }
const DIFF_LABEL   = { easy: '쉬움', medium: '보통', hard: '어려움' }
const DIFF_COLOR   = { easy: '#10b981', medium: '#f59e0b', hard: '#ef4444' }

export default function QuestionBankTab() {
  const [blueprints, setBlueprints] = useState([])
  const [questions, setQuestions]   = useState([])
  const [modalQ, setModalQ]         = useState(null)   // 열린 모달의 question
  const [editMode, setEditMode]     = useState(false)
  const [editDraft, setEditDraft]   = useState(null)
  const [saving, setSaving]         = useState(false)
  const [filters, setFilters]       = useState({
    blueprint_id: '', entity_id: '', question_type: '', difficulty: '', status: '',
  })

  useEffect(() => {
    getBlueprints().then(r => setBlueprints(r.blueprints || [])).catch(() => {})
  }, [])

  const load = useCallback(async () => {
    const active = Object.fromEntries(Object.entries(filters).filter(([, v]) => v))
    const res = await listWorkbenchQuestions(active).catch(() => ({ questions: [] }))
    const qs = res.questions || []
    // 기본(전체) 선택 시 archived 제외 — draft + published만 표시
    setQuestions(filters.status === '' ? qs.filter(q => q.status !== 'archived') : qs)
  }, [filters])

  useEffect(() => { load() }, [load])

  const openModal = (q) => {
    setModalQ(q)
    setEditMode(false)
    setEditDraft(null)
  }
  const closeModal = () => {
    setModalQ(null)
    setEditMode(false)
    setEditDraft(null)
  }

  const startEdit = () => {
    setEditDraft({
      question_text: modalQ.question_text,
      options: modalQ.options.map(o => ({ ...o })),
      correct_answer: modalQ.correct_answer,
      explanation: modalQ.explanation || '',
      difficulty: modalQ.difficulty || 'medium',
    })
    setEditMode(true)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await updateWorkbenchQuestion(modalQ.id, {
        question_text: editDraft.question_text,
        options: editDraft.options,
        correct_answer: editDraft.correct_answer,
        explanation: editDraft.explanation,
        difficulty: editDraft.difficulty,
      })
      setQuestions(qs => qs.map(q => q.id === updated.id ? updated : q))
      setModalQ(updated)
      setEditMode(false)
      setEditDraft(null)
    } finally {
      setSaving(false)
    }
  }

  const handleLifecycle = async (action) => {
    let updated
    if (action === 'publish')   updated = await publishWorkbenchQuestion(modalQ.id)
    if (action === 'unpublish') updated = await unpublishWorkbenchQuestion(modalQ.id)
    if (action === 'archive')   updated = await archiveWorkbenchQuestion(modalQ.id)
    setQuestions(qs => qs.map(q => q.id === updated.id ? updated : q))
    setModalQ(updated)
  }

  const handleDelete = async () => {
    if (!window.confirm('이 문항을 삭제하시겠습니까?')) return
    await deleteWorkbenchQuestion(modalQ.id)
    setQuestions(qs => qs.filter(q => q.id !== modalQ.id))
    closeModal()
  }

  return (
    <div style={S.root}>
      {/* 필터 바 */}
      <div style={S.filterBar}>
        <select style={S.sel} value={filters.blueprint_id} onChange={e => setFilters(f => ({ ...f, blueprint_id: e.target.value }))}>
          <option value="">전체 Blueprint</option>
          {blueprints.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
        </select>
        <input style={S.inp} placeholder="Entity 검색" value={filters.entity_id}
          onChange={e => setFilters(f => ({ ...f, entity_id: e.target.value }))} />
        <select style={S.sel} value={filters.question_type} onChange={e => setFilters(f => ({ ...f, question_type: e.target.value }))}>
          <option value="">전체 타입</option>
          <option value="MCQ">객관식</option>
          <option value="OX">O/X</option>
          <option value="short_answer">단답형</option>
        </select>
        <select style={S.sel} value={filters.difficulty} onChange={e => setFilters(f => ({ ...f, difficulty: e.target.value }))}>
          <option value="">전체 난이도</option>
          <option value="easy">쉬움</option>
          <option value="medium">보통</option>
          <option value="hard">어려움</option>
        </select>
        <select style={S.sel} value={filters.status} onChange={e => setFilters(f => ({ ...f, status: e.target.value }))}>
          <option value="">초안 + 출제됨</option>
          <option value="draft">초안</option>
          <option value="published">출제됨</option>
          <option value="archived">보관됨</option>
        </select>
        <span style={S.count}>{questions.length}개</span>
      </div>

      {/* 테이블 */}
      {questions.length === 0 ? (
        <div style={S.empty}>
          문항이 없습니다. <span style={{ color: '#999' }}>문제출제 탭에서 문항을 생성하세요.</span>
        </div>
      ) : (
        <div style={S.tableWrap}>
          <table style={S.table}>
            <thead>
              <tr>
                <th style={{ ...S.th, width: 40 }}>#</th>
                <th style={S.th}>지문</th>
                <th style={{ ...S.th, width: 80 }}>타입</th>
                <th style={{ ...S.th, width: 72 }}>난이도</th>
                <th style={{ ...S.th, width: 80 }}>상태</th>
                <th style={{ ...S.th, width: 90 }}>생성일</th>
              </tr>
            </thead>
            <tbody>
              {questions.map((q, i) => (
                <tr key={q.id} style={S.tr} className="qb-row" onClick={() => openModal(q)}>
                  <td style={{ ...S.td, color: '#aaa', textAlign: 'center' }}>{i + 1}</td>
                  <td style={{ ...S.td, ...S.tdText }}>
                    {q.question_text.slice(0, 80)}{q.question_text.length > 80 ? '…' : ''}
                  </td>
                  <td style={S.td}>
                    <span style={S.chip}>{TYPE_LABEL[q.question_type] || q.question_type}</span>
                  </td>
                  <td style={S.td}>
                    <span style={{ ...S.chip, background: DIFF_COLOR[q.difficulty] + '33', color: DIFF_COLOR[q.difficulty] }}>
                      {DIFF_LABEL[q.difficulty] || q.difficulty}
                    </span>
                  </td>
                  <td style={S.td}>
                    <span style={{ ...S.chip, background: STATUS_COLOR[q.status] + '33', color: STATUS_COLOR[q.status] }}>
                      {STATUS_LABEL[q.status] || q.status}
                    </span>
                  </td>
                  <td style={{ ...S.td, color: '#888', fontSize: 12 }}>
                    {q.created_at ? new Date(q.created_at).toLocaleDateString('ko') : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 모달 */}
      {modalQ && (
        <QuestionModal
          question={modalQ}
          editMode={editMode}
          editDraft={editDraft}
          saving={saving}
          onEditDraftChange={setEditDraft}
          onStartEdit={startEdit}
          onSave={handleSave}
          onCancelEdit={() => { setEditMode(false); setEditDraft(null) }}
          onLifecycle={handleLifecycle}
          onDelete={handleDelete}
          onClose={closeModal}
        />
      )}
    </div>
  )
}

function QuestionModal({ question: q, editMode, editDraft, saving, onEditDraftChange, onStartEdit, onSave, onCancelEdit, onLifecycle, onDelete, onClose }) {
  return (
    <div style={S.overlay} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={S.modal}>
        {/* 모달 헤더 */}
        <div style={S.modalHeader}>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <span style={{ ...S.mChip, background: STATUS_COLOR[q.status] + '22', color: STATUS_COLOR[q.status] }}>
              {STATUS_LABEL[q.status]}
            </span>
            <span style={{ ...S.mChip, background: DIFF_COLOR[q.difficulty] + '22', color: DIFF_COLOR[q.difficulty] }}>
              {DIFF_LABEL[q.difficulty]}
            </span>
            <span style={S.mChip}>{TYPE_LABEL[q.question_type]}</span>
          </div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <LifecycleButtons
              status={q.status}
              editMode={editMode}
              saving={saving}
              onStartEdit={onStartEdit}
              onSave={onSave}
              onCancelEdit={onCancelEdit}
              onLifecycle={onLifecycle}
              onDelete={onDelete}
            />
            <button style={S.closeBtn} onClick={onClose}>✕</button>
          </div>
        </div>

        {/* 모달 본문 */}
        <div style={S.modalBody}>
          {/* 지문 */}
          <section style={S.section}>
            <label style={S.label}>지문</label>
            {editMode ? (
              <textarea style={S.textarea} rows={4}
                value={editDraft.question_text}
                onChange={e => onEditDraftChange(d => ({ ...d, question_text: e.target.value }))} />
            ) : (
              <p style={S.body}>{q.question_text}</p>
            )}
          </section>

          {/* 선지 */}
          {(editMode ? editDraft.options : q.options).length > 0 && (
            <section style={S.section}>
              <label style={S.label}>선지</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {(editMode ? editDraft.options : q.options).map((opt, i) => {
                  const label = opt.label || String.fromCharCode(65 + i)
                  const isCorrect = editMode ? opt.is_correct : opt.is_correct
                  return (
                    <div key={i} style={{ ...S.optRow, background: isCorrect ? '#f0fdf4' : '#fafafa', borderColor: isCorrect ? '#86efac' : '#e2e8f0' }}>
                      {editMode ? (
                        <input type="checkbox" checked={!!opt.is_correct} title="정답으로 설정"
                          onChange={() => onEditDraftChange(d => {
                            const opts = d.options.map((o, j) => ({ ...o, is_correct: j === i }))
                            const newCorrect = opts[i].label || String.fromCharCode(65 + i)
                            return { ...d, options: opts, correct_answer: newCorrect }
                          })} />
                      ) : null}
                      <span style={{ ...S.optLabel, color: isCorrect ? '#10b981' : '#555' }}>{label}</span>
                      <div style={{ flex: 1 }}>
                        {editMode ? (
                          <input style={{ padding: '5px 8px', border: '1px solid #cbd5e1', borderRadius: 4, fontSize: 13, width: '100%', boxSizing: 'border-box', color: '#111827', background: '#fff' }}
                            value={opt.text}
                            onChange={e => onEditDraftChange(d => {
                              const opts = d.options.map((o, j) => j === i ? { ...o, text: e.target.value } : o)
                              return { ...d, options: opts }
                            })} />
                        ) : (
                          <span style={{ fontSize: 14, color: '#111827' }}>{opt.text}</span>
                        )}
                        {opt.rationale && !editMode && (
                          <p style={S.rationale}>{opt.rationale}</p>
                        )}
                      </div>
                      {isCorrect && !editMode && <span style={{ color: '#059669', fontSize: 13, fontWeight: 700, whiteSpace: 'nowrap' }}>정답</span>}
                    </div>
                  )
                })}
              </div>
            </section>
          )}

          {/* 정답 · 난이도 · 해설 */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <section style={S.section}>
              <label style={S.label}>정답</label>
              {editMode ? (
                <input style={{ padding: '5px 8px', border: '1px solid #cbd5e1', borderRadius: 4, fontSize: 14, width: '100%', boxSizing: 'border-box', color: '#111827', background: '#fff' }}
                  value={editDraft.correct_answer}
                  onChange={e => onEditDraftChange(d => ({ ...d, correct_answer: e.target.value }))} />
              ) : (
                <span style={{ fontSize: 18, fontWeight: 700, color: '#10b981' }}>{q.correct_answer}</span>
              )}
            </section>
            <section style={S.section}>
              <label style={S.label}>난이도</label>
              {editMode ? (
                <select style={{ padding: '5px 8px', border: '1px solid #cbd5e1', borderRadius: 4, fontSize: 13, color: '#111827', background: '#fff' }}
                  value={editDraft.difficulty}
                  onChange={e => onEditDraftChange(d => ({ ...d, difficulty: e.target.value }))}>
                  <option value="easy">쉬움</option>
                  <option value="medium">보통</option>
                  <option value="hard">어려움</option>
                </select>
              ) : (
                <span style={{ ...S.chip, background: DIFF_COLOR[q.difficulty] + '33', color: DIFF_COLOR[q.difficulty] }}>
                  {DIFF_LABEL[q.difficulty] || q.difficulty}
                </span>
              )}
            </section>
          </div>
          <section style={S.section}>
            <label style={S.label}>해설</label>
            {editMode ? (
              <textarea style={S.textarea} rows={3}
                value={editDraft.explanation}
                onChange={e => onEditDraftChange(d => ({ ...d, explanation: e.target.value }))} />
            ) : (
              <p style={{ ...S.body, color: '#555' }}>{q.explanation || '—'}</p>
            )}
          </section>

          {/* 메타 */}
          <section style={S.section}>
            <label style={S.label}>메타데이터</label>
            <div style={S.meta}>
              <span>Entity: <strong>{q.entity_id}</strong></span>
              {q.blueprint_id && <span>Blueprint: <strong>{q.blueprint_id.slice(0, 8)}…</strong></span>}
              <span>생성일: <strong>{q.created_at ? new Date(q.created_at).toLocaleString('ko') : '—'}</strong></span>
              <span>수정일: <strong>{q.updated_at ? new Date(q.updated_at).toLocaleString('ko') : '—'}</strong></span>
            </div>
            {q.node_snapshot && (
              <details style={{ marginTop: 8 }}>
                <summary style={{ cursor: 'pointer', fontSize: 12, color: '#666' }}>node_snapshot 보기</summary>
                <pre style={S.pre}>{JSON.stringify(q.node_snapshot, null, 2)}</pre>
              </details>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}

function LifecycleButtons({ status, editMode, saving, onStartEdit, onSave, onCancelEdit, onLifecycle, onDelete }) {
  if (editMode) return (
    <div style={{ display: 'flex', gap: 6 }}>
      <button style={S.btnSave} onClick={onSave} disabled={saving}>{saving ? '저장 중…' : '저장'}</button>
      <button style={S.btnGray} onClick={onCancelEdit}>취소</button>
    </div>
  )
  return (
    <div style={{ display: 'flex', gap: 6 }}>
      <button style={S.btnGray} onClick={onStartEdit}>편집</button>
      {status === 'draft'     && <button style={S.btnGreen}  onClick={() => onLifecycle('publish')}>출제 등록</button>}
      {status === 'published' && <button style={S.btnYellow} onClick={() => onLifecycle('unpublish')}>공개 취소</button>}
      {status === 'published' && <button style={S.btnSlate}  onClick={() => onLifecycle('archive')}>보관</button>}
      {(status === 'draft' || status === 'archived')
        ? <button style={S.btnRed}  onClick={onDelete}>삭제</button>
        : <button style={S.btnDis}  disabled title="보관 후 삭제 가능">삭제</button>}
    </div>
  )
}

const btn = { padding: '5px 12px', borderRadius: 4, cursor: 'pointer', fontSize: 12, border: 'none', fontWeight: 500 }

// ── 테이블 영역: dark navy 테마 ──────────────────────────────────────────────
// ── 모달 영역: white 배경, 검정 텍스트 ──────────────────────────────────────
const S = {
  root:       { display: 'flex', flexDirection: 'column', gap: 0 },

  // 필터: 흰 테두리, navy 배경, 흰 텍스트
  filterBar:  { display: 'flex', gap: 8, alignItems: 'center', padding: '10px 0', flexWrap: 'wrap' },
  sel:        { padding: '5px 8px', border: '1px solid #fff', borderRadius: 4, fontSize: 12, background: '#1e2130', color: '#e2e8f0' },
  inp:        { padding: '5px 8px', border: '1px solid #fff', borderRadius: 4, fontSize: 12, background: '#1e2130', color: '#e2e8f0' },
  count:      { marginLeft: 'auto', fontSize: 12, color: '#94a3b8' },

  // 테이블: dark 계열
  tableWrap:  { border: '1px solid #2d3748', borderRadius: 8, overflow: 'hidden' },
  table:      { width: '100%', borderCollapse: 'collapse' },
  th:         { padding: '10px 14px', background: '#1a1d2e', borderBottom: '1px solid #2d3748', fontSize: 12, fontWeight: 600, color: '#94a3b8', textAlign: 'left' },
  tr:         { cursor: 'pointer', transition: 'background 0.1s' },
  td:         { padding: '10px 14px', fontSize: 13, verticalAlign: 'middle', borderBottom: '1px solid #1e2130', color: '#e2e8f0' },
  tdText:     { color: '#e2e8f0', maxWidth: 0 },
  chip:       { display: 'inline-block', padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 500, background: '#2d3748', color: '#cbd5e1', whiteSpace: 'nowrap' },
  empty:      { padding: '48px 0', textAlign: 'center', fontSize: 14, color: '#94a3b8' },

  // 모달: white 배경
  overlay:    { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 },
  modal:      { background: '#fff', borderRadius: 10, width: '100%', maxWidth: 720, maxHeight: '90vh', display: 'flex', flexDirection: 'column', boxShadow: '0 20px 60px rgba(0,0,0,0.35)' },
  modalHeader:{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 20px', borderBottom: '1px solid #e2e8f0', flexShrink: 0 },
  modalBody:  { padding: '20px 24px', overflowY: 'auto' },
  closeBtn:   { padding: '4px 8px', background: 'none', border: '1px solid #cbd5e1', borderRadius: 4, cursor: 'pointer', fontSize: 14, color: '#475569' },

  // 모달 내부: 검정 계열 텍스트
  section:    { marginBottom: 18 },
  label:      { display: 'block', fontSize: 10, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 },
  body:       { fontSize: 14, color: '#111827', lineHeight: 1.7, margin: 0 },
  textarea:   { width: '100%', padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 4, fontSize: 14, lineHeight: 1.6, resize: 'vertical', boxSizing: 'border-box', color: '#111827', background: '#fff' },
  optRow:     { display: 'flex', alignItems: 'flex-start', gap: 10, padding: '8px 12px', borderRadius: 6, border: '1px solid #e2e8f0' },
  optLabel:   { fontWeight: 700, fontSize: 14, width: 22, flexShrink: 0, paddingTop: 1, color: '#111827' },
  rationale:  { fontSize: 12, color: '#6b7280', fontStyle: 'italic', margin: '4px 0 0' },
  meta:       { display: 'flex', flexWrap: 'wrap', gap: '6px 20px', fontSize: 12, color: '#374151' },
  pre:        { fontSize: 11, background: '#f8fafc', padding: 10, borderRadius: 4, overflow: 'auto', marginTop: 6, maxHeight: 180, color: '#374151' },

  // 모달 내 칩: 모달이 흰 배경이므로 기존 색상 유지
  mChip:      { display: 'inline-block', padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 500, background: '#e2e8f0', color: '#374151', whiteSpace: 'nowrap' },

  // 버튼
  btnGray:    { ...btn, background: '#f1f5f9', color: '#374151', border: '1px solid #cbd5e1' },
  btnSave:    { ...btn, background: '#3b82f6', color: '#fff' },
  btnGreen:   { ...btn, background: '#10b981', color: '#fff' },
  btnYellow:  { ...btn, background: '#f59e0b', color: '#fff' },
  btnSlate:   { ...btn, background: '#6b7280', color: '#fff' },
  btnRed:     { ...btn, background: '#ef4444', color: '#fff' },
  btnDis:     { ...btn, background: '#e5e7eb', color: '#9ca3af', cursor: 'not-allowed' },
}
