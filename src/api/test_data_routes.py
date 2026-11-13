"""Tests for the data/reference endpoints and the deploy files the API needs at runtime."""

import os
import re
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient  # noqa: E402

import app as api  # noqa: E402

client = TestClient(api.app)


def test_sources_lists_every_status_row_with_its_reason_and_link():
    b = client.get("/api/v1/data/sources").json()
    assert b["errors"] == [] and b["data"]["datasets"]
    for d in b["data"]["datasets"]:
        assert {"key", "dataset", "status", "reason", "source_url"} <= set(d)
    assert any(d["status"] == "not assessed" for d in b["data"]["datasets"])  # kept in the list
    assert b["data"]["processed_files"]


def test_reference_list_covers_every_csv_in_the_folder():
    b = client.get("/api/v1/data/reference").json()
    names = {f["file"] for f in b["data"]["files"]}
    on_disk = {n for n in os.listdir(os.path.join(ROOT, "data", "reference"))
               if n.endswith(".csv") and not n.startswith("_")}
    assert names == on_disk
    assert {f["kind"] for f in b["data"]["files"]} == {"item_value", "table"}


def test_disease_rules_shows_kept_and_skipped_rows_and_a_draft_notice():
    b = client.get("/api/v1/disease-rules").json()
    d = b["data"]
    assert b["errors"] == [] and d["file"] == "disease_rules_draft.csv"
    assert d["total_kept"] == len(d["rows"]) > 0
    assert all(r["source_url"].startswith("http") for r in d["rows"])
    assert all(p["url"] for p in b["provenance"])
    assert any("draft" in n["en"].lower() for n in b["notices"])
    for s in d["skipped"]:           # a skipped row is explained, never shown as a value
        assert s["reason"]


def test_table_file_is_paged():
    r = client.get("/api/v1/data/reference/crops", params={"limit": 2, "offset": 1})
    d = r.json()["data"]
    assert r.status_code == 200 and d["kind"] == "table" and len(d["rows"]) == 2


@pytest.mark.parametrize("path,params", [
    ("/api/v1/data/reference/nope", {}),
    ("/api/v1/data/reference/..%2Fapp", {}),
    ("/api/v1/data/reference/crops", {"limit": 0}),
    ("/api/v1/data/reference/crops", {"offset": -1}),
])
def test_bad_requests_use_the_error_envelope(path, params):
    r = client.get(path, params=params)
    assert r.status_code in (400, 404)
    if r.headers["content-type"].startswith("application/json") and "errors" in r.json():
        assert r.json()["data"] is None


def test_dockerfile_ships_the_docs_files_the_api_reads():
    """The Render image copies only some folders; /map/layers and /models need these two."""
    docker = open(os.path.join(ROOT, "Dockerfile"), encoding="utf-8").read()
    ignore = open(os.path.join(ROOT, ".dockerignore"), encoding="utf-8").read()
    for path in ("docs/w1b_data_status.csv", "docs/results/w3_metrics.json"):
        assert re.search(rf"^COPY {re.escape(path)} ", docker, re.M), path
        assert f"!{path}" in ignore, path
        assert os.path.isfile(os.path.join(ROOT, path))
