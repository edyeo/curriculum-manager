import { Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Students from './pages/Students'
import Features from './pages/Features'

export default function App() {
  return (
    <div className="app">
      <header className="header">
        <span className="logo">Virtual Student Manager</span>
        <nav>
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/students">Students</NavLink>
          <NavLink to="/features">Features</NavLink>
        </nav>
      </header>
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/students" element={<Students />} />
          <Route path="/features" element={<Features />} />
        </Routes>
      </main>
    </div>
  )
}
