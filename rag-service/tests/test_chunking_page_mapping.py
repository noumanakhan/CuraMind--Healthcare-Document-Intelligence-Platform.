"""
test_chunking_page_mapping.py
─────────────────────────────
Unit tests for chunk_text() after migration to LangChain's
RecursiveCharacterTextSplitter.

Only LangChain text splitting is exercised here — no retrievers, vector stores,
chains, or agents (per curamind-scoped-langchain-constraint).
"""
import pytest
from app.services.ingestion import chunk_text


def _pages(texts: list) -> list:
    """Build pages_data list from a list of page strings (1-indexed)."""
    return [{"page_number": i + 1, "text": t} for i, t in enumerate(texts)]


def test_single_page_short_text_single_chunk():
    """Text shorter than chunk_size must produce exactly one chunk on page 1."""
    pages = _pages(["Short clinical note."])
    chunks = chunk_text(pages, chunk_size=500, chunk_overlap=50)
    assert len(chunks) == 1
    assert chunks[0]["page_number"] == 1
    assert chunks[0]["chunk_index"] == 0
    assert "Short clinical note" in chunks[0]["chunk_text"]


def test_single_page_long_text_multiple_chunks_same_page():
    """Long text on page 2 must produce multiple chunks all tagged page 2."""
    long_text = "Patient has a history of hypertension and diabetes. " * 30
    pages = _pages(["Intro note.", long_text])
    chunks = chunk_text(pages, chunk_size=300, chunk_overlap=30)
    page2_chunks = [c for c in chunks if c["page_number"] == 2]
    assert len(page2_chunks) >= 2, "Long text on page 2 should produce multiple chunks"
    for c in page2_chunks:
        assert c["page_number"] == 2


def test_multi_page_page_numbers_are_preserved():
    """Each chunk must carry the page number of the page it came from."""
    pages = _pages([
        "Page one content with a clinical observation.",
        "Page two content with lab results and medication notes.",
        "Page three content with follow-up instructions.",
    ])
    chunks = chunk_text(pages, chunk_size=500, chunk_overlap=50)
    seen_pages = {c["page_number"] for c in chunks}
    assert seen_pages == {1, 2, 3}, f"Expected pages {{1,2,3}}, got {seen_pages}"


def test_chunk_indices_are_globally_sequential():
    """chunk_index must be a globally monotone sequence starting at 0."""
    pages = _pages(["Alpha " * 100, "Beta " * 100])
    chunks = chunk_text(pages, chunk_size=200, chunk_overlap=20)
    indices = [c["chunk_index"] for c in chunks]
    assert indices == list(range(len(indices))), "chunk_index must be globally sequential"


def test_empty_pages_are_skipped():
    """Pages with empty or whitespace-only text must be silently skipped."""
    pages = _pages(["Real content here.", "", "   ", "More real content."])
    chunks = chunk_text(pages, chunk_size=500, chunk_overlap=50)
    seen_pages = {c["page_number"] for c in chunks}
    assert 2 not in seen_pages
    assert 3 not in seen_pages
    assert 1 in seen_pages
    assert 4 in seen_pages


def test_no_empty_chunk_text():
    """chunk_text must never produce a chunk with empty or whitespace-only text."""
    pages = _pages(["  \n\n  ", "Real text here.", "   \t   "])
    chunks = chunk_text(pages, chunk_size=500, chunk_overlap=50)
    for c in chunks:
        assert c["chunk_text"].strip(), f"Empty chunk_text found: {c!r}"


def test_chunk_size_is_roughly_respected():
    """Every chunk must not massively exceed chunk_size characters."""
    long_text = "The patient presented with acute respiratory distress. " * 50
    pages = _pages([long_text])
    chunks = chunk_text(pages, chunk_size=200, chunk_overlap=20)
    for c in chunks:
        # Allow a small overshoot at separator boundaries.
        assert len(c["chunk_text"]) <= 300, (
            f"Chunk exceeds expected size: {len(c['chunk_text'])} chars"
        )


def test_large_multi_page_document():
    """10 pages of content should produce many well-tagged chunks."""
    pages = _pages([f"Page {i + 1} clinical notes. " * 40 for i in range(10)])
    chunks = chunk_text(pages, chunk_size=400, chunk_overlap=40)
    assert len(chunks) >= 10, "Expected at least one chunk per page"
    for c in chunks:
        assert "chunk_text" in c
        assert "page_number" in c
        assert "chunk_index" in c
        assert 1 <= c["page_number"] <= 10
