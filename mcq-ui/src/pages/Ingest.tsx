import React, { useEffect, useState, type JSX } from "react";
import api from "@/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import toast from "react-hot-toast";
import { useAuth } from "@/contexts/AuthContext";
import Loader from "@/components/Loader";

export default function Ingest(): JSX.Element {
  const [file, setFile] = useState<File | null>(null);
  const [bookId, setBookId] = useState("");
  const [chaptersJson, setChaptersJson] = useState("");
  const [chapterName, setChapterName] = useState("");
  const [startPage, setStartPage] = useState<number | "">("");
  const [endPage, setEndPage] = useState<number | "">("");
  const [loading, setLoading] = useState(false);
  const [books, setBooks] = useState<any[]>([]);
  const { user } = useAuth();

  // drag state for DnD
  const [dragActive, setDragActive] = useState(false);

  // modal state
  const [showBooksModal, setShowBooksModal] = useState(false);
  const [loadingBooks, setLoadingBooks] = useState(false);
  const [booksSearch, setBooksSearch] = useState("");

  useEffect(() => {
    loadBooks();
  }, []);

  useEffect(() => {
    if (showBooksModal) document.body.style.overflow = "hidden";
    else document.body.style.overflow = "";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setShowBooksModal(false);
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [showBooksModal]);

  const onFile = (f: FileList | null) => {
    if (!f || f.length === 0) {
      setFile(null);
      return;
    }
    const ff = f[0];
    if (!ff.name.toLowerCase().endsWith(".pdf")) {
      toast.error("Only PDF files supported");
      return;
    }
    setFile(ff);
  };

  // handlers for drag & drop
  const handleDrop = (ev: React.DragEvent) => {
    ev.preventDefault();
    ev.stopPropagation();
    setDragActive(false);
    const dt = ev.dataTransfer;
    if (dt && dt.files && dt.files.length > 0) {
      onFile(dt.files);
    }
  };

  const handleDragOver = (ev: React.DragEvent) => {
    ev.preventDefault();
    ev.stopPropagation();
    setDragActive(true);
  };

  const handleDragLeave = (ev: React.DragEvent) => {
    ev.preventDefault();
    ev.stopPropagation();
    setDragActive(false);
  };

  const submit = async () => {
    if (!file) return toast.error("Please choose a PDF file");
    const fd = new FormData();
    fd.append("pdf_file", file);
    if (bookId.trim()) fd.append("book_id", bookId.trim());
    if (chaptersJson.trim()) fd.append("chapters_json", chaptersJson.trim());
    if (chapterName.trim()) {
      fd.append("chapter_name", chapterName.trim());
      if (startPage !== "") fd.append("start_page", String(startPage));
      if (endPage !== "") fd.append("end_page", String(endPage));
    }

    setLoading(true);
    try {
      const res = await api.post("/books/ingest", fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success(`Ingested: ${res.data.book_id || "ok"}`);
      setFile(null);
      setBookId("");
      setChaptersJson("");
      setChapterName("");
      setStartPage("");
      setEndPage("");
      loadBooks();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Ingest failed");
    } finally {
      setLoading(false);
    }
  };

  const loadBooks = async () => {
    setLoadingBooks(true);
    try {
      const res = await api.get("/books/list");
      setBooks(Array.isArray(res.data) ? res.data : []);
    } catch {
      // ignore
    } finally {
      setLoadingBooks(false);
    }
  };

  const deleteBook = async (book_id: string) => {
    if (!confirm("Delete this book?")) return;
    try {
      await api.delete(`/books/${encodeURIComponent(book_id)}`);
      toast.success("Deleted");
      loadBooks();
    } catch {
      toast.error("Delete failed");
    }
  };

  const filteredBooks = booksSearch.trim()
    ? books.filter((b) => (b.title ?? b.book_id).toLowerCase().includes(booksSearch.toLowerCase()) || b.book_id.toLowerCase().includes(booksSearch.toLowerCase()))
    : books;

  return (
    <div className="max-w-5xl mx-auto py-8 px-4">
      <Card className="p-8 rounded-2xl shadow-xl border border-border bg-card/95 backdrop-blur-sm">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2 className="text-2xl font-semibold">Ingest Book (PDF)</h2>
            <p className="text-sm text-muted-foreground mt-1">Upload a PDF and optionally provide chapters or single-chapter metadata.</p>
          </div>

          {/* Top-right button to open books modal */}
          <div className="flex items-center gap-3">
            <Button
              onClick={() => { setShowBooksModal(true); }}
              variant="secondary"
              size="sm"
              className="inline-flex items-center gap-2"
              aria-label="Show uploaded books"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
                <path d="M2 5.5A2.5 2.5 0 014.5 3h11A2.5 2.5 0 0118 5.5V14a1 1 0 01-1 1h-3v-1a1 1 0 00-1-1H7a1 1 0 00-1 1v1H3a1 1 0 01-1-1V5.5z" />
              </svg>
              Uploaded books
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="text-sm font-medium">PDF File</label>

            {/* Drag & Drop area */}
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              className={`mt-2 flex items-center justify-between gap-4 w-full p-3 rounded-md border ${
                dragActive ? "border-primary bg-primary/5" : "border-border bg-input"
              } text-sm cursor-pointer hover:shadow-sm focus-within:ring-2 focus-within:ring-primary`}
            >
              <div className="flex-1">
                <div className="text-sm">
                  {file ? (
                    <span>Selected: <span className="font-medium">{file.name}</span></span>
                  ) : (
                    <span className="text-muted-foreground">Drop a PDF here, or click to choose</span>
                  )}
                </div>
                {file && <div className="text-xs text-muted-foreground mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</div>}
              </div>

              <div className="flex items-center gap-3">
                <label htmlFor="pdf-file" className="px-3 py-1 rounded-md border border-border bg-background text-sm cursor-pointer">
                  Browse
                </label>
                <span className="text-xs text-muted-foreground">PDF only</span>
              </div>

              <input id="pdf-file" type="file" accept="application/pdf" onChange={(e) => onFile(e.target.files)} className="sr-only" />
            </div>

            <div className="mt-4">
              <label htmlFor="ingest-book-id" className="text-sm font-medium">Book ID (optional)</label>
              <input
                id="ingest-book-id"
                value={bookId}
                onChange={(e) => setBookId(e.target.value)}
                className="w-full mt-2 p-3 rounded-md border border-border bg-input text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary transition"
                placeholder="e.g. book-123"
              />
            </div>

            <div className="mt-4">
              <label className="text-sm font-medium">Or single chapter info</label>
              <input
                value={chapterName}
                onChange={(e) => setChapterName(e.target.value)}
                placeholder="Chapter name"
                className="w-full mt-2 p-3 rounded-md border border-border bg-input text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary transition"
              />
              <div className="flex gap-2 mt-3">
                <input
                  type="number"
                  value={startPage as any}
                  onChange={(e) => setStartPage(e.target.value ? Number(e.target.value) : "")}
                  placeholder="start page"
                  className="p-3 border rounded w-32 focus:outline-none focus:ring-2 focus:ring-primary transition"
                />
                <input
                  type="number"
                  value={endPage as any}
                  onChange={(e) => setEndPage(e.target.value ? Number(e.target.value) : "")}
                  placeholder="end page"
                  className="p-3 border rounded w-32 focus:outline-none focus:ring-2 focus:ring-primary transition"
                />
              </div>
            </div>

            <div className="mt-6 flex gap-3">
              <Button onClick={submit} disabled={loading}>
                {loading ? (
                  <div className="flex items-center gap-2">
                    <Loader /> Ingesting...
                  </div>
                ) : (
                  "Ingest Book"
                )}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setFile(null);
                  setBookId("");
                  setChaptersJson("");
                  setChapterName("");
                  setStartPage("");
                  setEndPage("");
                }}
              >
                Clear
              </Button>
            </div>
          </div>

          <div>
            <label className="text-sm font-medium">Chapters JSON (optional)</label>
            <textarea
              value={chaptersJson}
              onChange={(e) => setChaptersJson(e.target.value)}
              rows={8}
              className="w-full mt-2 p-3 rounded-md border border-border bg-input text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary transition"
              placeholder='JSON array like [{"name":"Ch1","start_page":1,"end_page":12}]'
            />

            <div className="mt-6">
              <h4 className="text-sm font-semibold mb-2">Notes</h4>
              <div className="text-sm text-muted-foreground">Use the <strong>Uploaded books</strong> button on top-right to pick an existing book ID.</div>
            </div>
          </div>
        </div>
      </Card>

      {/* Books modal */}
      {showBooksModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setShowBooksModal(false)}
            aria-hidden
          />

          <div className="relative z-10 w-full max-w-3xl mx-4">
            <div className="bg-card rounded-2xl shadow-2xl border border-border overflow-hidden">
              <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                <div>
                  <h3 className="text-lg font-semibold">Uploaded books</h3>
                  <p className="text-sm text-muted-foreground mt-1">Click <span className="font-medium">Use</span> to copy the Book ID or delete if you have admin access.</p>
                </div>

                <div className="flex items-center gap-3">
                  <input
                    value={booksSearch}
                    onChange={(e) => setBooksSearch(e.target.value)}
                    placeholder="Search title or id..."
                    className="px-3 py-2 rounded-md border border-border bg-input focus:outline-none focus:ring-2 focus:ring-primary transition text-sm"
                    aria-label="Search uploaded books"
                  />
                  <Button variant="outline" onClick={() => setShowBooksModal(false)} aria-label="Close uploaded books modal" size="sm">
                    ✕
                  </Button>
                </div>
              </div>

              <div className="p-6 max-h-[60vh] overflow-auto space-y-3">
                {loadingBooks ? (
                  <Loader label="Loading books..." />
                ) : filteredBooks.length === 0 ? (
                  <div className="text-sm text-slate-500">No books uploaded yet.</div>
                ) : (
                  filteredBooks.map((b) => (
                    <div key={b.book_id} className="flex items-center justify-between gap-4 p-4 rounded-lg border border-border bg-background">
                      <div className="min-w-0">
                        {/* <div className="font-medium truncate">{b.title}</div> */}
                        <div className="font-medium truncate">{b.book_id}</div>
                        <div className="text-xs text-muted-foreground mt-1">{(b.inserted_chunks ?? 0) + " chunks"}</div>
                      </div>

                      <div className="flex items-center gap-3">
                        <Button
                          onClick={() => {
                            setBookId(b.book_id);
                            setShowBooksModal(false);
                          }}
                          size="sm"
                        >
                          Use
                        </Button>

                        {user?.role === "admin" && (
                          <Button
                            variant="destructive"
                            onClick={() => deleteBook(b.book_id)}
                            size="sm"
                          >
                            Delete
                          </Button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
