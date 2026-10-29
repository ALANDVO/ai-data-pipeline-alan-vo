import React from 'react'

export default function Callback() {
  return (
    <div className="callback-page">
      <div className="callback-card">
        <div className="callback-spinner"></div>
        <h2>Completing Sign In...</h2>
        <p>Please wait while we authenticate you with Keycloak.</p>
      </div>
    </div>
  )
}
