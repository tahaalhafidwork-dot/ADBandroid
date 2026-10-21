"""Verify the Aqarati Robot AI Lab structure and the path rules.

The check fails when a required folder or file is missing, when a source file
contains an absolute path, or when a path escapes the project root.
"""

from __future__ import annotations

import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend import paths  # noqa: E402

REQUIRED_DIRS = (
    "backend",
    "backend/app",
    "frontend",
    "data",
    "data/raw",
    "data/processed",
    "data/legacy",
    "data/imports",
    "tests",
    "docs",
    "scripts",
)

REQUIRED_FILES = (
    ".gitignore",
    "PROJECT_BOUNDARIES.md",
    "README.md",
    "backend/__init__.py",
    "backend/app/__init__.py",
    "backend/config.py",
    "backend/legacy_import.py",
    "backend/paths.py",
    "docs/architecture.md",
    "docs/data-import.md",
    "scripts/import_legacy_data.py",
    "scripts/verify_structure.py",
    "tests/test_import_readonly.py",
    "tests/test_paths.py",
    "tests/test_write_boundaries.py",
)

ABSOLUTE_PATH_PATTERNS = (
    re.compile(r"[A-Za-z]:[\\/]{1,2}[A-Za-z0-9_.-]+"),
    re.compile(r"/Users/[A-Za-z0-9_.-]+"),
    re.compile(r"/home/[A-Za-z0-9_.-]+"),
)

SCANNED_SUFFIXES = (".py", ".md", ".json", ".txt", ".cfg", ".toml")


def find_absolute_paths() -> list:
    """Return the source files that contain an absolute path literal."""
    offenders = []
    for path in paths.iter_project_files(SCANNED_SUFFIXES):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in ABSOLUTE_PATH_PATTERNS:
            if pattern.search(text):
                offenders.append(paths.relative_to_repo(path))
                break
    return offenders


def main() -> int:
    problems = []

    for relative in REQUIRED_DIRS:
        if not paths.project_path(relative).is_dir():
            problems.append("missing directory: {0}".format(relative))

    for relative in REQUIRED_FILES:
        if not paths.project_path(relative).is_file():
            problems.append("missing file: {0}".format(relative))

    offenders = find_absolute_paths()
    for relative in offenders:
        problems.append("absolute path literal in: {0}".format(relative))

    print("Project root: {0}".format(paths.relative_to_repo(paths.PROJECT_ROOT)))
    print("Repository root: {0}".format(paths.relative_to_repo(paths.REPO_ROOT)))
    print("Checked {0} directories and {1} files".format(len(REQUIRED_DIRS), len(REQUIRED_FILES)))

    if problems:
        print("\nFAILED:")
        for problem in problems:
            print("  - {0}".format(problem))
        return 1

    print("\nOK: structure complete, no absolute paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
