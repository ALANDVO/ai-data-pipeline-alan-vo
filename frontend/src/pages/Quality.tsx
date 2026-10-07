import React, { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import QualityScore from '../components/QualityScore'

interface Score {
  pipeline_id: string
  dataset: string
  completeness: number
  accuracy: number
  consistency: number
  timeliness: number
  overall: number
  issues: string[]
  scored_at: number
}

export default function Quality() {
  const [scores, setScores] = useState<Score[]>([])
  const [selected, setSelected] = useState<Score | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const data = await api.quality()
      setScores(data)
      if (data.length > 0 && !selected) setSelected(data[0])
    } catch (e: any) { setError(e.message) }
    finally { setLoading(false) }
  }, [selected])

  useEffect(() => { load() }, [])

  const avgOverall = scores.length ? scores.reduce((a, s) => a + s.overall, 0) / scores.length : 0

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Data Quality</h2>
          <p className="page-sub">LLM-assessed completeness, accuracy, consistency &amp; timeliness</p>
        </div>
        <button className="btn-secondary" onClick={load}>Refresh</button>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {loading ? <div className="loading">Loading quality scores…</div> : (
        <>
          <div className="quality-summary">
            <div className="stat-card"><span className="stat-label">Datasets Scored</span><span className="stat-value">{scores.length}</span></div>
            <div className="stat-card"><span className="stat-label">Average Overall</span><span className="stat-value">{(avgOverall * 100).toFixed(1)}%</span></div>
            <div className="stat-card"><span className="stat-label">Critical Issues</span><span className="stat-value">{scores.reduce((a, s) => a + s.issues.length, 0)}</span></div>
          </div>
          <div className="quality-layout">
            <div className="quality-list">
              {scores.map(s => (
                <div key={s.scored_at + s.pipeline_id + s.dataset}
                  className={`quality-item ${selected && selected.scored_at === s.scored_at && selected.pipeline_id === s.pipeline_id ? 'active' : ''}`}
                  onClick={() => setSelected(s)}>
                  <div className="quality-item-head">
                    <span className="mono">{s.pipeline_id}</span>
                    <span className="quality-dataset">{s.dataset}</span>
                  </div>
                  <div className="quality-item-score">
                    <QualityScore value={s.overall} size={40} />
                  </div>
                  <div className="quality-item-issues">{s.issues.length} issues</div>
                </div>
              ))}
              {scores.length === 0 && <div className="empty-state">No quality scores yet.</div>}
            </div>
            {selected && (
              <div className="quality-detail">
                <h3>{selected.dataset} — {selected.pipeline_id}</h3>
                <p className="quality-scored">{new Date(selected.scored_at * 1000).toLocaleString()}</p>
                <div className="quality-metrics">
                  <div className="metric-row"><span className="metric-label">Completeness</span><QualityScore value={selected.completeness} size={32} /><span className="metric-val">{(selected.completeness * 100).toFixed(1)}%</span></div>
                  <div className="metric-row"><span className="metric-label">Accuracy</span><QualityScore value={selected.accuracy} size={32} /><span className="metric-val">{(selected.accuracy * 100).toFixed(1)}%</span></div>
                  <div className="metric-row"><span className="metric-label">Consistency</span><QualityScore value={selected.consistency} size={32} /><span className="metric-val">{(selected.consistency * 100).toFixed(1)}%</span></div>
                  <div className="metric-row"><span className="metric-label">Timeliness</span><QualityScore value={selected.timeliness} size={32} /><span className="metric-val">{(selected.timeliness * 100).toFixed(1)}%</span></div>
                  <div className="metric-row overall"><span className="metric-label">Overall</span><QualityScore value={selected.overall} size={48} /><span className="metric-val">{(selected.overall * 100).toFixed(1)}%</span></div>
                </div>
                {selected.issues.length > 0 && (
                  <div className="quality-issues">
                    <h4>Detected Issues</h4>
                    <ul>{selected.issues.map((issue, i) => <li key={i}>{issue}</li>)}</ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
