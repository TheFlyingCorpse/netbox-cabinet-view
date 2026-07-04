"""Reject section sign and pilcrow characters."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from pathlib import Path

FORBIDDEN = {
    "\u00a7": "SECTION SIGN",
    "\u00b6": "PILCROW",
}

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


def _walk_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [dirname for dirname in dirnames if dirname not in SKIP_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


def check_file(path: Path) -> list[tuple[int, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except READ_EXCEPTIONS:
        return []
    hits: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if any(char in line for char in FORBIDDEN):
            hits.append((lineno, line.rstrip()))
    return hits


def main(argv: list[str]) -> int:
    targets = [Path(raw) for raw in argv[1:]] if len(argv) > 1 else list(_walk_files(Path.cwd()))
    failed = False
    for path in targets:
        if not path.is_file():
            continue
        hits = check_file(path)
        if not hits:
            continue
        failed = True
        print(f"{path}: forbidden section/pilcrow characters found:")
        for lineno, line in hits:
            replaced = line
            for char, label in FORBIDDEN.items():
                replaced = replaced.replace(char, f"[{label}]")
            print(f"  {lineno}: {replaced}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
