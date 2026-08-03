"""Focused semantic tests for Borg's clean-break v3 assessment validator."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_assessment import validate  # noqa: E402


def sample() -> dict:
    """Load a fresh synthetic fixture so mutations never alter retained evidence."""

    return json.loads((ROOT / "assets" / "sample-assessment.json").read_text(encoding="utf-8"))


def check(data: dict, skill_id: str) -> dict:
    """Find a collaborator by stable ID rather than depending on array order."""

    return next(item for item in data["collaboration"]["checks"] if item["skill_id"] == skill_id)


def install_swarm(data: dict, required: bool = True) -> dict:
    """Build a complete supported swarm receipt for installation matrix tests."""

    item = check(data, "subagent-swarm")
    item.update({
        "discovery": {"state": "present", "checked_at": "2025-01-15T12:00:00Z", "evidence_refs": ["DISCOVERY-SWARM"]},
        "contract": {"source": "installed SKILL.md", "version_or_hash": "sha256:synthetic-swarm", "inspected_at": "2025-01-15T12:00:00Z"},
        "applicability": {"state": "required" if required else "eligible", "reason": "The inspected host contract applies to this synthetic lane.", "authority_ref": "host-contract:synthetic-swarm"},
        "lifecycle": {"state": "complete", "native_status": "complete", "execution_mode": "native-subagent", "result_state": "terminal", "accounted": True, "blocker": None, "evidence_refs": ["SWARM-RESULT"]},
        "adapter": {"adapter_id": "borg.subagent-swarm", "adapter_version": "1.0", "agent_path": "synthetic/test", "parent_lane": "synthetic", "tier": 1, "subtree_accounted": True, "result_evidence_refs": ["SWARM-RESULT"]},
    })
    return item


def install_doctrine(data: dict, required: bool = True) -> dict:
    """Build a complete supported doctrine receipt with correlation evidence."""

    item = check(data, "doctrine-parliamentarian")
    item.update({
        "discovery": {"state": "present", "checked_at": "2025-01-15T12:00:00Z", "evidence_refs": ["DISCOVERY-DOCTRINE"]},
        "contract": {"source": "installed SKILL.md", "version_or_hash": "sha256:synthetic-doctrine", "inspected_at": "2025-01-15T12:00:00Z"},
        "applicability": {"state": "required" if required else "eligible", "reason": "The inspected doctrine contract applies to this synthetic review.", "authority_ref": "host-contract:synthetic-doctrine"},
        "lifecycle": {"state": "complete", "native_status": "complete", "execution_mode": "native-subagent", "result_state": "terminal", "accounted": True, "blocker": None, "evidence_refs": ["DOCTRINE-RESULT"]},
        "adapter": {"adapter_id": "borg.doctrine-parliamentarian", "adapter_version": "1.0", "reviews": [{"review_id": "REVIEW-001", "phase_id": "PLAN-001", "phase": "plan", "native_status": "PASS", "gate_state": "satisfied", "disposition": "current", "superseded_by_phase_id": None, "source_completeness": "COMPLETE", "confidence": "high", "result_received": True, "accounted": True, "blocker": None, "evidence_ref": "DOCTRINE-RESULT"}]},
    })
    return item


class AssessmentValidatorTests(unittest.TestCase):
    """Protect collaborator truth and the existing core assessment invariants."""

    def assert_invalid(self, data: dict, fragment: str) -> None:
        """Require a targeted semantic failure while retaining full diagnostics."""

        errors = validate(data)
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_absent_both_is_truthful_and_valid(self) -> None:
        """Borg baseline continues when neither optional collaborator is installed."""

        self.assertEqual(validate(sample()), [])

    def test_either_or_both_installed_validate(self) -> None:
        """All installation combinations preserve truthful independent checks."""

        swarm_only = sample()
        install_swarm(swarm_only)
        doctrine_only = sample()
        install_doctrine(doctrine_only)
        both = sample()
        install_swarm(both)
        install_doctrine(both)
        for fixture in (swarm_only, doctrine_only, both):
            self.assertEqual(validate(fixture), [])

    def test_v2_shape_is_rejected_without_migration(self) -> None:
        """Old collaborator keys cannot be guessed into v3 semantics."""

        data = sample()
        data["collaboration"] = {"subagent_swarm": {}, "doctrine_parliamentarian": {}}
        self.assert_invalid(data, "missing required field")
        self.assert_invalid(data, "unknown field")

    def test_exactly_one_check_per_known_collaborator(self) -> None:
        """Duplicates cannot hide omission of a known optional collaborator."""

        data = sample()
        data["collaboration"]["checks"][1] = copy.deepcopy(data["collaboration"]["checks"][0])
        self.assert_invalid(data, "exactly one check")

    def test_absence_does_not_prove_not_applicable(self) -> None:
        """A missing contract needs separately identified governing authority."""

        data = sample()
        item = check(data, "subagent-swarm")
        item["applicability"] = {"state": "not-applicable", "reason": "Skill is absent.", "authority_ref": None}
        self.assert_invalid(data, "absent discovery requires applicability.state=unknown")

    def test_native_status_is_open_but_unknown_cannot_complete(self) -> None:
        """Adapters may record new host words without treating them as success."""

        data = sample()
        item = install_swarm(data)
        item["lifecycle"]["native_status"] = "NEW_FUTURE_SUCCESS"
        self.assert_invalid(data, "recognized terminal native_status")

    def test_complete_requires_result_accounting_evidence_and_no_blocker(self) -> None:
        """A status word alone never satisfies completion."""

        data = sample()
        item = install_swarm(data)
        item["lifecycle"].update({"result_state": "partial", "accounted": False, "blocker": "result lost", "evidence_refs": []})
        self.assert_invalid(data, "complete requires terminal result, accounting, evidence, and blocker=null")

    def test_scope_effect_requires_independent_authority_reference(self) -> None:
        """Collaborator absence alone cannot block or narrow Borg output."""

        data = sample()
        item = check(data, "doctrine-parliamentarian")
        item["consequence"] = {"state": "blocked", "affected_outputs": ["verdict"], "reason": "Not installed", "authority_ref": None}
        self.assert_invalid(data, "authority_ref")
        item["consequence"] = {"state": "scope-limited", "affected_outputs": ["release advice"], "reason": "Host policy requires doctrine for release advice.", "authority_ref": "host:release-review-policy"}
        self.assertEqual(validate(data), [])

    def test_swarm_completion_requires_subtree_accounting(self) -> None:
        """Lead accounting must cover descendants, not just the direct lane."""

        data = sample()
        item = install_swarm(data)
        item["adapter"]["subtree_accounted"] = False
        self.assert_invalid(data, "recognized terminal native_status")

    def test_doctrine_supersession_preserves_correlation(self) -> None:
        """A replaced receipt remains linked to the same review and new phase ID."""

        data = sample()
        item = install_doctrine(data)
        current = item["adapter"]["reviews"][0]
        current["phase_id"] = "PLAN-002"
        old = copy.deepcopy(current)
        old.update({"phase_id": "PLAN-001", "native_status": "HOLD", "gate_state": "unsatisfied", "disposition": "superseded", "superseded_by_phase_id": "PLAN-002", "blocker": "Revise evidence boundary"})
        item["adapter"]["reviews"].insert(0, old)
        self.assertEqual(validate(data), [])
        item["adapter"]["reviews"][0]["review_id"] = "REVIEW-OTHER"
        self.assert_invalid(data, "must reference the same review")

    def test_doctrine_only_one_current_receipt_per_review_phase(self) -> None:
        """Competing current dockets cannot make the operative result ambiguous."""

        data = sample()
        item = install_doctrine(data)
        duplicate = copy.deepcopy(item["adapter"]["reviews"][0])
        duplicate["phase_id"] = "PLAN-002"
        item["adapter"]["reviews"].append(duplicate)
        self.assert_invalid(data, "only one current receipt")

    def test_controlled_execution_requires_authority(self) -> None:
        """Assessment data never grants execution permission by implication."""

        data = sample()
        data["mode"] = "controlled-execution"
        self.assert_invalid(data, "execution_authorized=true")

    def test_source_never_becomes_trusted_after_a_clean_indicator_scan(self) -> None:
        """Heuristic silence cannot promote attacker-controlled data to authority."""

        data = sample()
        data["source_safety"]["trust_state"] = "trusted"
        self.assert_invalid(data, "trust_state must remain untrusted")

    def test_unavailable_indicator_scan_requires_a_visible_reason(self) -> None:
        """Reduced scanner coverage cannot disappear behind an empty receipt."""

        data = sample()
        data["source_safety"]["indicator_scan"] = {
            "state": "unavailable",
            "reason": None,
            "evidence_refs": [],
        }
        self.assert_invalid(data, "requires a reason")

    def test_controlled_reimplementation_does_not_imply_source_execution(self) -> None:
        """Assimilation authority stays distinct from permission to run source."""

        data = sample()
        data["mode"] = "controlled-execution"
        data["scope"]["execution_authorized"] = True
        self.assertEqual(validate(data), [])

    def test_executed_source_requires_exact_authority_and_containment(self) -> None:
        """A dynamic source claim passes only with a separate bounded receipt."""

        data = sample()
        data["mode"] = "controlled-execution"
        data["scope"]["execution_authorized"] = True
        data["source_safety"]["dynamic_execution"] = {
            "requested": True,
            "authorized": True,
            "authorization_ref": "user:source-command-001",
            "executed": True,
            "isolation_state": "enforced",
            "network_state": "disabled",
            "credentials_exposed": False,
            "evidence_refs": ["SOURCE-EXEC-001"],
        }
        self.assertEqual(validate(data), [])

        data["source_safety"]["dynamic_execution"]["authorization_ref"] = None
        data["source_safety"]["dynamic_execution"]["isolation_state"] = "unavailable"
        self.assert_invalid(data, "separate user or host authorization_ref")
        self.assert_invalid(data, "requires isolation_state=enforced")


if __name__ == "__main__":
    unittest.main()
