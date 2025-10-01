import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api'
import { Card } from '../components/ui/card'
import { Button } from '../components/ui/button'
import toast from 'react-hot-toast'
import Loader from '../components/Loader'

export default function QuizView() {
  const { quizId } = useParams()
  const navigate = useNavigate()
  const [quiz, setQuiz] = useState<any>(null)
  const [selected, setSelected] = useState<Record<number, number[]>>({}) // questionIndex -> selected indices
  const [loading, setLoading] = useState(false)

  // question pagination
  const [page, setPage] = useState(1)
  const perPage = 5
  const totalQuestions = quiz?.questions ? quiz.questions.length : 0
  const totalPages = Math.max(1, Math.ceil(totalQuestions / perPage))

  // ref to scroll to top on page change
  const topRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (quizId) load()
  }, [quizId])

  useEffect(() => {
    // scroll smoothly to top when page changes
    if (topRef.current) topRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [page])

  useEffect(() => {
    // reset selected & page when quiz changes
    setSelected({})
    setPage(1)
  }, [quiz?.quiz_id])

  const load = async () => {
    setLoading(true)
    try {
      const res = await api.get(`/quizzes/${quizId}`)
      setQuiz(res.data)
    } catch (err) { toast.error('Could not load quiz') }
    finally { setLoading(false) }
  }

  const toggleOption = (qIdx: number, optIdx: number, multi: boolean) => {
    setSelected(prev => {
      const cur = prev[qIdx] ? [...prev[qIdx]] : []
      if (multi) {
        const exists = cur.indexOf(optIdx)
        if (exists === -1) cur.push(optIdx)
        else cur.splice(exists, 1)
      } else {
        // single-select replacement; allow unselect by clicking same option
        if (cur.length === 1 && cur[0] === optIdx) {
          return { ...prev, [qIdx]: [] }
        }
        return { ...prev, [qIdx]: [optIdx] }
      }
      return { ...prev, [qIdx]: cur }
    })
  }

  const submit = async () => {
    if (!quiz) return
    setLoading(true)
    try {
      const questions = quiz.questions || []
      const answers: number[][] = []
      for (let i = 0; i < questions.length; i++) {
        answers.push(selected[i] ? selected[i] : [])
      }
      const payload = { answers }
      const res = await api.post(`/quizzes/${quizId}/submit`, payload)
      const resultId = res.data?.result_id
      toast.success('Submitted')
      if (resultId) navigate(`/result/${resultId}`)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Submit failed')
    } finally { setLoading(false) }
  }

  if (loading || !quiz) {
    return (
      <div className="max-w-3xl mx-auto py-8 px-4">
        <div className="min-h-[40vh] flex items-center justify-center">
          <Loader label="Loading quiz..." />
        </div>
      </div>
    )
  }

  const quizTitle = quiz.quiz_title || quizId
  const startIndex = (page - 1) * perPage
  const currentQuestions = quiz.questions?.slice(startIndex, startIndex + perPage) ?? []

  return (
    <div className="max-w-3xl mx-auto space-y-4 py-8 px-4">
      <div ref={topRef} />

      <Card className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">{quizTitle}</h2>
            {quiz.chapter_name && <div className="text-sm text-muted-foreground mt-1">Chapters: {quiz.chapter_name}</div>}
            <div className="text-sm text-muted-foreground mt-1">{quiz.questions?.length ?? 0} questions • Difficulty: {quiz.difficulty ?? '-'}</div>
          </div>
        </div>

        <div className="mt-4 space-y-4">
          {currentQuestions.map((q:any, idx:number) => {
            const globalIdx = startIndex + idx
            const multi = (q.correct_answers && q.correct_answers.length > 1)
            const sel = selected[globalIdx] || []
            return (
              <div key={globalIdx} className="rounded-lg overflow-hidden shadow-sm">
                <div className="p-4 bg-gradient-to-r from-sidebar to-card">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="text-base font-semibold">{globalIdx + 1}. {q.question}</div>
                      {/* {q.explanation && <div className="text-xs text-muted-foreground mt-1">Hint: {q.explanation}</div>} */}
                    </div>
                    <div className="text-sm text-muted-foreground">{multi ? 'Multiple choice' : 'Single choice'}</div>
                  </div>

                  <div className="mt-3 space-y-2">
                    {q.options?.map((opt:string, oi:number) => {
                      const checked = sel.indexOf(oi) !== -1
                      return (
                        <label
                          key={oi}
                          className={`flex items-center gap-2 p-3 rounded-md cursor-pointer transition
                            ${checked ? 'ring-2 ring-primary/40 bg-primary/10' : 'bg-white/50'}`}
                        >
                          <input
                            type={multi ? 'checkbox' : 'radio'}
                            name={`q-${globalIdx}`}
                            checked={checked}
                            onChange={() => toggleOption(globalIdx, oi, multi)}
                            className="transform scale-95"
                            aria-checked={checked}
                          />
                          <div className={`${checked ? 'font-semibold' : ''} min-w-0`}>{opt}</div>
                        </label>
                      )
                    })}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        <div className="mt-4 flex items-center justify-between">
          <div>
            {totalQuestions > perPage && (
              <div className="flex items-center gap-2">
                <Button size="sm" variant="outline" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Prev</Button>
                <div className="text-sm">{page} / {totalPages}</div>
                <Button size="sm" variant="outline" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>Next</Button>
              </div>
            )}
          </div>

          <div>
            <Button onClick={submit} disabled={loading}>Submit Quiz</Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
