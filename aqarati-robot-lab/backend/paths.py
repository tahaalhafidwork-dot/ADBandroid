"""Project-root-relative path resolution and write-boundary enforcement.

Every path used inside Aqarati Robot AI Lab is derived from the project root,
which is located relative to this file. No absolute path and no path that
points at a developer machine is ever written in the source tree.

The module also provides the guard that keeps the new project independent:

* :func:`ensure_inside_project` - reject anything outside the project root.
* :func:`safe_write_path` / :func:`write_text` - the only sanctioned way to
  write a file, always inside the project root.
* :func:`ensure_read_only_source` - accept a legacy file as a read-only
  source, never as a write target.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Union

PathLike = Union[str, "os.PathLike[str]"]

#: Root of the Aqarati Robot AI Lab project (``aqarati-robot-lab/``).
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

#: Root of the repository that hosts this project. It is a *read-only* area
#: for the lab: legacy projects and their results live there.
REPO_ROOT: Path = PROJECT_ROOT.parent

#: Directories the project owns. Writing is allowed here and nowhere else.
PROJECT_DIRS: tuple = (
    "backend",
    "frontend",
    "data",
    "docs",
    "scripts",
    "tests",
)

#: Sub-directories of ``data/`` that hold generated or imported payloads.
DATA_DIRS: tuple = (
    "raw",
    "processed",
    "legacy",
    "imports",
)


class BoundaryError(PermissionError):
    """Raised when an operation would cross the project boundary."""


def project_path(*parts: PathLike) -> Path:
    """Return an absolute path built from the project root.

    The result is not required to exist. Use :func:`ensure_inside_project` to
    assert that it stays inside the project.
    """
    return PROJECT_ROOT.joinpath(*[str(part) for part in parts])


def repo_path(*parts: PathLike) -> Path:
    """Return an absolute path built from the repository root (read-only area)."""
    return REPO_ROOT.joinpath(*[str(part) for part in parts])


def data_path(*parts: PathLike) -> Path:
    """Return an absolute path inside ``data/``."""
    return project_path("data", *parts)


def _resolve(path: PathLike) -> Path:
    """Resolve ``path`` without requiring it to exist."""
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    # ``strict=False`` keeps working for paths that do not exist yet.
    return candidate.resolve()


def is_inside(path: PathLike, base: PathLike) -> bool:
    """Return ``True`` when ``path`` is inside ``base``."""
    try:
        _resolve(path).relative_to(_resolve(base))
    except ValueError:
        return False
    return True


def is_inside_project(path: PathLike) -> bool:
    """Return ``True`` when ``path`` is inside the project root."""
    return is_inside(path, PROJECT_ROOT)


def ensure_inside_project(path: PathLike) -> Path:
    """Return the resolved path, or raise if it leaves the project root."""
    resolved = _resolve(path)
    if not is_inside(resolved, PROJECT_ROOT):
        raise BoundaryError(
            "path escapes the Aqarati Robot AI Lab project root: {0}".format(resolved)
        )
    return resolved


def ensure_read_only_source(path: PathLike) -> Path:
    """Validate a legacy source.

    A legacy source must exist, must be a file or a directory, and must live
    *outside* the project root: the lab may read it but never write to it.
    """
    resolved = _resolve(path)
    if is_inside(resolved, PROJECT_ROOT):
        raise BoundaryError(
            "legacy source must be outside the project root: {0}".format(resolved)
        )
    if not resolved.exists():
        raise FileNotFoundError("legacy source does not exist: {0}".format(resolved))
    if not (resolved.is_file() or resolved.is_dir()):
        raise BoundaryError("legacy source is not a file: {0}".format(resolved))
    return resolved


def safe_write_path(path: PathLike) -> Path:
    """Return a writable path that is guaranteed to be inside the project.

    The parent directory is not created here; use :func:`write_text` when a
    single file has to be written safely.
    """
    resolved = ensure_inside_project(path)
    if resolved == _resolve(PROJECT_ROOT):
        raise BoundaryError("refusing to use the project root as a file target")
    return resolved


def write_text(path: PathLike, content: str, encoding: str = "utf-8") -> Path:
    """Write ``content`` to ``path`` after checking the write boundary."""
    target = safe_write_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding=encoding)
    return target


def write_bytes(path: PathLike, content: bytes) -> Path:
    """Write binary ``content`` to ``path`` after checking the write boundary."""
    target = safe_write_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return target


def relative_to_repo(path: PathLike) -> str:
    """Return ``path`` relative to the repository root, using ``/`` separators.

    The result never contains a drive letter or a machine specific prefix, so
    it can be stored in a manifest and committed.
    """
    resolved = _resolve(path)
    try:
        relative = resolved.relative_to(REPO_ROOT)
    except ValueError:
        relative = Path(os.path.relpath(resolved, REPO_ROOT))
    return relative.as_posix()


def iter_project_files(extensions: Iterable[str] = (".py", ".md", ".json", ".txt")) -> Iterable[Path]:
    """Yield the project's own source and documentation files."""
    allowed = tuple(extension.lower() for extension in extensions)
    for path in sorted(PROJECT_ROOT.rglob("*")):
        if not path.is_file():
            continue
        if any(part in {".git", "__pycache__"} for part in path.parts):
            continue
        if path.suffix.lower() in allowed:
            yield path
