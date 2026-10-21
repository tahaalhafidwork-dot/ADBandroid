"""Tests for the project-root path rules."""

from __future__ import annotations

import os
import unittest

from . import PROJECT_ROOT  # noqa: F401  (puts the project root on sys.path)

from backend import paths  # noqa: E402


class ProjectPathTests(unittest.TestCase):
    def test_project_root_is_the_lab_folder(self):
        self.assertEqual(paths.PROJECT_ROOT.name, "aqarati-robot-lab")
        self.assertEqual(paths.PROJECT_ROOT.parent, paths.REPO_ROOT)

    def test_project_path_is_rooted(self):
        path = paths.project_path("data", "imports", "manifest.json")
        self.assertTrue(path.is_absolute())
        self.assertTrue(str(path).startswith(str(paths.PROJECT_ROOT)))
        self.assertTrue(paths.is_inside(path, paths.PROJECT_ROOT))

    def test_relative_paths_are_resolved_against_the_project(self):
        path = paths.project_path("docs", "architecture.md")
        self.assertEqual(path, paths.PROJECT_ROOT / "docs" / "architecture.md")

    def test_repo_path_points_at_the_read_only_area(self):
        path = paths.repo_path("real_estate_ai_pipeline", "output")
        self.assertTrue(paths.is_inside(path, paths.REPO_ROOT))
        self.assertFalse(paths.is_inside(path, paths.PROJECT_ROOT))

    def test_data_path_is_inside_data(self):
        self.assertTrue(paths.is_inside(paths.data_path("raw"), paths.project_path("data")))

    def test_relative_to_repo_uses_posix_and_no_drive_letter(self):
        relative = paths.relative_to_repo(paths.project_path("docs", "architecture.md"))
        self.assertEqual(relative, "aqarati-robot-lab/docs/architecture.md")
        self.assertNotIn(":", relative)
        self.assertFalse(relative.startswith("/"))


class BoundaryTests(unittest.TestCase):
    def test_inside_project_is_detected(self):
        self.assertTrue(paths.is_inside_project(paths.project_path("data", "raw")))

    def test_outside_project_is_rejected(self):
        with self.assertRaises(paths.BoundaryError):
            paths.ensure_inside_project(paths.REPO_ROOT / "legacy_root_file.txt")

    def test_escape_with_relative_parts_is_rejected(self):
        with self.assertRaises(paths.BoundaryError):
            paths.ensure_inside_project(paths.PROJECT_ROOT / ".." / "outside.txt")

    def test_legacy_source_inside_the_project_is_rejected(self):
        with self.assertRaises(paths.BoundaryError):
            paths.ensure_read_only_source(paths.project_path("data", "raw", "anything.json"))

    def test_legacy_source_outside_the_project_is_accepted(self):
        legacy = paths.REPO_ROOT / "README.md"
        if not legacy.exists():
            self.skipTest("no legacy file available")
        resolved = paths.ensure_read_only_source(legacy)
        self.assertTrue(resolved.is_file())

    def test_missing_legacy_source_raises(self):
        with self.assertRaises(FileNotFoundError):
            paths.ensure_read_only_source(paths.REPO_ROOT / "definitely_missing_file.json")

    def test_project_root_itself_is_not_a_write_target(self):
        with self.assertRaises(paths.BoundaryError):
            paths.safe_write_path(paths.PROJECT_ROOT)

    def test_write_text_creates_the_file_inside_the_project(self):
        target = paths.project_path("data", "processed", "_boundary_probe.tmp")
        try:
            paths.write_text(target, "probe")
            self.assertTrue(target.exists())
            self.assertTrue(paths.is_inside(target, paths.PROJECT_ROOT))
        finally:
            if target.exists():
                target.unlink()

    def test_write_text_outside_the_project_is_refused(self):
        with self.assertRaises(paths.BoundaryError):
            paths.write_text(paths.REPO_ROOT / "_boundary_violation.txt", "nope")

    def test_relative_to_repo_for_a_path_outside_the_repository(self):
        outside = os.path.join(os.path.dirname(str(paths.REPO_ROOT)), "outside.txt")
        relative = paths.relative_to_repo(outside)
        self.assertNotIn(":", relative)
        self.assertFalse(relative.startswith("/"))


if __name__ == "__main__":
    unittest.main()
