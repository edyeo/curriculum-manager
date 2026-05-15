const BASE = '/api'

const headers = () => ({
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${localStorage.getItem('cm_token') || ''}`
})

const handle = async (res) => {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// Auth
export const login = (email, password) =>
  fetch(`${BASE}/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) }).then(handle)

export const getMe = () =>
  fetch(`${BASE}/auth/me`, { headers: headers() }).then(handle)

// Subjects
export const getSubjects = () =>
  fetch(`${BASE}/subjects`, { headers: headers() }).then(handle)

export const createSubject = (name, description) =>
  fetch(`${BASE}/subjects`, { method: 'POST', headers: headers(), body: JSON.stringify({ name, description }) }).then(handle)

export const deleteSubject = (id) =>
  fetch(`${BASE}/subjects/${id}`, { method: 'DELETE', headers: headers() }).then(handle)

// Nodes
export const getNodes = (subjectId) =>
  fetch(`${BASE}/subjects/${subjectId}/nodes`, { headers: headers() }).then(handle)

export const createNode = (subjectId, node) =>
  fetch(`${BASE}/subjects/${subjectId}/nodes`, { method: 'POST', headers: headers(), body: JSON.stringify(node) }).then(handle)

export const updateNode = (subjectId, nodeId, patch) =>
  fetch(`${BASE}/subjects/${subjectId}/nodes/${nodeId}`, { method: 'PATCH', headers: headers(), body: JSON.stringify(patch) }).then(handle)

export const deleteNode = (subjectId, nodeId) =>
  fetch(`${BASE}/subjects/${subjectId}/nodes/${nodeId}`, { method: 'DELETE', headers: headers() }).then(handle)

// Edges
export const getEdges = (subjectId) =>
  fetch(`${BASE}/subjects/${subjectId}/edges`, { headers: headers() }).then(handle)

export const createEdge = (subjectId, edge) =>
  fetch(`${BASE}/subjects/${subjectId}/edges`, { method: 'POST', headers: headers(), body: JSON.stringify(edge) }).then(handle)

export const deleteEdge = (subjectId, edgeId) =>
  fetch(`${BASE}/subjects/${subjectId}/edges/${edgeId}`, { method: 'DELETE', headers: headers() }).then(handle)

// Expand
export const expandCurriculum = (subjectId) =>
  fetch(`${BASE}/subjects/${subjectId}/curriculum/expand`, { method: 'POST', headers: headers() }).then(handle)

// Research
export const startResearch = (subjectId) =>
  fetch(`${BASE}/subjects/${subjectId}/research/start`, { method: 'POST', headers: headers() }).then(handle)

export const getResearchResults = (subjectId, filters = {}) => {
  const params = new URLSearchParams(Object.entries(filters).filter(([, v]) => v)).toString()
  return fetch(`${BASE}/subjects/${subjectId}/research/results${params ? '?' + params : ''}`, { headers: headers() }).then(handle)
}

// Questions
export const getQuestions = (subjectId, nodeId) =>
  fetch(`${BASE}/subjects/${subjectId}/nodes/${nodeId}/questions`, { headers: headers() }).then(handle)

export const generateQuestions = (subjectId, nodeId, count = 5) =>
  fetch(`${BASE}/subjects/${subjectId}/nodes/${nodeId}/questions`, { method: 'POST', headers: headers(), body: JSON.stringify({ count }) }).then(handle)
