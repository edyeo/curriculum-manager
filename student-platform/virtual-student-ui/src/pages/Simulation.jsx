import { useState, useEffect } from 'react'
import {
  fetchStudents, fetchKgQuestions,
  createSimulationRun, fetchSimulationRuns, fetchSimulationRun,
} from '../api/client'
import { useSubject } from '../context/SubjectContext'

// ── 단계 상수 ──────────────────────────────────────────────────────────────────
const STEP_STUDENTS = 'students'
const STEP_QUESTIONS = 'questions'
const STEP_RESULT = 'result'

export default function Simulation() {
  const { selectedId: subjectId } = useSubject()
  const [step, setStep] = useState(STEP_STUDENTS)
  const [mode, setMode] = useState('simple')          // simple | interview
  const [selectedStudentIds, setSelectedStudentIds] = useState([])
  const [questions, setQuestions] = useState([])       // [{question_text, question_id?}]
  const [running, setRunning] = useState(false)
  const [runResult, setRunResult] = useState(null)
  const [error, setError] = useState(null)
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)

  useEffect(() => {
    setStep(STEP_STUDENTS)
    setSelectedStudentIds([])
    setQuestions([])
    setRunResult(null)
    setError(null)
    loadHistory()
  }, [subjectId])

  async function loadHistory() {
    if (!subjectId) return
    setHistoryLoading(true)
    try {
      const runs = await fetchSimulationRuns(subjectId)
      setHistory(Array.isArray(runs) ? runs : [])
    } catch { setHistory([]) }
    finally { setHistoryLoading(false) }
  }

  async function handleRun() {
    if (!subjectId) return
    if (mode === 'simple' && questions.length === 0) {
      setError('질문을 하나 이상 추가하세요.')
      return
    }
    setRunning(true)
    setError(null)
    try {
      const result = await createSimulationRun({
        subject_id: subjectId,
        mode,
        student_ids: selectedStudentIds,
        questions: mode === 'simple' ? questions : [],
      })
      setRunResult(result)
      setStep(STEP_RESULT)
      loadHistory()
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(false)
    }
  }

  async function loadHistoryRun(runId) {
    try {
      const run = await fetchSimulationRun(runId)
      setRunResult(run)
      setStep(STEP_RESULT)
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <div className="section-header">
        <h2>Simulation</h2>
        {step !== STEP_STUDENTS && (
          <button className="btn-secondary" onClick={() => { setStep(STEP_STUDENTS); setRunResult(null); setError(null) }}>
            ← 처음으로
          </button>
        )}
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {step === STEP_STUDENTS && (
        <StudentSelectStep
          subjectId={subjectId}
          selected={selectedStudentIds}
          onSelect={setSelectedStudentIds}
          mode={mode}
          onModeChange={setMode}
          onNext={() => mode === 'interview' ? handleRun() : setStep(STEP_QUESTIONS)}
          running={running}
        />
      )}

      {step === STEP_QUESTIONS && (
        <QuestionStep
          subjectId={subjectId}
          questions={questions}
          onQuestionsChange={setQuestions}
          onBack={() => setStep(STEP_STUDENTS)}
          onRun={handleRun}
          running={running}
        />
      )}

      {step === STEP_RESULT && runResult && (
        <ResultView result={runResult} />
      )}

      <HistoryPanel
        history={history}
        loading={historyLoading}
        onSelect={loadHistoryRun}
      />
    </div>
  )
}

// ── Step 1: 학생 선택 ──────────────────────────────────────────────────────────

function StudentSelectStep({ subjectId, selected, onSelect, mode, onModeChange, onNext, running }) {
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!subjectId) return
    setLoading(true)
    fetchStudents({ subject_id: subjectId, page_size: 100 })
      .then(d => setStudents(d.items || []))
      .catch(() => setStudents([]))
      .finally(() => setLoading(false))
  }, [subjectId])

  function toggleAll() {
    if (selected.length === students.length) onSelect([])
    else onSelect(students.map(s => s.id))
  }

  function toggle(id) {
    onSelect(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  const canNext = selected.length > 0 && subjectId

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <h3>Step 1 — 학생 선택 <span className="badge">{selected.length}명 선택됨</span></h3>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <label style={{ fontSize: '0.875rem', fontWeight: 500 }}>모드:</label>
            <select
              value={mode}
              onChange={e => onModeChange(e.target.value)}
              style={{ border: '1.5px solid #c7d2fe', borderRadius: 6, padding: '4px 8px', fontSize: '0.875rem', background: '#f5f3ff' }}
            >
              <option value="simple">Simple Answer</option>
              <option value="interview">Interview Session</option>
            </select>
          </div>
        </div>

        {mode === 'interview' && (
          <div style={{ background: '#fef9c3', border: '1px solid #fde68a', borderRadius: 8, padding: '10px 14px', marginBottom: 14, fontSize: '0.85rem', color: '#92400e' }}>
            Interview 모드: interview_agent가 질문을 자동 생성하고, 학생 페르소나로 답변합니다. 질문 입력 단계를 건너뜁니다.
          </div>
        )}

        <table className="table">
          <thead>
            <tr>
              <th style={{ width: 40 }}>
                <input type="checkbox"
                  checked={selected.length === students.length && students.length > 0}
                  onChange={toggleAll}
                />
              </th>
              <th>이름</th>
              <th>설명</th>
              <th>생성일</th>
            </tr>
          </thead>
          <tbody>
            {students.map(s => (
              <tr key={s.id} style={{ cursor: 'pointer' }} onClick={() => toggle(s.id)}>
                <td onClick={e => e.stopPropagation()}>
                  <input type="checkbox" checked={selected.includes(s.id)} onChange={() => toggle(s.id)} />
                </td>
                <td>{s.name}</td>
                <td style={{ color: '#6b7280', fontSize: '0.875rem' }}>{s.description || '—'}</td>
                <td>{new Date(s.created_at).toLocaleDateString('ko-KR')}</td>
              </tr>
            ))}
            {!loading && students.length === 0 && (
              <tr><td colSpan={4} style={{ textAlign: 'center', color: '#999', padding: 24 }}>이 Subject에 학생이 없습니다</td></tr>
            )}
          </tbody>
        </table>

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 16 }}>
          <button
            className="btn-primary"
            disabled={!canNext || running}
            onClick={onNext}
          >
            {running ? '실행 중...' : mode === 'interview' ? '인터뷰 실행' : '다음 →'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Step 2: 질문 설정 ──────────────────────────────────────────────────────────

const Q_TYPES = [
  { value: 'SHORT_ANSWER', label: '단답형' },
  { value: 'DESCRIPTIVE', label: '서술형' },
  { value: 'MULTIPLE_CHOICE', label: '객관식' },
]

function QuestionStep({ subjectId, questions, onQuestionsChange, onBack, onRun, running }) {
  const [sourceTab, setSourceTab] = useState('manual')
  const [kgQuestions, setKgQuestions] = useState([])
  const [kgLoading, setKgLoading] = useState(false)
  const [manualText, setManualText] = useState('')
  const [manualType, setManualType] = useState('SHORT_ANSWER')
  const [manualAnswer, setManualAnswer] = useState('')

  useEffect(() => {
    if (sourceTab !== 'kg') return
    setKgLoading(true)
    fetchKgQuestions(subjectId)
      .then(setKgQuestions)
      .catch(() => setKgQuestions([]))
      .finally(() => setKgLoading(false))
  }, [sourceTab, subjectId])

  function addManual() {
    const text = manualText.trim()
    if (!text) return
    onQuestionsChange(prev => [...prev, {
      question_text: text,
      question_type: manualType,
      correct_answer: manualAnswer.trim() || null,
    }])
    setManualText('')
    setManualAnswer('')
  }

  function addKg(q) {
    if (questions.some(x => x.question_id === q.id)) return
    const typeMap = { MCQ: 'MULTIPLE_CHOICE', OX: 'MULTIPLE_CHOICE', short_answer: 'SHORT_ANSWER', descriptive: 'DESCRIPTIVE' }
    onQuestionsChange(prev => [...prev, {
      question_text: q.question_text,
      question_type: typeMap[q.question_type] || 'SHORT_ANSWER',
      question_id: q.id,
      correct_answer: q.correct_answer || null,
      explanation: q.explanation || null,
      options: q.options || null,
    }])
  }

  function removeQuestion(idx) {
    onQuestionsChange(prev => prev.filter((_, i) => i !== idx))
  }

  const typeLabel = (t) => Q_TYPES.find(x => x.value === t)?.label || t

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <h3>Step 2 — 질문 선택 <span className="badge">{questions.length}개 추가됨</span></h3>
          <div className="tabs">
            <button className={`tab ${sourceTab === 'manual' ? 'active' : ''}`} onClick={() => setSourceTab('manual')}>직접 입력</button>
            <button className={`tab ${sourceTab === 'kg' ? 'active' : ''}`} onClick={() => setSourceTab('kg')}>KG 질문</button>
          </div>
        </div>

        {sourceTab === 'manual' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                style={{ flex: 1, border: '1px solid #d1d5db', borderRadius: 6, padding: '8px 10px', fontSize: '0.875rem' }}
                placeholder="질문 텍스트"
                value={manualText}
                onChange={e => setManualText(e.target.value)}
              />
              <select
                value={manualType}
                onChange={e => setManualType(e.target.value)}
                style={{ border: '1px solid #d1d5db', borderRadius: 6, padding: '6px 8px', fontSize: '0.875rem' }}
              >
                {Q_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                style={{ flex: 1, border: '1px solid #d1d5db', borderRadius: 6, padding: '8px 10px', fontSize: '0.875rem' }}
                placeholder="정답 (선택사항 — 입력 시 채점됨)"
                value={manualAnswer}
                onChange={e => setManualAnswer(e.target.value)}
              />
              <button className="btn-primary" onClick={addManual} disabled={!manualText.trim()}>추가</button>
            </div>
          </div>
        )}

        {sourceTab === 'kg' && (
          <div style={{ maxHeight: 280, overflowY: 'auto', marginBottom: 16 }}>
            {kgLoading && <p style={{ color: '#999', padding: 8 }}>불러오는 중...</p>}
            {kgQuestions.map(q => (
              <div key={q.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f3f4f6', gap: 8 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '0.875rem' }}>{q.question_text}</div>
                  <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: 2 }}>
                    {q.question_type}
                    {q.correct_answer && <span style={{ marginLeft: 6, color: '#16a34a' }}>채점 가능</span>}
                  </div>
                </div>
                <button
                  className="btn-sm"
                  disabled={questions.some(x => x.question_id === q.id)}
                  onClick={() => addKg(q)}
                >
                  {questions.some(x => x.question_id === q.id) ? '추가됨' : '+ 추가'}
                </button>
              </div>
            ))}
            {!kgLoading && kgQuestions.length === 0 && (
              <p style={{ color: '#999', padding: 8 }}>Published 질문이 없습니다</p>
            )}
          </div>
        )}

        {questions.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#6b7280', marginBottom: 8 }}>선택된 질문</div>
            {questions.map((q, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderBottom: '1px solid #f3f4f6', gap: 8 }}>
                <div style={{ flex: 1 }}>
                  <span style={{ fontSize: '0.875rem' }}>{q.question_text}</span>
                  <span style={{ marginLeft: 6 }}><span className="badge-sm">{typeLabel(q.question_type)}</span></span>
                  {q.question_id && <span className="badge-sm" style={{ marginLeft: 4 }}>KG</span>}
                  {q.correct_answer && <span style={{ marginLeft: 6, fontSize: '0.75rem', color: '#16a34a' }}>채점 가능</span>}
                </div>
                <button className="btn-sm btn-danger" onClick={() => removeQuestion(i)}>✕</button>
              </div>
            ))}
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <button className="btn-secondary" onClick={onBack}>← 이전</button>
          <button
            className="btn-primary"
            disabled={questions.length === 0 || running}
            onClick={onRun}
          >
            {running ? '실행 중...' : '시뮬레이션 실행'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Step 3: 결과 분석 ──────────────────────────────────────────────────────────

function ResultView({ result }) {
  const [expandedCell, setExpandedCell] = useState(null)  // {studentIdx, qIdx}
  const [expandedDiagnosis, setExpandedDiagnosis] = useState(null)

  const students = result.results || []
  const isInterview = result.mode === 'interview'

  // Simple mode: collect unique questions from first student
  const questions = isInterview
    ? []
    : (students[0]?.answers || []).map(a => a.question_text)

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <h3>
            결과 분석
            <span className="badge-sm" style={{ marginLeft: 8 }}>{result.mode === 'interview' ? 'Interview' : 'Simple'}</span>
            <span className="badge-sm" style={{ marginLeft: 4 }}>{students.length}명</span>
          </h3>
        </div>

        {!isInterview && questions.length > 0 && (
          <div style={{ overflowX: 'auto' }}>
            <table className="table" style={{ minWidth: 600 }}>
              <thead>
                <tr>
                  <th style={{ minWidth: 120 }}>학생</th>
                  {questions.map((q, i) => (
                    <th key={i} style={{ minWidth: 200, fontWeight: 500, fontSize: '0.82rem' }}>
                      Q{i + 1}: {q.length > 40 ? q.slice(0, 40) + '…' : q}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {students.map((s, si) => (
                  <tr key={s.student_id}>
                    <td style={{ fontWeight: 600, fontSize: '0.875rem' }}>{s.student_name}</td>
                    {s.answers.map((a, qi) => {
                      const isOpen = expandedCell?.si === si && expandedCell?.qi === qi
                      const hasScore = a.score != null
                      const scoreColor = hasScore
                        ? a.score >= 0.7 ? '#16a34a' : a.score >= 0.4 ? '#ca8a04' : '#dc2626'
                        : '#9ca3af'
                      return (
                        <td key={qi} style={{ verticalAlign: 'top', cursor: 'pointer', padding: '8px 12px' }}
                            onClick={() => setExpandedCell(isOpen ? null : { si, qi })}>
                          {hasScore && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                              <span style={{ fontSize: '0.78rem', fontWeight: 700, color: scoreColor }}>
                                {(a.score * 100).toFixed(0)}점
                              </span>
                              {a.is_correct != null && (
                                <span style={{ fontSize: '0.72rem', background: a.is_correct ? '#dcfce7' : '#fee2e2', color: a.is_correct ? '#16a34a' : '#dc2626', padding: '1px 5px', borderRadius: 4 }}>
                                  {a.is_correct ? '정답' : '오답'}
                                </span>
                              )}
                            </div>
                          )}
                          <div style={{ fontSize: '0.82rem', color: '#374151', maxHeight: isOpen ? 'none' : 56, overflow: 'hidden' }}>
                            {a.answer_text}
                          </div>
                          {isOpen && a.feedback && (
                            <div style={{ marginTop: 6, padding: '6px 8px', background: '#f9fafb', borderRadius: 6, fontSize: '0.78rem', color: '#6b7280', borderLeft: `3px solid ${scoreColor}` }}>
                              {a.feedback}
                            </div>
                          )}
                          {!isOpen && a.answer_text.length > 100 && (
                            <span style={{ fontSize: '0.75rem', color: '#6366f1' }}>더 보기</span>
                          )}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {isInterview && (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
              {students.map(s => (
                <DiagnosisCard
                  key={s.student_id}
                  student={s}
                  expanded={expandedDiagnosis === s.student_id}
                  onToggle={() => setExpandedDiagnosis(expandedDiagnosis === s.student_id ? null : s.student_id)}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      <PatternChart students={students} isInterview={isInterview} />
    </div>
  )
}

function DiagnosisCard({ student, expanded, onToggle }) {
  const d = student.diagnosis
  const bandColors = { S: '#7c3aed', A: '#2563eb', B: '#16a34a', C: '#ca8a04', D: '#dc2626' }
  const band = d?.overall_band || '?'

  return (
    <div className="chart-card" style={{ cursor: 'pointer' }} onClick={onToggle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <h4 style={{ margin: 0 }}>{student.student_name}</h4>
        <span style={{ fontWeight: 700, fontSize: '1.1rem', color: bandColors[band] || '#6b7280' }}>{band}</span>
      </div>
      {d && (
        <>
          <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: 4 }}>
            <strong>강점:</strong> {(d.strengths || []).join(', ') || '—'}
          </div>
          <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: 4 }}>
            <strong>약점:</strong> {(d.weaknesses || []).join(', ') || '—'}
          </div>
          {expanded && (
            <>
              <div style={{ marginTop: 10, borderTop: '1px solid #e5e7eb', paddingTop: 10 }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#374151', marginBottom: 6 }}>대화 이력</div>
                {student.answers.map((a, i) => {
                  const sc = a.score
                  const scColor = sc != null ? (sc >= 0.7 ? '#16a34a' : sc >= 0.4 ? '#ca8a04' : '#dc2626') : null
                  return (
                    <div key={i} style={{ marginBottom: 10, fontSize: '0.8rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ color: '#4f46e5' }}>Q{i + 1}: {a.question_text}</span>
                        {sc != null && <span style={{ fontWeight: 700, color: scColor, whiteSpace: 'nowrap', marginLeft: 8 }}>{(sc * 100).toFixed(0)}점</span>}
                      </div>
                      <div style={{ color: '#374151', marginTop: 2 }}>A: {a.answer_text}</div>
                      {a.feedback && <div style={{ marginTop: 3, color: '#9ca3af', fontStyle: 'italic' }}>{a.feedback}</div>}
                    </div>
                  )
                })}
              </div>
              {(d.recommendations || []).length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: 4 }}>추천 학습</div>
                  <ul style={{ paddingLeft: 16, margin: 0 }}>
                    {d.recommendations.map((r, i) => (
                      <li key={i} style={{ fontSize: '0.8rem', color: '#374151' }}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}

function PatternChart({ students, isInterview }) {
  if (students.length < 2) return null

  // 답변 길이 기반 패턴 비교
  const data = students.map(s => ({
    name: s.student_name.slice(0, 10),
    avgLen: Math.round(
      (s.answers || []).reduce((acc, a) => acc + (a.answer_text?.length || 0), 0) /
      Math.max(s.answers.length, 1)
    ),
  }))

  const maxLen = Math.max(...data.map(d => d.avgLen), 1)

  return (
    <div className="card">
      <h3>패턴 비교 — 평균 답변 길이</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {data.map(d => (
          <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 100, fontSize: '0.8rem', textAlign: 'right', color: '#374151' }}>{d.name}</div>
            <div style={{ flex: 1, background: '#f3f4f6', borderRadius: 4, height: 22, overflow: 'hidden' }}>
              <div
                style={{
                  width: `${(d.avgLen / maxLen) * 100}%`,
                  background: '#6366f1',
                  height: '100%',
                  borderRadius: 4,
                  display: 'flex',
                  alignItems: 'center',
                  paddingLeft: 6,
                  minWidth: 30,
                }}
              >
                <span style={{ fontSize: '0.72rem', color: '#fff', whiteSpace: 'nowrap' }}>{d.avgLen}자</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── 과거 실행 목록 ──────────────────────────────────────────────────────────────

function HistoryPanel({ history, loading, onSelect }) {
  if (loading) return null
  if (history.length === 0) return null

  return (
    <div className="card" style={{ marginTop: 24 }}>
      <h3>과거 실행</h3>
      <table className="table">
        <thead>
          <tr><th>모드</th><th>학생</th><th>질문</th><th>실행일</th><th></th></tr>
        </thead>
        <tbody>
          {history.slice(0, 10).map(r => (
            <tr key={r.run_id}>
              <td><span className="badge-sm">{r.mode}</span></td>
              <td>{r.student_count}명</td>
              <td>{r.mode === 'interview' ? '자동' : `${r.question_count}개`}</td>
              <td>{new Date(r.created_at).toLocaleDateString('ko-KR')}</td>
              <td>
                <button className="btn-sm" onClick={() => onSelect(r.run_id)}>보기</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
