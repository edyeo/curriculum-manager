import { useState, useEffect } from 'react'
import { api } from './services/api'
import LoginPage from './components/LoginPage'
import RegisterPage from './components/RegisterPage'
import ConceptMap from './components/ConceptMap'
import QuestionSolver from './components/QuestionSolver'
import ResultView from './components/ResultView'
import MasteryDashboard from './components/MasteryDashboard'
import QuestionBrowse from './components/QuestionBrowse'
import QuestionSolve from './components/QuestionSolve'

const VIEWS = { LOGIN: 'login', REGISTER: 'register', MAP: 'map', SOLVER: 'solver', RESULT: 'result', MASTERY: 'mastery', BROWSE: 'browse', QUESTION_SOLVE: 'question_solve' }

export default function App() {
  const [view, setView] = useState(localStorage.getItem('student_token') ? VIEWS.MAP : VIEWS.LOGIN)
  const [student, setStudent] = useState(null)
  const [subjects, setSubjects] = useState([])
  const [selectedSubject, setSelectedSubject] = useState(null)
  const [graphData, setGraphData] = useState(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [questions, setQuestions] = useState([])
  const [selectedQuestion, setSelectedQuestion] = useState(null)
  const [submitResult, setSubmitResult] = useState(null)
  const [browseQuestion, setBrowseQuestion] = useState(null)

  // 초기 로드: 학생 정보 + 과목 목록
  useEffect(() => {
    if (!localStorage.getItem('student_token')) return
    api.me().then(setStudent).catch(() => {
      localStorage.removeItem('student_token')
      setView(VIEWS.LOGIN)
    })
    api.getSubjects().then(res => {
      const list = res.subjects || []
      setSubjects(list)
      if (list.length > 0) selectSubject(list[0])
    }).catch(() => {})
  }, [])

  const selectSubject = async (subject) => {
    setSelectedSubject(subject)
    setGraphData(null)
    try {
      const graph = await api.getGraph(subject.id)
      setGraphData(graph)
    } catch (e) {
      console.error('Failed to load graph', e)
    }
  }

  const handleLogin = (res) => {
    setStudent(res)
    setView(VIEWS.MAP)
    api.getSubjects().then(r => {
      const list = r.subjects || []
      setSubjects(list)
      if (list.length > 0) selectSubject(list[0])
    }).catch(() => {})
  }

  const handleNodeSelect = async (node) => {
    setSelectedNode(node)
    try {
      const res = await api.getQuestions(node.id)
      const qs = res.questions || []
      setQuestions(qs)
      if (qs.length > 0) {
        setSelectedQuestion(qs[0])
        setView(VIEWS.SOLVER)
      } else {
        alert('이 노드에 아직 문제가 없습니다.')
      }
    } catch {
      alert('문제를 불러오지 못했습니다.')
    }
  }

  const handleSubmitSuccess = (result, question, node) => {
    setSubmitResult(result)
    setView(VIEWS.RESULT)
    // 그래프 mastery 갱신
    if (graphData) {
      const updated = graphData.nodes.map(n =>
        n.id === node.id ? { ...n, mastery_score: result.mastery_after } : n
      )
      setGraphData({ ...graphData, nodes: updated })
    }
  }

  const handleNextRecommend = (recommend) => {
    if (recommend.recommended_node && recommend.recommended_question) {
      setSelectedNode(recommend.recommended_node)
      setSelectedQuestion(recommend.recommended_question)
      setView(VIEWS.SOLVER)
    } else {
      setView(VIEWS.MAP)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('student_token')
    setStudent(null)
    setView(VIEWS.LOGIN)
  }

  if (view === VIEWS.LOGIN) return <LoginPage onLogin={handleLogin} onGoRegister={() => setView(VIEWS.REGISTER)} />
  if (view === VIEWS.REGISTER) return <RegisterPage onLogin={handleLogin} onGoLogin={() => setView(VIEWS.LOGIN)} />

  return (
    <div style={styles.app}>
      {/* Header */}
      <header style={styles.header}>
        <span style={styles.logo}>학생 학습 플랫폼</span>
        <div style={styles.nav}>
          <button onClick={() => setView(VIEWS.MAP)} style={styles.navBtn(view === VIEWS.MAP)}>개념 맵</button>
          <button onClick={() => setView(VIEWS.BROWSE)} style={styles.navBtn(view === VIEWS.BROWSE || view === VIEWS.QUESTION_SOLVE)}>문제 탐색</button>
          <button onClick={() => setView(VIEWS.MASTERY)} style={styles.navBtn(view === VIEWS.MASTERY)}>이해도 현황</button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {subjects.length > 1 && (
            <select value={selectedSubject?.id || ''} onChange={e => {
              const s = subjects.find(s => s.id === e.target.value)
              if (s) selectSubject(s)
            }} style={styles.select}>
              {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          )}
          <span style={{ fontSize: 13, color: '#666' }}>{student?.name}</span>
          <button onClick={handleLogout} style={styles.logoutBtn}>로그아웃</button>
        </div>
      </header>

      {/* Main */}
      <main style={styles.main}>
        {view === VIEWS.MAP && (
          <>
            {selectedSubject && <h3 style={styles.subjectTitle}>{selectedSubject.name}</h3>}
            {graphData
              ? <ConceptMap subjectId={selectedSubject?.id} graphData={graphData} onNodeSelect={handleNodeSelect} />
              : <p style={{ color: '#888', textAlign: 'center' }}>그래프를 불러오는 중...</p>
            }
          </>
        )}

        {view === VIEWS.SOLVER && selectedQuestion && selectedNode && (
          <QuestionSolver
            question={selectedQuestion}
            node={{ ...selectedNode, subject_id: selectedSubject?.id }}
            onSubmitSuccess={handleSubmitSuccess}
            onBack={() => setView(VIEWS.MAP)}
          />
        )}

        {view === VIEWS.RESULT && submitResult && (
          <ResultView
            result={submitResult}
            question={selectedQuestion}
            node={selectedNode}
            subjectId={selectedSubject?.id}
            onNext={handleNextRecommend}
            onBackToMap={() => setView(VIEWS.MAP)}
          />
        )}

        {view === VIEWS.MASTERY && (
          <MasteryDashboard subjectId={selectedSubject?.id} graphData={graphData} />
        )}

        {view === VIEWS.BROWSE && (
          <QuestionBrowse
            onSelectQuestion={(q) => { setBrowseQuestion(q); setView(VIEWS.QUESTION_SOLVE) }}
            onBack={() => setView(VIEWS.MAP)}
          />
        )}

        {view === VIEWS.QUESTION_SOLVE && browseQuestion && (
          <QuestionSolve
            question={browseQuestion}
            onSubmitSuccess={() => {}}
            onBack={() => setView(VIEWS.BROWSE)}
          />
        )}
      </main>
    </div>
  )
}

const styles = {
  app: { fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif', minHeight: '100vh', background: '#f8f9fa' },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem 1.5rem', background: '#fff', borderBottom: '1px solid #e2e8f0', gap: 16 },
  logo: { fontWeight: 'bold', fontSize: 16, color: '#2d3748' },
  nav: { display: 'flex', gap: 8 },
  navBtn: (active) => ({ padding: '6px 14px', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13, background: active ? '#4a90e2' : '#f0f0f0', color: active ? '#fff' : '#555' }),
  select: { padding: '4px 8px', border: '1px solid #ddd', borderRadius: 4, fontSize: 13 },
  logoutBtn: { padding: '4px 12px', border: '1px solid #ddd', borderRadius: 4, cursor: 'pointer', fontSize: 13, background: '#fff' },
  main: { padding: '1.5rem', maxWidth: 900, margin: '0 auto' },
  subjectTitle: { fontSize: 15, color: '#555', marginBottom: '0.75rem' },
}
