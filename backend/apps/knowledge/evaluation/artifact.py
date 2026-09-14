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
    case_count: int = 25,
) -> dict:
    """Build a deterministic, machine-readable benchmark artifact."""
    return {
        "benchmark_id": benchmark_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "corpus_identifier": corpus_slug,
        "corpus_size": case_count,
        "case_count": case_count,
        "retrieval_strategy": strategy,
        "configuration": config,
        "overall_metrics": report.get("summary", {}),
        "category_metrics": report.get("by_category", {}),
        "case_results": report.get("cases", []),
        "latency_ms_summary": {
            "median": report.get("summary", {}).get("median_latency_ms"),
            "cases": [
                row.get("latency_ms") for row in report.get("cases", [])
            ],
        },
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
