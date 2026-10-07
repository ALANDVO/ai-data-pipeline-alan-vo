import React from 'react'
import { Link, NavLink } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const NAV_ITEMS = [
  { to: '/pipelines', label: 'Pipelines', icon: '🔀' },
  { to: '/pipelines/build', label: 'Builder', icon: '🏗️' },
  { to: '/jobs', label: 'Jobs', icon: '⚙️' },
  { to: '/quality', label: 'Quality', icon: '✅' },
  { to: '/logs', label: 'Logs', icon: '📋' },
]

export default function Header() {
  const { user, logout } = useAuth()
  return (
    <header className="app-header">
      <div className="header-brand">
        <span className="brand-icon">📊</span>
        <div className="brand-text">
          <h1>AI Data Pipeline</h1>
          <span className="brand-sub">Orchestrator</span>
        </div>
      </div>
      <nav className="header-nav">
        {NAV_ITEMS.map(item => (
          <NavLink key={item.to} to={item.to} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <span className="nav-icon">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="header-user">
        <div className="user-info">
          <span className="user-avatar">{user?.name?.[0]?.toUpperCase() || 'U'}</span>
          <div className="user-detail">
            <span className="user-name">{user?.name}</span>
            <span className="user-role">{user?.role}</span>
          </div>
        </div>
        <button className="btn-logout" onClick={logout}>Sign out</button>
      </div>
    </header>
  )
}
