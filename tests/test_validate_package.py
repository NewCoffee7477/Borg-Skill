"""Focused unit tests for Borg's inert package validator helpers."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_package import (  # noqa: E402
    EXPECTED_PACKAGE_VERSION,
    iter_manifest_files,
    validate_manifest_metadata,
    validate_package,
)


class PackageValidatorTests(unittest.TestCase):
    """Keep the canonical package check callable from a clean test process."""

    def test_project_package_passes(self) -> None:
        """The governed source tree must satisfy every static package gate.

        This intentionally checks the real project rather than a sanitized
        copy.  A stray cache, privacy finding, manifest drift, broken route,
        or contract regression therefore fails the ordinary test suite and
        cannot be hidden by test-fixture filtering.
        """

        self.assertEqual(validate_package(ROOT), [])

    def test_manifest_version_drift_is_rejected(self) -> None:
        """A stale or invented version cannot share the release's hashes."""

        manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
        manifest["version"] = "0.3.2"
        errors: list[str] = []
        validate_manifest_metadata(manifest, errors)
        self.assertIn(f"MANIFEST.json version must be {EXPECTED_PACKAGE_VERSION}", errors)

    def test_manifest_has_no_build_history_status_fields(self) -> None:
        """The public ledger contains identity and bytes, not process narration."""

        manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))

        self.assertEqual(set(manifest), {"package", "version", "files"})

    def test_only_root_git_transport_metadata_is_excluded(self) -> None:
        """Git internals stay out while nested repository content stays visible.

        The validator must work in a real checkout, but a source-controlled
        nested ``.git`` directory cannot exploit that exception to disappear
        from the exact source ledger.
        """

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text("transport only\n", encoding="utf-8")
            nested = root / "nested" / ".git"
            nested.mkdir(parents=True)
            (nested / "config").write_text("must remain visible\n", encoding="utf-8")
            (root / "source.txt").write_text("public source\n", encoding="utf-8")

            paths = iter_manifest_files(root)

            self.assertNotIn(".git/config", paths)
            self.assertIn("nested/.git/config", paths)
            self.assertIn("source.txt", paths)


if __name__ == "__main__":
    unittest.main()
