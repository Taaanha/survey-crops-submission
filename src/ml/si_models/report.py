"""Known-event loader, NDVI threshold loader and model-card text for the W3 comparisons."""

import os
import re

import numpy as np
import pandas as pd

from si_models.validation import SMALL_SAMPLE_NOTE

REFERENCE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "reference")
EVENTS_PATH = os.path.join(REFERENCE_DIR, "w3_known_events.csv")
NDVI_PATH = os.path.join(REFERENCE_DIR, "r02_ndvi_bare_soil.csv")
NDVI_ITEM = "ndvi_bare_soil_upper_limit_nasa"
EVENT_ITEM = re.compile(r"^event\.([a-z0-9_]+)\.([a-z_]+)$")
SEASONS = ("kharif1", "kharif2", "rabi")


def load_events(path=EVENTS_PATH):
    """(used, not_used). used: district, season_year, season, event, source_title, source_url.
    A row is used only with a 4-digit year value, a season in its unit and an http source link;
    everything else (GAP rows) is listed in not_used with its notes."""
    df = pd.read_csv(path, keep_default_na=False)
    used, unused = [], []
    for r in df.itertuples():
        m = EVENT_ITEM.match(r.item)
        season = str(r.unit).split(" ")[0]
        ok = (m and re.fullmatch(r"\d{4}", str(r.value).strip()) and season in SEASONS
              and str(r.source_url).startswith("http") and str(r.source_title).strip())
        if ok:
            used.append({"district": m.group(2), "season_year": int(r.value), "season": season,
                         "event": m.group(1), "source_title": r.source_title, "source_url": r.source_url})
        else:
            unused.append({"item": r.item, "reason": r.notes or "no cited source"})
    cols = ["district", "season_year", "season", "event", "source_title", "source_url"]
    return pd.DataFrame(used, columns=cols), unused


def load_ndvi_threshold(path=NDVI_PATH, item=NDVI_ITEM):
    """The cited NDVI threshold row as a dict (value, source_title, source_url, notes), or None when
    the row is missing or its value is not a plain number (GAP)."""
    df = pd.read_csv(path, keep_default_na=False)
    r = df[df.item == item]
    if r.empty or not re.fullmatch(r"-?\d+(\.\d+)?", str(r.iloc[0].value).strip()):
        return None
    r = r.iloc[0]
    return {"item": item, "value": float(r.value), "source_title": r.source_title,
            "source_url": r.source_url, "notes": r.notes}


def fmt(ci, digits=2):
    """'0.42 (95% interval 0.10 to 0.80, n = 12)'; 'not assessed (n = 0)' when there is no value."""
    if ci is None or ci["n"] == 0 or np.isnan(ci["value"]):
        return f"not assessed (n = {0 if ci is None else ci['n']})"
    if np.isnan(ci["lo"]):
        return f"{ci['value']:.{digits}f} (no interval, n = {ci['n']})"
    return f"{ci['value']:.{digits}f} (95% interval {ci['lo']:.{digits}f} to {ci['hi']:.{digits}f}, n = {ci['n']})"


def model_card(name, problem, method, inputs, n_text, metrics, limits, used_by_app, seed):
    """Markdown model card. inputs: [(dataset, source_url)]; metrics: [(label, text)]; limits: [text]."""
    lines = [f"# Model card: {name}", "",
             f"- **Problem:** {problem}", f"- **Method:** {method}",
             f"- **Used by the app:** {used_by_app}", f"- **Sample (n):** {n_text}",
             f"- **Validation:** leave-one-year-out; bootstrap 95% intervals; seed {seed}", "",
             "## Inputs"]
    lines += [f"- {d} ({u})" for d, u in inputs]
    lines += ["", "## Metrics (held-out years only)"]
    lines += [f"- {label}: {text}" for label, text in metrics]
    lines += ["", "## Limits"]
    lines += [f"- {t}" for t in limits]
    lines += [f"- {SMALL_SAMPLE_NOTE}",
              "- It describes past seasons (\"flags past seasons that look unusual\", \"estimated\", \"tested on\"); "
              "it says nothing about a coming season.", ""]
    return "\n".join(lines)
