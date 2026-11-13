"""
src/compute/common/provenance.py

Shared contract for "where did this number come from" (Layer 1, no AI).

A Provenance names the dataset, the page it can be checked on, the day it was
retrieved and the exact granule or file used. A Measured is a number with its
unit and its Provenance. New feature modules return these; old code still uses
the {value, unit, src} measures built in app.py (see docs/ARCHITECTURE_MAP.md).
"""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Provenance:
    dataset: str
    source_url: str
    retrieved: str            # ISO date (YYYY-MM-DD) the data was fetched or last checked
    granule_or_file: str      # e.g. a scene id, or "data/reference/crop_thresholds.csv"
    note: str = ""

    def __post_init__(self):
        for name in ("dataset", "source_url", "retrieved", "granule_or_file"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Provenance.{name} is required (no source means no number)")

    def to_dict(self):
        return asdict(self)


def measured(value, unit, provenance):
    """{"value", "unit", "provenance"}: a number that carries its source."""
    if not isinstance(provenance, Provenance):
        raise TypeError("provenance must be a Provenance")
    return {"value": value, "unit": unit, "provenance": provenance.to_dict()}
