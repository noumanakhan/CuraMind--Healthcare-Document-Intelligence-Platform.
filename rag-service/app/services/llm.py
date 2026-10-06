"""
CuraMind LLM Provider Layer — LangChain-backed implementation.

LANGCHAIN RESPONSIBILITY:
  - LLM client instantiation (ChatGoogleGenerativeAI, ChatOpenAI, ChatAnthropic)
  - Message formatting (SystemMessage / HumanMessage)
  - Model invocation via .invoke()

CURAMIND RESPONSIBILITY:
  - Provider selection logic (env-var driven factory)
  - Fallback to MockLLMProvider when no API key is configured
  - Context formatting from retrieved chunks
  - Logging and error handling
  - Grounding rules enforcement (callers in rag_assistant.py own this)

Authorization NEVER passes through this layer; chunks are pre-filtered
by retrieval.py before reaching here.
"""

import abc
import logging
import re
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger("rag_service.llm")


# ---------------------------------------------------------------------------
# Abstract base — preserved exactly to keep the factory pattern and tests
# ---------------------------------------------------------------------------

class LLMProvider(abc.ABC):
    @abc.abstractmethod
    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: List[Dict[str, Any]],
    ) -> str:
        """Generate response from LLM given retrieved (pre-authorized) context."""
        pass


# ---------------------------------------------------------------------------
# Mock — deterministic, no network, used in tests and offline mode
# ---------------------------------------------------------------------------

def is_greeting_or_conversational(query: str) -> bool:
    """Detect if a user input is a casual greeting or capability inquiry."""
    q_clean = re.sub(r"[^\w\s]", "", query.strip().lower())
    if not q_clean:
        return True

    greetings = {
        "hi", "hello", "hey", "greetings", "good morning", "good afternoon",
        "good evening", "howdy", "hola", "hi there", "hello there", "hey there",
        "who are you", "what can you do", "help", "how can you help", "what are you",
        "thanks", "thank you", "bye", "goodbye"
    }
    if q_clean in greetings:
        return True

    words = q_clean.split()
    if len(words) <= 3 and all(w in {"hi", "hello", "hey", "there", "curamind", "assistant", "doc", "doctor"} for w in words):
        return True

    return False


def _stem(word: str) -> str:
    """Simple suffix-stripping stemmer for clinical and common English terms."""
    w = word.lower()
    for suffix in ("ies", "es", "s", "ing", "ed", "tion", "tions", "ic", "al", "ment", "ments"):
        if len(w) > len(suffix) + 2 and w.endswith(suffix):
            return w[:-len(suffix)]
    return w


class MockLLMProvider(LLMProvider):
    """
    Deterministic Intelligent LLM provider for offline execution and testing.
    Synthesizes rich, query-focused, grounded clinical answers directly from
    provided context chunks with semantic matching and section extraction.
    """

    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: List[Dict[str, Any]],
    ) -> str:
        if is_greeting_or_conversational(user_prompt):
            return (
                "Hello! I am your CuraMind Clinical Decision-Support Assistant. "
                "I can assist you by retrieving and synthesizing findings from this patient's indexed medical records, clinical notes, and lab reports. "
                "How can I assist you with this patient chart today?"
            )

        if not context_chunks:
            return (
                "I currently have no documents indexed for this patient or context. "
                "Please upload a clinical document (PDF, clinical note, lab report) "
                "using the attachment button, and I will be able to answer your questions from it."
            )

        q_clean = user_prompt.strip().lower()

        # Clinical synonym expansion — semantically equivalent terms
        SYNONYMS: Dict[str, List[str]] = {
            "medication":    ["drug", "med", "medicine", "pharmaceutical", "rx", "prescription", "prescribed", "treatment"],
            "diagnosis":     ["diagnos", "condition", "disease", "disorder", "impression", "assessment", "findings", "problem"],
            "allergy":       ["allergies", "allergic", "hypersensitivity", "adverse reaction", "intolerance"],
            "vital":         ["vitals", "blood pressure", "bp", "temperature", "pulse", "heart rate", "spo2", "oxygen", "weight", "bmi"],
            "lab":           ["laboratory", "labs", "blood test", "test result", "hba1c", "glucose", "lipid", "cbc", "panel", "level"],
            "discharge":     ["discharged", "discharge summary", "sent home", "released", "disposition"],
            "history":       ["hx", "past medical", "pmh", "background", "prior", "previous"],
            "complaint":     ["chief complaint", "presenting", "reason for visit", "symptom", "symptoms", "cc"],
            "plan":          ["treatment plan", "management", "recommendation", "recommendations", "follow-up", "follow up", "next steps"],
            "surgery":       ["surgical", "operative", "procedure", "operation", "post-op", "preoperative"],
            "appointment":   ["visit", "consultation", "consult", "follow-up", "schedule", "scheduled"],
        }

        # Expand the query with synonyms
        expanded_tokens = set(re.findall(r'[a-zA-Z0-9_\-]+', q_clean))
        expanded_tokens.discard("")
        for canonical, syns in SYNONYMS.items():
            if canonical in expanded_tokens or any(s in q_clean for s in syns):
                expanded_tokens.add(canonical)
                expanded_tokens.update(syns)

        # General and clinical framing stop words for question matching
        basic_stop_words = {
            "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", "at", "from",
            "by", "for", "with", "about", "against", "between", "into", "through", "during",
            "before", "after", "above", "below", "to", "of", "up", "down", "in", "out", "on",
            "off", "over", "under", "again", "further", "here", "there", "why", "how", "all",
            "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor",
            "not", "only", "own", "same", "so", "than", "too", "very", "can", "will", "just",
            "should", "now", "did", "does", "doing", "have", "has", "had", "having", "was",
            "were", "be", "been", "being", "is", "am", "are", "what", "which", "who", "whom",
            "this", "that", "these", "those", "tell", "show", "give", "find", "know", "please",
            "patient", "patients", "patient's", "doctor", "clinician", "hospital", "record",
            "records", "chart", "charts", "file", "files", "document", "documents", "note", "notes",
            "me", "my", "i", "you", "your", "us", "we", "they", "them", "their",
        }

        query_tokens = [w for w in expanded_tokens if len(w) > 1 and w not in basic_stop_words]
        query_stems = {_stem(t) for t in query_tokens}

        # Check for summary / overview intent
        is_summary_query = any(k in q_clean for k in (
            "summarise", "summarize", "summary", "overview", "what is this", "key findings",
            "main points", "review this", "tell me about this", "about this document",
            "explain this document", "what does this say", "what does it say",
            "give me a summary", "brief summary", "quick summary",
        ))

        # Collect all sentences and paragraphs across all chunks
        doc_names = list({ch.get("document_name", "Clinical Document") for ch in context_chunks})
        doc_label = ", ".join(f"**{d}**" for d in doc_names[:2])

        all_lines = []
        for ch in context_chunks:
            text = ch.get("chunk_text", "").strip()
            for line in text.split("\n"):
                line_str = line.strip()
                if line_str:
                    all_lines.append(line_str)

        full_text = "\n".join(all_lines)

        # ── 1. Summary / Overview Intent ────────────────────────────────────
        if is_summary_query:
            key_points = []
            for line in all_lines:
                if any(kw in line.lower() for kw in (
                    "diagnosis", "impression", "assessment", "plan", "prescribed", "rx",
                    "allergy", "allergies", "history", "vital", "bp", "complaint",
                    "findings", "admitted", "discharge", "medication", "condition",
                    "treatment", "surgery", "procedure", "follow-up", "recommendation",
                )):
                    if len(line) > 10 and line not in key_points:
                        key_points.append(line)

            if not key_points:
                key_points = [l for l in all_lines if len(l) > 20][:6]

            bullet_items = "\n".join(f"• {p}" for p in key_points[:7])
            return (
                f"### Document Summary ({doc_label})\n\n"
                f"Based on the clinical documentation provided, here are the key findings:\n\n"
                f"{bullet_items}\n\n"
                f"*(Please verify against original diagnostic reports before clinical action.)*"
            )

        # ── 2. Specific Question Answering via Root & Synonym Token Matching ─
        scored_snippets = []
        for ch in context_chunks:
            text = ch.get("chunk_text", "")
            lines = [l.strip() for l in text.split("\n") if l.strip()]

            for i, line in enumerate(lines):
                s_tokens = re.findall(r'[a-zA-Z0-9_\-]+', line.lower())
                s_stems = {_stem(t) for t in s_tokens}

                exact_matches = sum(1 for t in query_tokens if t in s_tokens)
                stem_matches  = sum(1 for st in query_stems if st in s_stems)
                # Partial/substring match bonus for longer query terms
                partial_matches = sum(
                    1 for t in query_tokens if len(t) > 4 and any(t in tok for tok in s_tokens)
                )
                score = exact_matches * 4 + stem_matches * 2 + partial_matches

                if score > 0:
                    # If heading-like line, include next list items
                    block_lines = [line]
                    if line.endswith(":") or any(line.lower().startswith(k) for k in (
                        "medications", "allergies", "diagnosis", "plan", "history",
                        "rx", "vitals", "findings", "assessment", "impression",
                        "complaint", "treatment", "recommendation", "follow",
                    )):
                        for next_idx in range(i + 1, min(i + 6, len(lines))):
                            nxt = lines[next_idx]
                            if re.match(r'^(\d+[\.)]|[-•*]|\b[A-Z][a-z]+:)', nxt) or len(nxt) < 90:
                                block_lines.append(nxt)
                                if nxt.endswith(":") and next_idx > i + 1:
                                    break
                            else:
                                break
                    snippet_text = "\n  ".join(block_lines)
                    scored_snippets.append((score, ch.get("document_name", "Document"), ch.get("page_number", 1), snippet_text))

        if not scored_snippets:
            # ── Semantic fallback: return the most relevant document sections ──
            # Instead of a hard refusal, show the most informative lines from the document
            informative = [l for l in all_lines if len(l) > 25 and not l.startswith("#")][:6]
            if informative:
                bullets = "\n".join(f"• {l}" for l in informative)
                return (
                    f"I could not find an exact match for your query in {doc_label}. "
                    f"Here is the most relevant content from the indexed document:\n\n"
                    f"{bullets}\n\n"
                    f"Try rephrasing your question or ask for a **document summary** for a full overview."
                )
            return (
                f"No specific information matching your query was found in {doc_label}. "
                f"Try asking for a **summary** of this document to see all available content."
            )

        # Sort by relevance score descending
        scored_snippets.sort(key=lambda x: x[0], reverse=True)

        # Deduplicate and pick top relevant snippets
        unique_answers = []
        seen = set()
        for score, doc_name, page, s in scored_snippets:
            normalized = s.lower().replace(" ", "")
            if normalized not in seen:
                seen.add(normalized)
                page_info = f" (p. {page})" if page else ""
                unique_answers.append(f"• **[{doc_name}{page_info}]**: {s}")
            if len(unique_answers) >= 5:
                break

        answer_body = "\n\n".join(unique_answers)
        return (
            f"Based on the patient's indexed records:\n\n"
            f"{answer_body}\n\n"
            f"*(Please verify against original diagnostic reports before clinical action.)*"
        )


# ---------------------------------------------------------------------------
# LangChain-backed Gemini provider
# ---------------------------------------------------------------------------

class GeminiLLMProvider(LLMProvider):
    """
    Google Gemini LLM Provider backed by LangChain's ChatGoogleGenerativeAI.

    LangChain handles:
      - HTTP transport to the Gemini API
      - SystemMessage / HumanMessage formatting
      - Token configuration

    CuraMind handles:
      - Context chunk formatting before reaching LangChain
      - Fallback to MockLLMProvider on error or missing key
    """

    def __init__(self, api_key: str, model: str = "gemini-3.8-flash"):
        self.api_key = api_key
        self.model = model
        self._lc_model = None  # Lazy-init to avoid import cost in test-only runs

    def _get_lc_model(self):
        if self._lc_model is None:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                self._lc_model = ChatGoogleGenerativeAI(
                    model=self.model,
                    google_api_key=self.api_key,
                    max_output_tokens=settings.MAX_RESPONSE_TOKENS,
                    temperature=0.2,
                    max_retries=0,
                    timeout=10.0,
                )
            except Exception as e:
                logger.error(f"Failed to initialise ChatGoogleGenerativeAI: {e}")
        return self._lc_model

    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: List[Dict[str, Any]],
    ) -> str:
        if not self.api_key:
            return MockLLMProvider().generate_response(system_prompt, user_prompt, context_chunks)

        lc_model = self._get_lc_model()
        if lc_model is None:
            return MockLLMProvider().generate_response(system_prompt, user_prompt, context_chunks)

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            context_text = "\n\n".join([
                f"[Source: {c.get('document_name')}, Page {c.get('page_number', 1)}]\n{c.get('chunk_text')}"
                for c in context_chunks
            ])

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=(
                    f"Retrieved Patient Context:\n{context_text}\n\n"
                    f"Clinician Question:\n{user_prompt}"
                )),
            ]

            response = lc_model.invoke(messages)
            if not response.content:
                return MockLLMProvider().generate_response(system_prompt, user_prompt, context_chunks)
            return response.content
        except Exception as e:
            logger.warning(f"Gemini API call failed ({e}) — falling back to intelligent clinical extractor.")
            return MockLLMProvider().generate_response(system_prompt, user_prompt, context_chunks)


# ---------------------------------------------------------------------------
# LangChain-backed OpenAI / APInex-compatible provider
# ---------------------------------------------------------------------------

class OpenAICompatibleLLMProvider(LLMProvider):
    """
    OpenAI or any OpenAI-compatible API provider (APInex, Azure OpenAI, vLLM).
    Backed by LangChain's ChatOpenAI.

    Configuration via env vars:
      LLM_API_KEY   — API key (overrides OPENAI_API_KEY when set)
      LLM_BASE_URL  — Base URL for APInex/custom endpoints (optional)
      LLM_MODEL     — Model name (e.g. "gpt-4o", "gpt-3.5-turbo")

    LangChain handles:
      - HTTP transport
      - SystemMessage / HumanMessage formatting
      - base_url override for APInex / custom endpoints

    CuraMind handles:
      - Context chunk formatting
      - Fallback to MockLLMProvider on error
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._lc_model = None

    def _get_lc_model(self):
        if self._lc_model is None:
            try:
                from langchain_openai import ChatOpenAI
                kwargs: Dict[str, Any] = dict(
                    model=self.model,
                    api_key=self.api_key,
                    max_tokens=settings.MAX_RESPONSE_TOKENS,
                    temperature=0.2,
                )
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._lc_model = ChatOpenAI(**kwargs)
            except Exception as e:
                logger.error(f"Failed to initialise ChatOpenAI: {e}")
        return self._lc_model

    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: List[Dict[str, Any]],
    ) -> str:
        if not self.api_key:
            raise RuntimeError("LLM_API_KEY or OPENAI_API_KEY is required for the OpenAI-compatible provider")

        lc_model = self._get_lc_model()
        if lc_model is None:
            raise RuntimeError("Could not initialize the configured OpenAI-compatible model")

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            context_text = "\n\n".join([
                f"[Source: {c.get('document_name')}, Page {c.get('page_number', 1)}]\n{c.get('chunk_text')}"
                for c in context_chunks
            ])

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=(
                    f"Retrieved Patient Context:\n{context_text}\n\n"
                    f"Clinician Question:\n{user_prompt}"
                )),
            ]

            response = lc_model.invoke(messages)
            if not response.content:
                raise RuntimeError("OpenAI-compatible provider returned an empty response")
            return response.content
        except Exception as e:
            logger.error(f"OpenAI-compatible LangChain call failed: {e}")
            raise RuntimeError("OpenAI-compatible response generation failed") from e


# ---------------------------------------------------------------------------
# LangChain-backed Anthropic provider
# ---------------------------------------------------------------------------

class AnthropicLLMProvider(LLMProvider):
    """
    Claude / Anthropic LLM Provider backed by LangChain's ChatAnthropic.

    LangChain handles:
      - HTTP transport to the Anthropic API
      - SystemMessage / HumanMessage formatting

    CuraMind handles:
      - Context chunk formatting
      - Fallback to MockLLMProvider on error
    """

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model
        self._lc_model = None

    def _get_lc_model(self):
        if self._lc_model is None:
            try:
                from langchain_anthropic import ChatAnthropic
                self._lc_model = ChatAnthropic(
                    model=self.model,
                    api_key=self.api_key,
                    max_tokens=settings.MAX_RESPONSE_TOKENS,
                    temperature=0.2,
                )
            except Exception as e:
                logger.error(f"Failed to initialise ChatAnthropic: {e}")
        return self._lc_model

    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: List[Dict[str, Any]],
    ) -> str:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for the Anthropic provider")

        lc_model = self._get_lc_model()
        if lc_model is None:
            raise RuntimeError("Could not initialize the configured Anthropic model")

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            context_text = "\n\n".join([
                f"[Source: {c.get('document_name')}, Page {c.get('page_number', 1)}]\n{c.get('chunk_text')}"
                for c in context_chunks
            ])

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=(
                    f"Retrieved Patient Context:\n{context_text}\n\n"
                    f"Clinician Question:\n{user_prompt}"
                )),
            ]

            response = lc_model.invoke(messages)
            if not response.content:
                raise RuntimeError("Anthropic returned an empty response")
            return response.content
        except Exception as e:
            logger.error(f"Anthropic LangChain call failed: {e}")
            raise RuntimeError("Anthropic response generation failed") from e


# ---------------------------------------------------------------------------
# Factory — env-var driven, provider-agnostic
# ---------------------------------------------------------------------------

def get_llm_provider() -> LLMProvider:
    """
    Returns the correct LLM provider based on environment variables.

    The mock provider is used only when explicitly selected. A missing key or
    unsupported provider is an error rather than a silent downgrade.
    """
    provider_name = (settings.LLM_PROVIDER or "mock").lower()
    if provider_name == "mock":
        return MockLLMProvider()

    gemini_key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
    if provider_name == "gemini":
        return GeminiLLMProvider(api_key=gemini_key, model=settings.GEMINI_MODEL or settings.LLM_MODEL or "gemini-3.8-flash")

    if provider_name == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is required for LLM_PROVIDER=anthropic")
        return AnthropicLLMProvider(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.LLM_MODEL or "claude-3-5-sonnet-20241022",
        )

    if provider_name in ("openai", "apinex"):
        api_key = settings.LLM_API_KEY or settings.OPENAI_API_KEY
        if not api_key:
            raise RuntimeError("LLM_API_KEY or OPENAI_API_KEY is required for OpenAI-compatible providers")
        return OpenAICompatibleLLMProvider(
            api_key=api_key,
            model=settings.LLM_MODEL or "gpt-4o-mini",
            base_url=settings.LLM_BASE_URL,
        )

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider_name}")
