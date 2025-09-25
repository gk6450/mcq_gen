import os
import io
import uuid
import hashlib
import random
import time
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
import anyio
import numpy as np
import pdfplumber

from sqlalchemy import select, delete
from app.database import AsyncSessionLocal
from app import models
from app.logger import get_logger

# huggingface client (sync)
from huggingface_hub import InferenceClient

try:
    PINECONE_AVAILABLE = True
except Exception:
    PINECONE_AVAILABLE = False

load_dotenv()
logger = get_logger()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX_NAME")
HF_USE_INFERENCE_API = os.getenv("HF_USE_INFERENCE_API", "true").lower() in ("1", "true")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

# default embedding model (fast and reliable)
HF_EMBED_MODEL = os.getenv("HF_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "400"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# tuning env vars
HF_BATCH_SIZE = int(os.getenv("HF_BATCH_SIZE", "8"))
HF_TIMEOUT = int(os.getenv("HF_TIMEOUT", "60"))
HF_MAX_RETRIES = int(os.getenv("HF_MAX_RETRIES", "3"))

if HF_USE_INFERENCE_API and not HF_API_TOKEN:
    logger.warning("HF_USE_INFERENCE_API is set but HF_API_TOKEN is missing")

# Initialize Pinecone client if available
pc = None
if PINECONE_AVAILABLE:
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        logger.info("Initialized Pinecone client")
    except Exception as e:
        logger.exception("Failed to initialize Pinecone client: %s", e)
        pc = None

# ---------- Helpers ----------
def compute_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

def extract_text_from_pdf_bytes_sync(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    logger.debug("extract_text_from_pdf_bytes_sync: starting extraction")
    pages = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, p in enumerate(pdf.pages):
            txt = p.extract_text() or ""
            pages.append({"page": i+1, "text": txt})
    logger.debug("PDF extraction complete: pages=%d", len(pages))
    return pages

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    tokens = text.split()
    if not tokens:
        return []
    chunks = []
    i = 0
    while i < len(tokens):
        chunk_tokens = tokens[i:i+chunk_size]
        chunks.append(" ".join(chunk_tokens))
        i += chunk_size - overlap
    return chunks

def prepare_chunks_from_pdf_sync(pdf_bytes: bytes, book_id: str, chapters: Optional[List[Dict[str, Any]]] = None):
    logger.debug("Preparing chunks for book_id=%s", book_id)
    pages = extract_text_from_pdf_bytes_sync(pdf_bytes)
    prepared = []
    for p in pages:
        page_no = p["page"]
        text = p["text"]
        if not text.strip():
            continue
        page_chunks = chunk_text(text)
        chapter_name = "full"
        if chapters:
            for ch in chapters:
                s = int(ch.get("start_page", 1))
                e = int(ch.get("end_page", s))
                if s <= page_no <= e:
                    chapter_name = ch.get("name", f"Chapter_{s}-{e}")
                    break
        for idx, c in enumerate(page_chunks):
            cid = str(uuid.uuid4())
            chash = compute_hash(c)
            prepared.append({
                "chunk_id": cid,
                "book_id": book_id,
                "chapter_name": chapter_name,
                "page": page_no,
                "chunk_index": idx,
                "text": c,
                "chunk_hash": chash
            })
    logger.debug("Prepared %d chunks for book_id=%s", len(prepared), book_id)
    return prepared

# ---------- Robust HF embeddings ----------
def _coerce_to_vector(item) -> List[float]:
    """
    Convert a single response item (list/tuple/ndarray/dict) to a 1D python list of floats.
    """
    # dict with embedding(s)
    if isinstance(item, dict):
        if "embedding" in item:
            arr = np.array(item["embedding"], dtype=float)
            return arr.flatten().tolist()
        if "embeddings" in item:
            arr = np.array(item["embeddings"], dtype=float)
            if arr.ndim == 1:
                return arr.flatten().tolist()
            if arr.ndim == 2 and arr.shape[0] == 1:
                return arr[0].flatten().tolist()
            return arr.flatten().tolist()
    # ndarray or list-like
    try:
        arr = np.array(item, dtype=float)
        if arr.ndim == 1:
            return arr.flatten().tolist()
        if arr.ndim == 2 and arr.shape[0] == 1:
            return arr[0].flatten().tolist()
        # flatten otherwise
        return arr.flatten().tolist()
    except Exception:
        if isinstance(item, (list, tuple)):
            return [float(x) for x in item]
        raise RuntimeError("Unable to coerce HF response item into vector")

def _hf_request_embeddings_sync(texts: List[str], model: str = HF_EMBED_MODEL) -> List[List[float]]:
    """
    Request embeddings with batching, normalization and retries.
    Normalizes all reasonable HF response shapes into one embedding per input.
    """
    if not texts:
        return []

    if not HF_API_TOKEN:
        raise RuntimeError("HF_API_TOKEN is not set; cannot request embeddings")

    client = InferenceClient(model=model, api_key=HF_API_TOKEN, timeout=HF_TIMEOUT)
    all_embeddings: List[List[float]] = []
    logger.debug("HF embeddings request: model=%s texts=%d batch_size=%d timeout=%s", model, len(texts), HF_BATCH_SIZE, HF_TIMEOUT)

    for i in range(0, len(texts), HF_BATCH_SIZE):
        batch = texts[i:i + HF_BATCH_SIZE]
        attempt = 0
        while True:
            try:
                resp = client.feature_extraction(batch)  # sync call to HF
                # debug logging: show shape/type info for diagnosis
                resp_type = type(resp)
                try:
                    resp_len = len(resp)
                except Exception:
                    resp_len = None
                arr_shape = None
                try:
                    arr = np.array(resp, dtype=float)
                    arr_shape = arr.shape
                except Exception:
                    arr = None
                logger.debug("HF resp for batch %d-%d type=%s len=%s arr_shape=%s", i, i+len(batch)-1, resp_type, resp_len, arr_shape)

                # CASE A: list/tuple with per-input items
                if isinstance(resp, (list, tuple)) and len(resp) == len(batch):
                    for item in resp:
                        vec = _coerce_to_vector(item)
                        all_embeddings.append(vec)
                    break

                # CASE B: numpy-like arr already computed
                if arr is not None:
                    if arr.ndim == 2 and arr.shape[0] == len(batch):
                        for row in arr:
                            all_embeddings.append(np.array(row).flatten().tolist())
                        break
                    if arr.ndim == 1:
                        if len(batch) == 1:
                            all_embeddings.append(arr.flatten().tolist())
                            break
                        # If arr.size divisible by batch: reshape attempt
                        if arr.size % len(batch) == 0:
                            dim = arr.size // len(batch)
                            try:
                                reshaped = arr.reshape(len(batch), dim)
                                for row in reshaped:
                                    all_embeddings.append(row.flatten().tolist())
                                break
                            except Exception:
                                pass
                        # fallback: repeat single vector for each input (logged)
                        logger.warning("HF returned single 1D vector for multi-input batch %d-%d; repeating it for each input", i, i+len(batch)-1)
                        for _ in batch:
                            all_embeddings.append(arr.flatten().tolist())
                        break

                # CASE C: list/tuple but len != batch (maybe nested candidates)
                if isinstance(resp, (list, tuple)):
                    flattened = []
                    for item in resp:
                        try:
                            vec = _coerce_to_vector(item)
                            flattened.append(vec)
                        except Exception:
                            continue
                    if len(flattened) == len(batch):
                        all_embeddings.extend(flattened)
                        break
                    if len(flattened) == 1 and len(batch) > 1:
                        logger.warning("HF returned single vector inside list for batch %d-%d; repeating", i, i+len(batch)-1)
                        for _ in batch:
                            all_embeddings.append(flattened[0])
                        break

                # CASE D: dict with 'embeddings' or 'embedding'
                if isinstance(resp, dict):
                    if "embeddings" in resp:
                        try:
                            emb_arr = np.array(resp["embeddings"], dtype=float)
                            if emb_arr.ndim == 2 and emb_arr.shape[0] == len(batch):
                                for row in emb_arr:
                                    all_embeddings.append(row.flatten().tolist())
                                break
                            if emb_arr.ndim == 1 and len(batch) == 1:
                                all_embeddings.append(emb_arr.flatten().tolist())
                                break
                        except Exception:
                            pass
                    if "embedding" in resp:
                        try:
                            emb_arr = np.array(resp["embedding"], dtype=float)
                            if emb_arr.ndim == 1 and len(batch) == 1:
                                all_embeddings.append(emb_arr.flatten().tolist())
                                break
                            if emb_arr.ndim == 2 and emb_arr.shape[0] == len(batch):
                                for row in emb_arr:
                                    all_embeddings.append(row.flatten().tolist())
                                break
                        except Exception:
                            pass

                # If we get here, we couldn't confidently coerce -> treat as transient and retry
                raise RuntimeError(f"Unrecognized HF response format for batch {i}-{i+len(batch)-1}. resp_type={resp_type} resp_len={resp_len} arr_shape={arr_shape}")

            except Exception as e:
                attempt += 1
                logger.warning("HF embeddings error attempt %d/%d for batch %d-%d: %s", attempt, HF_MAX_RETRIES, i, i+len(batch)-1, str(e))
                if attempt > HF_MAX_RETRIES:
                    logger.exception("Exceeded HF_MAX_RETRIES=%d; aborting for batch %d-%d", HF_MAX_RETRIES, i, i+len(batch)-1)
                    raise
                backoff = (2 ** (attempt - 1)) + random.random()
                logger.info("Retrying HF embeddings after %.2fs", backoff)
                time.sleep(backoff)
                continue

    # final sanity check
    if len(all_embeddings) != len(texts):
        logger.error("Embedding count mismatch: expected=%d got=%d", len(texts), len(all_embeddings))
        raise RuntimeError("Embedding generation returned mismatched number of vectors")
    logger.debug("Embeddings generation complete: total=%d model=%s", len(all_embeddings), model)
    return all_embeddings

# ---------- Pinecone helpers (sync) ----------
def _ensure_index_exists_sync(dim: int):
    if pc is None:
        raise RuntimeError("Pinecone client not initialized. Set PINECONE_API_KEY and pinecone package.")
    if not pc.has_index(PINECONE_INDEX):
        logger.info("Creating Pinecone index %s dim=%d", PINECONE_INDEX, dim)
        pc.create_index(
            name=PINECONE_INDEX,
            dimension=dim,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
    return pc.Index(PINECONE_INDEX)

def _upsert_vectors_sync(upserts: List[Dict[str, Any]]):
    if pc is None:
        raise RuntimeError("Pinecone client not initialized.")
    index = pc.Index(PINECONE_INDEX)
    BATCH = 128
    logger.debug("Upserting %d vectors to Pinecone in batches", len(upserts))
    for j in range(0, len(upserts), BATCH):
        batch = upserts[j:j+BATCH]
        index.upsert(vectors=batch)
    logger.info("Upsert to Pinecone finished: total=%d", len(upserts))

def _query_index_sync(qvec: List[float], top_k: int, filt: Optional[Dict[str, Any]] = None):
    if pc is None:
        raise RuntimeError("Pinecone client not initialized.")
    index = pc.Index(PINECONE_INDEX)
    logger.debug("Querying Pinecone top_k=%s filter=%s", top_k, bool(filt))
    if filt:
        resp = index.query(vector=qvec, top_k=top_k, include_metadata=True, filter=filt)
    else:
        resp = index.query(vector=qvec, top_k=top_k, include_metadata=True)
    matches = resp.get("matches", []) or resp.get("results", [])
    logger.debug("Pinecone query returned %d matches", len(matches))
    return matches

def _delete_by_filter_sync(book_id: str):
    if pc is None:
        raise RuntimeError("Pinecone client not initialized.")
    index = pc.Index(PINECONE_INDEX)
    index.delete(filter={"book_id": {"$eq": book_id}})
    logger.info("Pinecone vectors deleted for book_id=%s", book_id)
    return True

# ---------- Async wrappers and top-level functions ----------
async def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    return await anyio.to_thread.run_sync(extract_text_from_pdf_bytes_sync, pdf_bytes)

async def prepare_chunks_from_pdf(pdf_bytes: bytes, book_id: str, chapters: Optional[List[Dict[str, Any]]] = None):
    return await anyio.to_thread.run_sync(prepare_chunks_from_pdf_sync, pdf_bytes, book_id, chapters)

async def upsert_book_to_pinecone(book_id: str, pdf_bytes: bytes, chapters: Optional[List[Dict[str,Any]]] = None):
    logger.info("Upsert book to pinecone started: book_id=%s", book_id)
    prepared = await anyio.to_thread.run_sync(prepare_chunks_from_pdf_sync, pdf_bytes, book_id, chapters)
    if not prepared:
        logger.info("No chunks prepared for book_id=%s", book_id)
        return {"book_id": book_id, "inserted": 0, "skipped": 0}

    async with AsyncSessionLocal() as db:
        q = await db.execute(select(models.Chunk.chunk_hash).where(models.Chunk.book_id == book_id))
        existing_hashes = set(q.scalars().all())
    logger.debug("Found %d existing chunk_hashes for book_id=%s", len(existing_hashes), book_id)

    to_index = [p for p in prepared if p["chunk_hash"] not in existing_hashes]
    skipped = len(prepared) - len(to_index)
    logger.info("Prepared chunks=%d to_index=%d skipped=%d for book_id=%s", len(prepared), len(to_index), skipped, book_id)

    if not to_index:
        return {"book_id": book_id, "inserted": 0, "skipped": skipped}

    texts = [p["text"] for p in to_index]

    # Generate embeddings in thread
    embeddings = await anyio.to_thread.run_sync(_hf_request_embeddings_sync, texts)
    if not embeddings or len(embeddings) != len(texts):
        logger.error("Embedding generation failed or returned mismatched length")
        raise RuntimeError("Embedding generation returned mismatched number of vectors")

    dim = len(embeddings[0])
    await anyio.to_thread.run_sync(_ensure_index_exists_sync, dim)

    upserts = []
    for i, p in enumerate(to_index):
        meta = {
            "book_id": book_id,
            "chapter_name": p["chapter_name"],
            "page": p["page"],
            "chunk_index": p["chunk_index"],
            "text_preview": p["text"][:800]
        }
        upserts.append({"id": p["chunk_id"], "values": embeddings[i], "metadata": meta})

    await anyio.to_thread.run_sync(_upsert_vectors_sync, upserts)

    async with AsyncSessionLocal() as db:
        for p in to_index:
            chunk = models.Chunk(
                chunk_id=p["chunk_id"],
                book_id=book_id,
                chapter_name=p["chapter_name"],
                page=p["page"],
                chunk_index=p["chunk_index"],
                chunk_hash=p["chunk_hash"],
                full_text=p["text"]
            )
            db.add(chunk)
        await db.commit()
    logger.info("Inserted %d new chunks into Postgres for book_id=%s", len(to_index), book_id)
    return {"book_id": book_id, "inserted": len(to_index), "skipped": skipped}

async def retrieve_relevant_chunks(scope_book_id: str, scope_chapter: Optional[Union[str, List[str]]], query: str, top_k: int = 8):
    logger.debug("retrieve_relevant_chunks: book_id=%s chapter=%s query_len=%d", scope_book_id, scope_chapter, len(query))
    q_embs = await anyio.to_thread.run_sync(_hf_request_embeddings_sync, [query])
    if not q_embs:
        logger.warning("No embedding returned for query")
        return []
    qvec = q_embs[0]
    filt = {"book_id": {"$eq": scope_book_id}}
    if scope_chapter:
        if isinstance(scope_chapter, list):
            filt["chapter_name"] = {"$in": [str(x) for x in scope_chapter]}
        else:
            filt["chapter_name"] = {"$eq": str(scope_chapter)}

    matches = await anyio.to_thread.run_sync(_query_index_sync, qvec, top_k, filt)
    if not matches:
        logger.debug("Filtered query returned no matches, trying unfiltered")
        matches = await anyio.to_thread.run_sync(_query_index_sync, qvec, top_k, None)
        if not matches:
            logger.info("No matches found for query")
            return []

    chunk_ids = [m.get("id") if isinstance(m, dict) else getattr(m, "id", None) for m in matches]
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(models.Chunk).where(models.Chunk.chunk_id.in_(chunk_ids)))
        rows = r.scalars().all()
        mapping = {row.chunk_id: row.full_text for row in rows}

    results = []
    for m in matches:
        if isinstance(m, dict):
            cid = m.get("id")
            score = m.get("score")
            metadata = m.get("metadata", {}) or {}
        else:
            cid = getattr(m, "id", None)
            score = getattr(m, "score", None)
            metadata = getattr(m, "metadata", {}) or {}
        full_text = mapping.get(cid, metadata.get("text_preview", ""))
        results.append({"chunk_id": cid, "score": score, "metadata": metadata, "full_text": full_text})
    logger.debug("Returning %d relevant chunks", len(results))
    return results

async def list_chapters_for_book(book_id: str) -> List[str]:
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(models.Chunk.chapter_name).where(models.Chunk.book_id == book_id).distinct())
        rows = r.scalars().all()
    chapters = sorted([r for r in rows if r])
    logger.debug("Chapters for book_id=%s : %s", book_id, chapters)
    return chapters

async def delete_book_from_pinecone(book_id: str):
    logger.info("delete_book_from_pinecone called for book_id=%s", book_id)
    try:
        await anyio.to_thread.run_sync(_delete_by_filter_sync, book_id)
        logger.info("Pinecone vectors deleted for book_id=%s", book_id)
    except Exception as e:
        logger.exception("Pinecone deletion error for book_id=%s: %s", book_id, e)
    async with AsyncSessionLocal() as db:
        await db.execute(delete(models.Chunk).where(models.Chunk.book_id == book_id))
        await db.commit()
    logger.info("Postgres chunk rows deleted for book_id=%s", book_id)
    return True
