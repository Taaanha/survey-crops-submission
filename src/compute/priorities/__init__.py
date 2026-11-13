"""Farmer priorities (T2). Public API only; see MODULE.md."""

from .core import (FLOOD_HAZARDS, KEYS, METRICS, PrioritiesError, evaluate_candidates,
                   normalise_weights, rank_rotations, score_rotations)

__all__ = ["KEYS", "METRICS", "FLOOD_HAZARDS", "PrioritiesError", "normalise_weights",
           "score_rotations", "rank_rotations", "evaluate_candidates"]
