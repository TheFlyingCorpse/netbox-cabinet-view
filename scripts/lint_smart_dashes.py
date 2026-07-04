#!/usr/bin/env python3
"""Reject smart dashes (em-dash U+2014, en-dash U+2013) in code files
and markdown.

Source files (Python/YAML/shell), config files, and markdown prose must
use ASCII hyphen-minus (-) only. Smart dashes look right in source but
break in:

- busybox / ash / dash shells with non-UTF-8 locale (LC_ALL=C or similar)
- Docker log pipelines / journald with stripped multibyte encoding
- Windows-on-OT operator consoles (ISO-8859-1 default)
- grep / sed / awk rules that assume ASCII
- shell `${VAR:?message}` parameter expansion where the error path
  may render via a limited stderr encoder

Markdown is NOT exempt: operator runbooks and CHANGELOG entries get
grepped by the same downstream tools.

Run:
    python scripts/lint_smart_dashes.py [FILE ...]

Exit 0 clean. Exit 1 with file:line:char report otherwise.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from pathlib import Path

SMART_DASHES = {
    "\u2014": "em-dash (U+2014)",
    "\u2013": "en-dash (U+2013)",
}

# Extensions to check. Markdown IS included: operator runbooks and
# CHANGELOG entries get grepped by the same downstream tools that
# trip on multibyte dashes.
CODE_EXTS = {
    ".sh",
    ".bash",
    ".zsh",
    ".py",
    ".pyi",
    ".yml",
    ".yaml",
    ".html",
    ".htm",
    ".tmpl",
    ".template",
    ".j2",
    ".jinja",
    ".jinja2",
    ".toml",
    ".cfg",
    ".ini",
    ".conf",
    ".json",
    ".sql",
    ".dockerfile",
    ".md",
}

# Files that are not matched by extension but must still be checked.
NAMED_CHECK = {"Dockerfile", "Makefile"}

# Directories to skip when invoked without explicit file args.
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".claude",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "migrations",
}
READ_EXCEPTIONS = (OSError, UnicodeDecodeError)


def _should_check(path: Path) -> bool:
    if path.name in NAMED_CHECK:
        return True
    return path.suffix in CODE_EXTS


def _walk_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            if _should_check(path):
                yield path


def _scan(path: Path) -> list[tuple[int, int, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except READ_EXCEPTIONS:
        return []
    hits: list[tuple[int, int, str]] = []
    for line_idx, line in enumerate(text.splitlines(), start=1):
        for col_idx, char in enumerate(line, start=1):
            if char in SMART_DASHES:
                hits.append((line_idx, col_idx, SMART_DASHES[char]))
    return hits


def main(argv: list[str]) -> int:
    targets = [Path(path) for path in argv] if argv else list(_walk_files(Path.cwd()))

    any_hit = False
    for path in targets:
        if not path.is_file():
            continue
        if not _should_check(path):
            continue
        hits = _scan(path)
        if not hits:
            continue
        any_hit = True
        for line, col, kind in hits:
            print(f"{path}:{line}:{col}: {kind} - use ASCII hyphen (-)")

    if any_hit:
        print(
            "\nSmart dashes rejected. Replace em-dash (U+2014) and "
            "en-dash (U+2013) with ASCII hyphen (-) in code AND markdown. "
            "Markdown is NOT exempt; operator runbooks and CHANGELOG "
            "entries get grepped by the same tools that trip on multibyte "
            "dashes.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
