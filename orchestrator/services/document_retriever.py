"""
Retrieve relevant chunks from admin-uploaded knowledge documents for LLM Context.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from war_game.project_config import DOCUMENT_KNOWLEDGE_CONFIG

from .router import COUNTRY_ALIASES

TOP_K = int(DOCUMENT_KNOWLEDGE_CONFIG["retrieve_top_k"])
MAX_CONTEXT_CHARS = int(DOCUMENT_KNOWLEDGE_CONFIG["max_context_chars"])

_TOKEN_RE = re.compile(r"[A-Za-z0-9\u0600-\u06FF]{2,}")
_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "are",
        "was",
        "were",
        "have",
        "has",
        "will",
        "can",
        "about",
        "what",
        "which",
        "when",
        "where",
        "how",
        "who",
        "into",
        "over",
        "under",
        "than",
        "then",
        "them",
        "they",
        "their",
        "there",
        "please",
        "compare",
        "between",
        "یک",
        "این",
        "آن",
        "برای",
        "با",
        "از",
        "که",
        "را",
        "به",
        "در",
        "است",
        "هست",
        "مقایسه",
        "کن",
        "کنید",
        "بگو",
        "بگویید",
    }
)


def _tokenize(text: str) -> Set[str]:
    return {
        tok.lower()
        for tok in _TOKEN_RE.findall(text or "")
        if tok.lower() not in _STOPWORDS
    }


def _country_query_terms(countries: Sequence[str]) -> Set[str]:
    wanted = {c.lower() for c in countries if c}
    terms: Set[str] = set(wanted)
    for alias, canonical in COUNTRY_ALIASES.items():
        if canonical.lower() in wanted:
            terms.add(alias.lower())
            terms.add(canonical.lower())
    return terms


def _score_chunk(
    token_hints: str,
    query_tokens: Set[str],
    country_terms: Set[str],
) -> float:
    if not token_hints:
        return 0.0
    haystack_tokens = _tokenize(token_hints)
    if not haystack_tokens and not country_terms:
        return 0.0

    score = 0.0
    if query_tokens:
        overlap = query_tokens & haystack_tokens
        score += float(len(overlap))

    # Country mentions are strong signals for wargaming questions.
    for term in country_terms:
        if term and term in token_hints:
            score += 3.0

    return score


def retrieve_document_chunks(
    query: str,
    countries: Optional[Sequence[str]] = None,
    top_k: int = TOP_K,
    max_chars: int = MAX_CONTEXT_CHARS,
) -> List[Dict[str, Any]]:
    """
    Return top-k scored chunks from active, ready documents.
    Each item: {title, chunk_index, content, score}.
    """
    from orchestrator.models import KnowledgeDocument, KnowledgeDocumentChunk

    countries = list(countries or [])
    query_tokens = _tokenize(query)
    country_terms = _country_query_terms(countries)

    qs = (
        KnowledgeDocumentChunk.objects.filter(
            document__is_active=True,
            document__status=KnowledgeDocument.Status.READY,
        )
        .select_related("document")
        .only(
            "chunk_index",
            "content",
            "token_hints",
            "document__title",
        )
    )

    scored: List[Dict[str, Any]] = []
    for chunk in qs:
        score = _score_chunk(chunk.token_hints or chunk.content.lower(), query_tokens, country_terms)
        if score <= 0 and (query_tokens or country_terms):
            continue
        scored.append(
            {
                "title": chunk.document.title,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "score": score,
            }
        )

    # If nothing matched but documents exist, fall back to first chunks so
    # uploads still contribute when the query is very short/generic.
    if not scored:
        fallback = list(qs.order_by("document_id", "chunk_index")[:top_k])
        scored = [
            {
                "title": chunk.document.title,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "score": 0.0,
            }
            for chunk in fallback
        ]

    scored.sort(key=lambda item: (-item["score"], item["title"], item["chunk_index"]))

    selected: List[Dict[str, Any]] = []
    used = 0
    for item in scored:
        block_len = len(item["content"]) + len(item["title"]) + 32
        if selected and used + block_len > max_chars:
            break
        selected.append(item)
        used += block_len
        if len(selected) >= top_k:
            break
    return selected


def format_document_context(chunks: Iterable[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for item in chunks:
        title = item.get("title") or "Document"
        index = item.get("chunk_index", 0)
        content = (item.get("content") or "").strip()
        if not content:
            continue
        parts.append(f"[{title} — chunk {index}]\n{content}")
    if not parts:
        return ""
    return "Uploaded documents:\n" + "\n\n".join(parts)
