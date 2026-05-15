import React, { useState, useEffect } from 'react'
import * as api from '../services/contentsApi.js'

export default function ResearchTab({ subjectId }) {
  const [results, setResults] = useState([])
  const [keyword, setKeyword] = useState('')
  const [source, setSource] = useState('')
  const [loading, setLoading] = useState(false)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const data = await api.getResearchResults(subjectId, { keyword: keyword || undefined, source: source || undefined })
      const items = data?.data?.results || data?.results || []
      setResults(items)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { if (subjectId) load() }, [subjectId])

  const handleStart = async () => {
    setStarting(true)
    setError('')
    try {
      await api.startResearch(subjectId)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setStarting(false)
    }
  }

  return (
    <div className="research-tab">
      <div className="research-toolbar">
        <button className="btn-research" onClick={handleStart} disabled={starting}>
          {starting ? '리서치 중...' : '리서치 시작'}
        </button>
        <input placeholder="키워드 검색..." value={keyword} onChange={e => setKeyword(e.target.value)} onKeyDown={e => e.key === 'Enter' && load()} />
        <select value={source} onChange={e => { setSource(e.target.value); }}>
          <option value="">전체 소스</option>
          <option value="blog">blog</option>
          <option value="linkedin">linkedin</option>
          <option value="paper">paper</option>
          <option value="github">github</option>
        </select>
        <button onClick={load} disabled={loading}>{loading ? '로딩...' : '검색'}</button>
      </div>
      {error && <p style={{ color: '#f87171', marginBottom: 12 }}>{error}</p>}
      {results.length === 0 && !loading && (
        <p className="empty-msg">리서치 결과가 없습니다. "리서치 시작"을 눌러보세요.</p>
      )}
      {results.map((r, i) => (
        <div key={r.id || i} className="research-item">
          <div className="r-header">
            <span className="source-badge">{r.source}</span>
            <span className="r-keyword">{r.keyword}</span>
          </div>
          <div className="r-title">{r.title}</div>
          <div className="r-summary">{r.summary}</div>
          {r.url && <a className="r-link" href={r.url} target="_blank" rel="noreferrer">링크 열기 →</a>}
        </div>
      ))}
    </div>
  )
}
