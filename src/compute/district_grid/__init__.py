"""64-district boundaries and the common 0.1 degree analysis grid (W1).

The names below are loaded on first use, because boundaries.py and grid.py need shapely and the
deployed API (which only reads features.py through indicators) does not install it."""

__all__ = ["LIVE_DISTRICTS", "load_districts", "slug_for", "cell_weights", "district_mean", "imerg_axes"]


def __getattr__(name):
    if name in ("LIVE_DISTRICTS", "load_districts", "slug_for"):
        from . import boundaries
        return getattr(boundaries, name)
    if name in ("cell_weights", "district_mean", "imerg_axes"):
        from . import grid
        return getattr(grid, name)
    raise AttributeError(name)
