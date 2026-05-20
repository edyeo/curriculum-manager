import { Routes, Route, NavLink } from 'react-router-dom'
import { SubjectProvider, useSubject } from './context/SubjectContext'
import Dashboard from './pages/Dashboard'
import Students from './pages/Students'
import Features from './pages/Features'
import Simulation from './pages/Simulation'

export default function App() {
  return (
    <SubjectProvider>
      <div className="app">
        <AppHeader />
        <SubNav />
        <main className="main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/students" element={<Students />} />
            <Route path="/features" element={<Features />} />
            <Route path="/simulation" element={<Simulation />} />
          </Routes>
        </main>
      </div>
    </SubjectProvider>
  )
}

function AppHeader() {
  const { subjects, selectedId, setSelectedId } = useSubject()

  return (
    <header className="header">
      <span className="logo">Virtual Student Manager</span>
      <select
        className="subject-select"
        value={selectedId}
        onChange={e => setSelectedId(e.target.value)}
      >
        {subjects.length === 0 && <option value="">Subject 로딩 중…</option>}
        {subjects.map(s => (
          <option key={s.id} value={s.id}>{s.name}</option>
        ))}
      </select>
    </header>
  )
}

function SubNav() {
  return (
    <nav className="subnav">
      <NavLink to="/" end>Dashboard</NavLink>
      <NavLink to="/students">Students</NavLink>
      <NavLink to="/features">Features</NavLink>
      <NavLink to="/simulation">Simulation</NavLink>
    </nav>
  )
}
