// src/contexts/AuthContext.tsx
import React, { createContext, useContext, useEffect, useState } from 'react'
import api from '../api'
import toast from 'react-hot-toast'

type User = { id: number; username: string; email?: string; role?: string } | null

type AuthContextValue = {
  user: User
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string | undefined, password: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const tryLoad = async () => {
      const token = localStorage.getItem('token')
      if (token) {
        try { await refreshUser() } catch (e) { localStorage.removeItem('token'); setUser(null) }
      }
      setLoading(false)
    }
    tryLoad()
  }, [])

  const refreshUser = async () => {
    const res = await api.get('/auth/me')
    setUser(res.data)
    return res.data
  }

  const login = async (username: string, password: string) => {
    try {
      const body = new URLSearchParams()
      body.append('username', username)
      body.append('password', password)

      const res = await api.post('/auth/login', body.toString(), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })

      const token = res.data?.access_token || res.data?.token
      if (!token) throw new Error('No token received')

      localStorage.setItem('token', token)
      await refreshUser()
      toast.success('Logged in')
    } catch (err: any) {
      if (err.response?.status === 401) {
        toast.error('Invalid username or password')
      } else {
        toast.error(err.response?.data?.detail || 'Login failed')
      }
      throw err // rethrow if caller needs it
    }
  }


  const register = async (username: string, email: string | undefined, password: string) => {
    // backend sets role = student by default in your code
    await api.post('/auth/register', { username, email, password })
    toast.success('Registered. Please Login')
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
    toast.success('Logged out')
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
