"""Per-pixel flood event metrics (T3b). Pure deterministic code, no network.

A pixel's series is one value per satellite date: 1 = wet, 0 = dry, 255 = no observation.
Rules (data/reference/field_profile_rules.csv, project rules, not from the OPERA spec):
- an event is open while water is seen; it ends when `dry_obs_to_separate_events` observed dry
  dates in a row follow the last wet date;
- the drain date is the FIRST observed dry date after the last wet date, accepted only when it is
  confirmed by that many observed dry dates in a row;
- nothing is interpolated: cloudy dates stay unobserved, and the answer is a drain WINDOW
  [last wet date, first dry date];
- an event seen wet on fewer than `min_obs_per_event` observed dates, or whose window is longer
  than `max_drain_window_days`, gets status 'too few observations' and no drain date."""

import csv
import datetime as dt
import os

import numpy as np

from .core import NO_OBS, OPEN_WATER, PARTIAL_WATER

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
RULES_CSV = os.path.join(ROOT, "data", "reference", "field_profile_rules.csv")
_EPOCH_ORDINAL = 719163  # date(1970, 1, 1).toordinal()
_RULE_KEYS = ("min_obs_per_event", "max_drain_window_days", "dry_obs_to_separate_events")

STATUS = ["ok", "no event", "no observations", "too few observations",
          "still wet at series end", "drain not confirmed"]


def load_rules(path=RULES_CSV):
    """Rules from data/reference/field_profile_rules.csv as {item: number or text}."""
    rules = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            value = row["value"].strip()
            for cast in (int, float):
                try:
                    value = cast(value)
                    break
                except ValueError:
                    continue
            rules[row["item"]] = value
    return rules


def binary_water(states, view):
    """Class states (2 open water, 1 partial/vegetation water, 0 not water, 255 no observation)
    to 1 wet / 0 dry / 255 no observation. view 'open_water' counts only open water (the flood
    signal); 'any_water' also counts partial/vegetation water (context only)."""
    s = np.asarray(states)
    out = np.zeros(s.shape, dtype=np.uint8)
    if view == "open_water":
        out[s == OPEN_WATER] = 1
    elif view == "any_water":
        out[(s == OPEN_WATER) | (s == PARTIAL_WATER)] = 1
    else:
        raise ValueError(f"view must be 'open_water' or 'any_water', got {view!r}")
    out[s == NO_OBS] = NO_OBS
    return out


def _finish(ev, s, ords, dates, min_obs, max_gap, sep):
    wet, start, prior = ev["wet"], ev["start"], ev["prior_dry"]
    last_wet = wet[-1]
    dry_after = ev["dry_after"]
    first_dry = dry_after[0] if dry_after else None
    gap = ords[first_dry] - ords[last_wet] if first_dry is not None else None
    if first_dry is None:
        status = "still wet at series end"
    elif len(dry_after) < sep:
        status = "drain not confirmed"
    elif len(wet) < min_obs or gap > max_gap:
        status = "too few observations"
    else:
        status = "ok"
    ok = status == "ok"
    unobserved = None
    if first_dry is not None:
        unobserved = sum(1 for i in range(last_wet + 1, first_dry) if s[i] == NO_OBS)
    return {
        "start_date": dates[start],
        "last_wet_date": dates[last_wet],
        "first_dry_date": dates[first_dry] if first_dry is not None else None,
        "drain_date": dates[first_dry] if ok else None,
        "drain_window": [dates[last_wet], dates[first_dry]] if first_dry is not None else None,
        "gap_days": gap,
        "window_unobserved_dates": unobserved,
        "inundation_days_min": ords[last_wet] - ords[start],
        "inundation_days_max": (ords[first_dry] - ords[prior]) if ok and prior is not None else None,
        "left_censored": prior is None,
        "n_obs_event": len(wet),
        "status": status,
    }


def pixel_events(dates, series, min_obs_per_event=2, max_drain_window_days=12,
                 dry_obs_to_separate_events=2, **_other_rules):
    """Flood events of one pixel. dates: ISO strings in time order; series: 1 / 0 / 255.
    Returns {n_events (None if never observed), status, events: [...], n_observations, and the
    main event's numbers at top level: first_wet_date (of the first event), last_wet_date,
    first_dry_date, drain_date, drain_window, gap_days, inundation_days_min/max}.
    The main event is the one with the longest observed wet span."""
    s = np.asarray(series)
    if len(dates) != len(s):
        raise ValueError("dates and series must have the same length")
    ords = [dt.date.fromisoformat(d).toordinal() for d in dates]
    observed = [i for i in range(len(s)) if s[i] != NO_OBS]
    out = {"n_observations": len(observed), "n_events": None, "status": "no observations",
           "events": [], "first_wet_date": None, "last_wet_date": None, "first_dry_date": None,
           "drain_date": None, "drain_window": None, "gap_days": None,
           "inundation_days_min": None, "inundation_days_max": None}
    if not observed:
        return out

    raw, cur, last_dry = [], None, None
    for i in observed:
        if s[i] == 1:
            if cur is None:
                cur = {"start": i, "prior_dry": last_dry, "wet": [i], "dry_after": []}
            else:
                cur["wet"].append(i)
                cur["dry_after"] = []
        else:
            last_dry = i
            if cur is not None:
                cur["dry_after"].append(i)
                if len(cur["dry_after"]) >= dry_obs_to_separate_events:
                    raw.append(cur)
                    cur = None
    if cur is not None:
        raw.append(cur)

    events = [_finish(e, s, ords, dates, min_obs_per_event, max_drain_window_days,
                      dry_obs_to_separate_events) for e in raw]
    out["events"] = events
    out["n_events"] = len(events)
    if not events:
        out["status"] = "no event"
        return out
    main = max(range(len(events)), key=lambda k: (events[k]["inundation_days_min"], -k))
    m = events[main]
    out.update(status=m["status"], first_wet_date=events[0]["start_date"],
               last_wet_date=m["last_wet_date"], first_dry_date=m["first_dry_date"],
               drain_date=m["drain_date"], drain_window=m["drain_window"], gap_days=m["gap_days"],
               inundation_days_min=m["inundation_days_min"],
               inundation_days_max=m["inundation_days_max"])
    return out


def _day(iso):
    return -1 if iso is None else dt.date.fromisoformat(iso).toordinal() - _EPOCH_ORDINAL


def _num(v):
    return -1 if v is None else int(v)


def profile_stack(dates, stack, view, rules):
    """Event metrics for every pixel of a class stack [dates, rows, cols] (states 2/1/0/255).
    Returns int32 arrays [rows, cols], -1 = none / not applicable: n_events, status (index into
    STATUS), first_wet_date, last_wet_date, drain_date (days since 1970-01-01), window_start,
    window_end, gap_days, inundation_days_min, inundation_days_max, n_observed.
    Identical pixel series are computed once (fast on 667 x 667 grids)."""
    arr = np.asarray(stack)
    t, h, w = arr.shape
    b = binary_water(arr, view).reshape(t, -1)
    uniq, inverse = np.unique(b.T, axis=0, return_inverse=True)
    inverse = inverse.reshape(-1)
    kw = {k: rules[k] for k in _RULE_KEYS if k in rules}
    names = ("n_events", "status", "first_wet_date", "last_wet_date", "drain_date",
             "window_start", "window_end", "gap_days", "inundation_days_min",
             "inundation_days_max", "n_observed")
    table = {n: np.full(len(uniq), -1, dtype=np.int32) for n in names}
    for u, column in enumerate(uniq):
        r = pixel_events(dates, column, **kw)
        table["n_events"][u] = _num(r["n_events"])
        table["status"][u] = STATUS.index(r["status"])
        table["first_wet_date"][u] = _day(r["first_wet_date"])
        table["last_wet_date"][u] = _day(r["last_wet_date"])
        table["drain_date"][u] = _day(r["drain_date"])
        table["window_start"][u] = _day(r["drain_window"][0]) if r["drain_window"] else -1
        table["window_end"][u] = _day(r["drain_window"][1]) if r["drain_window"] else -1
        table["gap_days"][u] = _num(r["gap_days"])
        table["inundation_days_min"][u] = _num(r["inundation_days_min"])
        table["inundation_days_max"][u] = _num(r["inundation_days_max"])
        table["n_observed"][u] = r["n_observations"]
    return {n: table[n][inverse].reshape(h, w) for n in names}