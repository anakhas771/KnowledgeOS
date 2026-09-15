"""
Configuration for selectable embedding models — evaluation-only, no production
change until experiment succeeds.

Only 384-dimensional, sentence-transformers-compatible, free/local models are
listed. Changing dimensionality requires a VectorField migration; that is
deliberately deferred until an experiment proves the change beneficial.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingModelConfig:
    """Selectable embedding model for evaluation only."""

    name: str
    model_name: str
    dimensions: int
    source: str = "sentence-transformers"
    notes: str = ""

    def __post_init__(self) -> None:
        if self.dimensions <= 0:
            raise ValueError("dimensions must be positive")

        # Block any configuration that would require a VectorField change.
        if self.dimensions != 384:
            raise ValueError(
                f"Model '{self.name}' has dimensions={self.dimensions}, "
                "but production VectorField is fixed at 384. "
                "Keep current baseline until an experiment succeeds."
            )


# Baseline (current production): all-MiniLM-L6-v2 — 384 dims, local, fast,
# already loaded in the embedding-service container.
BASELINE = EmbeddingModelConfig(
    name="mini_l6",
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    dimensions=384,
    notes="Current production baseline; smallest, fastest.",
)

# Candidate: all-MiniLM-L12-v2 — same family, deeper network, slightly larger.
# Still 384 dims. Slightly higher quality on some benchmarks; slightly
# slower embedding and ~2x memory footprint. Included only because it is
# free/local, same dimensions, same source library, and requires no new
# package beyond what is already installed.
CANDIDATE = EmbeddingModelConfig(
    name="mini_l12",
    model_name="sentence-transformers/all-MiniLM-L12-v2",
    dimensions=384,
    notes="Same family, deeper, ~2x memory, ~1.5x latency.",
)

MODELS: dict[str, EmbeddingModelConfig] = {
    BASELINE.name: BASELINE,
    CANDIDATE.name: CANDIDATE,
}


def get_model_config(name: str) -> EmbeddingModelConfig:
    if name not in MODELS:
        raise ValueError(
            f"Unknown embedding model '{name}'. "
            f"Available: {', '.join(sorted(MODELS))}"
        )
    return MODELS[name]
