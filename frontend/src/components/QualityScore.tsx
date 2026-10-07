import React from 'react'

interface Props {
  value: number
  size?: number
  label?: string
}

function colorFor(value: number): string {
  if (value >= 0.9) return '#22c55e'
  if (value >= 0.7) return '#eab308'
  if (value >= 0.5) return '#f97316'
  return '#ef4444'
}

export default function QualityScore({ value, size = 48, label }: Props) {
  const pct = Math.max(0, Math.min(1, value))
  const radius = size / 2 - 4
  const circumference = 2 * Math.PI * radius
  const dash = circumference * (1 - pct)
  const color = colorFor(pct)
  return (
    <div className="quality-gauge" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="gauge-svg">
        <circle cx={size / 2} cy={size / 2} r={radius} className="gauge-track" />
        <circle cx={size / 2} cy={size / 2} r={radius} className="gauge-fill"
          style={{ stroke: color, strokeDasharray: `${circumference - dash} ${dash}`, transform: `rotate(-90deg)`, transformOrigin: 'center' }} />
      </svg>
      <div className="gauge-label" style={{ fontSize: size * 0.26 }}>{Math.round(pct * 100)}</div>
      {label && <div className="gauge-sub">{label}</div>}
    </div>
  )
}
