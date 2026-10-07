import React, { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

interface Pipeline {
  id: string
  name: string
  description: string
  status: string
  nodes: any[]
  edges: any[]
  created_at: number
  created_by: string
  last_run_at: number | null
  last_status: string | null
}

export default function Pipelines() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [running, setRunning] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const params = status ? `?status=${status}` : ''
      const data = await api.pipelines(params)
      setPipelines(data)
    } catch (e: any) { setError(e.message) }
    finally { setLoading(false) }
  }, [status])

  useEffect(() => { load() }, [load])

  const runPipeline = async (id: string) => {
    setRunning(id)
    try {
      await api.runPipeline(id)
    } catch (e: any) { alert(e.message) }
    finally { setRunning('') }
  }

  const statusBadge = (s: string | null) => {
    if (!s) return <span className="badge badge-neutral">never run</span>
    const cls = s === 'completed' ? 'badge-success' : s === 'running' ? 'badge-running' : s === 'failed' ? 'badge-error' : 'badge-neutral'
    return <span className={`badge ${cls}`}>{s}</span>
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Data Pipelines</h2>
          <p className="page-sub">{pipelines.length} pipelines · visual DAG orchestration</p>
        </div>
        <div className="header-actions">
          <select value={status} onChange={e => setStatus(e.target.value)}>
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="paused">Paused</option>
            <option value="failed">Failed</option>
          </select>
          <Link to="/pipelines/build" className="btn-primary">+ New Pipeline</Link>
        </div>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {loading ? <div className="loading">Loading pipelines…</div> : (
        <div className="pipeline-grid">
          {pipelines.map(p => (
            <div key={p.id} className="pipeline-card">
              <div className="pipeline-card-head">
                <h3>{p.name}</h3>
                <span className={`badge badge-${p.status === 'active' ? 'success' : p.status === 'paused' ? 'warning' : 'neutral'}`}>{p.status}</span>
              </div>
              <p className="pipeline-desc">{p.description}</p>
              <div className="pipeline-meta">
                <div><span className="meta-label">Nodes</span><span className="meta-value">{p.nodes?.length || 0}</span></div>
                <div><span className="meta-label">Edges</span><span className="meta-value">{p.edges?.length || 0}</span></div>
                <div><span className="meta-label">Last Run</span>{statusBadge(p.last_status)}</div>
              </div>
              <div className="pipeline-card-actions">
                <Link to={`/pipelines/${p.id}`} className="btn-secondary btn-sm">View</Link>
                <button className="btn-primary btn-sm" disabled={running === p.id} onClick={() => runPipeline(p.id)}>
                  {running === p.id ? 'Running…' : '▶ Run'}
                </button>
              </div>
            </div>
          ))}
          {pipelines.length === 0 && <div className="empty-state">No pipelines found. Create your first pipeline.</div>}
        </div>
      )}
    </div>
  )
}
