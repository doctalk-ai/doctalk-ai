"""Local per-arm retrieval configuration shim, used only by the eval tool.

This stands in for the not-yet-implemented "Per-Request Retrieval
Configuration" feature (an ``EffectiveRetrievalConfig`` /
``retrieve_for_documents`` boundary tracked separately). It must never be
imported from a production ``/chat`` code path. If that feature lands with
its own equivalents, this module should be reconciled with (or replaced
by) it rather than kept as a permanent parallel implementation.

``core.config.config`` and ``context_service.MAX_CONTEXT_CHARS`` are read
as plain process globals by ``rerank_chunks_if_enabled`` and
``SQLAlchemyService`` — not through any per-call parameter — so true
concurrent (``asyncio.gather``) arms would leak overrides across tasks.
Arms are therefore run sequentially, with every touched global saved
before an arm starts and restored in a ``finally`` block, which is exactly
the "env-switched sequential runs" fallback this feature explicitly
allows.
"""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from dataclasses import asdict, dataclass

from core.config import config
from db import find_similar_chunks
from db.base import ChunkMatch
from services import context_service
from services.reranker import _reset_reranker_provider, rerank_chunks_if_enabled


@dataclass
class EffectiveRetrievalConfig:
    """One eval "arm": the retrieval knobs under comparison."""

    label: str
    hybrid_retrieval_enabled: bool
    enable_reranking: bool
    reranker_provider: str = "similarity"
    match_count: int = 10
    max_context_chars: int = 32000
    allow_embedding_cache: bool = False


@dataclass
class ResolvedEnvironmentSnapshot:
    """Ambient env-derived retrieval/context config, captured for export reproducibility."""

    hybrid_retrieval_enabled: bool
    enable_reranking: bool
    reranker_provider: str
    enable_embedding_cache: bool
    max_context_chars: int
    embedding_provider: str
    embedding_model: str | None

    @classmethod
    def capture(cls) -> "ResolvedEnvironmentSnapshot":
        return cls(
            hybrid_retrieval_enabled=config.HYBRID_RETRIEVAL_ENABLED,
            enable_reranking=config.ENABLE_RERANKING,
            reranker_provider=config.RERANKER_PROVIDER,
            enable_embedding_cache=config.ENABLE_EMBEDDING_CACHE,
            max_context_chars=context_service.MAX_CONTEXT_CHARS,
            embedding_provider=config.EMBEDDING_PROVIDER,
            embedding_model=config.EMBEDDING_MODEL,
        )

    def as_dict(self) -> dict:
        return asdict(self)


@contextmanager
def apply_effective_config(effective: EffectiveRetrievalConfig):
    """Temporarily override global retrieval config for one arm's duration.

    Every touched attribute is restored in a ``finally`` block, so a raised
    exception mid-arm cannot leak overrides into the next arm or into any
    other code running in this process.
    """
    originals = {
        "HYBRID_RETRIEVAL_ENABLED": config.HYBRID_RETRIEVAL_ENABLED,
        "ENABLE_RERANKING": config.ENABLE_RERANKING,
        "RERANKER_PROVIDER": config.RERANKER_PROVIDER,
        "ENABLE_EMBEDDING_CACHE": config.ENABLE_EMBEDDING_CACHE,
    }
    original_max_context_chars = context_service.MAX_CONTEXT_CHARS

    try:
        config.HYBRID_RETRIEVAL_ENABLED = effective.hybrid_retrieval_enabled
        config.ENABLE_RERANKING = effective.enable_reranking
        config.RERANKER_PROVIDER = effective.reranker_provider
        config.ENABLE_EMBEDDING_CACHE = effective.allow_embedding_cache
        context_service.MAX_CONTEXT_CHARS = effective.max_context_chars
        # get_reranker_provider() caches a singleton keyed on config at first
        # call; without resetting it here, flipping ENABLE_RERANKING /
        # RERANKER_PROVIDER across arms would silently keep serving the
        # first arm's provider.
        _reset_reranker_provider()
        yield
    finally:
        for attr, value in originals.items():
            setattr(config, attr, value)
        context_service.MAX_CONTEXT_CHARS = original_max_context_chars
        _reset_reranker_provider()


async def retrieve_for_documents(
    doc_ids: list[str],
    query_embedding: list[float],
    effective: EffectiveRetrievalConfig,
    *,
    tenant_id: str,
    query_text: str | None = None,
) -> list[ChunkMatch]:
    """Eval tool's retrieve boundary.

    Runs the real retrieval pipeline (``find_similar_chunks`` +
    ``rerank_chunks_if_enabled``) for one arm, mirroring
    ``chat_service._retrieve_chunks_for_documents`` /
    ``_finalize_retrieved_chunks`` without going through the ``/chat`` HTTP
    surface and without ever calling answer generation.

    Must be called inside an active ``apply_effective_config(effective)``
    block — this function does not apply the override itself, since the
    caller also needs the override active for the query embedding call and
    for the assembled context preview.
    """
    per_document_chunks = await asyncio.gather(
        *[
            find_similar_chunks(
                doc_id=doc_id,
                query_embedding=query_embedding,
                match_count=effective.match_count,
                tenant_id=tenant_id,
                query_text=query_text,
            )
            for doc_id in doc_ids
        ]
    )

    merged: list[ChunkMatch] = []
    for chunks in per_document_chunks:
        merged.extend(chunks)

    return await rerank_chunks_if_enabled(
        query_text or "", merged, top_k=effective.match_count
    )
