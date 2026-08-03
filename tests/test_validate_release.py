"""Round-trip and adversarial tests for deterministic release packaging."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_release import build_release  # noqa: E402
from validate_release import validate_release  # noqa: E402


class ReleaseValidatorTests(unittest.TestCase):
    """Use isolated source/output roots so production state is never touched."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "source"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc"))
        self.output = Path(self.temporary.name) / "out"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_profiles_are_deterministic_and_host_specific(self) -> None:
        first = build_release(self.root, "codex", self.output / "one")
        second = build_release(self.root, "codex", self.output / "two")
        self.assertEqual(first[0].name, "borg-0.3.1-codex.zip")
        self.assertEqual(hashlib.sha256(first[0].read_bytes()).digest(), hashlib.sha256(second[0].read_bytes()).digest())
        self.assertEqual(validate_release(first[0], source_root=self.root), [])
        release_manifest = json.loads(first[1].read_text(encoding="utf-8"))
        self.assertEqual(
            set(release_manifest),
            {"schema", "package", "version", "profile", "common_core_sha256", "files"},
        )
        openclaw = build_release(self.root, "openclaw", self.output / "openclaw")
        with zipfile.ZipFile(first[0]) as codex_zip, zipfile.ZipFile(openclaw[0]) as openclaw_zip:
            self.assertIn("agents/openai.yaml", codex_zip.namelist())
            self.assertNotIn("agents/openai.yaml", openclaw_zip.namelist())
            self.assertNotIn("README.md", codex_zip.namelist())
            self.assertNotIn("MANIFEST.json", codex_zip.namelist())

    def test_unlisted_archive_member_is_rejected(self) -> None:
        archive, manifest, checksum = build_release(self.root, "openclaw", self.output)
        with zipfile.ZipFile(archive, "a") as bundle:
            bundle.writestr("extra.txt", b"unlisted")
        checksum.write_text(f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n", encoding="ascii")
        errors = validate_release(archive, manifest, checksum, source_root=self.root)
        self.assertTrue(any("unlisted" in error for error in errors))

    def test_traversal_member_is_rejected(self) -> None:
        archive, manifest, checksum = build_release(self.root, "openclaw", self.output)
        with zipfile.ZipFile(archive, "a") as bundle:
            bundle.writestr("../escape", b"bad")
        checksum.write_text(f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n", encoding="ascii")
        errors = validate_release(archive, manifest, checksum)
        self.assertTrue(any("unsafe release path" in error for error in errors))

    def test_rewritten_overlay_cannot_masquerade_as_source_release(self) -> None:
        """Source-root validation anchors the host overlay, not only common files.

        An internally consistent ZIP, ledger, and checksum are insufficient
        when authoritative source is supplied.  This models a modified Codex
        metadata overlay while leaving the common-core digest untouched.
        """

        archive, manifest_path, checksum = build_release(self.root, "codex", self.output)
        replacement = b"interface:\n  display_name: \"Altered\"\n"
        # Duplicate-member injection is intentional adversarial input.  The
        # standard library warns while creating it; suppress only that known
        # construction warning so test output remains a clean verification
        # signal while the validator still receives the hostile archive.
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Duplicate name: 'agents/openai.yaml'", category=UserWarning)
            with zipfile.ZipFile(archive, "a") as bundle:
                bundle.writestr("agents/openai.yaml", replacement)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        overlay = next(entry for entry in manifest["files"] if entry["path"] == "agents/openai.yaml")
        overlay["bytes"] = len(replacement)
        overlay["sha256"] = hashlib.sha256(replacement).hexdigest()
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        checksum.write_text(f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n", encoding="ascii")

        errors = validate_release(archive, manifest_path, checksum, source_root=self.root)
        self.assertTrue(any("does not match source bytes/mode: agents/openai.yaml" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
