import React from 'react'
import { useAuth } from '../auth/AuthContext'

export default function Login() {
  const { login } = useAuth()
  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">📊</div>
        <h1>AI Data Pipeline Orchestrator</h1>
        <p className="login-sub">Enterprise Data Pipelines · Visual DAG · LLM-Powered Quality</p>
        <button className="btn-primary" onClick={login}>Sign in with SSO</button>
        <p className="login-footer">Multi-Cloud · S3 · GCS · BigQuery · Postgres</p>
      </div>
    </div>
  )
}
