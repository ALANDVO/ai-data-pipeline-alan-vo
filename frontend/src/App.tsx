import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import Login from './pages/Login'
import Pipelines from './pages/Pipelines'
import PipelineBuilder from './pages/PipelineBuilder'
import Jobs from './pages/Jobs'
import Quality from './pages/Quality'
import Logs from './pages/Logs'
import Header from './components/Header'

export default function App() {
  const { user, loading } = useAuth()

  if (loading) {
    return <div className="app-loading">Loading…</div>
  }

  if (!user) {
    return <Login />
  }

  return (
    <div className="app-shell">
      <Header />
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Navigate to="/pipelines" replace />} />
          <Route path="/pipelines" element={<Pipelines />} />
          <Route path="/pipelines/build" element={<PipelineBuilder />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/quality" element={<Quality />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="*" element={<Navigate to="/pipelines" replace />} />
        </Routes>
      </main>
    </div>
  )
}
