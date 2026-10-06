import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

const DEFAULT_API_HOST = typeof window === 'undefined' ? 'localhost' : window.location.hostname
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || `http://${DEFAULT_API_HOST}:8000/api/v1`
const AuthContext = createContext(null)
let sessionBootstrapPromise

async function parseResponse(response) {
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const message = typeof data.detail === 'string' ? data.detail : 'Request failed. Please try again.'
    throw new Error(message)
  }
  return data
}

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(null)
  const [user, setUser] = useState(null)
  const [permissions, setPermissions] = useState([])
  const [authLoading, setAuthLoading] = useState(true)

  const fetchPermissions = useCallback(async (token) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/permissions`, {
        headers: { Authorization: `Bearer ${token}` },
        credentials: 'include',
      })
      const data = await parseResponse(response)
      setPermissions(data.permissions || [])
    } catch {
      setPermissions([])
    }
  }, [])

  const refreshSession = useCallback(async () => {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    })
    const data = await parseResponse(response)
    setAccessToken(data.access_token)
    setUser(data.user)
    if (data.access_token) {
      await fetchPermissions(data.access_token)
    }
    return data
  }, [fetchPermissions])

  useEffect(() => {
    let active = true
    if (!sessionBootstrapPromise) {
      sessionBootstrapPromise = fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      }).then(parseResponse).catch(() => null)
    }
    sessionBootstrapPromise
      .then(async (data) => {
        if (!active || !data) return
        setAccessToken(data.access_token)
        setUser(data.user)
        if (data.access_token) {
          await fetchPermissions(data.access_token)
        }
      })
      .finally(() => {
        if (active) setAuthLoading(false)
      })
    return () => { active = false }
  }, [fetchPermissions])

  const authenticate = useCallback(async (path, credentials) => {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    })
    const data = await parseResponse(response)
    setAccessToken(data.access_token)
    setUser(data.user)
    if (data.access_token) {
      await fetchPermissions(data.access_token)
    }
    return data.user
  }, [fetchPermissions])

  const login = useCallback((credentials) => authenticate('/auth/login', credentials), [authenticate])
  const register = useCallback((credentials) => authenticate('/auth/register', credentials), [authenticate])

  const logout = useCallback(async () => {
    try {
      await fetch(`${API_BASE_URL}/auth/logout`, { method: 'POST', credentials: 'include' })
    } catch {
      // Clear the in-memory session even if the server cannot be reached.
    } finally {
      setAccessToken(null)
      setUser(null)
      setPermissions([])
    }
  }, [])

  const request = useCallback(async (path, options = {}) => {
    const send = (token) => fetch(`${API_BASE_URL}${path}`, {
      ...options,
      credentials: 'include',
      headers: {
        ...(options.body && !(options.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
        ...options.headers,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })

    let response = await send(accessToken)
    if (response.status === 401 && accessToken) {
      try {
        const refreshed = await refreshSession()
        response = await send(refreshed.access_token)
      } catch {
        setAccessToken(null)
        setUser(null)
        setPermissions([])
        throw new Error('Your session has expired. Please sign in again.')
      }
    }
    return parseResponse(response)
  }, [accessToken, refreshSession])

  const hasPermission = useCallback((permission) => {
    return permissions.includes(permission)
  }, [permissions])

  const value = useMemo(
    () => ({
      accessToken,
      token: accessToken,
      user,
      permissions,
      hasPermission,
      authLoading,
      login,
      register,
      logout,
      request,
    }),
    [accessToken, user, permissions, hasPermission, authLoading, login, register, logout, request]
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}


export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within an AuthProvider')
  return context
}
