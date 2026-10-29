import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { api } from '../api/client'

interface User { email: string; name: string; role: string }
interface AuthState {
  user: User | null
  loading: boolean
  login: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState>({ user: null, loading: true, login: async () => {}, logout: async () => {} })

const KEYCLOAK_URL = import.meta.env.VITE_KEYCLOAK_URL || 'http://localhost:8080/realms/pipeline-realm'
const CLIENT_ID = import.meta.env.VITE_CLIENT_ID || 'pipeline-frontend'
const REDIRECT_URI = import.meta.env.VITE_REDIRECT_URI || `${window.location.origin}/callback`

function generateCodeVerifier(): string {
  const array = new Uint8Array(32)
  crypto.getRandomValues(array)
  return btoa(String.fromCharCode(...array))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
}

async function generateCodeChallenge(verifier: string): Promise<string> {
  const encoder = new TextEncoder()
  const data = encoder.encode(verifier)
  const digest = await crypto.subtle.digest('SHA-256', data)
  return btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const checkAuth = useCallback(async () => {
    const token = localStorage.getItem('token')
    if (!token) { setLoading(false); return }
    try {
      const me = await api.me()
      setUser(me)
    } catch {
      localStorage.removeItem('token')
    } finally {
      setLoading(false)
    }
  }, [])

  const handleCallback = useCallback(async () => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    const error = params.get('error')
    const errorDescription = params.get('error_description')

    if (error) {
      console.error('OIDC error:', error, errorDescription)
      window.history.replaceState({}, document.title, window.location.pathname)
      setLoading(false)
      return
    }

    if (!code) {
      setLoading(false)
      return
    }

    const codeVerifier = sessionStorage.getItem('pkce_verifier')
    if (!codeVerifier) {
      console.error('Missing PKCE code verifier')
      window.history.replaceState({}, document.title, window.location.pathname)
      setLoading(false)
      return
    }

    try {
      const res = await fetch(`${KEYCLOAK_URL}/protocol/openid-connect/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          grant_type: 'authorization_code',
          code,
          client_id: CLIENT_ID,
          redirect_uri: REDIRECT_URI,
          code_verifier: codeVerifier,
        }),
      })

      if (!res.ok) {
        throw new Error(`Token exchange failed: ${res.statusText}`)
      }

      const tokenData = await res.json()
      const accessToken = tokenData.access_token

      // Fetch user info
      const userinfoRes = await fetch(`${KEYCLOAK_URL}/protocol/openid-connect/userinfo`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      })
      const userinfo = await userinfoRes.json()

      // Store local session token (backend issues its own JWT after callback)
      // For now, we'll use the access token directly
      localStorage.setItem('token', accessToken)
      localStorage.setItem('id_token', tokenData.id_token || '')
      localStorage.setItem('refresh_token', tokenData.refresh_token || '')

      setUser({
        email: userinfo.email || 'unknown',
        name: userinfo.name || userinfo.preferred_username || 'User',
        role: 'data_engineer',
      })

      // Clean up
      sessionStorage.removeItem('pkce_verifier')
      window.history.replaceState({}, document.title, window.location.pathname)
    } catch (err) {
      console.error('Callback error:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  const login = useCallback(async () => {
    const codeVerifier = generateCodeVerifier()
    const codeChallenge = await generateCodeChallenge(codeVerifier)

    sessionStorage.setItem('pkce_verifier', codeVerifier)

    const authUrl = new URL(`${KEYCLOAK_URL}/protocol/openid-connect/auth`)
    authUrl.searchParams.set('client_id', CLIENT_ID)
    authUrl.searchParams.set('redirect_uri', REDIRECT_URI)
    authUrl.searchParams.set('response_type', 'code')
    authUrl.searchParams.set('scope', 'openid profile email')
    authUrl.searchParams.set('code_challenge', codeChallenge)
    authUrl.searchParams.set('code_challenge_method', 'S256')

    window.location.href = authUrl.toString()
  }, [])

  const logout = useCallback(async () => {
    const idToken = localStorage.getItem('id_token')
    const postLogoutRedirect = `${window.location.origin}/`

    // Call backend to get logout URL
    try {
      const res = await fetch('/api/auth/logout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: JSON.stringify({
          id_token_hint: idToken,
          post_logout_redirect_uri: postLogoutRedirect,
        }),
      })
      const data = await res.json()
      localStorage.removeItem('token')
      localStorage.removeItem('id_token')
      localStorage.removeItem('refresh_token')
      setUser(null)
      window.location.href = data.logout_url
    } catch {
      localStorage.removeItem('token')
      localStorage.removeItem('id_token')
      localStorage.removeItem('refresh_token')
      setUser(null)
      // Fallback to Keycloak logout
      window.location.href = `${KEYCLOAK_URL}/protocol/openid-connect/logout?post_logout_redirect_uri=${encodeURIComponent(postLogoutRedirect)}`
    }
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('code') || params.get('error')) {
      handleCallback()
    } else {
      checkAuth()
    }
  }, [checkAuth, handleCallback])

  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
