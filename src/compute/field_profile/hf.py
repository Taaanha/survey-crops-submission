"""Download the field-profile layers of one district from a Hugging Face dataset repo.

Plain HTTPS requests (no extra library). HF_TOKEN is read from the environment only for private
repos and is never printed. Repo: set HF_DATASET_REPO, or edit DEFAULT_REPO."""

import json
import os
import urllib.request

DEFAULT_REPO = os.environ.get("HF_DATASET_REPO", "Tanha01/survey-crops-data")


def _fetch(url, dest):
    req = urllib.request.Request(url)
    token = os.environ.get("HF_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as out:
        out.write(resp.read())


def download_layers(district, dest, repo=None):
    """Download layers_manifest_<district>.json and the layer files it lists (from the layers/
    folder of the dataset repo) into dest; files already present are kept. Returns dest."""
    base = f"https://huggingface.co/datasets/{repo or DEFAULT_REPO}/resolve/main/layers/"
    os.makedirs(dest, exist_ok=True)
    mname = f"layers_manifest_{district}.json"
    mpath = os.path.join(dest, mname)
    _fetch(base + mname, mpath)
    with open(mpath, encoding="utf-8") as f:
        manifest = json.load(f)
    for name in manifest["files"].values():
        target = os.path.join(dest, name)
        if not os.path.exists(target):
            _fetch(base + name, target)
    return dest