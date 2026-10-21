"""Import legacy data into Aqarati Robot AI Lab without touching the source.

Two modes are supported:

``copy``      the payload is copied into ``data/legacy/`` of this project.
``reference`` nothing is copied; only a manifest entry that points at the
              legacy file is written.

In both modes the legacy file is opened read-only. The importer hashes the
source before and after the operation and aborts if the source changed, which
is the machine-checkable guarantee that the legacy experiments are untouched.

The manifest (``data/imports/manifest.json``) stores repository relative paths
only, so it never leaks a developer machine path and can be committed.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from . import paths

COPY = "copy"
REFERENCE = "reference"
MODES = (COPY, REFERENCE)

#: Legacy roots of the repository that may be imported (read-only sources).
LEGACY_SOURCE_ROOTS = (
    "real_estate_ai_pipeline/output",
    "real_estate_ai_pipeline/data",
    "raqi_reverse_engineering",
    "evidence",
)

#: Files that are never imported unless the operator opts in explicitly.
PII_DENY_PATTERNS = (
    "ground_truth",
    "contact",
    "phone",
    "secret",
    "credential",
    "password",
    ".env",
)

MANIFEST_VERSION = 1


class ImportError_(RuntimeError):
    """Raised when an import cannot be performed safely."""


@dataclass
class ImportEntry:
    """One imported file."""

    source: str
    destination: Optional[str]
    mode: str
    sha256: str
    size: int
    modified_at: str
    pii_blocked: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "destination": self.destination,
            "mode": self.mode,
            "sha256": self.sha256,
            "size": self.size,
            "modified_at": self.modified_at,
            "pii_blocked": self.pii_blocked,
        }


@dataclass
class ImportResult:
    """Outcome of an import run."""

    mode: str
    entries: List[ImportEntry] = field(default_factory=list)
    skipped: List[Dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "entries": [entry.as_dict() for entry in self.entries],
            "skipped": list(self.skipped),
        }


def sha256_of(path: Path) -> str:
    """Return the SHA-256 digest of a file, read-only."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_pii_sensitive(path: Path) -> bool:
    """Return ``True`` when the file name suggests personal data."""
    name = path.name.lower()
    return any(pattern in name for pattern in PII_DENY_PATTERNS)


def known_legacy_sources() -> List[Path]:
    """Return the legacy roots that exist in the repository."""
    roots = []
    for relative in LEGACY_SOURCE_ROOTS:
        candidate = paths.repo_path(relative)
        if candidate.exists():
            roots.append(candidate)
    return roots


def _iter_source_files(source: Path) -> Iterable[Path]:
    if source.is_file():
        yield source
        return
    for path in sorted(source.rglob("*")):
        if path.is_file():
            yield path


def _relative_source(base: Path, path: Path) -> str:
    if base.is_file():
        return paths.relative_to_repo(path)
    return paths.relative_to_repo(path)


def _contains_absolute_path(value: str) -> bool:
    """Return ``True`` for a Windows drive path, a UNC path or a POSIX path."""
    if value.startswith(("/", "\\")):
        return True
    return len(value) > 1 and value[1] == ":"


def read_manifest(manifest_path: Path) -> Dict[str, Any]:
    """Read the import manifest, returning an empty manifest when absent."""
    if not manifest_path.exists():
        return {"version": MANIFEST_VERSION, "imports": []}
    with manifest_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_manifest(manifest_path: Path, manifest: Dict[str, Any]) -> Path:
    """Write the manifest after checking that it holds no absolute path."""
    for entry in manifest.get("imports", []):
        for key in ("source", "destination"):
            value = entry.get(key)
            if value and _contains_absolute_path(value):
                raise ImportError_(
                    "manifest must not contain absolute paths, got: {0}".format(value)
                )
    return paths.write_text(
        manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )


def import_source(
    source: Path,
    mode: str = COPY,
    dest_root: Optional[Path] = None,
    manifest_path: Optional[Path] = None,
    allow_pii: bool = False,
    name: Optional[str] = None,
) -> ImportResult:
    """Import a legacy file or directory into the lab.

    ``source`` is opened read-only and is never modified. ``dest_root`` and
    ``manifest_path`` default to the project's ``data/legacy`` and
    ``data/imports`` folders; tests override them with a temporary directory.
    """
    if mode not in MODES:
        raise ImportError_("unknown import mode: {0}".format(mode))

    source = paths.ensure_read_only_source(source)
    destination_root = dest_root or paths.data_path("legacy")
    manifest_file = manifest_path or paths.data_path("imports", "manifest.json")

    if not paths.is_inside(destination_root, paths.PROJECT_ROOT):
        raise paths.BoundaryError(
            "import destination must be inside the project: {0}".format(destination_root)
        )
    if not paths.is_inside(manifest_file, paths.PROJECT_ROOT):
        raise paths.BoundaryError(
            "manifest must be inside the project: {0}".format(manifest_file)
        )

    label = name or source.name
    result = ImportResult(mode=mode)

    before = {path: (sha256_of(path), path.stat().st_mtime) for path in _iter_source_files(source)}

    for file_path, (digest, mtime) in before.items():
        if is_pii_sensitive(file_path) and not allow_pii:
            result.skipped.append(
                {
                    "source": paths.relative_to_repo(file_path),
                    "reason": "looks like personal data, import skipped",
                }
            )
            continue

        destination: Optional[Path] = None
        if mode == COPY:
            if source.is_dir():
                relative = file_path.relative_to(source)
                destination = Path(destination_root) / label / relative
            else:
                destination = Path(destination_root) / label
            destination = paths.ensure_inside_project(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(file_path), str(destination))
            if sha256_of(destination) != digest:
                raise ImportError_("copy of {0} does not match the source".format(file_path))

        result.entries.append(
            ImportEntry(
                source=_relative_source(source, file_path),
                destination=paths.relative_to_repo(destination) if destination else None,
                mode=mode,
                sha256=digest,
                size=file_path.stat().st_size,
                modified_at=datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
            )
        )

    after = {path: (sha256_of(path), path.stat().st_mtime) for path in _iter_source_files(source)}
    if before != after:
        raise ImportError_("legacy source changed during the import, aborting")

    manifest = read_manifest(manifest_file)
    manifest.setdefault("version", MANIFEST_VERSION)
    manifest.setdefault("imports", []).append(
        {
            "imported_at": datetime.now(tz=timezone.utc).isoformat(),
            "mode": mode,
            "label": label,
            "entries": [entry.as_dict() for entry in result.entries],
            "skipped": result.skipped,
        }
    )
    write_manifest(manifest_file, manifest)
    return result
