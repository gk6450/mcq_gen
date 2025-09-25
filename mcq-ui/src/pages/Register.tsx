import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Card } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Eye, EyeOff } from 'lucide-react'

export default function Register() {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const { register } = useAuth()
  const nav = useNavigate()
  const [loading, setLoading] = useState(false)

  const handle = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await register(username, email || undefined, password)
      nav('/login')
    } catch (err) {
      // errors handled by context/toast
    } finally { setLoading(false) }
  }

  return (
    <div className="flex justify-center px-4 bg-gradient-to-br from-[#F8FAFF] via-[#EFF8FF] to-[#F7FBFF]">
      <Card className="w-full max-w-md p-8 rounded-2xl shadow-xl border border-border bg-card/95 backdrop-blur-sm animate-fade-in">
        <div className="flex flex-col items-center mb-3">
          <div className="w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold bg-secondary/10 text-secondary mb-3">
            +
          </div>
          <h2 className="text-2xl font-semibold">Create account (students)</h2>
        </div>

        <form onSubmit={handle} className="space-y-5">
          <div>
            <label htmlFor="reg-username" className="text-sm font-medium">Username</label>
            <input
              id="reg-username"
              name="username"
              autoComplete="username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              placeholder="choose a username"
              className="w-full mt-2 p-3 rounded-md border border-border bg-input text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary transition"
            />
          </div>

          <div>
            <label htmlFor="reg-email" className="text-sm font-medium">Email (optional)</label>
            <input
              id="reg-email"
              name="email"
              autoComplete="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full mt-2 p-3 rounded-md border border-border bg-input text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary transition"
            />
          </div>

          <div>
            <label htmlFor="reg-password" className="text-sm font-medium">Password</label>
            <div className="relative mt-2">
              <input
                id="reg-password"
                name="password"
                autoComplete="new-password"
                type={show ? "text" : "password"}
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                placeholder="At least 8 characters"
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

          <div className="flex items-center justify-between">
            <Button type="submit" disabled={loading} className="px-6 py-2">
              {loading ? 'Creating...' : 'Create account'}
            </Button>

            <Button variant="ghost" onClick={() => nav('/login')} className="px-3 py-2">Back</Button>
          </div>
        </form>

        <div className="mt-6 text-center text-xs text-muted-foreground">
          Already have an account? <button onClick={() => nav('/login')} className="underline">Sign in</button>
        </div>
      </Card>
    </div>
  )
}
