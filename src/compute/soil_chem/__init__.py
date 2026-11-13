"""Soil pH and organic carbon baseline from the saved SoilGrids file (Layer 1, no AI). Public API."""

from .loader import CSV_PATH, LABEL, soil_baseline, status_rows

__all__ = ["CSV_PATH", "LABEL", "soil_baseline", "status_rows"]
