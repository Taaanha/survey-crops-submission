"""
scripts/check_module_docs.py

Checks that every MODULE*.md under src/ matches the code: each bullet that
starts with a backticked signature, e.g. "- `guard(text, tool_results)` : ...",
must name a function that exists in one of the files on the "Code:" line, with
the same arguments (spaces ignored). Bullets whose arguments are "..." are only
checked for the name. Also checks that every CHAT KIT path exists.

Run from the repo root: python scripts/check_module_docs.py
Exit code 1 if anything does not match.
"""

import ast
import glob
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SIGNATURE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)\((.*?)\)`")


def functions_in(path):
    """{name: arguments as written by ast.unparse} for every def in a file."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    return {node.name: ast.unparse(node.args)
            for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def squash(text):
    return re.sub(r"\s+", "", text)


def module_files():
    return sorted(glob.glob(os.path.join(ROOT, "src", "**", "MODULE*.md"), recursive=True))


def check(md_path):
    """List of problems found in one MODULE file (empty = matches the code)."""
    with open(md_path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    rel = os.path.relpath(md_path, ROOT)
    problems, code_files = [], []
    for line in lines:
        if line.startswith("Code:"):
            code_files = [p.strip() for p in line[len("Code:"):].split(",") if p.strip()]
    if not code_files:
        return [f"{rel}: no 'Code:' line"]
    defs = {}
    for code in code_files:
        full = os.path.join(ROOT, code)
        if not os.path.exists(full):
            problems.append(f"{rel}: Code file {code} does not exist")
        elif code.endswith(".py"):
            for name, args in functions_in(full).items():
                defs.setdefault(name, args)
    in_api = False
    for line in lines:
        if line.startswith("Public API"):
            in_api = True
            continue
        if in_api and not line.startswith("-"):
            in_api = False
        if in_api:
            head = line.split(" : ", 1)[0]
            for name, args in SIGNATURE.findall(head):
                if name not in defs:
                    problems.append(f"{rel}: {name}() is not defined in the Code files")
                elif args != "..." and squash(args) != squash(defs[name]):
                    problems.append(f"{rel}: {name}({args}) differs from the code: {name}({defs[name]})")
        if line.startswith("CHAT KIT:"):
            for item in line[len("CHAT KIT:"):].split(","):
                path = re.sub(r"\s*\(.*", "", item).strip()
                if path and not os.path.exists(os.path.join(ROOT, path)):
                    problems.append(f"{rel}: CHAT KIT path {path} does not exist")
    return problems


def main():
    files = module_files()
    problems = [p for md in files for p in check(md)]
    for p in problems:
        print(p)
    print(f"{len(files)} MODULE files checked, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
