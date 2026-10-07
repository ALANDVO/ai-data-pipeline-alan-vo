import React, { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'

interface Log {
  id: string
  job_id: string | null
  pipeline_id: string | null
  level: string
  message: string
  timestamp: number
  source: string
}

const LEVEL_COLORS: Record<string, string> = {
  debug: '#64748b', info: '#3b82f6', warning: '#f59e0b', error: '#ef4444',
}

export default function Logs() {
  const [logs, setLogs] = useState<Log[]>([])
  const [level, setLevel] = useState('')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const params = new URLSearchParams()
      if (level) params.set('level', level)
      const data = await api.logs(params.toString())
      setLogs(data)
    } catch (e: any) { setError(e.message) }
    finally { setLoading(false) }
  }, [level])

  useEffect(() => { load() }, [load])

  const filtered = logs.filter(l => {
    if (search && !l.message.toLowerCase().includes(search.toLowerCase()) && !l.source.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Pipeline Logs</h2>
          <p className="page-sub">Real-time execution log across all pipelines</p>
        </div>
        <div className="header-actions">
          <input placeholder="Search logs…" value={search} onChange={e => setSearch(e.target.value)} className="log-search" />
          <select value={level} onChange={e => setLevel(e.target.value)}>
            <option value="">All Levels</option>
            <option value="debug">Debug</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="error">Error</option>
          </select>
          <button className="btn-secondary" onClick={load}>Refresh</button>
        </div>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {loading ? <div className="loading">Loading logs…</div> : (
        <div className="log-viewer">
          {filtered.map(log => (
            <div key={log.id} className="log-line">
              <span className="log-time">{new Date(log.timestamp * 1000).toLocaleTimeString()}</span>
              <span className="log-level" style={{ color: LEVEL_COLORS[log.level] || '#94a3b8' }}>{log.level.toUpperCase().padEnd(7)}</span>
              <span className="log-source">{log.source}</span>
              <span className="log-msg">{log.message}</span>
            </div>
          ))}
          {filtered.length === 0 && <div className="empty-state">No log entries match your filter.</div>}
        </div>
      )}
    </div>
  )
}
