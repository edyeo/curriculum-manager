import { useCallback, useEffect, useState } from 'react'
import ReactFlow, {
  Background, Controls, MiniMap,
  useNodesState, useEdgesState,
  MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'

// mastery → 색상
function masteryColor(score) {
  if (score === null || score === undefined) return '#b0b0b0'  // 미학습 회색
  if (score < 0.4) return '#fc8181'   // 빨강
  if (score < 0.7) return '#f6ad55'   // 노랑
  return '#68d391'                    // 초록
}

// 노드 타입별 형태 (ReactFlow custom node 스타일)
const NODE_STYLES = {
  Seed:      { borderRadius: '50%',  minWidth: 90 },
  Concept:   { borderRadius: '6px',  minWidth: 110 },
  TechStack: { borderRadius: '3px',  minWidth: 100, transform: 'rotate(0deg)' },
}

const EDGE_STYLES = {
  requires:       { strokeDasharray: undefined, stroke: '#4a90e2' },
  implemented_by: { strokeDasharray: '6 3',     stroke: '#9b59b6' },
  has_subtopic:   { strokeDasharray: '2 2',     stroke: '#95a5a6' },
}

function buildRFNodes(nodes) {
  // 타입별 y 오프셋으로 레이아웃 근사
  const typeOrder = { Seed: 0, Concept: 1, TechStack: 2 }
  const countByType = {}
  return nodes.map((n) => {
    const type = n.type || 'Concept'
    countByType[type] = (countByType[type] || 0) + 1
    const col = countByType[type]
    return {
      id: n.id,
      position: { x: col * 160, y: (typeOrder[type] ?? 1) * 200 },
      data: { label: n.name, node: n },
      style: {
        background: masteryColor(n.mastery_score),
        border: '2px solid #555',
        padding: '8px 10px',
        fontSize: '12px',
        cursor: 'pointer',
        ...NODE_STYLES[type],
      },
    }
  })
}

function buildRFEdges(edges) {
  return edges.map((e) => {
    const style = EDGE_STYLES[e.relation] || {}
    return {
      id: e.id,
      source: e.source_id,
      target: e.target_id,
      label: e.relation,
      style: { stroke: style.stroke, strokeDasharray: style.strokeDasharray },
      markerEnd: { type: MarkerType.ArrowClosed, color: style.stroke || '#555' },
      labelStyle: { fontSize: 10, fill: '#666' },
    }
  })
}

export default function ConceptMap({ subjectId, graphData, onNodeSelect }) {
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState([])
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState([])
  const [tooltip, setTooltip] = useState(null)

  useEffect(() => {
    if (!graphData) return
    setRfNodes(buildRFNodes(graphData.nodes || []))
    setRfEdges(buildRFEdges(graphData.edges || []))
  }, [graphData])

  const onNodeClick = useCallback((_, rfNode) => {
    onNodeSelect(rfNode.data.node)
  }, [onNodeSelect])

  const onNodeMouseEnter = useCallback((_, rfNode) => {
    const n = rfNode.data.node
    setTooltip({
      name: n.name,
      type: n.type,
      mastery: n.mastery_score !== null && n.mastery_score !== undefined
        ? `${(n.mastery_score * 100).toFixed(0)}%`
        : '미학습',
    })
  }, [])

  return (
    <div style={{ position: 'relative', width: '100%', height: '520px', border: '1px solid #ddd', borderRadius: '8px' }}>
      <ReactFlow
        nodes={rfNodes} edges={rfEdges}
        onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onNodeMouseEnter={onNodeMouseEnter}
        onNodeMouseLeave={() => setTooltip(null)}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>

      {tooltip && (
        <div style={styles.tooltip}>
          <strong>{tooltip.name}</strong>
          <span style={{ color: '#888', marginLeft: 6 }}>{tooltip.type}</span>
          <span style={{ marginLeft: 8 }}>이해도: {tooltip.mastery}</span>
        </div>
      )}

      {/* 범례 */}
      <div style={styles.legend}>
        {[['미학습', '#b0b0b0'], ['취약 (<40%)', '#fc8181'], ['보통 (40~70%)', '#f6ad55'], ['숙달 (>70%)', '#68d391']].map(([label, color]) => (
          <span key={label} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
            <span style={{ width: 12, height: 12, borderRadius: '50%', background: color, display: 'inline-block' }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}

const styles = {
  tooltip: {
    position: 'absolute', top: 10, left: '50%', transform: 'translateX(-50%)',
    background: 'rgba(0,0,0,0.75)', color: '#fff', padding: '6px 12px',
    borderRadius: 6, fontSize: 13, pointerEvents: 'none', zIndex: 10,
    display: 'flex', gap: 6, alignItems: 'center',
  },
  legend: {
    position: 'absolute', bottom: 10, left: 10,
    background: 'rgba(255,255,255,0.9)', padding: '6px 10px',
    borderRadius: 6, display: 'flex', gap: 12, flexWrap: 'wrap',
    boxShadow: '0 1px 4px rgba(0,0,0,0.15)',
  },
}
