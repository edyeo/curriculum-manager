import { useState, useEffect, useRef } from 'react'
import { api } from '../services/api'

export default function QuestionSolve({ question, onSubmitSuccess, onBack }) {
  const [answer, setAnswer] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const startMs = useRef(Date.now())

  useEffect(() => {
    setAnswer('')
    setResult(null)
    startMs.current = Date.now()
  }, [question?.id])

  const handleSubmit = async () => {
    if (!answer) return
    setSubmitting(true)
    try {
      const elapsed_ms = Date.now() - startMs.current
      const res = await api.submitQuestionAnswer(question.id, answer, elapsed_ms)
      setResult(res)
      if (onSubmitSuccess) onSubmitSuccess(res)
    } catch (e) {
      alert(e.message || '제출 실패')
    } finally {
      setSubmitting(false)
    }
  }

  if (!question) return null

  const qType = question.question_type || 'MCQ'
  const options = question.options || []

  return (
    <div style={S.root}>
      <div style={S.header}>
        <button onClick={onBack} style={S.backBtn}>← 목록으로</button>
        <div style={S.badges}>
          <span style={{ ...S.badge, background: DIFF_COLOR[question.difficulty] || '#ddd', color: '#fff' }}>
            {DIFF_LABEL[question.difficulty]}
          </span>
          <span style={{ ...S.badge, background: '#e2e8f0', color: '#555' }}>
            {TYPE_LABEL[qType]}
          </span>
        </div>
      </div>

      {/* 지문 */}
      <div style={S.questionBox}>
        <p style={S.questionText}>{question.question_text}</p>
      </div>

      {/* 답안 입력 */}
      {!result && (
        <div style={S.answerSection}>
          {qType === 'MCQ' && (
            <div style={S.optList}>
              {options.map((opt, i) => {
                const label = opt.label || String.fromCharCode(65 + i)
                return (
                  <label key={i} style={{ ...S.optRow, background: answer === label ? '#eff6ff' : '#fff', borderColor: answer === label ? '#3b82f6' : '#e2e8f0' }}>
                    <input
                      type="radio"
                      name="answer"
                      value={label}
                      checked={answer === label}
                      onChange={() => setAnswer(label)}
                      style={{ marginRight: 10 }}
                    />
                    <span style={S.optLabel}>{label}.</span>
                    <span>{opt.text}</span>
                  </label>
                )
              })}
            </div>
          )}
          {qType === 'OX' && (
            <div style={S.oxRow}>
              {['O', 'X'].map(v => (
                <button
                  key={v}
                  style={{ ...S.oxBtn, background: answer === v ? '#3b82f6' : '#f0f0f0', color: answer === v ? '#fff' : '#333' }}
                  onClick={() => setAnswer(v)}
                >{v}</button>
              ))}
            </div>
          )}
          {qType === 'short_answer' && (
            <input
              style={S.shortInput}
              placeholder="답을 입력하세요"
              value={answer}
              onChange={e => setAnswer(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
            />
          )}
          <button
            style={{ ...S.submitBtn, opacity: answer ? 1 : 0.5 }}
            onClick={handleSubmit}
            disabled={!answer || submitting}
          >
            {submitting ? '채점 중…' : '제출'}
          </button>
        </div>
      )}

      {/* 결과 */}
      {result && (
        <div style={S.resultBox}>
          <div style={{ ...S.verdict, color: result.is_correct ? '#10b981' : '#ef4444' }}>
            {result.is_correct ? '✓ 정답!' : '✗ 오답'}
          </div>

          {/* 선지 결과 표시 */}
          {qType === 'MCQ' && (
            <div style={S.optList}>
              {options.map((opt, i) => {
                const label = opt.label || String.fromCharCode(65 + i)
                const isCorrect = label === result.correct_answer
                const isSelected = label === answer
                return (
                  <div key={i} style={{
                    ...S.optRow,
                    background: isCorrect ? '#f0fdf4' : isSelected ? '#fef2f2' : '#fafafa',
                    borderColor: isCorrect ? '#10b981' : isSelected ? '#ef4444' : '#e2e8f0',
                  }}>
                    <span style={S.optLabel}>{label}.</span>
                    <div style={{ flex: 1 }}>
                      <span>{opt.text}</span>
                      {opt.rationale && isSelected && (
                        <p style={S.rationale}>{opt.rationale}</p>
                      )}
                    </div>
                    {isCorrect && <span style={{ color: '#10b981', fontWeight: 700 }}>✓</span>}
                  </div>
                )
              })}
            </div>
          )}

          {qType !== 'MCQ' && (
            <p style={S.answerReveal}>정답: <strong>{result.correct_answer}</strong></p>
          )}

          {result.selected_rationale && (
            <div style={S.explanationBox}>
              <strong style={S.explanationLabel}>선택 선지 해설</strong>
              <p style={S.explanationText}>{result.selected_rationale}</p>
            </div>
          )}
          {result.explanation && (
            <div style={S.explanationBox}>
              <strong style={S.explanationLabel}>종합 해설</strong>
              <p style={S.explanationText}>{result.explanation}</p>
            </div>
          )}

          <div style={S.resultActions}>
            <button style={S.backBtn} onClick={onBack}>← 목록으로</button>
          </div>
        </div>
      )}
    </div>
  )
}

const DIFF_LABEL = { easy: '쉬움', medium: '보통', hard: '어려움' }
const DIFF_COLOR = { easy: '#10b981', medium: '#f59e0b', hard: '#ef4444' }
const TYPE_LABEL = { MCQ: '객관식', OX: 'O/X', short_answer: '단답형' }

const S = {
  root: { maxWidth: 680, margin: '0 auto' },
  header: { display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 },
  backBtn: { padding: '6px 12px', border: '1px solid #ddd', borderRadius: 6, cursor: 'pointer', background: '#fff', fontSize: 13 },
  badges: { display: 'flex', gap: 6 },
  badge: { fontSize: 11, padding: '2px 8px', borderRadius: 10, fontWeight: 500 },
  questionBox: { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '20px 24px', marginBottom: 20 },
  questionText: { fontSize: 16, color: '#2d3748', lineHeight: 1.7, margin: 0 },
  answerSection: { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '20px 24px' },
  optList: { display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 },
  optRow: { display: 'flex', alignItems: 'flex-start', gap: 8, padding: '10px 14px', border: '1px solid #e2e8f0', borderRadius: 6, cursor: 'pointer' },
  optLabel: { fontWeight: 700, width: 24, flexShrink: 0 },
  oxRow: { display: 'flex', gap: 16, marginBottom: 20 },
  oxBtn: { flex: 1, padding: '16px', fontSize: 24, fontWeight: 700, border: '1px solid #ddd', borderRadius: 8, cursor: 'pointer' },
  shortInput: { width: '100%', padding: '10px 14px', border: '1px solid #ddd', borderRadius: 6, fontSize: 15, boxSizing: 'border-box', marginBottom: 16 },
  submitBtn: { padding: '10px 32px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 15, fontWeight: 600 },
  resultBox: { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '20px 24px' },
  verdict: { fontSize: 22, fontWeight: 700, marginBottom: 16 },
  answerReveal: { fontSize: 15, margin: '12px 0' },
  rationale: { fontSize: 12, color: '#888', fontStyle: 'italic', margin: '4px 0 0' },
  explanationBox: { background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 6, padding: '12px 16px', marginTop: 12 },
  explanationLabel: { fontSize: 12, color: '#64748b', display: 'block', marginBottom: 4 },
  explanationText: { fontSize: 14, color: '#374151', lineHeight: 1.6, margin: 0 },
  resultActions: { marginTop: 20, display: 'flex', gap: 10 },
}
