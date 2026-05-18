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

// Generate draft (for existing subject)
export const generateCurriculum = (subjectId) =>
  fetch(`${BASE}/subjects/${subjectId}/curriculum/generate`, { method: 'POST', headers: headers() }).then(handle)

// Expand
export const expandCurriculum = (subjectId) =>
  fetch(`${BASE}/subjects/${subjectId}/curriculum/expand`, { method: 'POST', headers: headers() }).then(handle)

// AI Link
export const aiLinkCurriculum = (subjectId, payload) =>
  fetch(`${BASE}/subjects/${subjectId}/curriculum/link-ai`, { method: 'POST', headers: headers(), body: JSON.stringify(payload) }).then(handle)

export const previewAiLink = (subjectId, payload) =>
  fetch(`${BASE}/subjects/${subjectId}/curriculum/link-ai/preview`, { method: 'POST', headers: headers(), body: JSON.stringify(payload) }).then(handle)

export const confirmAiLink = (subjectId, edges) =>
  fetch(`${BASE}/subjects/${subjectId}/curriculum/link-ai/confirm`, { method: 'POST', headers: headers(), body: JSON.stringify({ edges }) }).then(handle)

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

// ── EPIC-002: Blueprints ───────────────────────────────────────────────────────
export const getBlueprints = () =>
  fetch(`${BASE}/blueprints`, { headers: headers() }).then(handle)

export const createBlueprint = (body) =>
  fetch(`${BASE}/blueprints`, { method: 'POST', headers: headers(), body: JSON.stringify(body) }).then(handle)

export const getBlueprint = (id) =>
  fetch(`${BASE}/blueprints/${id}`, { headers: headers() }).then(handle)

export const updateBlueprint = (id, patch) =>
  fetch(`${BASE}/blueprints/${id}`, { method: 'PATCH', headers: headers(), body: JSON.stringify(patch) }).then(handle)

export const deleteBlueprint = (id) =>
  fetch(`${BASE}/blueprints/${id}`, { method: 'DELETE', headers: headers() }).then(handle)

export const createIntegrationItem = (blueprintId, body) =>
  fetch(`${BASE}/blueprints/${blueprintId}/integration-items`, { method: 'POST', headers: headers(), body: JSON.stringify(body) }).then(handle)

export const updateIntegrationItem = (blueprintId, itemId, patch) =>
  fetch(`${BASE}/blueprints/${blueprintId}/integration-items/${itemId}`, { method: 'PATCH', headers: headers(), body: JSON.stringify(patch) }).then(handle)

export const deleteIntegrationItem = (blueprintId, itemId) =>
  fetch(`${BASE}/blueprints/${blueprintId}/integration-items/${itemId}`, { method: 'DELETE', headers: headers() }).then(handle)

// ── EPIC-003: Question Workbench ───────────────────────────────────────────────
export const startGeneration = (entityId, blueprintId, integrationItemId, questionType = 'MCQ') =>
  fetch(`${BASE}/question-workbench/generate`, {
    method: 'POST', headers: headers(),
    body: JSON.stringify({ entity_id: entityId, blueprint_id: blueprintId, integration_item_id: integrationItemId, question_type: questionType }),
  }).then(handle)

export const getGenerationJob = (jobId) =>
  fetch(`${BASE}/question-workbench/jobs/${jobId}`, { headers: headers() }).then(handle)

export const subgraphSearch = (integrationItemId) =>
  fetch(`${BASE}/question-workbench/subgraph-search`, {
    method: 'POST', headers: headers(),
    body: JSON.stringify({ integration_item_id: integrationItemId }),
  }).then(handle)

export const listWorkbenchQuestions = (filters = {}) => {
  const params = new URLSearchParams(Object.entries(filters).filter(([, v]) => v)).toString()
  return fetch(`${BASE}/question-workbench/questions${params ? '?' + params : ''}`, { headers: headers() }).then(handle)
}

export const saveWorkbenchQuestion = (body) =>
  fetch(`${BASE}/question-workbench/questions`, { method: 'POST', headers: headers(), body: JSON.stringify(body) }).then(handle)

export const updateWorkbenchQuestion = (id, patch) =>
  fetch(`${BASE}/question-workbench/questions/${id}`, { method: 'PATCH', headers: headers(), body: JSON.stringify(patch) }).then(handle)

export const publishWorkbenchQuestion = (id) =>
  fetch(`${BASE}/question-workbench/questions/${id}/publish`, { method: 'POST', headers: headers() }).then(handle)

export const deleteWorkbenchQuestion = (id) =>
  fetch(`${BASE}/question-workbench/questions/${id}`, { method: 'DELETE', headers: headers() }).then(handle)

export const getWorkbenchQuestion = (id) =>
  fetch(`${BASE}/question-workbench/questions/${id}`, { headers: headers() }).then(handle)

export const unpublishWorkbenchQuestion = (id) =>
  fetch(`${BASE}/question-workbench/questions/${id}/unpublish`, { method: 'POST', headers: headers() }).then(handle)

export const archiveWorkbenchQuestion = (id) =>
  fetch(`${BASE}/question-workbench/questions/${id}/archive`, { method: 'POST', headers: headers() }).then(handle)
