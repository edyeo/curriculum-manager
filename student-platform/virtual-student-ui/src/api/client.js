const BASE = '/api/virtual-students'

async function request(url, options = {}) {
  const res = await fetch(url, options)
  if (res.status === 204) return null
  const text = await res.text()
  if (!res.ok) throw new Error(text || `HTTP ${res.status}`)
  return text ? JSON.parse(text) : null
}

export const fetchFeatureDefinitions = () => request(`${BASE}/feature-definitions`)

export const createFeatureDefinition = (data) =>
  request(`${BASE}/feature-definitions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

export const updateFeatureDefinition = (key, data) =>
  request(`${BASE}/feature-definitions/${key}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

export const deleteFeatureDefinition = (key) =>
  request(`${BASE}/feature-definitions/${key}`, { method: 'DELETE' })

export const fetchStudents = (params = {}) => {
  const q = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== ''))
  ).toString()
  return request(`${BASE}${q ? '?' + q : ''}`)
}

export const fetchStudent = (id) => request(`${BASE}/${id}`)

export const createStudent = (data) =>
  request(`${BASE}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

export const updateStudent = (id, data) =>
  request(`${BASE}/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

export const deleteStudent = (id) => request(`${BASE}/${id}`, { method: 'DELETE' })

export const fetchStats = (subjectId) => {
  const q = subjectId ? `?subject_id=${subjectId}` : ''
  return request(`${BASE}/stats${q}`)
}

export const generateStudents = (data) =>
  request(`${BASE}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

export const fetchSubjects = () =>
  request(`${BASE}/subjects`).then(d => d?.subjects ?? d ?? [])

export const seedStudents = (data) =>
  request(`${BASE}/seed`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

// ── Simulation ────────────────────────────────────────────────────────────────

const SIM = '/api/simulate'

export const createSimulationRun = (data) =>
  request(`${SIM}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

export const fetchSimulationRuns = (subjectId) => {
  const q = subjectId ? `?subject_id=${subjectId}` : ''
  return request(`${SIM}/runs${q}`)
}

export const fetchSimulationRun = (runId) =>
  request(`${SIM}/runs/${runId}`)

export const fetchKgQuestions = (subjectId) => {
  const q = subjectId ? `?subject_id=${subjectId}` : ''
  return request(`${SIM}/kg-questions${q}`).then(d => d?.questions ?? [])
}
