import React, { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import DAGViewer, { DAGNode, DAGEdge } from '../components/DAGViewer'

interface BuilderNode extends DAGNode {
  type: string
  config: Record<string, any>
}

let nodeCounter = 1
const genId = () => `node-${nodeCounter++}`

const NODE_TYPES: Record<string, { label: string; color: string; icon: string }> = {
  connector: { label: 'Connector', color: '#3b82f6', icon: '🔌' },
  transform: { label: 'Transform', color: '#22c55e', icon: '🔄' },
  llm: { label: 'LLM Enrich', color: '#a855f7', icon: '🤖' },
  quality: { label: 'Quality Check', color: '#f59e0b', icon: '✅' },
}

export default function PipelineBuilder() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [nodes, setNodes] = useState<BuilderNode[]>([])
  const [edges, setEdges] = useState<DAGEdge[]>([])
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [sourceNode, setSourceNode] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [validation, setValidation] = useState<any>(null)

  const addNode = (type: string) => {
    const id = genId()
    const node: BuilderNode = {
      id, type, name: `${type}-${id}`,
      config: type === 'connector' ? { source: 'postgres' } : {},
      position: { x: 80 + (nodes.length % 3) * 200, y: 60 + Math.floor(nodes.length / 3) * 120 },
    }
    setNodes([...nodes, node])
    setSelectedNode(id)
  }

  const removeNode = (id: string) => {
    setNodes(nodes.filter(n => n.id !== id))
    setEdges(edges.filter(e => e.source !== id && e.target !== id))
    if (selectedNode === id) setSelectedNode(null)
  }

  const connectNode = (targetId: string) => {
    if (!sourceNode || sourceNode === targetId) return
    const exists = edges.some(e => e.source === sourceNode && e.target === targetId)
    if (!exists) {
      setEdges([...edges, { id: `edge-${edges.length + 1}`, source: sourceNode, target: targetId }])
    }
    setSourceNode(null)
  }

  const removeEdge = (id: string) => setEdges(edges.filter(e => e.id !== id))

  const updateConfig = (key: string, value: any) => {
    if (!selectedNode) return
    setNodes(nodes.map(n => n.id === selectedNode ? { ...n, config: { ...n.config, [key]: value } } : n))
  }

  const save = async () => {
    if (!name) { alert('Pipeline name required'); return }
    if (nodes.length === 0) { alert('Add at least one node'); return }
    setSaving(true)
    try {
      const data = {
        name, description,
        nodes: nodes.map(n => ({ id: n.id, type: n.type, name: n.name, config: n.config, position: n.position })),
        edges,
      }
      const created = await api.createPipeline(data)
      const val = await api.validatePipeline(created.id)
      setValidation(val)
      if (!val.valid) {
        alert(`DAG issues: ${val.errors.join(', ')}`)
        return
      }
      navigate('/pipelines')
    } catch (e: any) {
      alert(e.message)
    } finally { setSaving(false) }
  }

  const selected = nodes.find(n => n.id === selectedNode)

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Pipeline Builder</h2>
          <p className="page-sub">Drag nodes, connect with edges, configure transforms</p>
        </div>
        <div className="header-actions">
          <button className="btn-secondary" onClick={() => setValidation(null)}>Reset</button>
          <button className="btn-primary" disabled={saving} onClick={save}>{saving ? 'Saving…' : 'Save Pipeline'}</button>
        </div>
      </div>

      <div className="builder-layout">
        <div className="builder-sidebar">
          <h4>Node Palette</h4>
          {Object.entries(NODE_TYPES).map(([type, meta]) => (
            <button key={type} className={`palette-btn palette-${type}`} onClick={() => addNode(type)}>
              <span className="palette-icon">{meta.icon}</span>
              <span>{meta.label}</span>
            </button>
          ))}
          {validation && (
            <div className="validation-box">
              <h4>DAG Validation</h4>
              {validation.valid ? (
                <div className="valid-msg">✓ Valid DAG</div>
              ) : (
                <ul>{validation.errors.map((e: string, i: number) => <li key={i}>{e}</li>)}</ul>
              )}
            </div>
          )}
        </div>

        <div className="builder-canvas">
          <div className="canvas-toolbar">
            <input placeholder="Pipeline name" value={name} onChange={e => setName(e.target.value)} />
            <input placeholder="Description (optional)" value={description} onChange={e => setDescription(e.target.value)} />
          </div>
          <DAGViewer nodes={nodes} edges={edges} selectedNode={selectedNode}
            onNodeClick={setSelectedNode} onConnectStart={setSourceNode} onConnectEnd={connectNode}
            onEdgeClick={removeEdge} />
          <div className="canvas-hint">
            {sourceNode ? 'Click a target node to connect' : 'Click a node to select · use "Connect" mode to link nodes'}
          </div>
        </div>

        <div className="builder-config">
          {selected ? (
            <>
              <h4>Node Config</h4>
              <div className="config-field">
                <label>Name</label>
                <input value={selected.name} onChange={e => setNodes(nodes.map(n => n.id === selected.id ? { ...n, name: e.target.value } : n))} />
              </div>
              <div className="config-field">
                <label>Type</label>
                <span className={`badge badge-${selected.type === 'connector' ? 'info' : selected.type === 'llm' ? 'purple' : 'success'}`}>{NODE_TYPES[selected.type]?.label || selected.type}</span>
              </div>
              {selected.type === 'connector' && (
                <>
                  <div className="config-field">
                    <label>Source</label>
                    <select value={selected.config.source || ''} onChange={e => updateConfig('source', e.target.value)}>
                      <option value="postgres">PostgreSQL</option>
                      <option value="s3">S3</option>
                      <option value="gcs">GCS</option>
                      <option value="bigquery">BigQuery</option>
                    </select>
                  </div>
                  <div className="config-field">
                    <label>Table / Path</label>
                    <input value={selected.config.table || selected.config.path || ''} onChange={e => updateConfig('table', e.target.value)} placeholder="orders" />
                  </div>
                </>
              )}
              {selected.type === 'transform' && (
                <>
                  <div className="config-field">
                    <label>Null Handling</label>
                    <select value={selected.config.nulls || ''} onChange={e => updateConfig('nulls', e.target.value)}>
                      <option value="">None</option>
                      <option value="fill">Fill</option>
                      <option value="drop">Drop</option>
                    </select>
                  </div>
                  <div className="config-field">
                    <label>Deduplicate</label>
                    <label className="checkbox"><input type="checkbox" checked={!!selected.config.dedup} onChange={e => updateConfig('dedup', e.target.checked)} /> Enabled</label>
                  </div>
                </>
              )}
              {selected.type === 'llm' && (
                <div className="config-field">
                  <label>LLM Task</label>
                  <select value={selected.config.task || 'categorize'} onChange={e => updateConfig('task', e.target.value)}>
                    <option value="categorize">Categorization</option>
                    <option value="extract">Entity Extraction</option>
                    <option value="summarize">Summarization</option>
                  </select>
                </div>
              )}
              <button className="btn-danger btn-sm" onClick={() => removeNode(selected.id)}>Remove Node</button>
            </>
          ) : (
            <div className="empty-config">
              <p>Select a node to configure</p>
              <p className="hint">Add nodes from the palette, then click to select.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
