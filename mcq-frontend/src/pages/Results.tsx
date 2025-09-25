import React, { useEffect, useRef, useState } from 'react'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'
import { Card } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import Loader from '@/components/Loader'

export default function Results() {
  const { user } = useAuth()
  const [results, setResults] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [adminMode, setAdminMode] = useState<'mine' | 'all'>('mine')

  // pagination
  const [page, setPage] = useState(1)
  const pageSize = 10
  const totalPages = Math.max(1, Math.ceil(results.length / pageSize))

  // ref to scroll to on page change
  const topRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => { load() }, [user, adminMode])

  useEffect(() => {
    // scroll to top of the list when page changes
    if (topRef.current) {
      topRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [page])

  const load = async () => {
    if (!user) return
    setLoading(true)
    try {
      if (user.role === 'admin' && adminMode === 'all') {
        const res = await api.get('/quizzes/result/all')
        setResults(res.data || [])
      } else {
        const res = await api.get('/quizzes/me/results')
        setResults(res.data || [])
      }
      setPage(1)
    } catch (err) { toast.error('Could not load results') }
    finally { setLoading(false) }
  }

  const fmtDate = (iso?: string) => iso ? new Date(iso).toLocaleString() : '-'

  const subtitle = user?.role === 'admin' && adminMode === 'all'
    ? 'All quiz attempts by students. Click View to inspect answers.'
    : 'Your recent quiz attempts. Click View to inspect answers.'

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto py-8 px-4">
        <div className="min-h-[40vh] flex items-center justify-center">
          <Loader label="Loading results..." />
        </div>
      </div>
    )
  }

  const paged = results.slice((page - 1) * pageSize, page * pageSize)

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      <div ref={topRef} />
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-semibold">Results</h2>
          <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>
        </div>

        {user?.role === 'admin' && (
          <div className="flex gap-2">
            <Button variant={adminMode === 'mine' ? 'default' : 'ghost'} size="sm" onClick={() => { setAdminMode('mine') }}>My results</Button>
            <Button variant={adminMode === 'all' ? 'default' : 'ghost'} size="sm" onClick={() => { setAdminMode('all') }}>All results</Button>
          </div>
        )}
      </div>

      {results.length === 0 ? (
        <Card className="p-6">No results yet</Card>
      ) : (
        <>
          <div className="space-y-4">
            {paged.map((r) => {
              const title = r.quiz_title || r.quiz_id
              return (
                <Card key={r.id} className="p-4">
                  <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-3">
                        <div className="text-lg font-semibold truncate">{title}</div>
                        {/* <div className="text-xs text-muted-foreground truncate">({r.quiz_id})</div> */}
                      </div>
                      {r.chapter_name && <div className="text-sm text-muted-foreground mt-1">Chapters: {r.chapter_name}</div>}
                      <div className="text-sm text-muted-foreground mt-1">Submitted: {fmtDate(r.submitted_at)}</div>
                    </div>

                    <div className="flex items-center gap-4">
                      <div className="text-sm text-muted-foreground text-right">
                        <div className="text-xs">Score</div>
                        <div className="text-lg font-bold">{Number(r.score).toFixed(2)}%</div>
                      </div>

                      <Link to={`/result/${r.id}`}>
                        <Button size="sm">View</Button>
                      </Link>
                    </div>
                  </div>
                </Card>
              )
            })}
          </div>

          {/* pagination controls */}
          <div className="mt-6 flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, results.length)} of {results.length}
            </div>

            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Prev</Button>
              <div className="text-sm">{page} / {totalPages}</div>
              <Button size="sm" variant="outline" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>Next</Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
