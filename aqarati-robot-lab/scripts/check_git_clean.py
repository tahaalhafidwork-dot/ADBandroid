"""Check that git only sees changes inside the new project folder.

Usage::

    python scripts/check_git_clean.py                # staged and unstaged scope
    python scripts/check_git_clean.py --staged-only  # what the commit contains
    python scripts/check_git_clean.py --allow-other   # report only, do not fail
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_NAME = os.path.basename(PROJECT_ROOT)
REPO_ROOT = os.path.dirname(PROJECT_ROOT)


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout


def _paths(*args: str, porcelain: bool = False) -> list:
    output = _git(*args)
    paths = []
    for raw in output.splitlines():
        if not raw.strip():
            continue
        if porcelain:
            # "<XY> <path>" - the status codes are not part of the path.
            line = raw.rstrip()[3:] if len(raw.rstrip()) > 3 else ""
            if " -> " in line:  # rename entry
                line = line.split(" -> ")[-1]
        else:
            line = raw.strip()
            if " -> " in line:
                line = line.split(" -> ")[-1]
        paths.append(line.strip('"'))
    return paths


def _outside(paths_list: list) -> list:
    allowed = PROJECT_NAME + "/"
    return [path for path in paths_list if not path.startswith(allowed)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged-only", action="store_true", help="only check the staged changes")
    parser.add_argument("--allow-other", action="store_true", help="report other changes but do not fail")
    args = parser.parse_args()

    if args.staged_only:
        changed = _paths("diff", "--cached", "--name-only")
        scope = "staged"
    else:
        changed = _paths("status", "--porcelain", porcelain=True)
        scope = "working tree"

    outside = _outside(changed)
    inside = [path for path in changed if path.startswith(PROJECT_NAME + "/")]

    print("Scope: {0}".format(scope))
    print("Inside {0}/: {1}".format(PROJECT_NAME, len(inside)))
    print("Outside {0}/: {1}".format(PROJECT_NAME, len(outside)))
    for path in outside:
        print("  outside: {0}".format(path))

    if outside and not args.allow_other:
        print("\nFAILED: changes outside the new project folder are present")
        return 1
    print("\nOK: {0} contains only the new project folder".format(scope))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
