"""Every src/**/MODULE*.md lists signatures and CHAT KIT paths that match the code."""

import importlib.util
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
spec = importlib.util.spec_from_file_location(
    "check_module_docs", os.path.join(ROOT, "scripts", "check_module_docs.py"))
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def test_there_is_a_module_file_for_each_feature_area():
    names = {os.path.basename(p) for p in checker.module_files()}
    assert {"MODULE_water_balance.md", "MODULE_crop_stages_gdd.md", "MODULE_risk_calendar.md",
            "MODULE_hindcast.md", "MODULE_enso.md", "MODULE_post_flood.md",
            "MODULE_field_twin.md", "MODULE_provenance_guard.md", "MODULE_api.md",
            "MODULE_data_inputs.md", "MODULE.md"} <= names


def test_module_files_match_the_code():
    problems = [p for md in checker.module_files() for p in checker.check(md)]
    assert problems == []


def test_checker_catches_a_wrong_signature(tmp_path):
    md = tmp_path / "MODULE_x.md"
    lines = ["Code: src/agents/guard.py", "Public API:", "- `guard(text)` : wrong"]
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    problems = checker.check(str(md))
    assert any("differs from the code" in p for p in problems)
