// src/App.tsx
import { type JSX } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Register from './pages/Register'
import Quizzes from './pages/Quizzes'
import Ingest from './pages/Ingest'
import GenerateQuiz from './pages/GenerateQuiz'
import Results from './pages/Results'
import QuizView from './pages/QuizView'
import ResultView from './pages/ResultView'
import { useAuth } from './contexts/AuthContext'
import Loader from './components/Loader'

function PrivateRoute({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth()
  if (loading) return (<div className="py-6 h-56 flex items-center justify-center">
    <Loader label="Loading..." />
  </div>)
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <div className="app-container">
      <Navbar />
      <main className="container-max py-8">
        <Routes>
          <Route path="/" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
          <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/quizzes" element={<PrivateRoute><Quizzes /></PrivateRoute>} />
          <Route path="/ingest" element={<PrivateRoute><Ingest /></PrivateRoute>} />
          <Route path="/generate" element={<PrivateRoute><GenerateQuiz /></PrivateRoute>} />
          <Route path="/results" element={<PrivateRoute><Results /></PrivateRoute>} />
          <Route path="/result/:resultId" element={<PrivateRoute><ResultView /></PrivateRoute>} />
          <Route path="/quiz/:quizId" element={<PrivateRoute><QuizView /></PrivateRoute>} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  )
}
