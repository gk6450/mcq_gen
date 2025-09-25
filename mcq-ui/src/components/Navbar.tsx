// src/components/Navbar.tsx
import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Button } from './ui/button'
import { Home, FileText, List, Activity, LogOut, ClipboardList } from 'lucide-react'
import Avatar from './Avatar'

export default function Navbar() {
  const { user, logout } = useAuth()
  const nav = useNavigate()

  return (
    <header className="bg-white border-b">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center text-white font-bold">AI</div>
          <div>
            <div className="text-lg font-semibold text-slate-900">MCQ Generator</div>
            <div className="text-xs text-slate-500">Practice & Assess</div>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-4">
          <Link to="/" className="flex items-center gap-2 text-sm px-3 py-2 rounded-md hover:bg-slate-50"><Home size={16}/> Home</Link>
          <Link to="/ingest" className="flex items-center gap-2 text-sm px-3 py-2 rounded-md hover:bg-slate-50"><FileText size={16}/> Ingest</Link>
          <Link to="/generate" className="flex items-center gap-2 text-sm px-3 py-2 rounded-md hover:bg-slate-50"><Activity size={16}/> New Quiz</Link>
          <Link to="/results" className="flex items-center gap-2 text-sm px-3 py-2 rounded-md hover:bg-slate-50"><ClipboardList size={16}/> Results</Link>
          <Link to="/quizzes" className="flex items-center gap-2 text-sm px-3 py-2 rounded-md hover:bg-slate-50"><List size={16}/> Quizzes</Link>
        </nav>

        <div className="flex items-center gap-3">
          {user ? (
            <div className="flex items-center gap-3">
              <div className="hidden md:block">
                <Avatar name={user.username} />
              </div>
              <div className="md:hidden">
                <Avatar name={user.username} size={28} />
              </div>
              <div className="hidden md:flex flex-col text-right mr-2">
                <div className="text-sm font-medium">{user.username}</div>
                <div className="text-xs text-slate-500">{user.role ?? 'student'}</div>
              </div>
              <Button variant="ghost" onClick={() => { logout(); nav('/login') }}><LogOut size={16}/> Logout</Button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link to="/login"><Button>Login</Button></Link>
              <Link to="/register"><Button variant="outline">Register</Button></Link>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
