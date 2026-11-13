"""Weather-outlook warnings (compare daily numbers with sourced thresholds). See MODULE.md."""

from .core import RULES, evaluate_days, load_thresholds

__all__ = ["RULES", "load_thresholds", "evaluate_days"]
