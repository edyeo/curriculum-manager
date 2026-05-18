const BASE = '/api'

const authHeader = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('student_token') || ''}`,
})

async function request(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: authHeader(),
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw Object.assign(new Error(err.detail || 'Request failed'), { status: res.status })
  }
  return res.json()
}

export const api = {
  // auth
  register: (email, name, password) => request('POST', '/auth/register', { email, name, password }),
  login: (email, password) => request('POST', '/auth/login', { email, password }),
  me: () => request('GET', '/auth/me'),

  // curriculum
  getSubjects: () => request('GET', '/curriculum/subjects'),
  getGraph: (subjectId) => request('GET', `/curriculum/graph/${subjectId}`),
  getQuestions: (nodeId) => request('GET', `/curriculum/nodes/${nodeId}/questions`),

  // question bank
  getPublishedQuestions: (filters = {}) => {
    const params = new URLSearchParams(Object.entries(filters).filter(([, v]) => v)).toString()
    return request('GET', `/questions/published${params ? '?' + params : ''}`)
  },
  getQuestionDetail: (id) => request('GET', `/questions/${id}`),
  submitQuestionAnswer: (id, answer, elapsed_ms = 0, subject_id = null) =>
    request('POST', `/questions/${id}/submit`, { answer, elapsed_ms, subject_id }),

  // study
  submit: (payload) => request('POST', '/study/submit', payload),
  getMastery: (subjectId) =>
    request('GET', `/study/mastery${subjectId ? `?subject_id=${subjectId}` : ''}`),
  getRecommend: (subjectId, currentNodeId) =>
    request('GET', `/study/recommend?subject_id=${subjectId}${currentNodeId ? `&current_node_id=${currentNodeId}` : ''}`),
  getCompetency: (subjectId) =>
    request('GET', `/study/competency?subject_id=${subjectId}`),
  getBlueprintMatrix: () =>
    request('GET', '/study/blueprint-matrix'),
}
