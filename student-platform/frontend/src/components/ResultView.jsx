import { api } from '../services/api'
import { useState } from 'react'

function MasteryBar({ label, before, after }) {
  const diff = (after - before).toFixed(3)
  const sign = diff > 0 ? '+' : ''
  return (
    <div style={{ marginBottom: '0.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
        <span>{label}</span>
        <span style={{ color: diff > 0 ? '#48bb78' : diff < 0 ? '#fc8181' : '#888' }}>
          {(after * 100).toFixed(0)}% ({sign}{(diff * 100).toFixed(0)}%)
        </span>
      </div>
      <div style={{ position: 'relative', height: 10, background: '#e2e8f0', borderRadius: 5 }}>
        <div style={{ position: 'absolute', left: 0, top: 0, height: '100%', width: `${before * 100}%`, background: '#a0aec0', borderRadius: 5 }} />
        <div style={{ position: 'absolute', left: 0, top: 0, height: '100%', width: `${after * 100}%`, background: after >= before ? '#48bb78' : '#fc8181', borderRadius: 5, transition: 'width 0.5s' }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#999', marginTop: 2 }}>
        <span>이전: {(before * 100).toFixed(0)}%</span>
        <span>이후: {(after * 100).toFixed(0)}%</span>
      </div>
    </div>
  )
}

export default function ResultView({ result, question, node, subjectId, onNext, onBackToMap }) {
  const [loadingNext, setLoadingNext] = useState(false)

  const handleNext = async () => {
    setLoadingNext(true)
    try {
      const recommend = await api.getRecommend(subjectId, node?.id)
      onNext(recommend)
    } catch {
      onBackToMap()
    } finally {
      setLoadingNext(false)
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.verdict(result.is_correct)}>
        {result.is_correct ? '✅ 정답' : '❌ 오답'}
        <span style={{ marginLeft: 12, fontSize: 16 }}>점수: {(result.score * 100).toFixed(0)}점</span>
      </div>

      {result.feedback && (
        <div style={styles.feedbackBox}>
          <strong style={{ fontSize: 13, color: '#555' }}>AI 피드백</strong>
          <p style={{ margin: '6px 0 0', fontSize: 14, lineHeight: 1.6 }}>{result.feedback}</p>
        </div>
      )}

      <div style={styles.masterySection}>
        <h4 style={{ margin: '0 0 0.75rem', fontSize: 14, color: '#555' }}>이해도 변화</h4>
        <MasteryBar
          label={node?.name || '현재 노드'}
          before={result.mastery_before}
          after={result.mastery_after}
        />
      </div>

      <div style={styles.actions}>
        <button onClick={handleNext} disabled={loadingNext} style={styles.nextBtn}>
          {loadingNext ? '추천 중...' : '다음 추천 문제 풀기'}
        </button>
        <button onClick={onBackToMap} style={styles.mapBtn}>
          개념 맵으로 돌아가기
        </button>
      </div>
    </div>
  )
}

const styles = {
  container: { maxWidth: 640, margin: '0 auto', padding: '1.5rem' },
  verdict: (correct) => ({
    textAlign: 'center', fontSize: 24, fontWeight: 'bold', padding: '1.5rem',
    borderRadius: 8, marginBottom: '1.5rem',
    background: correct ? '#f0fff4' : '#fff5f5',
    color: correct ? '#2f855a' : '#c53030',
    border: `2px solid ${correct ? '#9ae6b4' : '#feb2b2'}`,
  }),
  feedbackBox: { background: '#f7fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: '1rem', marginBottom: '1.5rem' },
  masterySection: { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '1rem', marginBottom: '1.5rem' },
  actions: { display: 'flex', flexDirection: 'column', gap: 10 },
  nextBtn: { padding: '0.75rem', background: '#4a90e2', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 15 },
  mapBtn: { padding: '0.75rem', background: '#fff', color: '#4a90e2', border: '1px solid #4a90e2', borderRadius: 6, cursor: 'pointer', fontSize: 15 },
}
