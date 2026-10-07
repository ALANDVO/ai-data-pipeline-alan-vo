import React, { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import JobStatus from '../components/JobStatus'

interface Job {
  id: string
  pipeline_id: string
  status: string
  triggered_by: string
  started_at: number | null
  completed_at: number | null
  duration_ms: number
  tasks: any[]
  error: string | null
}

export default function Jobs() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [status, setStatus] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const params = status ? `?status=${status}` : ''
      const data = await api.jobs(params)
      setJobs(data)
    } catch (e: any) { setError(e.message) }
    finally { setLoading(false) }
  }, [status])

  useEffect(() => { load() }, [load])

  const retry = async (id: string) => {
    try {
      await api.retryJob(id)
      load()
    } catch (e: any) { alert(e.message) }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Job History</h2>
          <p className="page-sub">Pipeline execution log with task-level detail</p>
        </div>
        <div className="header-actions">
          <select value={status} onChange={e => setStatus(e.target.value)}>
            <option value="">All Statuses</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="queued">Queued</option>
          </select>
          <button className="btn-secondary" onClick={load}>Refresh</button>
        </div>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {loading ? <div className="loading">Loading jobs…</div> : (
        <div className="job-list">
          {jobs.map(job => (
            <div key={job.id} className="job-row" onClick={() => setExpanded(expanded === job.id ? null : job.id)}>
              <div className="job-row-main">
                <span className="mono job-id">{job.id}</span>
                <JobStatus status={job.status} />
                <span className="job-meta">{job.triggered_by}</span>
                <span className="job-meta">{job.started_at ? new Date(job.started_at * 1000).toLocaleString() : '—'}</span>
                <span className="job-duration">{job.duration_ms > 0 ? (job.duration_ms / 1000).toFixed(1) + 's' : '—'}</span>
                <span className="job-tasks">{job.tasks?.length || 0} tasks</span>
                <span className={`expand-icon ${expanded === job.id ? 'expanded' : ''}`}>▸</span>
              </div>
              {expanded === job.id && (
                <div className="job-detail" onClick={e => e.stopPropagation()}>
                  {job.error && <div className="alert alert-error">Error: {job.error}</div>}
                  <h4>Tasks</h4>
                  <table className="data-table">
                    <thead><tr><th>Task</th><th>Status</th><th>Rows</th><th>Duration</th><th>Retries</th><th>Error</th></tr></thead>
                    <tbody>
                      {(job.tasks || []).map((t: any) => (
                        <tr key={t.task_id}>
                          <td className="mono">{t.task_id}</td>
                          <td><JobStatus status={t.status} /></td>
                          <td>{t.rows_processed?.toLocaleString?.() || t.rows_processed || 0}</td>
                          <td>{t.duration_ms > 0 ? (t.duration_ms / 1000).toFixed(2) + 's' : '—'}</td>
                          <td>{t.retries || 0}</td>
                          <td>{t.error || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <button className="btn-secondary btn-sm" onClick={() => retry(job.id)}>↻ Retry Job</button>
                </div>
              )}
            </div>
          ))}
          {jobs.length === 0 && <div className="empty-state">No jobs yet. Run a pipeline to see execution history.</div>}
        </div>
      )}
    </div>
  )
}
