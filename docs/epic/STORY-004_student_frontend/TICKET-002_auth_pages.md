# TICKET-002: 로그인 / 가입 페이지

## 메타

| 항목 | 내용 |
|---|---|
| 컴포넌트 | student-platform/frontend |
| 파일 | `src/components/LoginPage.jsx`, `src/components/RegisterPage.jsx` |
| 의존 | TICKET-001 |
| 선행 조건 | TICKET-001 완료 |

---

## 작업 내용

### `App.jsx` 라우팅

```jsx
// JWT 없으면 LoginPage, 있으면 메인 앱
if (!token) return <LoginPage onLogin={...} onGoRegister={...} />
```

### `LoginPage.jsx`

- email / password 입력
- `api.login()` 호출 → JWT 저장 → 메인으로 이동
- "계정이 없으신가요? 가입하기" 링크

### `RegisterPage.jsx`

- email / name / password 입력
- `api.register()` 호출 → JWT 저장 → 메인으로 이동

---

## 완료 기준

- [ ] 로그인 성공 시 JWT localStorage 저장 후 메인 화면 전환
- [ ] 가입 성공 시 자동 로그인 처리
- [ ] 잘못된 이메일/비밀번호 시 에러 메시지 표시
- [ ] 로그아웃 버튼: token 삭제 후 LoginPage로 이동
