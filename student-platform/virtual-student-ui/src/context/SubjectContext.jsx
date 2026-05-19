import { createContext, useContext, useState, useEffect } from 'react'
import { fetchSubjects } from '../api/client'

const SubjectContext = createContext(null)

export function SubjectProvider({ children }) {
  const [subjects, setSubjects] = useState([])
  const [selectedId, setSelectedId] = useState('')

  useEffect(() => {
    fetchSubjects()
      .then(list => {
        setSubjects(list)
        if (list.length > 0) setSelectedId(list[0].id)
      })
      .catch(() => {})
  }, [])

  const selected = subjects.find(s => s.id === selectedId) ?? null

  return (
    <SubjectContext.Provider value={{ subjects, selectedId, setSelectedId, selected }}>
      {children}
    </SubjectContext.Provider>
  )
}

export function useSubject() {
  const ctx = useContext(SubjectContext)
  if (!ctx) throw new Error('useSubject must be used within SubjectProvider')
  return ctx
}
