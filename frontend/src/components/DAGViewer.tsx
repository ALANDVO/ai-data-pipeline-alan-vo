import React from 'react'

export interface DAGNode {
  id: string
  name: string
  type?: string
  position: { x: number; y: number }
  [key: string]: any
}

export interface DAGEdge {
  id: string
  source: string
  target: string
}

interface Props {
  nodes: DAGNode[]
  edges: DAGEdge[]
  selectedNode?: string | null
  onNodeClick?: (id: string) => void
  onConnectStart?: (id: string) => void
  onConnectEnd?: (id: string) => void
  onEdgeClick?: (id: string) => void
}

const NODE_COLORS: Record<string, string> = {
  connector: '#3b82f6', transform: '#22c55e', llm: '#a855f7', quality: '#f59e0b',
}

const NODE_W = 140
const NODE_H = 50

export default function DAGViewer({ nodes, edges, selectedNode, onNodeClick, onConnectStart, onConnectEnd, onEdgeClick }: Props) {
  const maxX = Math.max(...nodes.map(n => n.position.x + NODE_W), 400)
  const maxY = Math.max(...nodes.map(n => n.position.y + NODE_H), 200)
  const width = Math.max(maxX + 40, 600)
  const height = Math.max(maxY + 40, 300)

  const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]))

  const renderEdge = (edge: DAGEdge) => {
    const src = nodeMap[edge.source]
    const tgt = nodeMap[edge.target]
    if (!src || !tgt) return null
    const x1 = src.position.x + NODE_W
    const y1 = src.position.y + NODE_H / 2
    const x2 = tgt.position.x
    const y2 = tgt.position.y + NODE_H / 2
    const midX = (x1 + x2) / 2
    const path = `M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`
    return (
      <g key={edge.id} className="dag-edge" onClick={() => onEdgeClick?.(edge.id)}>
        <path d={path} className="dag-edge-path" />
        <circle cx={x2} cy={y2} r={4} className="dag-edge-arrow" />
      </g>
    )
  }

  const renderNode = (node: DAGNode) => {
    const color = NODE_COLORS[node.type || ''] || '#64748b'
    const isSelected = selectedNode === node.id
    return (
      <g key={node.id} className={`dag-node ${isSelected ? 'selected' : ''}`}
        onClick={() => onNodeClick?.(node.id)} onDoubleClick={() => onConnectStart?.(node.id)}>
        <rect x={node.position.x} y={node.position.y} width={NODE_W} height={NODE_H}
          rx={8} className="dag-node-rect" style={{ stroke: color }} />
        <rect x={node.position.x} y={node.position.y} width={4} height={NODE_H} rx={2} fill={color} />
        <text x={node.position.x + 14} y={node.position.y + 22} className="dag-node-name">{node.name.slice(0, 16)}</text>
        <text x={node.position.x + 14} y={node.position.y + 38} className="dag-node-type">{node.type || 'node'}</text>
      </g>
    )
  }

  return (
    <div className="dag-container">
      <svg width={width} height={height} className="dag-svg">
        <defs>
          <pattern id="grid" width={20} height={20} patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#1e293b" strokeWidth={1} />
          </pattern>
        </defs>
        <rect width={width} height={height} fill="url(#grid)" />
        {edges.map(renderEdge)}
        {nodes.map(renderNode)}
      </svg>
    </div>
  )
}
