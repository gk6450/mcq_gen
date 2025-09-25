import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'
import toast from 'react-hot-toast'
import { useAuth } from '../contexts/AuthContext'
import { Card } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { ChartContainer } from '../components/ui/chart'
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Sector,
} from 'recharts'
import Loader from '../components/Loader'

type ResultRow = { id: number; quiz_id: string; quiz_title?: string; chapter_name?: string; username?: string; score: number; total?: number; submitted_at?: string }
type QuizItem = { quiz_id: string; quiz: any }

const COLORS = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
]

export default function Dashboard() {
  const { user } = useAuth()
  const [recentQuizzes, setRecentQuizzes] = useState<QuizItem[]>([])
  const [results, setResults] = useState<ResultRow[]>([])
  const [recentAttempts, setRecentAttempts] = useState<ResultRow[]>([])
  const [loadingQuizzes, setLoadingQuizzes] = useState(false)
  const [loadingResults, setLoadingResults] = useState(false)
  const [adminMode, setAdminMode] = useState<'mine' | 'all'>('mine')

  const [activeIndex, setActiveIndex] = useState<number | null>(null)

  useEffect(() => { fetchRecentQuizzes() }, [])
  useEffect(() => { fetchResults() }, [user, adminMode])

  const fetchRecentQuizzes = async () => {
    setLoadingQuizzes(true)
    try {
      const res = await api.get('/quizzes/list')
      setRecentQuizzes(Array.isArray(res.data) ? res.data.slice(0, 4) : [])
    } catch (err) { toast.error('Could not load quizzes') }
    finally { setLoadingQuizzes(false) }
  }

  const fetchResults = async () => {
    if (!user) return
    setLoadingResults(true)
    try {
      let res
      if (user.role === 'admin' && adminMode === 'all') {
        res = await api.get('/quizzes/result/all')
      } else {
        res = await api.get('/quizzes/me/results')
      }
      const arr = Array.isArray(res.data) ? res.data : []
      setResults(arr)
      // recent attempts: take top 4 by submitted_at desc (backend usually already ordered)
      const sorted = [...arr].sort((a, b) => {
        const ta = a.submitted_at ? new Date(a.submitted_at).getTime() : 0
        const tb = b.submitted_at ? new Date(b.submitted_at).getTime() : 0
        return tb - ta
      })
      setRecentAttempts(sorted.slice(0, 4))
    } catch (err) { toast.error('Could not load results') }
    finally { setLoadingResults(false) }
  }

  // buckets based on results
  const buckets = useMemo(() => {
    const b = { r0_25: 0, r26_60: 0, r61_89: 0, r90_100: 0 }
    results.forEach(r => {
      let s = Number(r.score || 0)
      if (Number.isNaN(s)) s = 0
      s = Math.max(0, Math.min(100, s))
      if (s <= 25) b.r0_25++
      else if (s <= 60) b.r26_60++
      else if (s <= 89) b.r61_89++
      else b.r90_100++
    })
    return [
      { name: '0–25%', value: b.r0_25 },
      { name: '26–60%', value: b.r26_60 },
      { name: '61–89%', value: b.r61_89 },
      { name: '90–100%', value: b.r90_100 },
    ]
  }, [results])

  const totalInBuckets = buckets.reduce((s, b) => s + (b.value || 0), 0)
  const fmtDate = (d?: string) => d ? new Date(d).toLocaleString() : ''

  const renderActiveShape = (props: any) => {
    const { cx, cy, startAngle, endAngle, innerRadius, outerRadius, fill } = props
    return (
      <g>
        <Sector
          cx={cx}
          cy={cy}
          innerRadius={innerRadius}
          outerRadius={outerRadius + 12}
          startAngle={startAngle}
          endAngle={endAngle}
          fill={fill}
        />
      </g>
    )
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

  return (
    <div className="max-w-6xl mx-auto mt-8 space-y-6 px-4">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold text-foreground">Dashboard</h1>

        {user?.role === 'admin' && (
          <div className="flex items-center gap-2">
            <Button variant={adminMode === 'mine' ? 'default' : 'ghost'} onClick={() => setAdminMode('mine')}>My results</Button>
            <Button variant={adminMode === 'all' ? 'default' : 'ghost'} onClick={() => setAdminMode('all')}>All results</Button>
          </div>
        )}
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        {/* Recent Quizzes */}
        <Card className="col-span-2 p-4 bg-card border border-border rounded-lg shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-card-foreground">Recent Quizzes</h3>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => { fetchRecentQuizzes(); fetchResults(); }} size="sm">Refresh</Button>
              <Link to="/results"><Button variant="ghost" size="sm">View all</Button></Link>
            </div>
          </div>

          {loadingQuizzes ? (
            <div className="py-6 h-56 flex items-center justify-center">
              <Loader label="Loading quizzes..." />
            </div>
          ) : (
            <div className="grid md:grid-cols-2 gap-3">
              {recentQuizzes.map((q: any) => {
                const chapterInfo = q.quiz?.scope ? parseScope(q.quiz.scope) : undefined
                return(
                <div key={q.quiz_id} className="p-3 border border-border rounded-md shadow-sm transition flex flex-col justify-between bg-gradient-to-r from-sidebar to-card hover:shadow-md hover:ring-2 hover:ring-primary hover:ring-offset-1 hover:ring-offset-card">
                  <div>
                    <div className="font-semibold text-card-foreground truncate">{q.quiz?.quiz_title ?? q.quiz_id}</div>
                    <div className="text-sm text-muted-foreground mt-1">
                      {q.quiz?.num_questions ?? '-'}q • {q.quiz?.source_book ?? '-'} • {q.quiz?.difficulty ?? '-'}
                    </div>
                    {chapterInfo && <div className="text-xs text-muted-foreground mt-1 truncate">{chapterInfo}</div>}
                  </div>

                  <div className="mt-3 flex justify-end">
                    <Link to={`/quiz/${q.quiz_id}`}><Button variant="outline" size="sm">Try now</Button></Link>
                  </div>
                </div>
              )}
              )}
            </div>
          )}
        </Card>

        {/* Performance overview */}
        <Card className="p-4 bg-card border border-border rounded-lg shadow-sm">
          <h4 className="text-md font-semibold text-card-foreground">Performance overview</h4>

          <div className="mt-3" style={{ height: '28vh', minHeight: 220 }}>
            {loadingResults ? (
              <div className="h-full flex flex-col items-center justify-center">
                <Loader label="Loading results..." />
              </div>
            ) : (
              <ChartContainer config={{}}>
                {totalInBuckets === 0 ? (
                  <div className="h-full flex items-center justify-center text-muted-foreground">No data to display</div>
                ) : (
                  <>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart margin={{ top: 32, right: 20, bottom: 48, left: 20 }}>
                        <Pie
                          data={buckets}
                          dataKey="value"
                          nameKey="name"
                          innerRadius={50}
                          outerRadius={72}
                          paddingAngle={4}
                          onMouseEnter={(_, index) => setActiveIndex(index)}
                          onMouseLeave={() => setActiveIndex(null)}
                          activeIndex={activeIndex ?? undefined}
                          activeShape={renderActiveShape}
                        >
                          {buckets.map((_entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(value: number, name: string) => [`${value}`, name]} />
                      </PieChart>
                    </ResponsiveContainer>

                    <div className="mt-2 flex items-center justify-center gap-3">
                      {buckets.map((b, i) => (
                        <div key={b.name} className="flex items-center gap-1 text-xs text-muted-foreground">
                          <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: COLORS[i % COLORS.length], border: '1px solid rgba(0,0,0,0.06)' }} />
                          <span className="whitespace-nowrap">{b.name} ({b.value})</span>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </ChartContainer>
            )}
          </div>

          {!loadingResults && (
            <div className="mt-4">
              <div className="text-sm text-muted-foreground">
                {results.length === 0 ? 'No results yet.' : `Showing ${results.length} result${results.length > 1 ? 's' : ''}`}
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* Previously attempted quizzes (show up to 4) */}
      <Card className="p-4 bg-card border border-border rounded-lg shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-card-foreground">Previously attempted quizzes</h3>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => { fetchRecentQuizzes(); fetchResults(); }} size="sm">Refresh</Button>
            <Link to="/results"><Button variant="ghost" size="sm">View all</Button></Link>
          </div>
        </div>

        {loadingResults ? (
          <div className="py-6 h-56 flex items-center justify-center">
            <Loader label="Loading results..." />
          </div>
        ) : recentAttempts.length === 0 ? (
          <div className="p-4 text-muted-foreground">{user ? 'No recent attempts' : 'Login to see your results'}</div>
        ) : (
          <div className="grid md:grid-cols-2 gap-3">
            {recentAttempts.map((r) => (
              <div key={r.id} className="p-3 border border-border rounded-md shadow-sm transition hover:shadow-md bg-gradient-to-r from-sidebar to-card hover:ring-2 hover:ring-primary hover:ring-offset-1 hover:ring-offset-card">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-semibold text-sm text-card-foreground truncate">{r.quiz_title || r.quiz_id}</div>
                    {r.chapter_name && <div className="text-xs text-muted-foreground mt-1 truncate">Chapters: {r.chapter_name.replace(',', ', ')}</div>}
                    <div className="text-xs text-muted-foreground mt-1">{r.username ? `by ${r.username} • ` : ''}{fmtDate(r.submitted_at)}</div>
                    <div className="text-sm text-card-foreground mt-2">Score: <span className="font-medium">{Number(r.score).toFixed(2)}%</span></div>
                  </div>

                  <div className="flex flex-col items-end gap-2">
                    <Link to={`/result/${r.id}`}><Button size="sm">View result</Button></Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
