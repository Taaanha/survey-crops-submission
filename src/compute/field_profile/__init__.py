"""Field water profile at 30 m (OPERA water stacks and per-pixel flood metrics). See MODULE.md."""

from .core import (NO_OBS, NOT_WATER, OPEN_WATER, PARTIAL_WATER, district_grid, encode_hls,
                   encode_s1, merge_water, validate_manifest)
from .events import STATUS, binary_water, load_rules, pixel_events, profile_stack
from .profile import field_profile, write_layers

__all__ = ["OPEN_WATER", "PARTIAL_WATER", "NOT_WATER", "NO_OBS", "encode_hls", "encode_s1",
           "merge_water", "district_grid", "validate_manifest", "STATUS", "binary_water",
           "load_rules", "pixel_events", "profile_stack", "write_layers", "field_profile",
           "opera_coverage", "build_water_stack"]


def __getattr__(name):  # network code is imported only when used
    if name in ("opera_coverage", "build_water_stack"):
        from . import access
        return getattr(access, name)
    raise AttributeError(name)