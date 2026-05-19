import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts'
import { fetchStudents, fetchStats } from '../api/client'
import { useSubject } from '../context/SubjectContext'

const CATEGORY_TABS = ['전체', '숙련도', '학습특성', '기질', '답변 행동']

export default function Dashboard() {
  const { selectedId: subjectId } = useSubject()
  const [students, setStudents] = useState({ total: 0, items: [], page: 1, page_size: 20 })
  const [stats, setStats] = useState(null)
  const [page, setPage] = useState(1)
  const [categoryTab, setCategoryTab] = useState('전체')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => { setPage(1) }, [subjectId])
  useEffect(() => { load() }, [subjectId, page])

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const params = { page, page_size: 20 }
      if (subjectId) params.subject_id = subjectId

      const [studentsData, statsData] = await Promise.all([
        fetchStudents(params),
        fetchStats(subjectId || null),
      ])

      setStudents(studentsData)
      setStats(statsData)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const filteredDist = (stats?.feature_distributions || []).filter(
    fd => categoryTab === '전체' || fd.category === categoryTab
  )
  const totalPages = Math.ceil(students.total / 20)

  return (
    <div>
      <div className="section-header">
        <h2>Dashboard</h2>
      </div>

      {error && (
        <div className="error-banner">
          데이터를 불러올 수 없습니다: {error}
          <button onClick={load}>재시도</button>
        </div>
      )}

      <div className="card">
        <h3>
          학생 목록
          <span className="badge">{students.total}명</span>
        </h3>
        <table className="table">
          <thead>
            <tr><th>#</th><th>이름</th><th>Subject</th><th>생성일</th></tr>
          </thead>
          <tbody>
            {students.items.map((s, i) => (
              <tr key={s.id}>
                <td>{(page - 1) * 20 + i + 1}</td>
                <td>{s.name}</td>
                <td><span className="tag">{s.subject_id}</span></td>
                <td>{new Date(s.created_at).toLocaleDateString('ko-KR')}</td>
              </tr>
            ))}
            {!loading && students.items.length === 0 && (
              <tr>
                <td colSpan={4} style={{ textAlign: 'center', color: '#999', padding: '24px' }}>
                  등록된 가상 학생이 없습니다
                </td>
              </tr>
            )}
          </tbody>
        </table>
        {totalPages > 1 && (
          <div className="pagination">
            <button disabled={page === 1} onClick={() => setPage(p => p - 1)}>‹</button>
            <span>{page} / {totalPages}</span>
            <button disabled={page === totalPages} onClick={() => setPage(p => p + 1)}>›</button>
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Feature 분포</h3>
          <div className="tabs">
            {CATEGORY_TABS.map(tab => (
              <button
                key={tab}
                className={`tab ${categoryTab === tab ? 'active' : ''}`}
                onClick={() => setCategoryTab(tab)}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>
        <div className="chart-grid">
          {filteredDist.map(fd => <DistributionCard key={fd.feature_key} fd={fd} />)}
          {filteredDist.length === 0 && !loading && (
            <p style={{ color: '#999' }}>표시할 데이터가 없습니다.</p>
          )}
        </div>
      </div>
    </div>
  )
}

function DistributionCard({ fd }) {
  if (fd.value_type === 'categorical') {
    const data = fd.distribution.map(d => ({ name: d.value, count: d.count, ratio: d.ratio }))
    return (
      <div className="chart-card">
        <h4>
          {fd.display_name}
          <span className="badge-sm">{fd.category}</span>
        </h4>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={data} layout="vertical" margin={{ left: 10, right: 24, top: 4, bottom: 4 }}>
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="name" width={56} tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(v, _, p) => [`${v}명 (${(p.payload.ratio * 100).toFixed(0)}%)`, '학생 수']}
            />
            <Bar dataKey="count" fill="#6366f1" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    )
  }

  if (fd.value_type === 'numeric') {
    const { min, max, mean, buckets } = fd.distribution
    const data = buckets.map(b => ({ name: b.range, count: b.count }))
    return (
      <div className="chart-card">
        <h4>
          {fd.display_name}
          <span className="badge-sm">{fd.category}</span>
        </h4>
        <div className="stat-row">
          <span>min: {min}</span>
          <span>max: {max}</span>
          <span>평균: {mean}</span>
        </div>
        <ResponsiveContainer width="100%" height={150}>
          <BarChart data={data} margin={{ left: 0, right: 10, top: 4, bottom: 4 }}>
            <XAxis dataKey="name" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v) => [`${v}명`, '학생 수']} />
            <Bar dataKey="count" fill="#10b981" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    )
  }

  return null
}
