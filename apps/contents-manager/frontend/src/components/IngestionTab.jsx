import React, { useState } from 'react'
import IngestionSourceListView from './ingestion/IngestionSourceListView.jsx'
import IngestionSourceAddView from './ingestion/IngestionSourceAddView.jsx'
import IngestionAuditView from './ingestion/IngestionAuditView.jsx'

function NavItem({ id, label, active, onClick }) {
  return (
    <div
      onClick={() => onClick(id)}
      style={{
        padding: '7px 12px 7px 28px',
        fontSize: 12,
        cursor: 'pointer',
        color: active === id ? '#e2e8f0' : '#64748b',
        background: active === id ? '#1e2130' : 'transparent',
        borderLeft: `2px solid ${active === id ? '#4f46e5' : 'transparent'}`,
        userSelect: 'none',
      }}
    >
      {label}
    </div>
  )
}

function NavGroup({ label, open, onToggle, children }) {
  return (
    <div>
      <div
        onClick={onToggle}
        style={{
          padding: '10px 12px',
          fontSize: 11,
          fontWeight: 600,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          userSelect: 'none',
          letterSpacing: '0.05em',
          textTransform: 'uppercase',
          color: '#94a3b8',
        }}
      >
        <span style={{ fontSize: 9, color: '#4b5563' }}>{open ? '▾' : '▸'}</span>
        {label}
      </div>
      {open && children}
    </div>
  )
}

export default function IngestionTab() {
  const [active, setActive] = useState('source-list')
  const [sourceOpen, setSourceOpen] = useState(true)
  const [auditKey, setAuditKey] = useState(0)

  const handleSaved = () => setActive('source-list')
  const handleParsed = () => setAuditKey(k => k + 1)

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>

      {/* 좌측 네비게이션 */}
      <div style={{
        width: 160, flexShrink: 0,
        background: '#0d1117',
        borderRight: '1px solid #1f2937',
        paddingTop: 8,
      }}>
        <NavGroup label="Source" open={sourceOpen} onToggle={() => setSourceOpen(v => !v)}>
          <NavItem id="source-list" label="조회" active={active} onClick={setActive} />
          <NavItem id="source-add"  label="추가" active={active} onClick={setActive} />
        </NavGroup>

        <div
          onClick={() => setActive('audit')}
          style={{
            padding: '10px 12px',
            fontSize: 11,
            fontWeight: 600,
            cursor: 'pointer',
            color: active === 'audit' ? '#e2e8f0' : '#94a3b8',
            background: active === 'audit' ? '#1e2130' : 'transparent',
            borderLeft: `2px solid ${active === 'audit' ? '#4f46e5' : 'transparent'}`,
            userSelect: 'none',
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
          }}
        >
          Audit
        </div>
      </div>

      {/* 메인 콘텐츠 */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {active === 'source-list' && <IngestionSourceListView onParsed={handleParsed} />}
        {active === 'source-add'  && <IngestionSourceAddView  onSaved={handleSaved} />}
        {active === 'audit'       && <IngestionAuditView key={auditKey} />}
      </div>
    </div>
  )
}
