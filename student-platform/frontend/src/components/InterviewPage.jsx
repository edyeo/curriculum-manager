import { useState, useRef, useEffect } from 'react'
import { api } from '../services/api'

// ── 메인: 서브 탭 컨테이너 ────────────────────────────────────────────────────
export default function InterviewPage({ subject }) {
  const [subTab, setSubTab] = useState('conduct')

  return (
    <div>
      <div style={S.subNav}>
        {[['conduct', '인터뷰 수행'], ['history', '인터뷰 히스토리']].map(([key, label]) => (
          <button
            key={key}
            style={S.subTabBtn(subTab === key)}
            onClick={() => setSubTab(key)}
          >
            {label}
          </button>
        ))}
      </div>
      {subTab === 'conduct'
        ? <InterviewConduct subject={subject} />
        : <InterviewHistory subject={subject} />
      }
    </div>
  )
}

// ── 인터뷰 수행 ───────────────────────────────────────────────────────────────
function InterviewConduct({ subject }) {
  const [phase, setPhase] = useState('idle')
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [turnsRemaining, setTurnsRemaining] = useState(null)
  const [diagnosis, setDiagnosis] = useState(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  if (!subject) return <p style={S.hint}>과목을 선택하면 인터뷰를 시작할 수 있습니다.</p>

  const handleStart = async () => {
    setLoading(true)
    try {
      const res = await api.startInterview(subject.id)
      setSessionId(res.session_id)
      setTurnsRemaining(res.max_turns - 1)
      setMessages([{ role: 'ai', text: res.question }])
      setPhase('active')
    } catch (e) {
      alert(e.message || '인터뷰를 시작할 수 없습니다.')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async () => {
    if (!input.trim() || loading) return
    const answer = input.trim()
    setInput('')
    setLoading(true)
    setMessages(prev => [...prev, { role: 'user', text: answer }])
    try {
      const res = await api.submitInterviewAnswer(sessionId, answer)
      const turn = res.turn
      setMessages(prev => prev.map((m, i) =>
        i === prev.length - 1 ? { ...m, score: turn.score, feedback: turn.feedback } : m
      ))
      if (res.session_status === 'max_turns_reached') {
        setMessages(prev => [...prev, { role: 'ai', text: res.message }])
        setTurnsRemaining(0)
        return
      }
      setTurnsRemaining(res.turns_remaining)
      setMessages(prev => [...prev, { role: 'ai', text: res.next_question }])
    } catch (e) {
      alert(e.message || '답변 제출에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const handleEnd = async () => {
    if (!window.confirm('인터뷰를 종료하고 진단 결과를 확인하시겠습니까?')) return
    setLoading(true)
    try {
      const res = await api.endInterview(sessionId)
      setDiagnosis(res)
      setPhase('ended')
    } catch (e) {
      alert(e.message || '세션 종료에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setPhase('idle'); setSessionId(null); setMessages([]); setDiagnosis(null); setTurnsRemaining(null)
  }

  if (phase === 'idle') return (
    <div style={S.idleWrap}>
      <div style={S.idleCard}>
        <div style={S.idleIcon}>🎤</div>
        <h2 style={S.idleTitle}>가상 인터뷰</h2>
        <p style={S.idleDesc}>
          <strong>{subject.name}</strong> 과목에 대한 AI 면접관과의 인터뷰를 시작합니다.<br />
          질문에 자유롭게 답변하면 이해도를 진단해 드립니다.
        </p>
        <ul style={S.idleInfo}>
          <li>최대 15턴의 질문으로 진행됩니다.</li>
          <li>답변 후 즉시 피드백을 확인할 수 있습니다.</li>
          <li>종료 시 최종 진단 리포트가 제공됩니다.</li>
        </ul>
        <button onClick={handleStart} disabled={loading} style={S.startBtn}>
          {loading ? '시작하는 중...' : '인터뷰 시작'}
        </button>
      </div>
    </div>
  )

  if (phase === 'ended' && diagnosis) return (
    <DiagnosisView diagnosis={diagnosis} subjectName={subject.name} onReset={handleReset} />
  )

  return (
    <div style={S.chatWrap}>
      <div style={S.chatHeader}>
        <span style={S.chatTitle}>인터뷰 진행 중 — {subject.name}</span>
        <div style={S.chatMeta}>
          {turnsRemaining !== null && <span style={S.turnsLeft}>남은 질문 {turnsRemaining}턴</span>}
          <button onClick={handleEnd} disabled={loading} style={S.endBtn}>종료하기</button>
        </div>
      </div>
      <div style={S.messageList}>
        {messages.map((m, i) => (
          <div key={i} style={m.role === 'ai' ? S.aiBubbleWrap : S.userBubbleWrap}>
            {m.role === 'ai' && <div style={S.aiAvatar}>AI</div>}
            <div style={S.bubbleCol}>
              <div style={m.role === 'ai' ? S.aiBubble : S.userBubble}>{m.text}</div>
              {m.role === 'user' && m.score !== undefined && (
                <div style={S.feedbackCard}>
                  <span style={{ ...S.scoreBadge, background: scoreColor(m.score) }}>
                    {Math.round(m.score * 100)}점
                  </span>
                  <span style={S.feedbackText}>{m.feedback}</span>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div style={S.aiBubbleWrap}>
            <div style={S.aiAvatar}>AI</div>
            <div style={S.aiBubble}><span style={S.dots}>···</span></div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div style={S.inputBar}>
        <textarea
          style={S.textarea}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit() } }}
          placeholder="답변을 입력하세요. (Enter로 제출, Shift+Enter로 줄바꿈)"
          rows={3}
          disabled={loading}
        />
        <button onClick={handleSubmit} disabled={loading || !input.trim()} style={S.submitBtn}>전송</button>
      </div>
    </div>
  )
}

// ── 인터뷰 히스토리 ───────────────────────────────────────────────────────────
function InterviewHistory({ subject }) {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)   // 상세 조회 중인 세션
  const [detail, setDetail] = useState(null)

  useEffect(() => {
    api.listInterviewSessions()
      .then(res => setSessions(res.sessions || []))
      .catch(() => setSessions([]))
      .finally(() => setLoading(false))
  }, [])

  const handleSelect = async (session) => {
    if (selected?.session_id === session.session_id) {
      setSelected(null); setDetail(null); return
    }
    setSelected(session)
    setDetail(null)
    try {
      const [sessionData, diagnosisData] = await Promise.all([
        api.getInterviewSession(session.session_id),
        api.getInterviewDiagnosis(session.session_id),
      ])
      setDetail({ turns: sessionData.turns || [], diagnosis: diagnosisData })
    } catch { setDetail(null) }
  }

  const filtered = subject
    ? sessions.filter(s => s.subject_id === subject.id)
    : sessions

  if (loading) return <p style={S.hint}>불러오는 중...</p>
  if (filtered.length === 0) return <p style={S.hint}>완료된 인터뷰가 없습니다.</p>

  return (
    <div style={S.historyWrap}>
      {filtered.map(s => (
        <div key={s.session_id} style={S.historyCard}>
          <button style={S.historyRow} onClick={() => handleSelect(s)}>
            <div style={S.historyLeft}>
              <div style={{ ...S.bandPill, background: bandColor(s.overall_band) }}>
                {s.overall_band ?? '?'}
              </div>
              <div>
                <div style={S.historyDate}>{formatDate(s.ended_at || s.started_at)}</div>
                <div style={S.historyMeta}>{s.turn_count}턴 완료</div>
              </div>
            </div>
            <span style={S.chevron}>{selected?.session_id === s.session_id ? '▲' : '▼'}</span>
          </button>

          {selected?.session_id === s.session_id && (
            <div style={S.detailPanel}>
              {!detail
                ? <p style={S.hint}>불러오는 중...</p>
                : (
                  <>
                    <TurnHistory turns={detail.turns} />
                    <div style={S.diagDivider} />
                    <DiagnosisView diagnosis={detail.diagnosis} subjectName={subject?.name} compact />
                  </>
                )
              }
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// ── 대화기록 뷰 (히스토리 상세) ──────────────────────────────────────────────
function TurnHistory({ turns }) {
  if (!turns || turns.length === 0) return null
  return (
    <div style={S.turnHistoryWrap}>
      <p style={S.turnHistoryTitle}>대화 기록</p>
      <div style={S.turnList}>
        {turns.map((t) => (
          <div key={t.turn_number} style={S.turnItem}>
            <div style={S.turnAiRow}>
              <span style={S.turnAvatar}>AI</span>
              <div style={S.turnAiBubble}>{t.question}</div>
            </div>
            <div style={S.turnUserRow}>
              <div style={S.turnColRight}>
                <div style={S.turnUserBubble}>{t.answer}</div>
                <div style={S.turnFeedbackCard}>
                  <span style={{ ...S.scoreBadge, background: scoreColor(t.score) }}>
                    {Math.round(t.score * 100)}점
                  </span>
                  <span style={S.feedbackText}>{t.feedback}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── 진단 뷰 (수행/히스토리 공용) ──────────────────────────────────────────────
function DiagnosisView({ diagnosis, subjectName, onReset, compact }) {
  return (
    <div style={compact ? {} : S.diagWrap}>
      <div style={compact ? S.diagCardCompact : S.diagCard}>
        {!compact && <h2 style={S.diagTitle}>인터뷰 진단 결과</h2>}
        {!compact && subjectName && <p style={S.diagSubject}>{subjectName}</p>}

        <div style={S.bandRow}>
          <div style={{ ...S.bandBadge, background: bandColor(diagnosis.overall_band) }}>
            {diagnosis.overall_band}
          </div>
          <span style={S.bandLabel}>종합 등급</span>
        </div>

        {diagnosis.strengths?.length > 0 && (
          <Section title="잘 이해한 개념" color="#48bb78">
            {diagnosis.strengths.map((s, i) => <Tag key={i} text={s} color="#c6f6d5" textColor="#276749" />)}
          </Section>
        )}

        {diagnosis.weaknesses?.length > 0 && (
          <Section title="보완이 필요한 개념" color="#fc8181">
            {diagnosis.weaknesses.map((s, i) => <Tag key={i} text={s} color="#fed7d7" textColor="#9b2c2c" />)}
          </Section>
        )}

        {diagnosis.not_covered?.length > 0 && (
          <Section title="이번 인터뷰에서 다루지 않은 개념" color="#a0aec0">
            {diagnosis.not_covered.map((s, i) => <Tag key={i} text={s} color="#edf2f7" textColor="#4a5568" />)}
          </Section>
        )}

        {diagnosis.recommendations?.length > 0 && (
          <div style={S.recSection}>
            <p style={S.recTitle}>다음 학습 추천</p>
            <ol style={S.recList}>
              {diagnosis.recommendations.map((r, i) => <li key={i} style={S.recItem}>{r}</li>)}
            </ol>
          </div>
        )}

        {onReset && <button onClick={onReset} style={S.resetBtn}>새 인터뷰 시작</button>}
      </div>
    </div>
  )
}

// ── 소형 컴포넌트 ──────────────────────────────────────────────────────────────
function Section({ title, color, children }) {
  return (
    <div style={S.section}>
      <p style={{ ...S.sectionTitle, color }}>{title}</p>
      <div style={S.tagRow}>{children}</div>
    </div>
  )
}

function Tag({ text, color, textColor }) {
  return <span style={{ ...S.tag, background: color, color: textColor }}>{text}</span>
}

// ── 헬퍼 ──────────────────────────────────────────────────────────────────────
function bandColor(band) {
  return { S: '#6b46c1', A: '#2b6cb0', B: '#276749', C: '#c05621', D: '#9b2c2c' }[band] || '#718096'
}
function scoreColor(score) {
  if (score >= 0.7) return '#48bb78'
  if (score >= 0.4) return '#ed8936'
  return '#fc8181'
}
function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getFullYear()}.${String(d.getMonth()+1).padStart(2,'0')}.${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

// ── 스타일 ────────────────────────────────────────────────────────────────────
const S = {
  hint: { color: '#888', textAlign: 'center', paddingTop: '3rem' },

  // 서브 탭
  subNav:      { display: 'flex', gap: 0, borderBottom: '1px solid #e2e8f0', marginBottom: '1.2rem' },
  subTabBtn:   (active) => ({
    padding: '8px 20px', border: 'none', borderBottom: active ? '2px solid #4a90e2' : '2px solid transparent',
    marginBottom: -1, cursor: 'pointer', fontSize: 13, fontWeight: active ? 600 : 400,
    background: 'transparent', color: active ? '#4a90e2' : '#718096',
  }),

  // idle
  idleWrap:    { display: 'flex', justifyContent: 'center', paddingTop: '2rem' },
  idleCard:    { background: '#fff', borderRadius: 12, padding: '2.5rem', maxWidth: 480, width: '100%', boxShadow: '0 2px 12px rgba(0,0,0,0.08)', textAlign: 'center' },
  idleIcon:    { fontSize: 48, marginBottom: 12 },
  idleTitle:   { fontSize: 22, fontWeight: 700, color: '#2d3748', margin: '0 0 8px' },
  idleDesc:    { color: '#4a5568', lineHeight: 1.7, marginBottom: 16 },
  idleInfo:    { textAlign: 'left', color: '#718096', fontSize: 13, lineHeight: 2, paddingLeft: 20, marginBottom: 24 },
  startBtn:    { padding: '12px 36px', background: '#4a90e2', color: '#fff', border: 'none', borderRadius: 8, fontSize: 15, fontWeight: 600, cursor: 'pointer' },

  // chat
  chatWrap:    { display: 'flex', flexDirection: 'column', height: 'calc(100vh - 180px)', background: '#fff', borderRadius: 12, boxShadow: '0 2px 12px rgba(0,0,0,0.08)', overflow: 'hidden' },
  chatHeader:  { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.8rem 1.2rem', borderBottom: '1px solid #e2e8f0', background: '#f7fafc' },
  chatTitle:   { fontWeight: 600, color: '#2d3748', fontSize: 14 },
  chatMeta:    { display: 'flex', alignItems: 'center', gap: 12 },
  turnsLeft:   { fontSize: 12, color: '#718096' },
  endBtn:      { padding: '5px 14px', border: '1px solid #fc8181', color: '#e53e3e', borderRadius: 6, cursor: 'pointer', fontSize: 13, background: '#fff' },
  messageList: { flex: 1, overflowY: 'auto', padding: '1.2rem', display: 'flex', flexDirection: 'column', gap: 16 },
  aiBubbleWrap:  { display: 'flex', alignItems: 'flex-start', gap: 10 },
  userBubbleWrap:{ display: 'flex', flexDirection: 'row-reverse', alignItems: 'flex-start', gap: 10 },
  bubbleCol:     { display: 'flex', flexDirection: 'column', gap: 6, maxWidth: '72%' },
  aiAvatar:      { width: 32, height: 32, borderRadius: '50%', background: '#4a90e2', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, flexShrink: 0 },
  aiBubble:      { background: '#f0f4f8', borderRadius: '0 12px 12px 12px', padding: '10px 14px', color: '#2d3748', fontSize: 14, lineHeight: 1.6 },
  userBubble:    { background: '#4a90e2', borderRadius: '12px 0 12px 12px', padding: '10px 14px', color: '#fff', fontSize: 14, lineHeight: 1.6 },
  dots:          { letterSpacing: 3, fontSize: 18 },
  feedbackCard:  { background: '#f7fafc', borderRadius: 8, padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: 4, border: '1px solid #e2e8f0' },
  scoreBadge:    { display: 'inline-block', padding: '2px 10px', borderRadius: 12, fontSize: 12, fontWeight: 700, color: '#fff', alignSelf: 'flex-start' },
  feedbackText:  { fontSize: 12, color: '#4a5568', lineHeight: 1.5 },
  inputBar:      { display: 'flex', gap: 10, padding: '0.8rem 1.2rem', borderTop: '1px solid #e2e8f0', background: '#f7fafc' },
  textarea:      { flex: 1, padding: '8px 12px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 14, resize: 'none', fontFamily: 'inherit', outline: 'none' },
  submitBtn:     { padding: '0 20px', background: '#4a90e2', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600 },

  // history
  historyWrap:   { display: 'flex', flexDirection: 'column', gap: 10 },
  historyCard:   { background: '#fff', borderRadius: 10, boxShadow: '0 1px 6px rgba(0,0,0,0.07)', overflow: 'hidden' },
  historyRow:    { display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', padding: '14px 16px', background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left' },
  historyLeft:   { display: 'flex', alignItems: 'center', gap: 14 },
  bandPill:      { width: 36, height: 36, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, fontWeight: 800, color: '#fff', flexShrink: 0 },
  historyDate:   { fontSize: 14, fontWeight: 600, color: '#2d3748' },
  historyMeta:   { fontSize: 12, color: '#718096', marginTop: 2 },
  chevron:       { fontSize: 11, color: '#a0aec0' },
  detailPanel:   { borderTop: '1px solid #e2e8f0', padding: '16px' },

  // diagnosis
  diagWrap:        { display: 'flex', justifyContent: 'center', paddingTop: '1rem' },
  diagCard:        { background: '#fff', borderRadius: 12, padding: '2rem', maxWidth: 600, width: '100%', boxShadow: '0 2px 12px rgba(0,0,0,0.08)' },
  diagCardCompact: { width: '100%' },
  diagTitle:       { fontSize: 20, fontWeight: 700, color: '#2d3748', margin: '0 0 4px' },
  diagSubject:     { color: '#718096', fontSize: 13, marginBottom: 20 },
  bandRow:         { display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 },
  bandBadge:       { width: 52, height: 52, borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, fontWeight: 800, color: '#fff' },
  bandLabel:       { fontSize: 14, color: '#4a5568' },
  section:         { marginBottom: 16 },
  sectionTitle:    { fontSize: 13, fontWeight: 600, marginBottom: 8 },
  tagRow:          { display: 'flex', flexWrap: 'wrap', gap: 6 },
  tag:             { padding: '3px 10px', borderRadius: 20, fontSize: 12, fontWeight: 500 },
  recSection:      { marginBottom: 20, background: '#f7fafc', borderRadius: 8, padding: '12px 16px' },
  recTitle:        { fontWeight: 600, fontSize: 13, color: '#2d3748', marginBottom: 8 },
  recList:         { margin: 0, padding: '0 0 0 18px', color: '#4a5568', fontSize: 13, lineHeight: 2 },
  recItem:         { marginBottom: 2 },
  resetBtn:        { marginTop: 8, padding: '10px 28px', background: '#4a90e2', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600 },

  // turn history
  turnHistoryWrap:  { marginBottom: 4 },
  turnHistoryTitle: { fontSize: 13, fontWeight: 700, color: '#4a5568', marginBottom: 10 },
  turnList:         { display: 'flex', flexDirection: 'column', gap: 14 },
  turnItem:         { display: 'flex', flexDirection: 'column', gap: 8 },
  turnAiRow:        { display: 'flex', alignItems: 'flex-start', gap: 8 },
  turnAvatar:       { width: 26, height: 26, borderRadius: '50%', background: '#4a90e2', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 700, flexShrink: 0 },
  turnAiBubble:     { background: '#f0f4f8', borderRadius: '0 10px 10px 10px', padding: '8px 12px', color: '#2d3748', fontSize: 13, lineHeight: 1.6, maxWidth: '85%' },
  turnUserRow:      { display: 'flex', justifyContent: 'flex-end' },
  turnColRight:     { display: 'flex', flexDirection: 'column', gap: 5, maxWidth: '85%' },
  turnUserBubble:   { background: '#4a90e2', borderRadius: '10px 0 10px 10px', padding: '8px 12px', color: '#fff', fontSize: 13, lineHeight: 1.6 },
  turnFeedbackCard: { background: '#f7fafc', borderRadius: 8, padding: '6px 10px', display: 'flex', flexDirection: 'column', gap: 3, border: '1px solid #e2e8f0' },

  diagDivider:      { margin: '20px 0', borderTop: '1px dashed #e2e8f0' },
}
