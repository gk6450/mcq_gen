import { useEffect, useRef, useState } from 'react'
import api from '../api'
import { Card } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAuth } from '../contexts/AuthContext'
import Loader from '../components/Loader'

export default function Quizzes() {
  const [quizzes, setQuizzes] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const { user } = useAuth()

  // pagination
  const [page, setPage] = useState(1)
  const pageSize = 10
  const totalPages = Math.max(1, Math.ceil(quizzes.length / pageSize))

  // ref to scroll to on page change
  const topRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => { load() }, [])

  useEffect(() => {
    // scroll to top of the list when page changes
    if (topRef.current) {
      topRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [page])

  const load = async () => {
    setLoading(true)
    try {
      const res = await api.get('/quizzes/list')
      setQuizzes(Array.isArray(res.data) ? res.data : [])
      setPage(1)
    } catch (err) { toast.error('Could not load quizzes') }
    finally { setLoading(false) }
  }

  const deleteQuiz = async (quizId: string) => {
    if (!confirm('Delete this quiz?')) return
    try {
      await api.delete(`/quizzes/${quizId}`)
      toast.success('Deleted')
      load()
    } catch (err) { toast.error('Delete failed') }
  }

  const parseScope = (rawScope: string | undefined) => {
    if (!rawScope) return '-'
    try {
      const s = String(rawScope)
      // look for chapters=[...] or chapter=...
      if (s.includes('chapters=')) {
        // extract substring after chapters=
        const idx = s.indexOf('chapters=')
        const part = s.slice(idx + 'chapters='.length).trim()
        // try to parse JSON array
        try {
          const arr = JSON.parse(part)
          if (Array.isArray(arr)) return `Chapters: ${arr.join(', ')}`
        } catch {
          // fallback: strip trailing commas/braces
          const cleaned = part.replace(/^[\s{[]+|[\s}\]]+$/g, '')
          return `Chapters: ${cleaned}`
        }
      }
      if (s.includes('chapter=')) {
        const idx = s.indexOf('chapter=')
        const part = s.slice(idx + 'chapter='.length).trim()
        return `Chapter: ${part}`
      }
      return s
    } catch {
      return rawScope
    }
  }

  // page slice
  const paged = quizzes.slice((page - 1) * pageSize, page * pageSize)

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <div ref={topRef} />

      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-semibold">Available Quizzes</h2>
          <p className="text-sm text-muted-foreground mt-1">Browse and attempt quizzes created in the system.</p>
        </div>

        <div className="flex gap-2">
          <Link to="/generate"><Button>Generate Quiz</Button></Link>
          <Button variant="outline" onClick={load}>Refresh</Button>
        </div>
      </div>

      {loading ? (
        <div className="min-h-[40vh] flex items-center justify-center">
          <Loader label="Loading quizzes..." />
        </div>
      ) : quizzes.length === 0 ? (
        <Card className="text-center p-6"><div className="text-slate-600">No quizzes available yet.</div></Card>
      ) : (
        <>
          <div className="space-y-4">
            {paged.map((q) => {
              const quizTitle = q.quiz?.quiz_title || q.quiz_id
              const chapterInfo = q.quiz?.scope ? parseScope(q.quiz.scope) : undefined
              return (
                <Card key={q.quiz_id} className="flex items-center justify-between p-4 flex-row">
                  <div className="min-w-0">
                    <div className="font-semibold text-lg text-card-foreground truncate">{quizTitle}</div>
                    <div className="text-sm text-muted-foreground mt-1">
                      {q.quiz?.num_questions ?? '-'}q • {q.quiz?.source_book ?? '-'} • {q.quiz?.difficulty ?? '-'}
                    </div>
                    {chapterInfo && <div className="text-xs text-muted-foreground mt-1 truncate">{chapterInfo}</div>}
                  </div>

                  <div className="flex items-center gap-2">
                    <Link to={`/quiz/${q.quiz_id}`}><Button variant="outline" size="sm">Attempt</Button></Link>
                    {user?.role === 'admin' && <Button variant="destructive" size="sm" onClick={() => deleteQuiz(q.quiz_id)}>Delete</Button>}
                  </div>
                </Card>
              )
            })}
          </div>

          {/* Pagination controls */}
          <div className="mt-6 flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, quizzes.length)} of {quizzes.length}
            </div>

            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" onClick={() => setPage(p => {
                const next = Math.max(1, p - 1)
                return next
              })} disabled={page === 1}>Prev</Button>

              <div className="text-sm">{page} / {totalPages}</div>

              <Button size="sm" variant="outline" onClick={() => setPage(p => {
                const next = Math.min(totalPages, p + 1)
                return next
              })} disabled={page === totalPages}>Next</Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
