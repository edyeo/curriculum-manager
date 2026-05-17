# TICKET-001: Vite 프로젝트 구조 및 API 클라이언트

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | student-platform/frontend |
| 파일 | `student-platform/frontend/` (신규) |
| 의존 | 없음 |
| 선행 조건 | 없음 |

---

## 작업 내용

### 디렉토리 구조

```
student-platform/frontend/
├── index.html
├── vite.config.js        # proxy: /api → student-backend:8020
├── package.json
├── src/
│   ├── main.jsx
│   ├── App.jsx
│   ├── services/
│   │   └── api.js        # backend API 호출 함수 모음
│   ├── store/
│   │   └── auth.js       # JWT 토큰 관리 (localStorage)
│   └── components/       # 각 TICKET에서 추가
└── Dockerfile
```

### `services/api.js` 구조

```js
const BASE = '/api'

const authHeader = () => ({
  Authorization: `Bearer ${localStorage.getItem('student_token')}`
})

export const api = {
  // auth
  register: (email, name, password) => ...,
  login: (email, password) => ...,

  // curriculum
  getSubjects: () => ...,
  getGraph: (subjectId) => ...,          // nodes + edges + mastery
  getQuestions: (nodeId) => ...,

  // study
  submit: (payload) => ...,             // 답안 제출
  getMastery: () => ...,
  getRecommend: (subjectId, nodeId) => ...
}
```

### `vite.config.js` 프록시

```js
server: {
  proxy: {
    '/api': { target: 'http://localhost:8020', rewrite: p => p.replace(/^\/api/, '') }
  }
}
```

---

## 완료 기준

- [ ] `npm run dev` 로 :3001 기동
- [ ] `/api/*` 요청이 student-backend:8020으로 프록시됨
- [ ] `localStorage` 기반 JWT 저장/로드 동작
