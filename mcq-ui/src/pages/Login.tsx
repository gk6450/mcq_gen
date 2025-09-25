import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Card } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Eye, EyeOff } from 'lucide-react'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const { login } = useAuth()
  const nav = useNavigate()
  const [loading, setLoading] = useState(false)

  const handle = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await login(username, password)
      nav('/')
    } catch (err: any) {
      // login errors handled in context or toast
    } finally { setLoading(false) }
  }

  return (
    <div className="flex justify-center px-4 py-8 bg-gradient-to-br from-[#F8FAFF] via-[#EFF8FF] to-[#F7FBFF]">
      <Card className="w-full max-w-md p-8 rounded-2xl shadow-xl border border-border bg-card/95 backdrop-blur-sm animate-fade-in">
        {/* header */}
        <div className="flex flex-col items-center mb-3">
          <div className="w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold bg-primary/10 text-primary mb-3">
            S
          </div>
          <h2 className="text-2xl font-semibold">Sign in</h2>
        </div>

        <form onSubmit={handle} className="space-y-5">
          <div>
            <label htmlFor="username" className="text-sm font-medium">Username</label>
            <input
              id="username"
              name="username"
              autoComplete="username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              placeholder="username"
              className="w-full mt-2 p-3 rounded-md border border-border bg-input text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary transition"
            />
          </div>

          <div>
            <label htmlFor="password" className="text-sm font-medium">Password</label>
            <div className="relative mt-2">
              <input
                id="password"
                name="password"
                autoComplete="current-password"
                type={show ? "text" : "password"}
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                placeholder="••••••••"
                className="w-full p-3 pr-12 rounded-md border border-border bg-input text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary transition"
              />
              <button
                type="button"
                onClick={() => setShow(s => !s)}
                aria-pressed={show}
                aria-label={show ? 'Hide password' : 'Show password'}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-600 hover:text-foreground"
              >
                {show ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between text-sm">
            <a
              href="#"
              onClick={(e) => { e.preventDefault(); /* handle forgot password or nav */ }}
              className="text-muted-foreground hover:text-foreground"
            >
              Forgot password?
            </a>

            <div className="flex items-center gap-3">
              <Button type="submit" disabled={loading} className="px-6 py-2">
                {loading ? 'Signing in...' : 'Sign in'}
              </Button>

              <Button variant="ghost" asChild className="px-3 py-2">
                <a href="#" onClick={(e) => { e.preventDefault(); nav('/register') }}>Register</a>
              </Button>
            </div>
          </div>
        </form>

        {/* footer */}
        <div className="mt-6 text-center text-xs text-muted-foreground">
          By signing in you agree to our <a className="underline" href="#">Terms</a> & <a className="underline" href="#">Privacy</a>.
        </div>
      </Card>
    </div>
  )
}
