import { useEffect, useState, type JSX } from "react";
import api from "@/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import Loader from "@/components/Loader";

type BookItem = { book_id: string; title?: string };

export default function GenerateQuiz(): JSX.Element {
  const [bookId, setBookId] = useState("");
  const [books, setBooks] = useState<BookItem[]>([]);
  const [chapters, setChapters] = useState<string[]>([]);
  const [selectedChapters, setSelectedChapters] = useState<string[]>([]);
  const [customChaptersText, setCustomChaptersText] = useState("");
  // allow empty while editing; on blur treat as 0
  const [num, setNum] = useState<number | "">(10);
  const [difficulty, setDifficulty] = useState<"easy" | "medium" | "hard">("medium");
  const [loadingBooks, setLoadingBooks] = useState(false);
  const [loadingChapters, setLoadingChapters] = useState(false);
  const [generating, setGenerating] = useState(false);
  const nav = useNavigate();

  useEffect(() => {
    loadBooks();
  }, []);

  const loadBooks = async () => {
    setLoadingBooks(true);
    try {
      const res = await api.get("/books/list");
      if (Array.isArray(res.data)) setBooks(res.data.map((b: any) => ({ book_id: b.book_id, title: b.title })));
      else setBooks([]);
    } catch {
      toast.error("Could not load books");
    } finally {
      setLoadingBooks(false);
    }
  };

  useEffect(() => {
    if (!bookId) {
      setChapters([]);
      setSelectedChapters([]);
      return;
    }
    loadChapters(bookId);
  }, [bookId]);

  const loadChapters = async (id: string) => {
    setLoadingChapters(true);
    setChapters([]);
    setSelectedChapters([]);
    try {
      const res = await api.get(`/books/${encodeURIComponent(id)}/chapters`);
      if (res.data && Array.isArray(res.data.chapters)) setChapters(res.data.chapters);
      else setChapters([]);
    } catch {
      toast.error("Could not load chapters for selected book");
    } finally {
      setLoadingChapters(false);
    }
  };

  const toggleChapter = (name: string) =>
    setSelectedChapters((p) => (p.includes(name) ? p.filter((x) => x !== name) : [...p, name]));

  const create = async () => {
    if (!bookId) return toast.error("Please select a book");
    setGenerating(true);
    try {
      const payload = {
        book_id: bookId,
        // send chapter_name as comma-separated string when you selected chips:
        chapter_name: selectedChapters.length ? selectedChapters.join(", ") : (customChaptersText?.trim() || undefined),
        // only send chapters_json when user pasted a JSON array string (starts with '[')
        ...(customChaptersText.trim().startsWith("[") ? { chapters_json: customChaptersText.trim() } : {}),
        num_questions: num === "" ? 0 : num,
        difficulty,
      };

      console.log("Generating quiz with payload:", payload);

      const res = await api.post("/quizzes/generate", payload, {
        headers: { "Content-Type": "application/json" },
      });
      const quizId = res.data?.quiz_id || res.data?.id;
      toast.success("Quiz generated");
      if (quizId) nav(`/quiz/${quizId}`);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Could not generate quiz");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      <Card className="p-8 rounded-2xl shadow-xl border border-border bg-card/95 backdrop-blur-sm">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2 className="text-2xl font-semibold">Generate Quiz</h2>
            <p className="text-sm text-muted-foreground mt-1">Pick book & chapters, set difficulty and number of questions.</p>
          </div>
        </div>

        <div className="space-y-6">
          <div>
            <label htmlFor="select-book" className="text-sm font-medium">Select Book</label>
            <div className="mt-2">
              {loadingBooks ? (
                <Loader label="Loading books..." />
              ) : (
                <select
                  id="select-book"
                  value={bookId}
                  onChange={(e) => setBookId(e.target.value)}
                  className="w-full mt-1 p-3 rounded-md border border-border bg-input text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary transition"
                >
                  <option value="">-- Select a book --</option>
                  {books.map((b) => (
                    <option key={b.book_id} value={b.book_id}>
                      {b.title ?? b.book_id}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>

          <div>
            <label className="text-sm font-medium">Chapters (pick or type comma-separated)</label>
            <div className="mt-2">
              {loadingChapters ? (
                <Loader label="Loading chapters..." />
              ) : chapters.length === 0 ? (
                <div className="text-sm text-slate-500">No chapters available for this book.</div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {chapters.map((c) => {
                    const active = selectedChapters.includes(c);
                    return (
                      <button
                        key={c}
                        type="button"
                        onClick={() => toggleChapter(c)}
                        className={`px-3 py-1 rounded-full text-sm border transition focus:outline-none focus:ring-2 focus:ring-primary ${active ? "bg-primary text-white border-primary" : "bg-background text-foreground border-border hover:shadow-sm"
                          }`}
                        aria-pressed={active}
                      >
                        {c}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="mt-3">
              <input
                id="custom-chapters"
                placeholder="Type chapters: Chapter 1, Chapter 2 — or paste JSON array [{}] "
                value={customChaptersText}
                onChange={(e) => setCustomChaptersText(e.target.value)}
                className="w-full mt-1 p-3 rounded-md border border-border bg-input text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary transition"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="difficulty" className="text-sm font-medium">Difficulty</label>
              <select
                id="difficulty"
                className="w-full mt-2 p-3 rounded-md border border-border bg-input focus:outline-none focus:ring-2 focus:ring-primary transition"
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value as any)}
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>

            <div>
              <label htmlFor="num-questions" className="text-sm font-medium">Number of questions</label>
              <input
                id="num-questions"
                type="number"
                min={0}
                value={num}
                onChange={(e) => {
                  if (e.target.value === "") setNum("");
                  else setNum(Number(e.target.value));
                }}
                onBlur={() => {
                  if (num === "") setNum(0);
                }}
                className="mt-2 p-3 rounded-md border border-border bg-input text-foreground focus:outline-none focus:ring-2 focus:ring-primary transition w-full"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button onClick={create} disabled={generating} className="px-5 py-2">
              {generating ? (
                <div className="flex items-center gap-2">
                  <Loader size={14} /> Generating...
                </div>
              ) : (
                "Generate Quiz"
              )}
            </Button>

            <Button
              variant="outline"
              onClick={() => {
                setBookId("");
                setChapters([]);
                setSelectedChapters([]);
                setCustomChaptersText("");
                setNum(10);
                setDifficulty("medium");
              }}
              className="px-4 py-2"
            >
              Reset
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
