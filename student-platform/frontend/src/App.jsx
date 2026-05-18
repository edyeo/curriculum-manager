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

const TAB = { MAP: 'map', BROWSE: 'browse', MASTERY: 'mastery' }
const VIEWS = { LOGIN: 'login', REGISTER: 'register', MAP: 'map', SOLVER: 'solver', RESULT: 'result', MASTERY: 'mastery', BROWSE: 'browse', QUESTION_SOLVE: 'question_solve' }

const tabOf = (view) => {
  if (view === VIEWS.SOLVER || view === VIEWS.RESULT) return TAB.MAP
  if (view === VIEWS.QUESTION_SOLVE) return TAB.BROWSE
  return view
}

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

  const activeTab = tabOf(view)

  return (
    <div style={S.app}>
      {/* Header: 로고 + 과목 선택 + 사용자 */}
      <header style={S.header}>
        <span style={S.logo}>학생 학습 플랫폼</span>
        <div style={S.headerRight}>
          {subjects.length > 0 && (
            <select
              value={selectedSubject?.id || ''}
              onChange={e => {
                const s = subjects.find(s => s.id === e.target.value)
                if (s) selectSubject(s)
              }}
              style={S.subjectSelect}
            >
              {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          )}
          <span style={S.studentName}>{student?.name}</span>
          <button onClick={handleLogout} style={S.logoutBtn}>로그아웃</button>
        </div>
      </header>

      {/* Tab nav */}
      <nav style={S.tabNav}>
        {[
          [TAB.MAP,     '개념 맵'],
          [TAB.BROWSE,  '문제 탐색'],
          [TAB.MASTERY, '이해도 현황'],
        ].map(([tab, label]) => (
          <button
            key={tab}
            style={S.tabBtn(activeTab === tab)}
            onClick={() => setView(tab)}
          >
            {label}
          </button>
        ))}
      </nav>

      {/* Main */}
      <main style={S.main}>
        {view === VIEWS.MAP && (
          <>
            {graphData
              ? <ConceptMap subjectId={selectedSubject?.id} graphData={graphData} onNodeSelect={handleNodeSelect} />
              : <p style={S.hint}>그래프를 불러오는 중...</p>
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
            subject={selectedSubject}
            onSelectQuestion={(q) => { setBrowseQuestion(q); setView(VIEWS.QUESTION_SOLVE) }}
          />
        )}

        {view === VIEWS.QUESTION_SOLVE && browseQuestion && (
          <QuestionSolve
            question={browseQuestion}
            subjectId={selectedSubject?.id}
            onSubmitSuccess={() => {}}
            onBack={() => setView(VIEWS.BROWSE)}
          />
        )}
      </main>
    </div>
  )
}

const S = {
  app:           { fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif', minHeight: '100vh', background: '#f8f9fa' },
  header:        { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.6rem 1.5rem', background: '#fff', borderBottom: '1px solid #e2e8f0' },
  logo:          { fontWeight: 'bold', fontSize: 16, color: '#2d3748' },
  headerRight:   { display: 'flex', alignItems: 'center', gap: 12 },
  subjectSelect: { padding: '5px 10px', border: '1px solid #ddd', borderRadius: 6, fontSize: 13, background: '#fff', color: '#2d3748', cursor: 'pointer' },
  studentName:   { fontSize: 13, color: '#666' },
  logoutBtn:     { padding: '4px 12px', border: '1px solid #ddd', borderRadius: 4, cursor: 'pointer', fontSize: 13, background: '#fff' },
  tabNav:        { display: 'flex', gap: 0, background: '#fff', borderBottom: '2px solid #e2e8f0', padding: '0 1.5rem' },
  tabBtn:        (active) => ({
    padding: '10px 20px', border: 'none', borderBottom: active ? '2px solid #4a90e2' : '2px solid transparent',
    marginBottom: -2, cursor: 'pointer', fontSize: 14, fontWeight: active ? 600 : 400,
    background: 'transparent', color: active ? '#4a90e2' : '#718096', transition: 'all 0.15s',
  }),
  main:          { padding: '1.5rem', maxWidth: 900, margin: '0 auto' },
  hint:          { color: '#888', textAlign: 'center', paddingTop: '2rem' },
}
