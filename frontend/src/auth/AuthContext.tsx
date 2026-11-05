import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import { api } from '../api/client'

interface User { email: string; name: string; role: string }
interface AuthState {
  user: User | null
  loading: boolean
  login: () => Promise<void>
  logout: () => Promise<void>
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthState>({ user: null, loading: true, login: async () => {}, logout: async () => {}, isAuthenticated: false })

const KEYCLOAK_URL = import.meta.env.VITE_KEYCLOAK_URL || 'http://localhost:8080/realms/pipeline-realm'
const CLIENT_ID = import.meta.env.VITE_CLIENT_ID || 'pipeline-frontend'
const REDIRECT_URI = import.meta.env.VITE_REDIRECT_URI || `${window.location.origin}/callback`

// In-memory token storage (with optional localStorage persistence for page refreshes)
interface TokenData {
  accessToken: string
  idToken: string
  refreshToken: string
  expiresAt: number // Unix timestamp in ms
}

let _memoryToken: TokenData | null = null

export function getStoredToken(): TokenData | null {
  if (_memoryToken && _memoryToken.expiresAt > Date.now()) {
    return _memoryToken
  }
  // Fallback to localStorage for page refresh recovery
  const stored = localStorage.getItem('oidc_token_data')
  if (stored) {
    try {
      const parsed = JSON.parse(stored) as TokenData
      if (parsed.expiresAt > Date.now()) {
        _memoryToken = parsed
        return parsed
      }
    } catch {
      // Ignore parse errors
    }
  }
  return null
}

function setStoredToken(tokenData: TokenData | null) {
  _memoryToken = tokenData
  if (tokenData) {
    localStorage.setItem('oidc_token_data', JSON.stringify(tokenData))
  } else {
    localStorage.removeItem('oidc_token_data')
    localStorage.removeItem('token')
    localStorage.removeItem('id_token')
    localStorage.removeItem('refresh_token')
  }
}

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

async function refreshAccessToken(refreshToken: string): Promise<TokenData | null> {
  try {
    const res = await fetch(`${KEYCLOAK_URL}/protocol/openid-connect/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        client_id: CLIENT_ID,
        refresh_token: refreshToken,
      }),
    })

    if (!res.ok) {
      console.error('Token refresh failed:', res.statusText)
      return null
    }

    const tokenData = await res.json()
    const accessToken = tokenData.access_token
    const idToken = tokenData.id_token || ''
    const newRefreshToken = tokenData.refresh_token || refreshToken
    const expiresIn = tokenData.expires_in || 300 // Default 5 min if not provided

    const newTokenData: TokenData = {
      accessToken,
      idToken,
      refreshToken: newRefreshToken,
      expiresAt: Date.now() + expiresIn * 1000 - 60000, // Refresh 1 min before expiry
    }

    setStoredToken(newTokenData)
    return newTokenData
  } catch (err) {
    console.error('Token refresh error:', err)
    return null
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearRefreshTimer = useCallback(() => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current)
      refreshTimerRef.current = null
    }
  }, [])

  const scheduleTokenRefresh = useCallback((expiresAt: number) => {
    clearRefreshTimer()
    const delay = Math.max(0, expiresAt - Date.now())
    refreshTimerRef.current = setTimeout(async () => {
      const tokenData = getStoredToken()
      if (tokenData?.refreshToken) {
        const newTokenData = await refreshAccessToken(tokenData.refreshToken)
        if (newTokenData) {
          scheduleTokenRefresh(newTokenData.expiresAt)
        } else {
          // Refresh failed, logout
          await logout()
        }
      }
    }, delay)
  }, [clearRefreshTimer])

  const checkAuth = useCallback(async () => {
    const tokenData = getStoredToken()
    if (!tokenData) { setLoading(false); return }
    try {
      const me = await api.me()
      setUser(me)
      scheduleTokenRefresh(tokenData.expiresAt)
    } catch {
      setStoredToken(null)
    } finally {
      setLoading(false)
    }
  }, [scheduleTokenRefresh])

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
      const idToken = tokenData.id_token || ''
      const refreshToken = tokenData.refresh_token || ''
      const expiresIn = tokenData.expires_in || 300

      // Fetch user info
      const userinfoRes = await fetch(`${KEYCLOAK_URL}/protocol/openid-connect/userinfo`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      })
      const userinfo = await userinfoRes.json()

      const newTokenData: TokenData = {
        accessToken,
        idToken,
        refreshToken,
        expiresAt: Date.now() + expiresIn * 1000 - 60000,
      }

      setStoredToken(newTokenData)
      setUser({
        email: userinfo.email || 'unknown',
        name: userinfo.name || userinfo.preferred_username || 'User',
        role: 'data_engineer',
      })

      scheduleTokenRefresh(newTokenData.expiresAt)

      // Clean up
      sessionStorage.removeItem('pkce_verifier')
      window.history.replaceState({}, document.title, window.location.pathname)
    } catch (err) {
      console.error('Callback error:', err)
    } finally {
      setLoading(false)
    }
  }, [scheduleTokenRefresh])

  const login = useCallback(async () => {
    const codeVerifier = generateCodeVerifier()
    const codeChallenge = await generateCodeChallenge(codeVerifier)

    sessionStorage.setItem('pkce_verifier', codeVerifier)

    const authUrl = new URL(`${KEYCLOAK_URL}/protocol/openid-connect/auth`)
    authUrl.searchParams.set('client_id', CLIENT_ID)
    authUrl.searchParams.set('redirect_uri', REDIRECT_URI)
    authUrl.searchParams.set('response_type', 'code')
    authUrl.searchParams.set('scope', 'openid profile email offline_access')
    authUrl.searchParams.set('code_challenge', codeChallenge)
    authUrl.searchParams.set('code_challenge_method', 'S256')

    window.location.href = authUrl.toString()
  }, [])

  const logout = useCallback(async () => {
    clearRefreshTimer()
    const tokenData = getStoredToken()
    const idToken = tokenData?.idToken
    const postLogoutRedirect = `${window.location.origin}/`

    // Call backend to get logout URL
    try {
      const res = await fetch('/api/auth/logout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${tokenData?.accessToken || ''}`,
        },
        body: JSON.stringify({
          id_token_hint: idToken,
          post_logout_redirect_uri: postLogoutRedirect,
        }),
      })
      const data = await res.json()
      setStoredToken(null)
      setUser(null)
      window.location.href = data.logout_url
    } catch {
      setStoredToken(null)
      setUser(null)
      // Fallback to Keycloak logout
      window.location.href = `${KEYCLOAK_URL}/protocol/openid-connect/logout?post_logout_redirect_uri=${encodeURIComponent(postLogoutRedirect)}`
    }
  }, [clearRefreshTimer])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('code') || params.get('error')) {
      handleCallback()
    } else {
      checkAuth()
    }

    return () => clearRefreshTimer()
  }, [checkAuth, handleCallback, clearRefreshTimer])

  return <AuthContext.Provider value={{ user, loading, login, logout, isAuthenticated: !!user }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
