"""Eval orchestration: dataset loading, per-arm retrieval, metrics, compare, export.

Never imports or calls answer generation (``generate_answer`` /
``generate_answer_stream``) — this module's retrieve boundary stops at
assembled context, exactly like ``eval_config.retrieve_for_documents``.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from db.base import ChunkMatch
from services import eval_metrics
from services.context_service import build_context_from_chunks
from services.eval_config import (
    EffectiveRetrievalConfig,
    ResolvedEnvironmentSnapshot,
    apply_effective_config,
    retrieve_for_documents,
)
from services.eval_fixtures import EvalDataset, dataset_hash
from services.embedding_service import get_embedding

EVAL_TOOL_VERSION = "0.1.0"
DEFAULT_K_VALUES: tuple[int, ...] = (5, 10)


def _candidate_summary(chunk: ChunkMatch) -> dict:
    return {
        "id": chunk.id,
        "document_id": chunk.document_id,
        "chunk_index": chunk.chunk_index,
        "similarity": chunk.similarity,
        "score_type": chunk.score_type,
        "rerank_order": chunk.rerank_order,
    }


@dataclass
class QueryResult:
    query: str
    candidates: list[dict]
    metrics: dict[str, float]
    context_preview: str


@dataclass
class ArmResult:
    config: EffectiveRetrievalConfig
    resolved_env: ResolvedEnvironmentSnapshot
    query_results: list[QueryResult] = field(default_factory=list)
    aggregate_metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class EvalRunResult:
    run_id: str
    timestamp: str
    tool_version: str
    dataset_name: str
    dataset_hash: str
    arms: list[ArmResult]

    def to_export_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "tool_version": self.tool_version,
            "dataset_name": self.dataset_name,
            "dataset_hash": self.dataset_hash,
            "arms": [
                {
                    "config_snapshot": {
                        "effective_config": vars(arm.config),
                        "resolved_environment": arm.resolved_env.as_dict(),
                    },
                    "aggregate_metrics": arm.aggregate_metrics,
                    "per_query_metrics": [
                        {
                            "query": qr.query,
                            "metrics": qr.metrics,
                            "candidates": qr.candidates,
                            "context_preview": qr.context_preview,
                        }
                        for qr in arm.query_results
                    ],
                }
                for arm in self.arms
            ],
        }


def _aggregate(query_results: list[QueryResult]) -> dict[str, float]:
    if not query_results:
        return {}
    keys = query_results[0].metrics.keys()
    return {
        key: sum(qr.metrics[key] for qr in query_results) / len(query_results)
        for key in keys
    }


async def _run_arm(
    dataset: EvalDataset,
    effective: EffectiveRetrievalConfig,
    *,
    tenant_id: str,
    k_values: tuple[int, ...],
    resolved_env: ResolvedEnvironmentSnapshot,
) -> ArmResult:
    query_results: list[QueryResult] = []

    for q in dataset.queries:
        with apply_effective_config(effective):
            embedding = await get_embedding(q.query)
            candidates = await retrieve_for_documents(
                q.doc_ids,
                embedding,
                effective,
                tenant_id=tenant_id,
                query_text=q.query,
            )
            context_preview = build_context_from_chunks(candidates)

        ranked_keys = [
            eval_metrics.chunk_match_key(c.document_id, c.chunk_index)
            for c in candidates
        ]
        relevant = q.relevant_keys()

        metrics: dict[str, float] = {"mrr": eval_metrics.mrr(ranked_keys, relevant)}
        for k in k_values:
            metrics[f"recall@{k}"] = eval_metrics.recall_at_k(ranked_keys, relevant, k)
            metrics[f"ndcg@{k}"] = eval_metrics.ndcg_at_k(ranked_keys, relevant, k)

        query_results.append(
            QueryResult(
                query=q.query,
                candidates=[_candidate_summary(c) for c in candidates],
                metrics=metrics,
                context_preview=context_preview,
            )
        )

    return ArmResult(
        config=effective,
        resolved_env=resolved_env,
        query_results=query_results,
        aggregate_metrics=_aggregate(query_results),
    )


async def run_eval(
    dataset: EvalDataset,
    arms: list[EffectiveRetrievalConfig],
    *,
    tenant_id: str,
    k_values: tuple[int, ...] = DEFAULT_K_VALUES,
    export_path: str | Path | None = None,
) -> EvalRunResult:
    """Run one or more config arms against ``dataset`` sequentially.

    Sequential execution (rather than ``asyncio.gather`` across arms) is
    required by the global-config override shim in ``eval_config`` — see
    that module's docstring.
    """
    resolved_env = ResolvedEnvironmentSnapshot.capture()

    arm_results = [
        await _run_arm(
            dataset,
            effective,
            tenant_id=tenant_id,
            k_values=k_values,
            resolved_env=resolved_env,
        )
        for effective in arms
    ]

    result = EvalRunResult(
        run_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        tool_version=EVAL_TOOL_VERSION,
        dataset_name=dataset.name,
        dataset_hash=dataset_hash(dataset.source_path) if dataset.source_path else "",
        arms=arm_results,
    )

    if export_path is not None:
        export_run(result, export_path)

    return result


def export_run(result: EvalRunResult, path: str | Path) -> None:
    Path(path).write_text(json.dumps(result.to_export_dict(), indent=2), encoding="utf-8")


def diff_arms(arm_results: list[ArmResult]) -> list[dict]:
    """Per-query candidate-set diff across 2+ arms (compare mode)."""
    if len(arm_results) < 2:
        return []

    diffs = []
    for i, first_qr in enumerate(arm_results[0].query_results):
        per_arm = []
        for arm in arm_results:
            qr = arm.query_results[i]
            per_arm.append(
                {
                    "label": arm.config.label,
                    "candidate_ids": [c["id"] for c in qr.candidates],
                    "context_preview": qr.context_preview,
                }
            )
        candidate_sets = [set(pa["candidate_ids"]) for pa in per_arm]
        differs = any(cs != candidate_sets[0] for cs in candidate_sets[1:])
        diffs.append({"query": first_qr.query, "arms": per_arm, "differs": differs})

    return diffs
