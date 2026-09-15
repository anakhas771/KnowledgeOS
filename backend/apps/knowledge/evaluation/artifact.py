from __future__ import annotations

import json
import tempfile
import os
from datetime import datetime, timezone
from typing import Any


def build_experiment_artifact(
    benchmark_id: str,
    strategy: str,
    config: dict[str, Any],
    report: dict,
    corpus_slug: str = "knowledgeos-retrieval-evaluation",
    case_count: int | None = None,
) -> dict:
    """Build a deterministic, machine-readable benchmark artifact.
    strategy may include 'reranked' identification.

    ``case_count`` defaults to the number of evaluated cases in ``report`` so
    the artifact cannot claim a corpus size the run did not actually measure.
    """
    cases = report.get("cases", [])
    resolved_case_count = (
        case_count
        if case_count is not None
        else len(cases)
    )

    return {
        "benchmark_id": benchmark_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "corpus_identifier": corpus_slug,
        "corpus_size": resolved_case_count,
        "case_count": resolved_case_count,
        "retrieval_strategy": strategy,
        "configuration": config,
        "overall_metrics": report.get("summary", {}),
        "category_metrics": report.get("by_category", {}),
        "case_results": cases,
        "latency_ms_summary": {
            "median": report.get("summary", {}).get("median_latency_ms"),
            "cases": [
                row.get("latency_ms") for row in cases
            ],
        },
    }


def build_pool_sweep_artifact(
    benchmark_id: str,
    strategy: str,
    reports_by_pool: dict[int, dict],
    final_k: int,
    corpus_slug: str = "knowledgeos-retrieval-evaluation",
) -> dict:
    """
    Build one artifact covering a candidate-pool sensitivity sweep.

    Each entry is a full experiment artifact for a single pool size, so every
    measurement remains individually identifiable (pool size, reranking
    config, final K, overall/category metrics, latency, per-case rows). The
    sweep wrapper only records what was held fixed across the runs.
    """
    return {
        "benchmark_id": benchmark_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "corpus_identifier": corpus_slug,
        "retrieval_strategy": strategy,
        "experiment": "candidate_pool_size_sensitivity",
        "independent_variable": "candidate_pool_size",
        "final_k": final_k,
        "pool_sizes": sorted(reports_by_pool),
        "runs": [
            {
                "candidate_pool_size": pool_size,
                "final_k": final_k,
                **build_experiment_artifact(
                    benchmark_id=f"{benchmark_id}:pool={pool_size}",
                    strategy=strategy,
                    config=reports_by_pool[pool_size].get(
                        "configuration",
                        {},
                    ),
                    report=reports_by_pool[pool_size],
                    corpus_slug=corpus_slug,
                ),
            }
            for pool_size in sorted(reports_by_pool)
        ],
    }


def write_artifact_atomic(
    artifact: dict,
    output_path: str,
) -> None:
    """Write artifact to a temporary file then rename for atomicity.
    Prevents partial/misleading result files on failure."""
    dir_name = os.path.dirname(output_path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix=".tmp_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write("\n")
        os.rename(tmp_path, output_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def load_artifact(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
