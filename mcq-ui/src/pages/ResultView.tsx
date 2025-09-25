import React, { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import api from '../api'
import { Card } from '../components/ui/card'
import { Button } from '../components/ui/button'
import toast from 'react-hot-toast'
import Loader from '@/components/Loader'

export default function ResultView() {
  const { resultId } = useParams()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  // question pagination
  const [page, setPage] = useState(1)
  const perPage = 5
  const totalQuestions = data?.questions ? data.questions.length : 0
  const totalPages = Math.max(1, Math.ceil(totalQuestions / perPage))

  // ref to scroll to on page change
  const topRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => { if (resultId) load() }, [resultId])

  useEffect(() => {
    // scroll to top of the list when page changes
    if (topRef.current) {
      topRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [page])

  useEffect(() => {
    // reset question page when data changes
    setPage(1)
  }, [data?.questions?.length])

  const load = async () => {
    setLoading(true)
    try {
      const res = await api.get(`/quizzes/result/${resultId}`)
      setData(res.data)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Could not load result')
    } finally { setLoading(false) }
  }

  if (loading || !data) {
    return (
      <div className="max-w-3xl mx-auto py-8 px-4">
        <div className="min-h-[40vh] flex items-center justify-center">
          <Loader label="Loading result..." />
        </div>
      </div>
    )
  }

  const quizTitle = data.quiz_title || data.quiz_id
  const chapterInfo = data.chapter_name

  // slice questions for current page
  const startIndex = (page - 1) * perPage
  const currentQuestions = data.questions?.slice(startIndex, startIndex + perPage) ?? []

  return (
    <div className="max-w-3xl mx-auto py-8 px-4 space-y-6">
      <div ref={topRef} />
      <Card className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 className="text-2xl font-semibold">{quizTitle}</h2>
            {chapterInfo && <div className="text-sm text-muted-foreground mt-1">Chapters: {chapterInfo}</div>}
            <div className="text-sm text-muted-foreground mt-2">Submitted: {data.submitted_at ? new Date(data.submitted_at).toLocaleString() : '-'}</div>
          </div>

          <div className="text-right">
            <div className="text-sm text-muted-foreground">Score</div>
            <div className="text-2xl font-bold">{Number(data.score).toFixed(2)}%</div>
          </div>
        </div>
      </Card>

      <div className="space-y-4">
        {currentQuestions.map((q: any, idx: number) => {
          const globalIndex = startIndex + idx
          const d = Array.isArray(data.details) ? data.details.find((dd: any) => dd.id === q.id || dd.question === q.question) : null
          const given = d?.given ?? []
          const correct = d?.correct ?? []
          const isCorrect = d?.is_correct ?? (JSON.stringify(given) === JSON.stringify(correct))

          return (
            <div key={globalIndex} className="rounded-lg overflow-hidden shadow-sm">
              <div className="p-4 bg-card">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="text-base font-semibold">{globalIndex + 1}. {q.question}</div>
                    {/* {q.explanation && <div className="text-xs text-muted-foreground mt-1">Hint: {q.explanation}</div>} */}
                  </div>
                  <div className="text-sm text-right">
                    <div className={`${isCorrect ? 'text-green-700' : 'text-red-700'} font-semibold`}>{isCorrect ? 'Correct' : 'Wrong'}</div>
                  </div>
                </div>

                <div className="mt-3 space-y-2">
                  {q.options?.map((opt: string, oi: number) => {
                    const userPicked = Array.isArray(given) ? given.indexOf(oi) !== -1 : false
                    const isRightOpt = Array.isArray(correct) ? correct.indexOf(oi) !== -1 : false

                    return (
                      <div
                        key={oi}
                        className={`flex items-center gap-3 p-3 rounded-md transition
                          ${userPicked ? 'ring-2 ring-primary/40 bg-primary/10' : 'bg-white/50'}
                          ${isRightOpt ? 'border border-green-200' : 'border border-transparent'}`}
                      >
                        <div className="w-5 text-sm">{userPicked ? '●' : ''}</div>
                        <div className={`${isRightOpt ? 'font-semibold text-green-800' : ''} min-w-0`}>{opt}</div>
                        {isRightOpt && <div className="ml-auto text-xs text-green-700 font-medium">Answer</div>}
                      </div>
                    )
                  })}
                </div>

                <div className="mt-3 text-sm text-muted-foreground">
                  <div>Explanation: {d?.explanation ?? q.explanation ?? '—'}</div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* question pagination controls */}
      {(
        <div className="flex items-center justify-between mt-4">
          <div className="text-sm text-muted-foreground">Questions {startIndex + 1} - {Math.min(startIndex + perPage, totalQuestions)} of {totalQuestions}</div>

          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Prev</Button>
            <div className="text-sm">{page} / {totalPages}</div>
            <Button size="sm" variant="outline" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>Next</Button>
          </div>
        </div>
      )}
    </div>
  )
}
