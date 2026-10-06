"""
summarize_and_compare.py
────────────────────────
Full RAG pipeline for ad-hoc document uploads:

  Upload → Extract text → Chunk (LangChain RecursiveCharacterTextSplitter)
         → Embed every chunk (Gemini / OpenAI / deterministic mock)
         → In-memory semantic search (cosine similarity)         ← NEW
         → In-memory keyword search (BM25-style TF-IDF)          ← NEW
         → Reciprocal Rank Fusion (RRF) hybrid reranking         ← NEW
         → Top-K relevant chunks → LLM generation

Design constraints (curamind-scoped-langchain-constraint):
  - LangChain is ONLY used for text splitting (via ingestion.chunk_text).
  - Retrieval, embedding, ranking, and LLM calls are plain Python.
"""
import logging
import math
import re
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from app.services.ingestion import chunk_text, extract_text_from_raw
from app.services.embeddings import get_embedding_provider
from app.services.llm import get_llm_provider

logger = logging.getLogger("rag_service.summarize_and_compare")

# ─────────────────────────────────────────────────────────────────────────────
# System prompts
# ─────────────────────────────────────────────────────────────────────────────

SUMMARISE_SYSTEM_PROMPT = """
You are the CuraMind Clinical Document Summarisation AI.
Produce a concise, accurate clinical summary grounded ONLY in the retrieved context below.

Required sections (use ## headings):
## Chief Complaint
## Diagnoses
## Key Clinical Findings
## Medications & Treatments
## Laboratory / Imaging Results
## Follow-Up Plan
## Clinical Impression  ← one sentence

Rules:
- Flag contradictions, missing data, or abnormal values with ⚠️.
- If a field is absent, write: "Not documented."
- Do NOT infer or assume beyond what is written.
"""

COMPARE_AI_SYSTEM_PROMPT = """
You are the CuraMind Clinical Document Comparison AI.
You are given retrieved passages from two clinical documents (Document A and Document B).

Required output (use ## headings):
## Chief Complaint        — SAME / DIFFERENT / ONLY IN A / ONLY IN B + explanation
## Diagnoses              — SAME / DIFFERENT / ONLY IN A / ONLY IN B + explanation
## Medications            — SAME / DIFFERENT / ONLY IN A / ONLY IN B + explanation
## Vitals & Labs          — SAME / DIFFERENT / ONLY IN A / ONLY IN B + explanation
## Outcomes / Follow-Up   — SAME / DIFFERENT / ONLY IN A / ONLY IN B + explanation
## Clinically Significant Discrepancies  — list each with ⚠️
## Overall AI Comparison Summary         — 2-3 sentences

Rules:
- Flag discrepancies with ⚠️.
- Base analysis ONLY on the provided passages. Do not infer.
"""

QUERY_ANSWER_SYSTEM_PROMPT = """
You are the CuraMind Clinical Assistant.
Answer the clinician's question using ONLY the retrieved document passages below.

Rules:
1. Cite the source page for every key assertion, e.g. (Page 2).
2. If the answer is not in the passages, state: "Not found in the provided document."
3. NEVER diagnose, prescribe, or give clinical advice beyond what is documented.
4. Flag abnormal values, contradictions, or missing data with ⚠️.
"""

# ─────────────────────────────────────────────────────────────────────────────
# In-memory RAG pipeline (embed → semantic search → keyword search → RRF)
# ─────────────────────────────────────────────────────────────────────────────

def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Pure-Python cosine similarity between two unit-normalised vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


def _tokenize(text: str) -> List[str]:
    """Simple whitespace + punctuation tokenizer for keyword scoring."""
    return re.findall(r'\b\w{2,}\b', text.lower())


STOP_WORDS = {
    "a","an","the","and","or","but","if","then","for","with","at","from",
    "by","to","of","in","on","is","are","was","were","be","been","has","have",
    "not","it","its","this","that","these","those","which","who","what","how",
    "all","any","each","so","than","do","did","does","no","nor","only","own",
    "can","will","just","should","now","also","as","up","down","out","about",
}


def _bm25_scores(query_tokens: List[str], chunks: List[Dict[str, Any]],
                 k1: float = 1.2, b: float = 0.75) -> List[float]:
    """
    BM25 keyword relevance scores for all chunks against query tokens.
    Returns a list of float scores aligned to the input chunks list.
    """
    if not chunks or not query_tokens:
        return [0.0] * len(chunks)

    # Build corpus term frequencies and document lengths
    tf_corpus = []
    df = defaultdict(int)
    doc_lengths = []

    for ch in chunks:
        tokens = _tokenize(ch.get("chunk_text", ""))
        tf = defaultdict(int)
        for t in tokens:
            if t not in STOP_WORDS:
                tf[t] += 1
        tf_corpus.append(tf)
        doc_lengths.append(len(tokens))
        for t in tf:
            df[t] += 1

    N = len(chunks)
    avg_dl = sum(doc_lengths) / N if N else 1.0
    query_terms = [t for t in query_tokens if t not in STOP_WORDS]

    scores = []
    for i, tf in enumerate(tf_corpus):
        dl = doc_lengths[i]
        score = 0.0
        for term in query_terms:
            f = tf.get(term, 0)
            idf = math.log((N - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5) + 1)
            numerator = f * (k1 + 1)
            denominator = f + k1 * (1 - b + b * dl / avg_dl)
            score += idf * (numerator / denominator if denominator else 0)
        scores.append(score)
    return scores


def _rrf_fuse(semantic_ranks: List[int], keyword_ranks: List[int],
              n: int, rrf_k: int = 60) -> List[Tuple[int, float]]:
    """
    Reciprocal Rank Fusion (RRF).
    Returns list of (original_index, fused_score) sorted descending.
    """
    scores = defaultdict(float)
    for rank, idx in enumerate(semantic_ranks):
        scores[idx] += 1.0 / (rrf_k + rank + 1)
    for rank, idx in enumerate(keyword_ranks):
        scores[idx] += 1.0 / (rrf_k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def _build_chunk_index(chunks: List[Dict[str, Any]]) -> Tuple[List[List[float]], List[Dict]]:
    """
    Embed all chunks in batch and return (embeddings, enriched_chunks).
    This runs the full RAG embedding step on the in-memory chunk list.
    """
    provider = get_embedding_provider()
    texts = [c["chunk_text"] for c in chunks]
    embeddings = provider.embed_batch(texts)
    return embeddings, chunks


def retrieve_relevant_chunks(
    query: str,
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
    top_k: int = 8,
) -> List[Dict[str, Any]]:
    """
    Full in-memory hybrid retrieval:
      1. Embed query
      2. Cosine similarity semantic ranking
      3. BM25 keyword ranking
      4. RRF fusion
      5. Return top_k chunks

    This is the same algorithm as the PostgreSQL hybrid search used for
    stored documents, executed in-memory for ad-hoc uploads.
    """
    if not chunks:
        return []

    provider = get_embedding_provider()
    query_emb = provider.embed_text(query)
    query_tokens = _tokenize(query)

    # 1. Semantic scores → ranked indices
    semantic_scores = [_cosine_similarity(query_emb, emb) for emb in embeddings]
    semantic_ranked = sorted(range(len(chunks)), key=lambda i: semantic_scores[i], reverse=True)

    # 2. BM25 keyword scores → ranked indices
    kw_scores = _bm25_scores(query_tokens, chunks)
    keyword_ranked = sorted(range(len(chunks)), key=lambda i: kw_scores[i], reverse=True)

    # 3. RRF fusion
    fused = _rrf_fuse(semantic_ranked, keyword_ranked, n=len(chunks))

    # 4. Top-K
    top_indices = [idx for idx, _ in fused[:top_k]]
    return [
        {**chunks[i], "semantic_score": round(semantic_scores[i], 4)}
        for i in top_indices
    ]


def _retrieved_to_context(retrieved: List[Dict[str, Any]], doc_label: str = "") -> str:
    """Format retrieved chunks as labelled context for the LLM."""
    parts = []
    for ch in retrieved:
        page = ch.get("page_number", "?")
        score = ch.get("semantic_score", "")
        label = f"[{doc_label + ' · ' if doc_label else ''}Page {page}]"
        parts.append(f"{label}\n{ch['chunk_text']}")
    return "\n\n---\n\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def summarise_document(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Full RAG pipeline for a single document:
      Extract → Chunk → Embed → Semantic+Keyword search → Top-K → LLM summary.

    The summarisation query is a comprehensive clinical extraction prompt,
    ensuring the most relevant passages are retrieved before generation.
    """
    logger.info(f"[RAG] Summarising document: {filename}")
    full_text, pages_data = extract_text_from_raw(file_bytes, filename)
    chunks = chunk_text(pages_data, chunk_size=600, chunk_overlap=60)

    if not full_text.strip() or not chunks:
        return {
            "filename": filename,
            "full_text_excerpt": "",
            "chunks_count": 0,
            "summary": "❌ Could not extract readable text from this document.",
        }

    # Build in-memory embedding index
    embeddings, chunks = _build_chunk_index(chunks)

    # Retrieve top-K most relevant chunks via hybrid search
    retrieval_query = (
        "chief complaint diagnosis medications treatments lab results "
        "vitals findings follow-up clinical impression outcome"
    )
    retrieved = retrieve_relevant_chunks(retrieval_query, chunks, embeddings, top_k=10)

    context = _retrieved_to_context(retrieved, doc_label=filename)
    llm = get_llm_provider()
    context_chunks = [{"chunk_text": context, "document_name": filename, "page_number": 1}]

    summary_text = llm.generate_response(
        system_prompt=SUMMARISE_SYSTEM_PROMPT,
        user_prompt=f"Produce a structured clinical summary for '{filename}' using the retrieved passages.",
        context_chunks=context_chunks,
    )

    return {
        "filename": filename,
        "full_text_excerpt": full_text[:800].strip(),
        "chunks_count": len(chunks),
        "retrieved_count": len(retrieved),
        "summary": summary_text,
    }


def compare_uploaded_documents(
    file_a_bytes: bytes,
    filename_a: str,
    file_b_bytes: bytes,
    filename_b: str,
) -> Dict[str, Any]:
    """
    Full RAG pipeline for two documents:
      Each doc: Extract → Chunk → Embed → Hybrid retrieve relevant passages
      Both docs' retrieved passages → LLM comparison.

    Uses two separate retrieval queries (one per category) to ensure
    all comparison dimensions are covered.
    """
    logger.info(f"[RAG] Comparing: {filename_a} vs {filename_b}")

    # Process Document A
    full_a, pages_a = extract_text_from_raw(file_a_bytes, filename_a)
    chunks_a = chunk_text(pages_a, chunk_size=600, chunk_overlap=60)
    embs_a, chunks_a = _build_chunk_index(chunks_a)

    # Process Document B
    full_b, pages_b = extract_text_from_raw(file_b_bytes, filename_b)
    chunks_b = chunk_text(pages_b, chunk_size=600, chunk_overlap=60)
    embs_b, chunks_b = _build_chunk_index(chunks_b)

    # Retrieve top passages from each doc covering all comparison dimensions
    COMPARE_QUERY = (
        "chief complaint diagnosis medications treatment vitals "
        "lab results imaging findings outcomes follow-up plan"
    )
    retrieved_a = retrieve_relevant_chunks(COMPARE_QUERY, chunks_a, embs_a, top_k=8)
    retrieved_b = retrieve_relevant_chunks(COMPARE_QUERY, chunks_b, embs_b, top_k=8)

    context_a = _retrieved_to_context(retrieved_a, doc_label=f"Doc A: {filename_a}")
    context_b = _retrieved_to_context(retrieved_b, doc_label=f"Doc B: {filename_b}")

    combined_context = (
        f"=== DOCUMENT A: {filename_a} ===\n\n{context_a}\n\n"
        f"=== DOCUMENT B: {filename_b} ===\n\n{context_b}"
    )

    llm = get_llm_provider()
    context_chunks = [{"chunk_text": combined_context, "document_name": "Comparison", "page_number": 1}]
    ai_comparison = llm.generate_response(
        system_prompt=COMPARE_AI_SYSTEM_PROMPT,
        user_prompt="Compare the two clinical documents based on the retrieved passages above.",
        context_chunks=context_chunks,
    )

    return {
        "doc_a": {
            "filename": filename_a,
            "full_text_excerpt": full_a[:500].strip(),
            "chunks_count": len(chunks_a),
            "retrieved_count": len(retrieved_a),
        },
        "doc_b": {
            "filename": filename_b,
            "full_text_excerpt": full_b[:500].strip(),
            "chunks_count": len(chunks_b),
            "retrieved_count": len(retrieved_b),
        },
        "ai_comparison": ai_comparison,
    }


def answer_question_about_document(
    question: str,
    file_bytes: bytes,
    filename: str,
    chunks: List[Dict[str, Any]] = None,
    embeddings: List[List[float]] = None,
    top_k: int = 6,
) -> Dict[str, Any]:
    """
    RAG Q&A over a single uploaded document:
      Extract → Chunk → Embed → Hybrid retrieve (semantic + BM25 + RRF)
      → Top-K relevant chunks → LLM answer with page citations.

    Accepts pre-computed chunks/embeddings to allow multiple questions
    over the same document without re-processing.
    """
    logger.info(f"[RAG] Q&A on '{filename}': {question[:80]}")

    if chunks is None or embeddings is None:
        _, pages_data = extract_text_from_raw(file_bytes, filename)
        chunks = chunk_text(pages_data, chunk_size=600, chunk_overlap=60)
        embeddings, chunks = _build_chunk_index(chunks)

    retrieved = retrieve_relevant_chunks(question, chunks, embeddings, top_k=top_k)

    if not retrieved:
        return {
            "answer": "Not found in the provided document.",
            "citations": [],
            "retrieved_count": 0,
        }

    context = _retrieved_to_context(retrieved, doc_label=filename)
    llm = get_llm_provider()
    context_chunks = [{"chunk_text": context, "document_name": filename, "page_number": 1}]

    answer_text = llm.generate_response(
        system_prompt=QUERY_ANSWER_SYSTEM_PROMPT,
        user_prompt=question,
        context_chunks=context_chunks,
    )

    citations = [
        {"page_number": ch.get("page_number"), "snippet": ch["chunk_text"][:120] + "…"}
        for ch in retrieved
    ]

    return {
        "answer": answer_text,
        "citations": citations,
        "retrieved_count": len(retrieved),
    }
