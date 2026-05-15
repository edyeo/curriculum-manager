import React, { useEffect, useRef, useState } from 'react'

const NODE_W = 160
const NODE_H = 58
const H_GAP = 200
const V_GAP = 70

const TYPE_STYLE = {
  Seed:      { bg: '#0f2140', border: '#3b82f6', badge: '#3b82f6', text: '#93c5fd' },
  Concept:   { bg: '#0f2d1e', border: '#22c55e', badge: '#22c55e', text: '#86efac' },
  TechStack: { bg: '#2d0f1e', border: '#ec4899', badge: '#ec4899', text: '#f9a8d4' },
}
const DEFAULT_TYPE_STYLE = { bg: '#1a2535', border: '#4a5568', badge: '#4a5568', text: '#94a3b8' }

// Palette: cycle through these for unknown relation types
const EDGE_PALETTE = ['#6366f1', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4', '#f97316']
const RELATION_COLORS = {
  prerequisite: '#6366f1',
  requires:     '#6366f1',
  includes:     '#10b981',
  contains:     '#10b981',
  related_to:   '#f59e0b',
  related:      '#f59e0b',
  implements:   '#ec4899',
  extends:      '#8b5cf6',
  uses:         '#06b6d4',
  supports:     '#f97316',
}

function edgeColor(relationType, colorCache) {
  const key = (relationType || '').toLowerCase()
  if (RELATION_COLORS[key]) return RELATION_COLORS[key]
  if (!colorCache[key]) {
    colorCache[key] = EDGE_PALETTE[Object.keys(colorCache).length % EDGE_PALETTE.length]
  }
  return colorCache[key]
}

// Layout visible nodes: one column per depth, nodes sorted by type within each column
function layout(visibleNodes) {
  const byDepth = {}
  for (const n of visibleNodes) {
    if (!byDepth[n.depth]) byDepth[n.depth] = []
    byDepth[n.depth].push(n)
  }
  const positions = {}
  let col = 0
  for (const depth of [1, 2, 3]) {
    const group = byDepth[depth] || []
    if (!group.length) continue
    group.sort((a, b) => a.type.localeCompare(b.type) || a.name.localeCompare(b.name))
    group.forEach((n, i) => {
      positions[n.id] = { x: col * (NODE_W + H_GAP) + 20, y: i * (NODE_H + V_GAP) + 20 }
    })
    col++
  }
  return positions
}

export default function GraphView({ nodes, edges }) {
  const svgRef = useRef(null)
  const [tooltip, setTooltip] = useState(null)
  // { [type]: maxVisibleDepth } — defaults to 1 for each type
  const [expandedDepths, setExpandedDepths] = useState({})

  // Max depth available per type
  const typeMaxDepths = {}
  for (const n of nodes) {
    typeMaxDepths[n.type] = Math.max(typeMaxDepths[n.type] || 0, n.depth)
  }

  const getMaxVisible = (type) => expandedDepths[type] ?? 1

  const visibleNodes = nodes.filter(n => n.depth <= getMaxVisible(n.type))
  const visibleSet = new Set(visibleNodes.map(n => n.id))
  const visibleEdges = edges.filter(e => visibleSet.has(e.source_id) && visibleSet.has(e.target_id))

  const positions = layout(visibleNodes)

  const handleNodeClick = (node) => {
    const { type, depth } = node
    const cur = getMaxVisible(type)
    const max = typeMaxDepths[type] || 1
    if (depth === cur && cur < max) {
      // Frontier node → expand one more depth
      setExpandedDepths(prev => ({ ...prev, [type]: cur + 1 }))
    } else if (depth < cur) {
      // Clicking an inner node → collapse back to this depth
      setExpandedDepths(prev => ({ ...prev, [type]: depth }))
    } else {
      // Already at max → collapse to 1
      setExpandedDepths(prev => ({ ...prev, [type]: 1 }))
    }
  }

  // Draw edges with arrows + colored labels
  useEffect(() => {
    const svg = svgRef.current
    if (!svg) return
    svg.innerHTML = ''

    const colorCache = {}
    const usedColors = new Set(visibleEdges.map(e => edgeColor(e.relation_type, colorCache)))

    // Arrow marker defs per color
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs')
    for (const color of usedColors) {
      const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker')
      const mid = `arr-${color.slice(1)}`
      marker.setAttribute('id', mid)
      marker.setAttribute('viewBox', '0 0 10 10')
      marker.setAttribute('refX', '8')
      marker.setAttribute('refY', '5')
      marker.setAttribute('markerWidth', '5')
      marker.setAttribute('markerHeight', '5')
      marker.setAttribute('orient', 'auto-start-reverse')
      const poly = document.createElementNS('http://www.w3.org/2000/svg', 'path')
      poly.setAttribute('d', 'M 0 0 L 10 5 L 0 10 z')
      poly.setAttribute('fill', color)
      marker.appendChild(poly)
      defs.appendChild(marker)
    }
    svg.appendChild(defs)

    for (const e of visibleEdges) {
      const s = positions[e.source_id]
      const t = positions[e.target_id]
      if (!s || !t) continue

      const color = edgeColor(e.relation_type, colorCache)
      const mid = `arr-${color.slice(1)}`

      const sx = s.x + NODE_W, sy = s.y + NODE_H / 2
      const tx = t.x,          ty = t.y + NODE_H / 2

      // If same column (same x), use a looping arc to the right
      let pathD
      if (Math.abs(sx - tx) < 10) {
        const cx = sx + 60
        pathD = `M ${sx} ${sy} C ${cx} ${sy}, ${cx} ${ty}, ${tx + NODE_W} ${ty}`
      } else {
        const mx = (sx + tx) / 2
        pathD = `M ${sx} ${sy} C ${mx} ${sy}, ${mx} ${ty}, ${tx} ${ty}`
      }

      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path')
      path.setAttribute('d', pathD)
      path.setAttribute('stroke', color)
      path.setAttribute('stroke-width', '1.5')
      path.setAttribute('fill', 'none')
      path.setAttribute('marker-end', `url(#${mid})`)
      svg.appendChild(path)

      // Label: pill background + text
      const lx = (sx + tx) / 2
      const ly = (sy + ty) / 2
      const labelText = (e.relation_type || '').replace(/_/g, ' ')
      const labelW = Math.max(labelText.length * 6.5 + 12, 30)

      const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
      rect.setAttribute('x', lx - labelW / 2)
      rect.setAttribute('y', ly - 10)
      rect.setAttribute('width', labelW)
      rect.setAttribute('height', 18)
      rect.setAttribute('rx', '5')
      rect.setAttribute('fill', '#0b1120')
      rect.setAttribute('fill-opacity', '0.9')
      rect.setAttribute('stroke', color)
      rect.setAttribute('stroke-width', '0.5')
      svg.appendChild(rect)

      const text = document.createElementNS('http://www.w3.org/2000/svg', 'text')
      text.setAttribute('x', lx)
      text.setAttribute('y', ly + 3)
      text.setAttribute('text-anchor', 'middle')
      text.setAttribute('font-size', '10')
      text.setAttribute('font-family', 'sans-serif')
      text.setAttribute('fill', color)
      text.textContent = labelText
      svg.appendChild(text)
    }
  }, [visibleNodes, visibleEdges, JSON.stringify(positions)])

  const canvasWidth  = (Object.values(positions).reduce((m, p) => Math.max(m, p.x), 0) || 0) + NODE_W + 60
  const canvasHeight = (Object.values(positions).reduce((m, p) => Math.max(m, p.y), 0) || 0) + NODE_H + 60

  return (
    <div className="graph-tab" style={{ overflow: 'auto', display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Legend bar */}
      <div style={{
        padding: '8px 16px', display: 'flex', gap: 20, flexWrap: 'wrap', alignItems: 'center',
        borderBottom: '1px solid #1e2d3d', fontSize: 11, flexShrink: 0,
      }}>
        {Object.entries(TYPE_STYLE).map(([type, st]) => {
          const max = typeMaxDepths[type]
          if (!max) return null
          const cur = getMaxVisible(type)
          return (
            <span key={type} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 10, height: 10, borderRadius: 2, background: st.badge, display: 'inline-block', flexShrink: 0 }} />
              <span style={{ color: st.text, fontWeight: 500 }}>{type}</span>
              <span style={{ color: '#475569' }}>D{cur}/{max}</span>
            </span>
          )
        })}
        <span style={{ color: '#334155', marginLeft: 'auto', fontSize: 10 }}>
          노드 클릭 → 같은 타입 depth 펼치기 / 안쪽 클릭 → 접기
        </span>
      </div>

      {/* Canvas */}
      <div style={{ overflow: 'auto', flex: 1 }}>
        <div style={{ width: canvasWidth, height: canvasHeight, position: 'relative' }}>
          <svg
            ref={svgRef}
            style={{ width: canvasWidth, height: canvasHeight, position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
          />

          {visibleNodes.map(n => {
            const pos = positions[n.id]
            if (!pos) return null
            const st = TYPE_STYLE[n.type] || DEFAULT_TYPE_STYLE
            const cur = getMaxVisible(n.type)
            const max = typeMaxDepths[n.type] || 1
            const isFrontier = n.depth === cur
            const hasMore = isFrontier && cur < max

            return (
              <div
                key={n.id}
                onClick={() => handleNodeClick(n)}
                onMouseEnter={() => setTooltip({ n, x: pos.x, y: pos.y })}
                onMouseLeave={() => setTooltip(null)}
                style={{
                  position: 'absolute',
                  left: pos.x, top: pos.y,
                  width: NODE_W, height: NODE_H,
                  background: st.bg,
                  border: `1.5px solid ${isFrontier ? st.border : st.border + '55'}`,
                  borderRadius: 8,
                  padding: '7px 10px',
                  cursor: 'pointer',
                  userSelect: 'none',
                  boxShadow: isFrontier ? `0 0 8px ${st.border}33` : 'none',
                  transition: 'border-color 0.15s, box-shadow 0.15s',
                }}
              >
                <div style={{
                  fontSize: 11, fontWeight: 600, color: st.text,
                  overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis',
                  marginBottom: 4,
                }}>
                  {n.name}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 10 }}>
                  <span style={{
                    background: st.badge + '22', color: st.badge,
                    padding: '1px 5px', borderRadius: 3, fontWeight: 500,
                  }}>
                    {n.type}
                  </span>
                  <span style={{ color: '#475569' }}>D{n.depth}</span>
                  {hasMore && (
                    <span style={{ color: st.border, marginLeft: 'auto', fontSize: 13, lineHeight: 1 }}>▸</span>
                  )}
                  {!hasMore && n.depth > 1 && isFrontier && max === n.depth && (
                    <span style={{ color: '#334155', marginLeft: 'auto', fontSize: 11 }}>▾</span>
                  )}
                </div>
              </div>
            )
          })}

          {tooltip && (() => {
            const { n, x, y } = tooltip
            const st = TYPE_STYLE[n.type] || DEFAULT_TYPE_STYLE
            return (
              <div style={{
                position: 'absolute',
                left: x + NODE_W + 10, top: y,
                background: '#0b1120',
                border: `1px solid ${st.border}55`,
                borderRadius: 8,
                padding: '10px 14px',
                maxWidth: 260, zIndex: 20,
                fontSize: 12, lineHeight: 1.6,
                pointerEvents: 'none',
              }}>
                <div style={{ fontWeight: 600, color: st.text, marginBottom: 4 }}>{n.name}</div>
                <div style={{ color: '#475569', fontSize: 10, marginBottom: n.description ? 6 : 0 }}>
                  {n.type} · Depth {n.depth}
                </div>
                {n.description && (
                  <div style={{ color: '#94a3b8', fontSize: 11 }}>{n.description}</div>
                )}
              </div>
            )
          })()}
        </div>
      </div>
    </div>
  )
}
