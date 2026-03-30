import { createContext, useContext, useEffect, useMemo, useState } from 'react'

const AUTH_STORAGE_KEY = 'nyaysaathi_auth_v1'
const DEMO_USERNAME = 'admin'
const DEMO_PASSWORD = '1234'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isInitializing, setIsInitializing] = useState(true)

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(AUTH_STORAGE_KEY)
      setIsAuthenticated(stored === '1')
    } catch {
      setIsAuthenticated(false)
    } finally {
      setIsInitializing(false)
    }
  }, [])

  const login = (username, password) => {
    const ok = username === DEMO_USERNAME && password === DEMO_PASSWORD
    if (!ok) {
      return { ok: false, message: 'Invalid credentials. Use admin / 1234.' }
    }

    setIsAuthenticated(true)
    try {
      window.localStorage.setItem(AUTH_STORAGE_KEY, '1')
    } catch {
      // Ignore storage failures and keep in-memory auth state.
    }

    return { ok: true }
  }

  const logout = () => {
    setIsAuthenticated(false)
    try {
      window.localStorage.removeItem(AUTH_STORAGE_KEY)
    } catch {
      // Ignore storage failures.
    }
  }

  const value = useMemo(
    () => ({ isAuthenticated, isInitializing, login, logout }),
    [isAuthenticated, isInitializing]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used inside AuthProvider')
  }
  return ctx
}
