import { useEffect, useRef, useState } from 'react'
import { api } from '../services/api'

export default function QuestionSolver({ question, node, onSubmitSuccess, onBack }) {
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const startTime = useRef(Date.now())

  useEffect(() => {
    setAnswer('')
    setError('')
    startTime.current = Date.now()
  }, [question])

  const content = typeof question.content === 'object'
    ? question.content
    : { question_text: question.content, choices: [] }

  const handleSubmit = async () => {
    if (!answer.trim()) { setError('답안을 입력하세요.'); return }
    setLoading(true)
    setError('')
    try {
      const timeTaken = Math.round((Date.now() - startTime.current) / 1000)
      const result = await api.submit({
        question_id: question.id,
        node_id: node.id,
        subject_id: node.subject_id || '',
        question_type: question.type,
        question_text: content.question_text || '',
        correct_answer: question.answer || '',
        user_answer: answer,
        explanation: question.explanation || '',
        time_taken_seconds: timeTaken,
      })
      onSubmitSuccess(result, question, node)
    } catch (err) {
      setError(err.message || '제출 실패')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.container}>
      <button onClick={onBack} style={styles.backBtn}>← 개념 맵으로</button>

      <div style={styles.meta}>
        <span style={styles.badge(typeColor(question.type))}>{question.type}</span>
        <span style={styles.badge('#888')}>{question.difficulty}</span>
        <span style={{ color: '#666', fontSize: 13 }}>노드: {node.name}</span>
      </div>

      <div style={styles.questionBox}>
        <p style={styles.questionText}>{content.question_text}</p>
      </div>

      {question.type === 'MULTIPLE_CHOICE' && content.choices?.length > 0 ? (
        <div style={styles.choices}>
          {content.choices.map((choice, i) => (
            <label key={i} style={styles.choiceLabel(answer === choice)}>
              <input type="radio" name="choice" value={choice}
                checked={answer === choice}
                onChange={() => setAnswer(choice)}
                style={{ marginRight: 8 }}
              />
              {choice}
            </label>
          ))}
        </div>
      ) : (
        <textarea
          value={answer}
          onChange={e => setAnswer(e.target.value)}
          placeholder={question.type === 'DESCRIPTIVE' ? '서술형 답안을 입력하세요...' : '답안을 입력하세요...'}
          style={styles.textarea}
          rows={question.type === 'DESCRIPTIVE' ? 6 : 3}
        />
      )}

      {error && <p style={styles.error}>{error}</p>}

      <button onClick={handleSubmit} disabled={loading || !answer.trim()} style={styles.submitBtn}>
        {loading ? '채점 중...' : '제출하기'}
      </button>
    </div>
  )
}

function typeColor(type) {
  return type === 'MULTIPLE_CHOICE' ? '#4a90e2' : type === 'SHORT_ANSWER' ? '#48bb78' : '#ed8936'
}

const styles = {
  container: { maxWidth: 680, margin: '0 auto', padding: '1.5rem' },
  backBtn: { background: 'none', border: 'none', color: '#4a90e2', cursor: 'pointer', fontSize: 14, marginBottom: '1rem' },
  meta: { display: 'flex', gap: 8, alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap' },
  badge: (color) => ({
    background: color, color: '#fff', padding: '2px 8px', borderRadius: 10, fontSize: 12,
  }),
  questionBox: { background: '#f9fafb', border: '1px solid #e2e8f0', borderRadius: 8, padding: '1rem', marginBottom: '1rem' },
  questionText: { margin: 0, lineHeight: 1.6, fontSize: 15 },
  choices: { display: 'flex', flexDirection: 'column', gap: 8, marginBottom: '1rem' },
  choiceLabel: (selected) => ({
    display: 'flex', alignItems: 'center', padding: '0.6rem 1rem',
    border: `2px solid ${selected ? '#4a90e2' : '#ddd'}`,
    borderRadius: 6, cursor: 'pointer', background: selected ? '#ebf4ff' : '#fff',
    fontSize: 14,
  }),
  textarea: { width: '100%', padding: '0.75rem', border: '1px solid #ddd', borderRadius: 6, fontSize: 14, resize: 'vertical', boxSizing: 'border-box', marginBottom: '1rem' },
  error: { color: '#e53e3e', fontSize: 13 },
  submitBtn: { width: '100%', padding: '0.75rem', background: '#4a90e2', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 15 },
}
