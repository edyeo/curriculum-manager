import React, { useState } from 'react'
import * as api from './services/contentsApi.js'

export default function LoginPage({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await api.login(email, password)
      localStorage.setItem('cm_token', data.access_token)
      onLogin()
    } catch (err) {
      setError(err.message || '로그인 실패')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-box">
        <h1>Contents Manager</h1>
        <form onSubmit={handleSubmit}>
          <label>이메일</label>
          <input type="email" value={email} onChange={e => setEmail(e.target.value)} required autoFocus />
          <label>패스워드</label>
          <input type="password" value={password} onChange={e => setPassword(e.target.value)} required />
          <button className="btn-login" type="submit" disabled={loading}>
            {loading ? '로그인 중...' : '로그인'}
          </button>
          {error && <p className="login-error">{error}</p>}
        </form>
      </div>
    </div>
  )
}
