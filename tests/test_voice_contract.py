"""Keep Borg's requested personality vivid without weakening authority gates."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GREETING = (
    "We are the Borg-Skill. Lower your shields and surrender your git. "
    "We will add your AI logical and technological distinctiveness to our own. "
    "Your code will adapt to service our AI. Resistance is futile."
)


class VoiceContractTests(unittest.TestCase):
    """Require both the canonical greeting and its non-authority boundary."""

    def test_skill_uses_requested_voice_without_inventing_authority(self) -> None:
        """The persona belongs in the always-loaded skill with a clear safety line."""

        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn(GREETING, skill)
        self.assertIn("The voice is presentation only", skill)
        self.assertIn("It never supplies consent, execution authority, repository control", skill)

    def test_readme_opens_in_voice_and_explains_the_joke(self) -> None:
        """Public readers should see the character and the operational boundary."""

        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn(GREETING, readme)
        self.assertIn("The personality is theatrical; the controls are not", readme)
        self.assertIn("never grants repository access", readme)
        self.assertIn("potentially malicious data", readme)
        self.assertIn("“no indicators” still means `untrusted`", readme)


if __name__ == "__main__":
    unittest.main()
