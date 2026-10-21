"""Tests that enforce the write boundary of Aqarati Robot AI Lab.

Two complementary checks:

* a static check, the lab code must not contain a write call that bypasses
  the guarded helpers in ``backend/paths.py``;
* a dynamic check, a write to a legacy file or to any path outside the
  project must fail and must leave the legacy file untouched.
"""

from __future__ import annotations

import re
import unittest

from . import PROJECT_ROOT  # noqa: F401  (puts the project root on sys.path)

from backend import paths  # noqa: E402

SCANNED_ROOTS = ("backend", "scripts")

#: Write helpers that are only allowed inside the guarded module.
GUARDED_MODULE = paths.relative_to_repo(paths.project_path("backend", "paths.py"))

WRITE_CALL_PATTERNS = (
    re.compile(r"\.open\(\s*[\"'][wax]"),
    re.compile(r"open\([^)]*[\"'][wax]"),
    re.compile(r"(?<!paths)\.write_text\("),
    re.compile(r"(?<!paths)\.write_bytes\("),
    re.compile(r"os\.remove\("),
    re.compile(r"os\.unlink\("),
    re.compile(r"os\.rmdir\("),
    re.compile(r"shutil\.rmtree\("),
    re.compile(r"shutil\.move\("),
    re.compile(r"os\.rename\("),
)


def _scanned_files():
    for root in SCANNED_ROOTS:
        base = paths.project_path(root)
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            yield path


class StaticWriteBoundaryTests(unittest.TestCase):
    def test_no_write_call_bypasses_the_guard(self):
        offenders = []
        for path in _scanned_files():
            relative = paths.relative_to_repo(path)
            if relative.endswith(GUARDED_MODULE):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in WRITE_CALL_PATTERNS:
                if pattern.search(text):
                    offenders.append((relative, pattern.pattern))
        self.assertEqual(
            offenders,
            [],
            "writes must go through backend/paths.py: {0}".format(offenders),
        )

    def test_guarded_module_is_the_only_writer(self):
        writers = []
        for path in _scanned_files():
            text = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"(?<!paths)\.write_(text|bytes)\(", text):
                writers.append(paths.relative_to_repo(path))
        self.assertEqual(writers, [GUARDED_MODULE])

    def test_no_absolute_path_literals_in_the_code(self):
        pattern = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]{1,2}[A-Za-z0-9_.-]+")
        offenders = []
        for path in _scanned_files():
            if pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
                offenders.append(paths.relative_to_repo(path))
        self.assertEqual(offenders, [])

    def test_project_root_is_not_hardcoded_in_the_code(self):
        offenders = []
        for path in _scanned_files():
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "aqarati-robot-lab" in text and "aqarati-robot-lab" != path.name:
                # The folder name may only appear in a comment or a docstring
                # that explains the layout, never as a path to build on.
                for line in text.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("*"):
                        continue
                    if "aqarati-robot-lab" in line:
                        offenders.append("{0}: {1}".format(paths.relative_to_repo(path), stripped))
        self.assertEqual(offenders, [])


class DynamicWriteBoundaryTests(unittest.TestCase):
    def test_writing_to_a_legacy_file_is_refused(self):
        legacy = paths.REPO_ROOT / "README.md"
        if not legacy.exists():
            self.skipTest("no legacy file available")
        before = legacy.read_bytes()
        with self.assertRaises(paths.BoundaryError):
            paths.write_text(legacy, "tampered")
        self.assertEqual(legacy.read_bytes(), before)

    def test_writing_outside_the_project_is_refused(self):
        target = paths.REPO_ROOT / "_aqarati_lab_violation.txt"
        with self.assertRaises(paths.BoundaryError):
            paths.write_bytes(target, b"nope")
        self.assertFalse(target.exists())

    def test_write_bytes_inside_the_project_works(self):
        target = paths.project_path("data", "processed", "_boundary_probe.bin")
        try:
            paths.write_bytes(target, b"probe")
            self.assertTrue(target.exists())
        finally:
            if target.exists():
                target.unlink()

    def test_legacy_roots_are_reachable_but_not_writable(self):
        from backend import legacy_import

        for root in legacy_import.known_legacy_sources():
            self.assertTrue(paths.is_inside(root, paths.REPO_ROOT))
            self.assertFalse(paths.is_inside(root, paths.PROJECT_ROOT))
            with self.assertRaises(paths.BoundaryError):
                paths.write_text(root / "should_not_exist.txt", "nope")


if __name__ == "__main__":
    unittest.main()
