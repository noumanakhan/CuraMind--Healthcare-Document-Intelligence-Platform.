import abc
import logging
import re
from typing import Any, Dict, List, Optional
import httpx
from app.config import settings

logger = logging.getLogger("rag_service.llm")


class LLMProvider(abc.ABC):
    @abc.abstractmethod
    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: List[Dict[str, Any]],
    ) -> str:
        """Generate response from LLM given retrieved context."""
        pass


class MockLLMProvider(LLMProvider):
    """
    Deterministic Mock LLM provider for testing and offline execution.
    Generates realistic, grounded clinical assistant responses strictly from provided context.
    """
    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: List[Dict[str, Any]],
    ) -> str:
        if not context_chunks:
            return "No relevant clinical information was found in the patient's indexed documents."

        q_lower = user_prompt.lower()
        stop_words = {
            "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", "at", "from",
            "by", "for", "with", "about", "against", "between", "into", "through", "during",
            "before", "after", "above", "below", "to", "of", "up", "down", "in", "out", "on",
            "off", "over", "under", "again", "further", "here", "there", "why", "how", "all",
            "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor",
            "not", "only", "own", "same", "so", "than", "too", "very", "can", "will", "just",
            "should", "now", "did", "does", "doing", "have", "has", "had", "having", "was",
            "were", "be", "been", "being", "is", "am", "are", "what", "which", "who", "whom",
            "this", "that", "these", "those", "patient", "patient's", "doctor", "clinician",
            "hospital", "record", "chart", "note", "file", "document", "tell", "show", "give",
            "find", "know", "medical", "admission", "status"
        }

        # Extract meaningful topical keywords
        keywords = [w for w in re.findall(r'\w+', q_lower) if len(w) > 2 and w not in stop_words]

        # Check if question is relevant to any chunk content
        relevant_chunks = []
        for ch in context_chunks:
            text = ch.get("chunk_text", "").lower()
            text_words = set(re.findall(r'\w+', text))
            matches = sum(1 for kw in keywords if kw in text_words)
            if matches > 0:
                relevant_chunks.append(ch)

        if not relevant_chunks or not keywords:
            return "No relevant clinical information was found in the patient's indexed documents to answer this specific inquiry."

        # Construct grounded response summarizing relevant facts
        summaries = []
        for ch in relevant_chunks[:3]:
            doc_name = ch.get("document_name", "Document")
            page_info = f" (p. {ch.get('page_number')})" if ch.get("page_number") else ""
            snippet = ch.get("chunk_text", "").strip()[:150].replace("\n", " ")
            summaries.append(f"According to **{doc_name}**{page_info}: \"{snippet}...\"")

        response_body = "\n\n".join(summaries)
        return (
            f"Based on the patient's indexed clinical chart:\n\n{response_body}\n\n"
            f"*(Please verify against original diagnostic reports before clinical action.)*"
        )


class AnthropicLLMProvider(LLMProvider):
    """
    Claude / Anthropic LLM Provider for production.
    """
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model

    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: List[Dict[str, Any]],
    ) -> str:
        if not self.api_key:
            return MockLLMProvider().generate_response(system_prompt, user_prompt, context_chunks)
        try:
            context_text = "\n\n".join([
                f"[Source: {c.get('document_name')}, Page {c.get('page_number', 1)}]\n{c.get('chunk_text')}"
                for c in context_chunks
            ])
            full_user_content = f"Retrieved Patient Context:\n{context_text}\n\nClinician Question:\n{user_prompt}"

            with httpx.Client(timeout=45.0) as client:
                res = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "max_tokens": settings.MAX_RESPONSE_TOKENS,
                        "system": system_prompt,
                        "messages": [{"role": "user", "content": full_user_content}]
                    }
                )
                res.raise_for_status()
                data = res.json()
                return data["content"][0]["text"]
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            return MockLLMProvider().generate_response(system_prompt, user_prompt, context_chunks)


def get_llm_provider() -> LLMProvider:
    if settings.LLM_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
        return AnthropicLLMProvider(api_key=settings.ANTHROPIC_API_KEY, model=settings.LLM_MODEL)
    return MockLLMProvider()
