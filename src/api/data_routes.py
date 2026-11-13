"""Read-only endpoints for the data the app holds (proposed in docs/contract_change_proposals.md section 14).

  GET /api/v1/data/sources                      every processed dataset: status, source link, units, resolution
  GET /api/v1/data/reference                    every file in data/reference/ (kind, rows kept / skipped)
  GET /api/v1/data/reference/{name}?limit=&offset=   one file, row by row
  GET /api/v1/disease-rules                     data/reference/disease_rules_draft.csv (same as above, by name)

Nothing is computed or invented here. Item/value files go through the strict loader
(src/compute/reference.py): a row is "kept" only with a source link and a parseable value, otherwise it
is listed under "skipped" with the reason, never hidden and never shown as a number. Wide tables
(crops.csv, soil_params.csv, ...) are returned as they are, with their own *_src columns.
register(app, envelope, ApiError) is called once from app.py."""

import csv
import functools
import os

import pandas as pd
from fastapi.responses import JSONResponse

import reference as ref
from sat_layers.status import STATUS_PATH, load_status

ROOT = ref.REPO_ROOT
REF_DIR = ref.REFERENCE_DIR
PROCESSED_DIR = os.path.join(ROOT, "data", "processed")
MAX_LIMIT = 5000
DISEASE_FILE = "disease_rules_draft.csv"


def _none(value):
    return None if isinstance(value, float) and value != value else value


def _records(df):
    return [{k: _none(v) for k, v in row.items()} for row in df.to_dict("records")]


@functools.lru_cache(maxsize=1)
def reference_files():
    """{file name: {"kind", "columns", "kept", "skipped"}} for every csv in data/reference/."""
    out = {}
    for name in sorted(os.listdir(REF_DIR)):
        if not name.endswith(".csv") or name.startswith("_"):
            continue
        path = os.path.join(REF_DIR, name)
        with open(path, encoding="utf-8-sig", newline="") as f:
            header = [h.strip() for h in next(csv.reader(f), [])]
        if header[:len(ref.COLUMNS)] == ref.COLUMNS:
            kept, skipped = ref.load_file(path)
            out[name] = {"kind": "item_value", "columns": header, "kept": len(kept), "skipped": len(skipped)}
        else:
            n = len(pd.read_csv(path, dtype=str, keep_default_na=False))
            out[name] = {"kind": "table", "columns": header, "kept": n, "skipped": 0}
    return out


def processed_files():
    out = []
    for name in sorted(os.listdir(PROCESSED_DIR)):
        path = os.path.join(PROCESSED_DIR, name)
        if os.path.isfile(path) and not name.startswith("."):
            out.append({"file": name, "bytes": os.path.getsize(path)})
    return out


def register(app, envelope, ApiError):
    def respond(endpoint, request, build):
        try:
            data, notices, provenance = build()
            return JSONResponse(envelope(endpoint, request, data, None, notices, provenance=provenance))
        except ApiError as err:
            body = envelope(endpoint, request, None,
                            errors=[{"code": err.code, "en": err.en, "bn": err.bn}], provenance=[])
            return JSONResponse(body, status_code=err.status)
        except Exception as exc:  # noqa: BLE001 - the contract forbids an empty body
            err = ApiError("INTERNAL", f"Internal error: {type(exc).__name__}")
            return JSONResponse(envelope(endpoint, request, None, provenance=[], errors=[
                {"code": err.code, "en": err.en, "bn": err.bn}]), status_code=500)

    @app.get("/api/v1/data/sources")
    def data_sources():
        def build():
            status = _records(load_status(STATUS_PATH))
            data = {"datasets": status, "processed_files": processed_files(),
                    "note": "From docs/w1b_data_status.csv (status and reason as recorded) and the "
                            "files in data/processed/. A dataset marked 'not assessed' is listed with "
                            "its reason and is not used. Licence text is not part of this table."}
            prov = []
            for r in status:
                if r.get("source_url"):
                    prov.append({"id": f"s{len(prov) + 1}", "dataset": r["dataset"],
                                 "url": r["source_url"], "source_url": r["source_url"]})
            return data, [], prov
        return respond("/api/v1/data/sources", {}, build)

    @app.get("/api/v1/data/reference")
    def data_reference_list():
        def build():
            files = reference_files()
            data = {"files": [{"file": k, **v} for k, v in files.items()],
                    "note": "item_value files: a row is kept only with a source link and a value that "
                            "parses; the rest are listed as skipped with the reason. table files are "
                            "returned as they are."}
            return data, [], []
        return respond("/api/v1/data/reference", {}, build)

    def one_file(endpoint, name, limit, offset):
        request = {"name": name, "limit": limit, "offset": offset}

        def build():
            files = reference_files()
            fname = name if name.endswith(".csv") else f"{name}.csv"
            if fname not in files:
                raise ApiError("BAD_PARAMETER", f"Unknown reference file: {name}. Known: "
                               f"{', '.join(sorted(files))}", "name")
            lim = MAX_LIMIT if limit is None else limit
            if not (1 <= lim <= MAX_LIMIT) or offset < 0:
                raise ApiError("BAD_PARAMETER", f"limit must be 1 to {MAX_LIMIT}, offset 0 or more.",
                               "limit")
            info, path = files[fname], os.path.join(REF_DIR, fname)
            notices = []
            if info["kind"] == "item_value":
                kept, skipped = ref.load_file(path)
                rows = _records(kept.iloc[offset:offset + lim])
                data = {"file": fname, "kind": "item_value", "total_kept": len(kept),
                        "rows": rows, "skipped": _records(skipped)}
                prov, seen = [], set()
                for r in rows:
                    if r["source_url"] not in seen:
                        seen.add(r["source_url"])
                        prov.append({"id": f"r{len(prov) + 1}", "dataset": r["source_title"],
                                     "url": r["source_url"], "source_url": r["source_url"],
                                     "page": r["page"]})
                if len(skipped):
                    notices.append({"level": "caution",
                                    "en": f"{len(skipped)} row(s) in {fname} are not used because they "
                                          "have no source link or the value does not parse (see skipped).",
                                    "bn": f"{fname} ফাইলের {len(skipped)}টি সারি ব্যবহার হয়নি, কারণ "
                                          "সূত্রের লিংক নেই বা মান পড়া যায়নি (skipped দেখুন)।"})
                if fname == DISEASE_FILE:
                    notices.append({"level": "caution",
                                    "en": "Disease weather rules are a draft. Only the potato late-blight "
                                          "rows are used (counts in /risk-calendar); the others are not "
                                          "used in any count or ranking.",
                                    "bn": "রোগের আবহাওয়া-নিয়মগুলো খসড়া। শুধু আলুর লেট ব্লাইটের সারিগুলো ব্যবহার হয় "
                                          "(গণনা /risk-calendar-এ); বাকিগুলো কোনো গণনা বা র‍্যাঙ্কিংয়ে ব্যবহার হয় না।"})
                return data, notices, prov
            df = pd.read_csv(path, dtype=str, keep_default_na=False)
            data = {"file": fname, "kind": "table", "columns": info["columns"], "total_rows": len(df),
                    "rows": _records(df.iloc[offset:offset + lim])}
            return data, notices, []
        return respond(endpoint, request, build)

    @app.get("/api/v1/data/reference/{name}")
    def data_reference_file(name: str, limit: int = None, offset: int = 0):
        return one_file(f"/api/v1/data/reference/{name}", name, limit, offset)

    @app.get("/api/v1/disease-rules")
    def disease_rules():
        return one_file("/api/v1/disease-rules", DISEASE_FILE, None, 0)
