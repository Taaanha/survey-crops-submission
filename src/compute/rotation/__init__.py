"""Full-year rotation engine (T1). Public API only; see MODULE.md."""

from .context import RotationContext, load_context
from .core import candidate_rotations, evaluate_rotation, excluded_crops
from .crop_table import load_crop_table

__all__ = ["RotationContext", "load_context", "candidate_rotations", "evaluate_rotation",
           "excluded_crops", "load_crop_table"]
