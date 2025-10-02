# MCQ Generator (AI-powered MCQ Platform)

[Try it out](https://mcq-gen-two.vercel.app/)

MCQ Generator is an **AI-powered** web application that converts uploaded PDFs (single chapter, multiple chapters, or whole books) into interactive multiple-choice quizzes. It uses a Retrieval-Augmented Generation (RAG) pipeline: documents are chunked, embedded, and stored in a vector database (Pinecone). When generating quizzes, the app retrieves relevant chunks and uses an LLM (Gemini/ OpenAI) together with the retrieved context to produce high-quality, context-aware MCQs.

---

## Who this is for

**Students**

* Register and login to the site.
* Generate new quiz by specifying book, chapters, no. of questions & difficulty.
* Browse and take generated quizzes.
* Attempt quizzes and receive immediate scoring and detailed explanations.
* Review history of past attempts and detailed per-question feedback.

**Admins**

* Admins can **only login** (admins can’t self-register via the UI). Admin accounts are created manually (in DB).
* Upload and ingest PDFs (single chapter, multiple chapters, or entire books).
* Delete uploaded books and already generated quizzes.
* View students' results.

**Note**: Role-based access is enforced on the backend - some endpoints are admin-only.

---

## Feature list

* Authentication: Register (students), Login (students + admins), JWT-based session.
* Document ingestion: upload PDFs (chapter/whole book). Ingested chunks are embedded and upserted into the vector DB.
* AI quiz generation: create MCQ quizzes using retrieved document context + LLM generation.
* RAG (Retrieval-Augmented Generation): the quiz generation uses semantic retrieval from Pinecone to ground LLM responses in the actual document content.
* Quiz taking: paginated question view, answer submission and grading.
* Results history: view past attempts with per-question correctness and AI-generated explanations.
* Admin controls: delete books, delete generated quizzes, view analytics.

---

## Tech Stack

### Frontend

* **React + Vite** - fast dev server and modern SPA architecture.
* **shadcn/ui + Tailwind CSS** - pre-built UI primitives and utility-first styling for rapid, consistent UI development.
* **Axios** - API client with request/response interceptors for attaching JWT tokens and handling errors.
* **React Router** - navigation between pages (dashboard, ingestion, generate quiz, quiz view, results).
* **react-hook-form + zod** - forms and validation for robust UX.
* **recharts** - visual analytics in the admin dashboard.

### Backend

* **Python + FastAPI** - async-first framework with excellent performance for I/O-bound tasks and simple dependency injection.
* **SQLAlchemy (async)** + **MySQL** (Aiven or local) - persistent relational storage for users, books, chunks, quizzes and results.
* **Pinecone** - vector index for semantic retrieval of text chunks.
* **Hugging Face Inference API** - embeddings using `sentence-transformers/all-MiniLM-L6-v2` (384-dim embeddings). Chosen for high quality and compatibility with Pinecone.
* **AI providers: Gemini / OpenAI** - pluggable LLM backends for quiz generation. Code supports switching providers.
* **python-jose / bcrypt** - secure JWT creation and password hashing.

---

## Architecture & data flow

```
[Browser / React UI]  <--Axios (VITE_API_BASE_URL + Bearer token)-->  [FastAPI Backend]
                                                           |-- MySQL (Aiven Console)
                                                           |-- Pinecone (vector index, dims=384)
                                                           |-- Hugging Face Inference API (embeddings)
                                                           |-- LLM Provider (Gemini or OpenAI)

Main flows:
 1) Ingest: Browser -> POST /books/ingest (file upload) -> Backend chunks file -> HF embeddings -> Pinecone upsert -> metadata saved to MySQL
 2) Generate Quiz: Browser -> POST /quizzes/generate -> Backend creates query embedding -> Pinecone query for relevant chunks -> Pass context + prompt to LLM -> LLM returns structured quiz -> Backend saves quiz metadata & questions
 3) Take Quiz: Browser GET quiz -> user answers -> POST /quizzes/{id}/submit -> backend grades (optionally re-using embeddings/LLM for explanations) -> results persisted in MySQL
```

---

## RAG (Retrieval-Augmented Generation)

This app uses RAG for quiz generation: instead of relying purely on a generative model's internal knowledge, the backend retrieves semantically relevant chunks from the ingested document and includes them as context in prompts to the LLM. This increases factual accuracy and ensures generated MCQs align with the source document.

---

## Example user flows

**Ingest a book**

1. User (admin/student) logs in.
2. Navigate to Upload / Ingest page and choose either single chapter, multiple chapters or full book upload.
3. Click "Ingest" — backend splits the PDF into chunks, creates embeddings, upserts to Pinecone, and saves chunk metadata to the DB.
4. Ingestion status toast is shown and the new book appears in the uploaded books list.

**Generate a quiz**

1. User selects an ingested book, chapter(s) or whole book, difficulty, no. of questions and chooses "Generate Quiz".
2. Backend retrieves relevant chunks using the query embedding and calls the configured LLM (Gemini or OpenAI) with a templated prompt.
3. LLM returns a structured quiz (questions, options, correct answers, explanations). Backend saves the generated quiz.

**Student attempts a quiz**

1. Student logs in and opens a quiz.
2. The quiz UI presents paginated questions.
3. Student submits answers and receives a graded result and AI-generated explanations for each question.
4. Results are saved and can be viewed later in the results's history.

**Admin deletes a book / quiz**

1. Admin logs in and navigates to the uploaded books / quiz list.
2. Admin clicks delete — backend removes DB metadata and optionally purges entries from the vector DB.

---

## Running locally (development)

### Prerequisites

* Python 3.10+ and pip
* Node 18+ and npm/yarn
* MySQL (Aiven or local instance) — connection URL
* Pinecone account or a local vector DB
* Hugging Face Inference API token for embeddings (or alternative embedding provider)
* LLM provider API key (Gemini or OpenAI)

### Backend (mcq-backend)

1. `cd mcq-backend`
2. Create and activate virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .\.venv\Scripts\activate   # Windows (PowerShell)
   ```
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
4. Create `.env` at the project root (see template below).
5. Start the backend:

   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
6. On startup, the app will attempt to create DB tables automatically (dev convenience).

### Frontend (mcq-ui)

1. `cd mcq-ui`
2. Install node deps:

   ```bash
   npm install
   # or
   yarn
   ```
3. Create `.env` / `.env.local` with `VITE_API_BASE_URL` (see template below).
4. Start dev server:

   ```bash
   npm run dev
   ```
5. Open the Vite dev URL (default `http://localhost:5173`) and use the UI.

---

## `.env` templates

### Backend `.env`

```env
# Database
DATABASE_URL=mysql://<user>:<password>@<host>:<port>/<dbname>
MYSQL_CONNECT_TIMEOUT=30
MYSQL_INIT_TIMEZONE=+05:30

# JWT
SECRET_KEY=your_jwt_secret_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Pinecone (or local vectordb)
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=mcq_index

# Optional runtime limits
CONTEXT_CHAR_LIMIT=4000
CHUNK_SIZE=400
CHUNK_OVERLAP=50

# Hugging Face Embeddings
HF_API_TOKEN=your_hf_api_token
HF_EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
HF_USE_INFERENCE_API=true
HF_BATCH_SIZE=8
HF_TIMEOUT=60
HF_MAX_RETRIES=3

# LLM Provider (choose one or supply both)
GEMINI_API_KEY=your_gemini_api_key_or_empty
OPENAI_API_KEY=your_openai_api_key_or_empty

# Operational
LOG_LEVEL=INFO
```

**Important notes:**

* `PINECONE_DIMENSIONS` should be `384` to match `all-MiniLM-L6-v2` embeddings.
* The backend code normalizes `DATABASE_URL` for async MySQL by replacing `mysql://` with `mysql+asyncmy://` at runtime; you can safely provide a standard MySQL connection string.
* Admin accounts are not created through the public register route. Seed admin users directly into the DB.

### Frontend `.env` (place in `mcq-ui/.env`)

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## Where to look in the codebase (quick map)

* `mcq-backend/app/auth.py` — login/register, JWT creation/verification, admin guard
* `mcq-backend/app/database.py` — DB connection helpers and `DATABASE_URL` normalization
* `mcq-backend/app/vectordb_pinecone.py` — chunking, HF embeddings, Pinecone upsert and query
* `mcq-backend/app/routes/books.py` — ingestion endpoints and book management
* `mcq-backend/app/routes/quizzes.py` — quiz generation and submission
* `mcq-ui/src/api.ts` — Axios client, baseURL, and token handling
* `mcq-ui/src/contexts/AuthContext.tsx` — frontend auth lifecycle
* `mcq-ui/src/pages/*` — ingestion, generate quiz, quiz view, results, admin pages

---
