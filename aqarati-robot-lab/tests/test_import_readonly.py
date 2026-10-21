"""Tests for the legacy import mechanism.

The import must never modify a legacy file. The tests use a temporary
directory outside the project as a stand-in for a legacy source, and a
temporary directory inside the project as the destination, so the real
repository stays untouched.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from . import PROJECT_ROOT  # noqa: F401  (puts the project root on sys.path)

from backend import legacy_import, paths  # noqa: E402


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ImportReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="aqarati_lab_legacy_")
        self.source_dir = Path(self.temp_dir) / "legacy_source"
        self.source_dir.mkdir()
        self.source_file = self.source_dir / "listings.json"
        self.source_file.write_text(
            json.dumps({"listings": [{"id": 1}, {"id": 2}]}), encoding="utf-8"
        )
        self.pii_file = self.source_dir / "ground_truth.json"
        self.pii_file.write_text(json.dumps({"phone": "0000"}), encoding="utf-8")
        self.dest_root = paths.project_path("data", "processed", "_import_test")
        self.manifest = paths.project_path("data", "processed", "_import_test_manifest.json")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        if self.dest_root.exists():
            shutil.rmtree(self.dest_root, ignore_errors=True)
        if self.manifest.exists():
            self.manifest.unlink()

    def test_copy_mode_copies_without_touching_the_source(self):
        before_digest = _digest(self.source_file)
        before_mtime = self.source_file.stat().st_mtime

        result = legacy_import.import_source(
            self.source_dir,
            mode=legacy_import.COPY,
            dest_root=self.dest_root,
            manifest_path=self.manifest,
        )

        self.assertEqual(_digest(self.source_file), before_digest)
        self.assertEqual(self.source_file.stat().st_mtime, before_mtime)
        copied = self.dest_root / self.source_dir.name / "listings.json"
        self.assertTrue(copied.exists())
        self.assertEqual(_digest(copied), before_digest)
        self.assertEqual(len(result.entries), 1)  # the PII file is skipped

    def test_reference_mode_copies_nothing(self):
        result = legacy_import.import_source(
            self.source_file,
            mode=legacy_import.REFERENCE,
            dest_root=self.dest_root,
            manifest_path=self.manifest,
        )
        self.assertFalse(self.dest_root.exists())
        self.assertEqual(len(result.entries), 1)
        self.assertIsNone(result.entries[0].destination)
        self.assertTrue(self.manifest.exists())

    def test_pii_files_are_skipped_by_default(self):
        result = legacy_import.import_source(
            self.source_dir,
            mode=legacy_import.COPY,
            dest_root=self.dest_root,
            manifest_path=self.manifest,
        )
        self.assertEqual(len(result.skipped), 1)
        self.assertIn("ground_truth.json", result.skipped[0]["source"])
        self.assertFalse((self.dest_root / self.source_dir.name / "ground_truth.json").exists())

    def test_pii_files_can_be_imported_explicitly(self):
        result = legacy_import.import_source(
            self.source_dir,
            mode=legacy_import.COPY,
            dest_root=self.dest_root,
            manifest_path=self.manifest,
            allow_pii=True,
        )
        self.assertEqual(result.skipped, [])
        self.assertEqual(len(result.entries), 2)

    def test_manifest_holds_relative_paths_only(self):
        legacy_import.import_source(
            self.source_file,
            mode=legacy_import.COPY,
            dest_root=self.dest_root,
            manifest_path=self.manifest,
        )
        raw = self.manifest.read_text(encoding="utf-8")
        self.assertNotIn(str(paths.REPO_ROOT), raw)
        self.assertNotIn(os.path.splitdrive(str(paths.REPO_ROOT))[0], raw)
        manifest = json.loads(raw)
        for entry in manifest["imports"][0]["entries"]:
            self.assertFalse(entry["source"].startswith("/"))
            self.assertNotIn(":", entry["source"])
            self.assertFalse(entry["destination"].startswith("/"))
            self.assertNotIn(":", entry["destination"])

    def test_source_inside_the_project_is_refused(self):
        with self.assertRaises(paths.BoundaryError):
            legacy_import.import_source(
                paths.project_path("data", "raw"),
                mode=legacy_import.COPY,
                dest_root=self.dest_root,
                manifest_path=self.manifest,
            )

    def test_destination_outside_the_project_is_refused(self):
        with self.assertRaises(paths.BoundaryError):
            legacy_import.import_source(
                self.source_file,
                mode=legacy_import.COPY,
                dest_root=Path(self.temp_dir) / "outside",
                manifest_path=self.manifest,
            )

    def test_missing_source_raises(self):
        with self.assertRaises(FileNotFoundError):
            legacy_import.import_source(
                Path(self.temp_dir) / "missing.json",
                mode=legacy_import.COPY,
                dest_root=self.dest_root,
                manifest_path=self.manifest,
            )

    def test_unknown_mode_is_refused(self):
        with self.assertRaises(legacy_import.ImportError_):
            legacy_import.import_source(
                self.source_file,
                mode="move",
                dest_root=self.dest_root,
                manifest_path=self.manifest,
            )

    def test_manifest_write_rejects_absolute_paths(self):
        manifest = {
            "version": 1,
            "imports": [
                {
                    "source": str(self.source_file),
                    "destination": None,
                }
            ],
        }
        with self.assertRaises(legacy_import.ImportError_):
            legacy_import.write_manifest(self.manifest, manifest)

    def test_known_legacy_sources_stay_outside_the_project(self):
        for root in legacy_import.known_legacy_sources():
            self.assertFalse(paths.is_inside(root, paths.PROJECT_ROOT))


if __name__ == "__main__":
    unittest.main()
