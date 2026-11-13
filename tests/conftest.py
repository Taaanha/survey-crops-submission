"""Puts src/compute on the import path so tests/<feature>/ can `import common`."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for sub in (("src", "compute"), ("src", "agents"), ("src", "acquire"), ("src", "ml")):
    path = os.path.join(ROOT, *sub)
    if path not in sys.path:
        sys.path.insert(0, path)
