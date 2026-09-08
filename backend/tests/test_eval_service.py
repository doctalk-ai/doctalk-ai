"""Tests for the retrieval eval tool: metrics, compare mode, export, no-LLM guard."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from core.config import config
from db.base import ChunkMatch
from services import eval_metrics
from services.eval_config import EffectiveRetrievalConfig
from services.eval_fixtures import load_dataset
from services.eval_service import diff_arms, run_eval

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "eval"


def _chunk(doc_id: str, chunk_index: int, *, score: float = 0.5) -> ChunkMatch:
    return ChunkMatch(
        id=f"{doc_id}:{chunk_index}",
        chunk_text=f"content for {doc_id} chunk {chunk_index}",
        document_id=doc_id,
        chunk_index=chunk_index,
        similarity=score,
        file_name=f"{doc_id}.txt",
    )


# ---------------------------------------------------------------------------
# eval_metrics — pure unit tests against hand-computed values
# ---------------------------------------------------------------------------


def test_recall_at_k():
    ranked = ["a", "b", "c", "d"]
    relevant = {"b", "d", "z"}
    assert eval_metrics.recall_at_k(ranked, relevant, k=2) == pytest.approx(1 / 3)
    assert eval_metrics.recall_at_k(ranked, relevant, k=4) == pytest.approx(2 / 3)


def test_recall_at_k_no_relevant_returns_zero():
    assert eval_metrics.recall_at_k(["a"], set(), k=5) == 0.0


def test_mrr_first_hit_rank():
    assert eval_metrics.mrr(["a", "b", "c"], {"b"}) == pytest.approx(0.5)
    assert eval_metrics.mrr(["a", "b", "c"], {"z"}) == 0.0


def test_ndcg_at_k_perfect_order_is_one():
    ranked = ["a", "b", "c"]
    relevant = {"a", "b"}
    assert eval_metrics.ndcg_at_k(ranked, relevant, k=2) == pytest.approx(1.0)


def test_ndcg_at_k_worse_order_is_less_than_one():
    ranked = ["c", "a", "b"]
    relevant = {"a", "b"}
    score = eval_metrics.ndcg_at_k(ranked, relevant, k=2)
    assert 0.0 < score < 1.0


def test_chunk_match_key_falls_back_to_document_id():
    assert eval_metrics.chunk_match_key("doc-1", 3) == ("doc-1", 3)
    assert eval_metrics.chunk_match_key("doc-1", None) == "doc-1"
    assert eval_metrics.chunk_match_key(None, 3) is None


# ---------------------------------------------------------------------------
# run_eval — single arm against the checked-in basic fixture
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_eval_single_arm_reports_sane_metrics():
    dataset = load_dataset(FIXTURES_DIR / "basic_queries.json")

    async def fake_find_similar_chunks(*, doc_id, query_embedding, match_count, tenant_id, query_text=None, session_id=None):
        # One correct hit plus filler, regardless of arm config.
        return [_chunk(doc_id, 0), _chunk(doc_id, 1), _chunk(doc_id, 2)]

    arm = EffectiveRetrievalConfig(
        label="current-config",
        hybrid_retrieval_enabled=False,
        enable_reranking=False,
    )

    with patch("services.eval_config.find_similar_chunks", AsyncMock(side_effect=fake_find_similar_chunks)), \
         patch("services.eval_service.get_embedding", AsyncMock(return_value=[0.1, 0.2, 0.3])):
        result = await run_eval(dataset, [arm], tenant_id="tenant-eval-test")

    assert len(result.arms) == 1
    arm_result = result.arms[0]
    assert len(arm_result.query_results) == len(dataset.queries)
    for metric_name in ("mrr", "recall@5", "recall@10", "ndcg@5", "ndcg@10"):
        value = arm_result.aggregate_metrics[metric_name]
        assert 0.0 <= value <= 1.0

    for qr in arm_result.query_results:
        assert qr.context_preview  # context assembled per query


# ---------------------------------------------------------------------------
# Compare mode — 2 arms against the diverging fixture must show real diffs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_mode_arms_produce_different_candidates():
    dataset = load_dataset(FIXTURES_DIR / "diverging_queries.json")

    async def fake_find_similar_chunks(*, doc_id, query_embedding, match_count, tenant_id, query_text=None, session_id=None):
        # Read the live override so vector-only vs hybrid arms diverge —
        # this simulates SQLAlchemyService branching on HYBRID_RETRIEVAL_ENABLED
        # without requiring a live Postgres/pgvector instance for this test.
        if config.HYBRID_RETRIEVAL_ENABLED:
            return [_chunk(doc_id, 9, score=0.9), _chunk(doc_id, 1, score=0.7)]
        return [_chunk(doc_id, 2, score=0.8), _chunk(doc_id, 3, score=0.6)]

    vector_only = EffectiveRetrievalConfig(
        label="vector-only", hybrid_retrieval_enabled=False, enable_reranking=False
    )
    hybrid = EffectiveRetrievalConfig(
        label="hybrid", hybrid_retrieval_enabled=True, enable_reranking=False
    )

    with patch("services.eval_config.find_similar_chunks", AsyncMock(side_effect=fake_find_similar_chunks)), \
         patch("services.eval_service.get_embedding", AsyncMock(return_value=[0.1, 0.2, 0.3])):
        result = await run_eval(dataset, [vector_only, hybrid], tenant_id="tenant-eval-test")

    diffs = diff_arms(result.arms)
    assert len(diffs) == len(dataset.queries)
    assert all(d["differs"] for d in diffs), "arms must diverge, not just match_count"
    for d in diffs:
        for arm_entry in d["arms"]:
            assert arm_entry["context_preview"]


# ---------------------------------------------------------------------------
# Export schema
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_writes_expected_schema(tmp_path):
    dataset = load_dataset(FIXTURES_DIR / "basic_queries.json")

    async def fake_find_similar_chunks(*, doc_id, query_embedding, match_count, tenant_id, query_text=None, session_id=None):
        return [_chunk(doc_id, 0)]

    arm = EffectiveRetrievalConfig(
        label="current-config", hybrid_retrieval_enabled=False, enable_reranking=False
    )
    export_path = tmp_path / "run.json"

    with patch("services.eval_config.find_similar_chunks", AsyncMock(side_effect=fake_find_similar_chunks)), \
         patch("services.eval_service.get_embedding", AsyncMock(return_value=[0.1, 0.2, 0.3])):
        await run_eval(dataset, [arm], tenant_id="tenant-eval-test", export_path=export_path)

    payload = json.loads(export_path.read_text(encoding="utf-8"))
    for key in ("run_id", "timestamp", "tool_version", "dataset_name", "dataset_hash", "arms"):
        assert key in payload

    arm_payload = payload["arms"][0]
    assert "config_snapshot" in arm_payload
    assert "effective_config" in arm_payload["config_snapshot"]
    assert "resolved_environment" in arm_payload["config_snapshot"]
    assert "aggregate_metrics" in arm_payload
    assert "per_query_metrics" in arm_payload
    assert len(arm_payload["per_query_metrics"]) == len(dataset.queries)


# ---------------------------------------------------------------------------
# No answer-generation call anywhere in the eval path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_eval_never_calls_answer_generation():
    dataset = load_dataset(FIXTURES_DIR / "basic_queries.json")

    async def fake_find_similar_chunks(*, doc_id, query_embedding, match_count, tenant_id, query_text=None, session_id=None):
        return [_chunk(doc_id, 0)]

    arm = EffectiveRetrievalConfig(
        label="current-config", hybrid_retrieval_enabled=False, enable_reranking=False
    )

    with patch("services.eval_config.find_similar_chunks", AsyncMock(side_effect=fake_find_similar_chunks)), \
         patch("services.eval_service.get_embedding", AsyncMock(return_value=[0.1, 0.2, 0.3])), \
         patch("services.answer_service.generate_answer", AsyncMock(side_effect=AssertionError("must not be called"))) as gen, \
         patch("services.answer_service.generate_answer_stream", AsyncMock(side_effect=AssertionError("must not be called"))) as gen_stream:
        await run_eval(dataset, [arm], tenant_id="tenant-eval-test")

    gen.assert_not_called()
    gen_stream.assert_not_called()


# ---------------------------------------------------------------------------
# Config override restore-on-finally (no leaked global state)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_config_overrides_restored_after_run():
    dataset = load_dataset(FIXTURES_DIR / "basic_queries.json")

    async def fake_find_similar_chunks(*, doc_id, query_embedding, match_count, tenant_id, query_text=None, session_id=None):
        return [_chunk(doc_id, 0)]

    original_hybrid = config.HYBRID_RETRIEVAL_ENABLED
    original_rerank = config.ENABLE_RERANKING

    arm = EffectiveRetrievalConfig(
        label="flipped",
        hybrid_retrieval_enabled=not original_hybrid,
        enable_reranking=not original_rerank,
    )

    with patch("services.eval_config.find_similar_chunks", AsyncMock(side_effect=fake_find_similar_chunks)), \
         patch("services.eval_service.get_embedding", AsyncMock(return_value=[0.1, 0.2, 0.3])):
        await run_eval(dataset, [arm], tenant_id="tenant-eval-test")

    assert config.HYBRID_RETRIEVAL_ENABLED == original_hybrid
    assert config.ENABLE_RERANKING == original_rerank
