"""
CuraMind Embedding Provider Layer — LangChain-backed implementation.

LANGCHAIN RESPONSIBILITY:
  - Embedding model instantiation (GoogleGenerativeAIEmbeddings, OpenAIEmbeddings)
  - HTTP transport to the embedding API
  - Batch embedding via .embed_documents()
  - Single-text embedding via .embed_query()

CURAMIND RESPONSIBILITY:
  - Provider selection logic (env-var driven factory)
  - Dimension enforcement (1536 dims expected by pgvector schema)
  - Fallback to DeterministicMockEmbeddingProvider when no API key available
  - Padding/truncating vectors to maintain schema compatibility

Authorization context is NEVER passed through the embedding layer;
all security filtering happens at the SQL retrieval layer (postgres.py,
retrieval.py) — embeddings only convert text to vectors.
"""

import abc
import hashlib
import logging
import math
from typing import List, Optional

from app.config import settings

logger = logging.getLogger("rag_service.embeddings")

# Target vector dimension expected by the pgvector schema (vector(1536))
_TARGET_DIM: int = 1536


def _pad_or_truncate(vec: List[float], target: int = _TARGET_DIM) -> List[float]:
    """Ensure vector has exactly `target` dimensions.

    - If the provider returns more dims, truncate and renormalize.
    - If fewer dims, zero-pad and renormalize.

    This is a safety guard so a provider returning 768-dim or 3072-dim
    vectors never corrupts the pgvector column.
    """
    if len(vec) == target:
        return vec

    if len(vec) > target:
        vec = vec[:target]
    else:
        vec = vec + [0.0] * (target - len(vec))

    # Re-normalize to unit length after resize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0.0:
        vec = [round(x / norm, 6) for x in vec]
    return vec


# ---------------------------------------------------------------------------
# Abstract base — kept exactly as before so tests and callers are unaffected
# ---------------------------------------------------------------------------

class EmbeddingProvider(abc.ABC):
    @abc.abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for single text snippet."""
        pass

    @abc.abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a batch of text chunks."""
        pass


# ---------------------------------------------------------------------------
# Mock — deterministic, no network, for tests and offline mode
# ---------------------------------------------------------------------------

class DeterministicMockEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic Mock Embedding Provider with semantic clustering.
    Produces unit-normalized 1536-dimensional vectors based on word tokens
    ensuring semantic similarity search works reliably without external API keys.
    No LangChain dependency; always available as fallback.
    """
    DIMENSION: int = _TARGET_DIM

    def _generate_vector(self, text: str) -> List[float]:
        vec = [0.0] * self.DIMENSION
        cleaned = text.lower().strip()
        words = cleaned.split()

        if not words:
            vec[0] = 1.0
            return vec

        for word in words:
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
            idx1 = h % self.DIMENSION
            idx2 = (h >> 16) % self.DIMENSION
            idx3 = (h >> 32) % self.DIMENSION
            vec[idx1] += 1.0
            vec[idx2] += 0.5
            vec[idx3] += 0.25

        full_h = int(hashlib.sha256(cleaned.encode("utf-8")).hexdigest(), 16)
        for i in range(16):
            pos = (full_h + i * 97) % self.DIMENSION
            vec[pos] += 0.1

        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0.0:
            vec[0] = 1.0
            return vec
        return [round(x / norm, 6) for x in vec]

    def embed_text(self, text: str) -> List[float]:
        return self._generate_vector(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self._generate_vector(t) for t in texts]


# ---------------------------------------------------------------------------
# LangChain-backed Gemini embedding provider
# ---------------------------------------------------------------------------

class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Google Gemini text embedding provider backed by LangChain's
    GoogleGenerativeAIEmbeddings.

    LangChain handles:
      - HTTP transport to the Gemini embedding API
      - Batch embedding via .embed_documents()
      - Query embedding via .embed_query()

    CuraMind handles:
      - Dim enforcement (pad/truncate to 1536 for pgvector schema safety)
      - Fallback to DeterministicMockEmbeddingProvider on error
    """

    def __init__(self, api_key: str, model: str = "text-embedding-004"):
        self.api_key = api_key
        self.model = model
        self._lc_embedder = None

    def _get_lc_embedder(self):
        if self._lc_embedder is None:
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings
                self._lc_embedder = GoogleGenerativeAIEmbeddings(
                    model=f"models/{self.model}",
                    google_api_key=self.api_key,
                )
            except Exception as e:
                logger.error(f"Failed to initialise GoogleGenerativeAIEmbeddings: {e}")
        return self._lc_embedder

    def embed_text(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required for Gemini embeddings")

        lc = self._get_lc_embedder()
        if lc is None:
            raise RuntimeError("Could not initialize the configured Gemini embedding model")

        try:
            raw = lc.embed_documents(texts)
            if len(raw) == len(texts):
                return [_pad_or_truncate(v) for v in raw]
            raise RuntimeError("Gemini embedding provider returned a mismatched vector count")
        except Exception as e:
            logger.error(f"Gemini embedding call failed: {e}")
            raise RuntimeError("Gemini embedding generation failed") from e


# ---------------------------------------------------------------------------
# LangChain-backed OpenAI embedding provider
# ---------------------------------------------------------------------------

class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI text embedding provider backed by LangChain's OpenAIEmbeddings.
    Also supports any OpenAI-compatible endpoint via LLM_BASE_URL.

    LangChain handles:
      - HTTP transport
      - Batch embedding via .embed_documents()
      - Query embedding via .embed_query()

    CuraMind handles:
      - Dim enforcement (pad/truncate to 1536)
      - Fallback to DeterministicMockEmbeddingProvider on error
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._lc_embedder = None

    def _get_lc_embedder(self):
        if self._lc_embedder is None:
            try:
                from langchain_openai import OpenAIEmbeddings
                kwargs = dict(model=self.model, api_key=self.api_key)
                if self.base_url:
                    kwargs["openai_api_base"] = self.base_url
                self._lc_embedder = OpenAIEmbeddings(**kwargs)
            except Exception as e:
                logger.error(f"Failed to initialise OpenAIEmbeddings: {e}")
        return self._lc_embedder

    def embed_text(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI-compatible embeddings")

        lc = self._get_lc_embedder()
        if lc is None:
            raise RuntimeError("Could not initialize the configured OpenAI embedding model")

        try:
            raw = lc.embed_documents(texts)
            if len(raw) == len(texts):
                return [_pad_or_truncate(v) for v in raw]
            raise RuntimeError("OpenAI embedding provider returned a mismatched vector count")
        except Exception as e:
            logger.error(f"OpenAI embedding call failed: {e}")
            raise RuntimeError("OpenAI embedding generation failed") from e


# ---------------------------------------------------------------------------
# Factory — env-var driven, provider-agnostic
# ---------------------------------------------------------------------------

def get_embedding_provider() -> EmbeddingProvider:
    """
    Returns the correct embedding provider based on environment variables.

    Priority:
      1. mock    — if EMBEDDING_PROVIDER is explicitly set to "mock"
      2. gemini  — when EMBEDDING_PROVIDER="gemini" or (EMBEDDING_PROVIDER not set and GEMINI_API_KEY is present)
      3. openai  — when EMBEDDING_PROVIDER="openai" and OPENAI_API_KEY is set
      4. mock    — fallback for tests / offline execution

    The pgvector schema stores vector(1536); all providers enforce this
    dimension via _pad_or_truncate() so the schema is never broken by a
    provider returning a different native dimension.
    """
    if settings.EMBEDDING_PROVIDER == "mock":
        return DeterministicMockEmbeddingProvider()

    gemini_key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
    if settings.EMBEDDING_PROVIDER == "gemini":
        if not gemini_key:
            raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required for EMBEDDING_PROVIDER=gemini")
        return GeminiEmbeddingProvider(api_key=gemini_key, model=settings.GEMINI_EMBEDDING_MODEL)

    if settings.EMBEDDING_PROVIDER == "openai":
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is required for EMBEDDING_PROVIDER=openai")
        return OpenAIEmbeddingProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.EMBEDDING_MODEL,
            base_url=settings.LLM_BASE_URL,  # reuse base_url for APInex-compatible embedding endpoints
        )

    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {settings.EMBEDDING_PROVIDER}")
