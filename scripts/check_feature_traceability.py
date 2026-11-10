"""Check that every scenario in features/ is tested and every test names a scenario.

Each scenario carries one tag `@AC-<key>-<n>`, where `<key>` is its file's name
(`features/<key>.feature`). Each test function in `tests/test_*.py` names the tags it
exercises in its docstring. See knowledge/feature_procedure.md.

Errors: a feature file whose name isn't a key; a scenario with no tag, or more than one;
text that starts like a tag but isn't one; a tag that isn't on a scenario; a tag whose key
isn't its file's; a tag used twice; a scenario no test names; a test file that isn't valid
Python; a test that names no tag; a test that names a tag that doesn't exist. Step doc
strings are skipped, and functions nested inside a test aren't tests.

Usage: python scripts/check_feature_traceability.py [--root DIR]   (exit 1 on any problem)
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY = re.compile(r"^[a-z0-9_]+$")
TAG = re.compile(r"@AC-([a-z0-9_]+)-(\d+)(?![\w-])")
SCENARIO = re.compile(r"^\s*(Scenario|Scenario Outline|Scenario Template|Example):")
DOC_STRING = ('"""', "```")


def read_features(root: Path, problems: list[str]) -> dict[str, str]:
    """Return {tag: 'file:line'} for every tagged scenario, recording problems."""
    scenarios: dict[str, str] = {}
    for f in sorted((root / "features").glob("*.feature")):
        rel = f.relative_to(root).as_posix()
        if not KEY.match(f.stem):
            problems.append(f"{rel}: file name isn't a key ([a-z0-9_]+)")
            continue
        lines = f.read_text(encoding="utf-8").splitlines()
        if not any(line.lstrip().startswith("Feature:") for line in lines):
            problems.append(f"{rel}: has no Feature: line")
        pending: list[tuple[str, int]] = []
        in_doc = None
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if in_doc:
                if s.startswith(in_doc):
                    in_doc = None
                continue
            if s.startswith(DOC_STRING):
                in_doc = s[:3]
            elif s.startswith("@"):
                for token in s.split():
                    m = TAG.fullmatch(token)
                    if m:
                        pending.append((token, i))
                    elif token.startswith("@AC-"):
                        problems.append(f"{rel}:{i}: {token!r} isn't an @AC-<key>-<n> tag")
                continue
            elif SCENARIO.match(line):
                where = f"{rel}:{i}"
                if len(pending) != 1:
                    problems.append(f"{where}: scenario has {len(pending)} @AC- tags, not one")
                    # Keep them, so tests naming them aren't reported as well.
                    for tag, _ in pending:
                        scenarios.setdefault(tag, where)
                else:
                    tag = pending[0][0]
                    if tag.split("-")[1] != f.stem:
                        problems.append(f"{where}: {tag} doesn't use this file's key {f.stem!r}")
                    elif tag in scenarios:
                        problems.append(f"{where}: {tag} is already used at {scenarios[tag]}")
                    else:
                        scenarios[tag] = where
                pending = []
                continue
            if s and not s.startswith("#"):
                for tag, n in pending:
                    problems.append(f"{rel}:{n}: {tag} isn't on a scenario")
                pending = []
        for tag, n in pending:
            problems.append(f"{rel}:{n}: {tag} isn't on a scenario")
    return scenarios


def test_functions(body: list[ast.stmt]):
    """Yield the test functions pytest would collect from a module or class body.

    That is `test*` functions, also under if, try and with blocks, and their methods in
    `Test*` classes, but not functions nested inside functions or methods of other classes."""
    for node in body:
        if isinstance(node, ast.ClassDef):
            if node.name.startswith("Test"):
                yield from test_functions(node.body)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test"):
                yield node
        elif isinstance(node, (ast.If, ast.Try, ast.With)):
            for block in ("body", "orelse", "finalbody"):
                yield from test_functions(getattr(node, block, []))
            for handler in getattr(node, "handlers", []):
                yield from test_functions(handler.body)


def read_tests(root: Path, problems: list[str]) -> dict[str, set[str]]:
    """Return {'file::test': {tags}} for every test function in tests/test_*.py."""
    tests: dict[str, set[str]] = {}
    for f in sorted((root / "tests").glob("test_*.py")):
        rel = f.relative_to(root).as_posix()
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError as e:
            problems.append(f"{rel}:{e.lineno}: can't be read as Python ({e.msg})")
            continue
        for node in test_functions(tree.body):
            doc = ast.get_docstring(node) or ""
            tests[f"{rel}::{node.name}"] = {f"@AC-{k}-{n}" for k, n in TAG.findall(doc)}
    return tests


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=ROOT, help="repository root (default: this one)")
    root = ap.parse_args(argv).root
    problems: list[str] = []
    scenarios = read_features(root, problems)
    tests = read_tests(root, problems)
    named: set[str] = set()
    for test, tags in tests.items():
        if not tags:
            problems.append(f"{test}: names no @AC- tag in its docstring")
        for tag in sorted(tags - scenarios.keys()):
            problems.append(f"{test}: names {tag}, which no scenario has")
        named |= tags
    for tag, where in sorted(scenarios.items(), key=lambda kv: kv[1]):
        if tag not in named:
            problems.append(f"{where}: no test names {tag}")
    for p in problems:
        print(f"[ERROR] {p}")
    print(f"{len(problems)} problem(s): {len(scenarios)} scenario(s), {len(tests)} test(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
