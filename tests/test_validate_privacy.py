"""Negative and exception tests for the masked, local-only privacy scanner."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_privacy import scan_paths, scan_text  # noqa: E402


class PrivacyValidatorTests(unittest.TestCase):
    """Exercise high-risk rules without depending on the executing machine."""

    def test_sensitive_classes_are_rejected_and_masked(self) -> None:
        text = "\n".join((
            "owner: person@private.invalid",  # privacy-fixture
            "phone: 302-555-0199",  # privacy-fixture
            "path: /Users/privateperson/project",  # privacy-fixture
            "server: 192.168.1.20",  # privacy-fixture
            "password=correct-horse-battery",  # privacy-fixture
            "-----BEGIN PRIVATE KEY-----",  # privacy-fixture
            "event: 123e4567-e89b-42d3-a456-426614174000",  # privacy-fixture
        ))
        findings = scan_text(text, "fixture.txt", machine_tokens=())
        rules = {finding.rule for finding in findings}
        self.assertTrue({"email", "phone", "home-path", "private-host", "credential-assignment", "private-key", "uuid-event-id"} <= rules)
        rendered = "\n".join(finding.render() for finding in findings)
        self.assertNotIn("correct-horse-battery", rendered)
        self.assertNotIn("person@private.invalid", rendered)  # privacy-fixture

    def test_narrow_portable_exceptions_pass(self) -> None:
        text = "\n".join((
            "#!/usr/bin/env python3",
            "contact: builder@example.com",  # privacy-fixture
            "synthetic fixture identifier: 00000000-0000-4000-8000-000000000000",
            "schema: https://json-schema.org/draft/2020-12/schema",
            "path: references/methodology.md",
        ))
        self.assertEqual(scan_text(text, "fixture.txt", machine_tokens=()), [])

    def test_injected_deny_token_is_rejected(self) -> None:
        findings = scan_text("marker: PROJECT-CANARY", "fixture.txt", deny_tokens=["PROJECT-CANARY"], machine_tokens=())
        self.assertEqual([finding.rule for finding in findings], ["machine-token"])

    def test_root_git_metadata_is_not_treated_as_publishable_source(self) -> None:
        """Local Git identity data is audited separately from committed bytes."""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text(
                "email = owner@private.invalid\n",  # privacy-fixture
                encoding="utf-8",
            )
            (root / "README.md").write_text("portable source\n", encoding="utf-8")

            self.assertEqual(scan_paths(root), [])


if __name__ == "__main__":
    unittest.main()
