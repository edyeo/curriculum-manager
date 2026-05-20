import { useState } from 'react'
import { api } from '../services/api'

export default function RegisterPage({ onLogin, onGoLogin }) {
  const [form, setForm] = useState({ email: '', name: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await api.register(form.email, form.name, form.password)
      localStorage.setItem('student_token', res.token)
      onLogin(res)
    } catch (err) {
      setError(err.message || '가입 실패')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h2 style={styles.title}>회원 가입</h2>
        <form onSubmit={handleSubmit} style={styles.form}>
          <input type="email" placeholder="이메일" value={form.email}
            onChange={e => setForm({ ...form, email: e.target.value })}
            style={styles.input} required />
          <input type="text" placeholder="이름" value={form.name}
            onChange={e => setForm({ ...form, name: e.target.value })}
            style={styles.input} required />
          <input type="password" placeholder="비밀번호" value={form.password}
            onChange={e => setForm({ ...form, password: e.target.value })}
            style={styles.input} required />
          {error && <p style={styles.error}>{error}</p>}
          <button type="submit" disabled={loading} style={styles.btn}>
            {loading ? '처리 중...' : '가입하기'}
          </button>
        </form>
        <p style={styles.link}>
          이미 계정이 있으신가요?{' '}
          <button onClick={onGoLogin} style={styles.textBtn}>로그인</button>
        </p>
      </div>
    </div>
  )
}

const styles = {
  container: { display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#f5f5f5' },
  card: { background: '#fff', padding: '2rem', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)', width: '360px' },
  title: { textAlign: 'center', marginBottom: '1.5rem', color: '#333' },
  form: { display: 'flex', flexDirection: 'column', gap: '0.75rem' },
  input: { padding: '0.6rem', border: '1px solid #ddd', borderRadius: '4px', fontSize: '14px' },
  btn: { padding: '0.75rem', background: '#48bb78', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '14px' },
  error: { color: '#e53e3e', fontSize: '13px', margin: 0 },
  link: { textAlign: 'center', marginTop: '1rem', fontSize: '13px', color: '#666' },
  textBtn: { background: 'none', border: 'none', color: '#4a90e2', cursor: 'pointer', fontSize: '13px' },
}
