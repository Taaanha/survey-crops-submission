"""
src/compute/strategies/facts.py

Per-crop cited facts for the W4 strategy cards: root depth (FAO-56 Table 22),
crop family and the pest-cycle rule, nitrogen fixing (crops.csv legume flag),
forage, residue / organic matter, and market price. Layer 1, no AI.

Every fact is either {"status": "assessed", ...} with full provenance or
{"status": "gap", "reason": ...}. A gap is never shown as 0.

Two files are read raw (with a source-URL check), not through the strict
loader, which skips every row in them: crop_family.csv (unit "family" /
"statement" is not a loader text unit) and forage.csv (values like
"30.0 (range 26.4 to 33.8)"). The returned provenance says so, the same way
W2's heavy_rain.py reports its raw BMD row. Research teammate: normalising
those units/values lets the strict loader take over.
"""

import datetime as _dt
import os
import re

import pandas as pd

from reference import REFERENCE_DIR, load_reference
from common import Provenance, measured
from rotation.crop_table import load_crop_table
from prices import describe as describe_price, to_bdt_per_kg, TARGET_UNIT as PRICE_UNIT

FACT_FILES = ["crop_params.csv", "residue.csv", "prices.csv"]
RAW_FILES = {"family": "crop_family.csv", "forage": "forage.csv"}
URL_RE = re.compile(r"^https?://", re.IGNORECASE)

# FAO-56 Table 22 has one "Rice" row; both seasons use it and the note says so.
TABLE22_ALIAS = {"aman_rice": "rice", "boro_rice": "rice"}

PRICE_PREFERENCE = ("farmgate_or_wholesale", "wholesale", "wholesale_high_quality",
                    "wholesale_coarse", "retail", "retail_high_quality", "retail_coarse")

PEST_RULE_ITEM = "rotation.pest_cycle.same_family_succession"
PEST_NOTE = ("needs local review (US vegetable-garden source, not Bangladesh field crops; "
             "the source says avoiding pest buildup, not that rotation breaks every cycle)")
RAW_NOTE = ("read raw from {file} (the strict loader skips these rows: unit/value format); "
            "research teammate to normalise")


def _gap(reason):
    return {"status": "gap", "reason": reason}


def _file_date(name, reference_dir=REFERENCE_DIR):
    path = os.path.join(reference_dir, name)
    return _dt.date.fromtimestamp(os.path.getmtime(path)).isoformat()


def _prov(file, line, source_title, source_url, page, note=""):
    return Provenance(dataset=source_title or "data/reference row",
                      source_url=source_url,
                      retrieved=_file_date(file),
                      granule_or_file=f"data/reference/{file}:{line}",
                      note=(f"page: {page}; " if page else "") + note)


def _kept_measure(row, note=""):
    return measured(float(row["value"]), row["unit"],
                    _prov(row["file"], row["line"], row["source_title"],
                          row["source_url"], row["page"], note))


def load_facts_reference(reference_dir=REFERENCE_DIR):
    """The strict-loader view of the W4 fact files (kept and skipped rows)."""
    return load_reference(files=FACT_FILES, reference_dir=reference_dir)


def _load_raw(which, reference_dir=REFERENCE_DIR):
    """Rows of a raw-read file that carry a real URL and a non-GAP value."""
    name = RAW_FILES[which]
    path = os.path.join(reference_dir, name)
    if not os.path.exists(path):
        return pd.DataFrame(), name
    table = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    ok = table[table["source_url"].str.strip().str.match(URL_RE)
               & (table["value"].str.strip() != "")
               & (table["value"].str.strip().str.upper() != "GAP")].copy()
    ok["line"] = ok.index + 2        # header is line 1
    return ok, name


# ---------------- root depth (FAO-56 Table 22, strict loader) ----------------

def root_depth(crop, ref=None, reference_dir=REFERENCE_DIR):
    ref = ref or load_facts_reference(reference_dir)
    alias = TABLE22_ALIAS.get(crop, crop)
    lo, hi = ref.rows(f"{alias}.zr_min_m"), ref.rows(f"{alias}.zr_max_m")
    if lo.empty or hi.empty:
        return _gap(f"no cited FAO-56 Table 22 root depth row for {crop} "
                    "(crop_params.csv; research teammate)")
    note = f"Table 22 '{alias}' row used for {crop}" if alias != crop else ""
    return {"status": "assessed",
            "zr_min_m": _kept_measure(lo.iloc[0], note),
            "zr_max_m": _kept_measure(hi.iloc[0], note),
            "note": note or "FAO-56 Table 22 effective rooting depth; deep roots "
                            "are read as better infiltration (FAO-56 usage)"}


# ---------------- family and the pest-cycle rule (raw read) ----------------

def family(crop, ref=None, reference_dir=REFERENCE_DIR):
    rows, name = _load_raw("family", reference_dir)
    if rows.empty:
        return _gap("crop_family.csv not found or has no row with a source URL")
    hit = rows[rows["item"].str.strip() == f"{crop}.family.name"]
    if hit.empty:
        return _gap(f"no cited family row for {crop} in {name}")
    r = hit.iloc[0]
    return {"status": "assessed", "value": r["value"].strip(),
            "provenance": _prov(name, r["line"], r["source_title"], r["source_url"],
                                r["page"], RAW_NOTE.format(file=name)).to_dict()}


def pest_rule(ref=None, reference_dir=REFERENCE_DIR):
    rows, name = _load_raw("family", reference_dir)
    hit = rows[rows["item"].str.strip() == PEST_RULE_ITEM] if not rows.empty else rows
    if rows.empty or hit.empty:
        return _gap("no cited pest-cycle rule row (crop_family.csv)")
    r = hit.iloc[0]
    return {"status": "assessed", "value": r["value"].strip(),
            "provenance": _prov(name, r["line"], r["source_title"], r["source_url"],
                                r["page"], RAW_NOTE.format(file=name)).to_dict(),
            "note": PEST_NOTE}


def pest_cycle_break(crops, ref=None, reference_dir=REFERENCE_DIR):
    """Whether consecutive crops change family, under the cited rule.
    Labelled "needs local review"; a crop with no family row makes it a gap."""
    rule = pest_rule(ref, reference_dir)
    if rule["status"] == "gap":
        return rule
    families = []
    for crop in crops:
        fam = family(crop, ref, reference_dir)
        if fam["status"] == "gap":
            return _gap(f"family unknown for {crop}: {fam['reason']}")
        families.append(fam["value"])
    breaks = all(a != b for a, b in zip(families, families[1:])) if len(families) > 1 else False
    return {"status": "assessed", "breaks_cycle": breaks, "families": families,
            "rule": rule, "note": PEST_NOTE}


# ---------------- nitrogen fixing (crops.csv legume flag) ----------------

def nitrogen_fixing(crop, crop_table=None):
    table = crop_table if crop_table is not None else load_crop_table()
    rows = table[table["crop"] == crop]
    if rows.empty:
        return _gap(f"{crop} is not in data/reference/crops.csv")
    r = rows.iloc[0]
    flag = r["is_legume"].strip().lower()
    if flag not in ("yes", "no"):
        return _gap(f"legume flag unknown for {crop} (NEEDS SOURCE in crops.csv)")
    return {"status": "assessed", "value": flag == "yes", "source": r["legume_src"],
            "note": "legume flag from data/reference/crops.csv (nitrogen fixing read "
                    "as a yes/no fact; no kg N per hectare is cited)"}


# ---------------- forage (raw read), residue and price (strict loader) ----------------

def forage(crop, ref=None, reference_dir=REFERENCE_DIR):
    rows, name = _load_raw("forage", reference_dir)
    hit = rows[rows["item"].str.startswith(f"{crop}.forage.")] if not rows.empty else rows
    if rows.empty or hit.empty:
        return _gap(f"no cited forage row for {crop} (forage.csv; research teammate)")
    out = [{"item": r["item"], "value_text": r["value"], "unit": r["unit"],
            "provenance": _prov(name, r["line"], r["source_title"], r["source_url"],
                                r["page"], RAW_NOTE.format(file=name)).to_dict()}
           for _, r in hit.iterrows()]
    return {"status": "assessed", "rows": out,
            "note": "values quoted as stated in the source page, not recomputed"}


def residue(crop, ref=None, reference_dir=REFERENCE_DIR):
    """Cited residue / organic-matter rows. A ratio needs a yield to become t/ha,
    and no yield model is wired, so the rows are shown as cited facts only."""
    ref = ref or load_facts_reference(reference_dir)
    hit = ref.with_prefix(f"{crop}.residue.")
    if hit.empty:
        return _gap(f"no cited residue row for {crop} (residue.csv; research teammate)")
    rows = [{"item": r["item"], "measure": _kept_measure(r)} for _, r in hit.iterrows()]
    return {"status": "assessed", "rows": rows,
            "note": "cited ratios and amounts only; no residue-per-hectare is computed "
                    "(no yield model), so this is organic-matter context, not a score"}


def price(crop, ref=None, reference_dir=REFERENCE_DIR):
    """The first cited price row in PRICE_PREFERENCE order, as BDT/kg of the
    market product, with its type, month, market and source mode (prices module).
    Never an income estimate (no yield times price model)."""
    ref = ref or load_facts_reference(reference_dir)
    for suffix in PRICE_PREFERENCE:
        rows = ref.rows(f"{crop}.price.{suffix}")
        rows = rows[rows["kind"] == "number"]
        for _, r in rows.iterrows():
            kg = to_bdt_per_kg(r["value"], r["unit"])
            if kg is None:        # a unit we cannot convert exactly is skipped, never guessed
                continue
            was = f" (converted from {r['value']} {r['unit']})" if r["unit"].lower() != "bdt/kg" else ""
            r = r.copy()
            r["value"], r["unit"] = kg, PRICE_UNIT
            return {"status": "assessed", "item": r["item"], "crop": crop,
                    "measure": _kept_measure(r, "a price (BDT per kg of the market product), "
                                                "not farm-gate income per hectare" + was),
                    **describe_price(r["item"])}
    return _gap(f"no cited price for {crop} (prices.csv; the DAM farmgate rows "
                "without a source URL are skipped; research teammate)")
