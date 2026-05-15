import React, { useEffect, useRef, useState } from 'react'

const NODE_W = 140
const NODE_H = 52
const H_GAP = 180
const V_GAP = 80

function layout(nodes) {
  const byDepth = { 1: [], 2: [], 3: [] }
  for (const n of nodes) byDepth[n.depth]?.push(n)
  const positions = {}
  let col = 0
  for (const depth of [1, 2, 3]) {
    const group = byDepth[depth]
    group.forEach((n, i) => {
      positions[n.id] = { x: col * (NODE_W + H_GAP) + 20, y: i * (NODE_H + V_GAP) + 20 }
    })
    if (group.length) col++
  }
  return positions
}

export default function GraphView({ nodes, edges }) {
  const svgRef = useRef(null)
  const [tooltip, setTooltip] = useState(null)

  const positions = layout(nodes)

  useEffect(() => {
    const svg = svgRef.current
    if (!svg) return
    svg.innerHTML = ''
    for (const e of edges) {
      const s = positions[e.source_id]
      const t = positions[e.target_id]
      if (!s || !t) continue
      const x1 = s.x + NODE_W, y1 = s.y + NODE_H / 2
      const x2 = t.x, y2 = t.y + NODE_H / 2
      const mx = (x1 + x2) / 2

      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path')
      path.setAttribute('d', `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`)
      path.setAttribute('stroke', '#3a4a6a')
      path.setAttribute('stroke-width', '1.5')
      path.setAttribute('fill', 'none')
      svg.appendChild(path)

      const label = document.createElementNS('http://www.w3.org/2000/svg', 'text')
      label.setAttribute('x', mx)
      label.setAttribute('y', (y1 + y2) / 2 - 4)
      label.setAttribute('text-anchor', 'middle')
      label.setAttribute('font-size', '10')
      label.setAttribute('fill', '#4a5568')
      label.textContent = e.relation_type
      svg.appendChild(label)
    }
  }, [nodes, edges])

  const canvasWidth = (Object.values(positions).reduce((m, p) => Math.max(m, p.x), 0) || 0) + NODE_W + 40
  const canvasHeight = (Object.values(positions).reduce((m, p) => Math.max(m, p.y), 0) || 0) + NODE_H + 40

  return (
    <div className="graph-tab" style={{ overflow: 'auto' }}>
      <div className="graph-canvas" style={{ width: canvasWidth, height: canvasHeight, position: 'relative' }}>
        <svg ref={svgRef} className="graph-svg" style={{ width: canvasWidth, height: canvasHeight }} />
        {nodes.map(n => {
          const pos = positions[n.id]
          if (!pos) return null
          return (
            <div
              key={n.id}
              className={`graph-node type-${n.type}`}
              style={{ left: pos.x, top: pos.y, width: NODE_W, height: NODE_H, position: 'absolute' }}
              onMouseEnter={() => setTooltip({ id: n.id, name: n.name, desc: n.description, x: pos.x, y: pos.y })}
              onMouseLeave={() => setTooltip(null)}
            >
              <div className="node-name" style={{ fontSize: 12, fontWeight: 500, overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>{n.name}</div>
              <div className="node-type" style={{ fontSize: 10, color: '#64748b' }}>{n.type} · D{n.depth}</div>
            </div>
          )
        })}
        {tooltip && (
          <div style={{
            position: 'absolute', left: tooltip.x + NODE_W + 8, top: tooltip.y,
            background: '#1a1d2e', border: '1px solid #2d3748', borderRadius: 8,
            padding: '10px 14px', maxWidth: 240, zIndex: 10, fontSize: 12, lineHeight: 1.5,
          }}>
            <strong>{tooltip.name}</strong>
            {tooltip.desc && <p style={{ color: '#94a3b8', marginTop: 4 }}>{tooltip.desc}</p>}
          </div>
        )}
      </div>
    </div>
  )
}
