import React from 'react'

interface Props {
  status: string
  size?: 'sm' | 'md'
}

const STATUS_CONFIG: Record<string, { label: string; cls: string; icon: string }> = {
  queued: { label: 'Queued', cls: 'status-queued', icon: '⏳' },
  running: { label: 'Running', cls: 'status-running', icon: '⚡' },
  completed: { label: 'Completed', cls: 'status-completed', icon: '✓' },
  failed: { label: 'Failed', cls: 'status-failed', icon: '✗' },
  pending: { label: 'Pending', cls: 'status-queued', icon: '⏸' },
}

export default function JobStatus({ status, size = 'md' }: Props) {
  const cfg = STATUS_CONFIG[status] || { label: status, cls: 'status-unknown', icon: '?' }
  return (
    <span className={`job-status ${cfg.cls} ${size === 'sm' ? 'status-sm' : ''}`}>
      <span className="status-icon">{cfg.icon}</span>
      {cfg.label}
    </span>
  )
}
