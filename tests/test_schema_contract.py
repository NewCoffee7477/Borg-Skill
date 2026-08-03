"""Parity checks between the v3 JSON Schema and normative Python validator."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_assessment import (  # noqa: E402
    KNOWN_COLLABORATORS,
    TOP_LEVEL_FIELDS,
    VALID_APPLICABILITY,
    VALID_ASSIMILATION_FORMS,
    VALID_CONFIDENCE,
    VALID_CONSEQUENCE,
    VALID_DISCOVERY,
    VALID_DOD_STATUS,
    VALID_GATE_STATE,
    VALID_GRADES,
    VALID_INDICATOR_SCAN,
    VALID_ISOLATION_STATE,
    VALID_LIFECYCLE,
    VALID_MODES,
    VALID_NETWORK_STATE,
    VALID_RESULT_STATE,
    VALID_REASON_CODES,
    VALID_REVIEW_DISPOSITION,
    VALID_REVIEW_PHASES,
    VALID_ROBUSTNESS,
    VALID_SOURCE_COMPLETENESS,
)


def schema() -> dict:
    """Read the canonical schema fresh so tests cannot share mutations."""

    return json.loads((ROOT / "assets" / "assessment-schema.json").read_text(encoding="utf-8"))


class SchemaParityTests(unittest.TestCase):
    """Protect structural vocabularies while leaving native status open."""

    def test_schema_identity_and_top_level_fields(self) -> None:
        """The clean-break edition and closed top level remain explicit."""

        value = schema()
        self.assertEqual(value["$id"], "urn:borg:assessment-schema:3.1")
        self.assertEqual(set(value["required"]), TOP_LEVEL_FIELDS)
        self.assertFalse(value["additionalProperties"])

    def test_core_enums_match(self) -> None:
        """Core Borg vocabularies cannot drift across declarative contracts."""

        properties = schema()["properties"]
        capability = properties["capabilities"]["items"]["properties"]
        candidate = properties["candidates"]["items"]["properties"]
        self.assertEqual(set(properties["mode"]["enum"]), VALID_MODES)
        self.assertEqual(set(capability["evidence_grade"]["enum"]), VALID_GRADES)
        self.assertEqual(set(capability["confidence"]["enum"]), VALID_CONFIDENCE)
        self.assertEqual(set(candidate["assimilation_form"]["enum"]), VALID_ASSIMILATION_FORMS)
        self.assertEqual(set(candidate["reason_codes"]["items"]["enum"]), VALID_REASON_CODES)
        self.assertEqual(set(candidate["robustness"]["enum"]), VALID_ROBUSTNESS)

    def test_collaboration_envelope_and_enums_match(self) -> None:
        """The envelope requires exactly two checks and shared normalized states."""

        value = schema()
        collaboration = value["properties"]["collaboration"]
        checks = collaboration["properties"]["checks"]
        record = value["$defs"]["collaboratorCheck"]["properties"]
        self.assertEqual(collaboration["properties"]["envelope_version"]["const"], "3.0")
        self.assertEqual((checks["minItems"], checks["maxItems"]), (2, 2))
        self.assertEqual(set(record["skill_id"]["enum"]), KNOWN_COLLABORATORS)
        self.assertEqual(set(record["discovery"]["properties"]["state"]["enum"]), VALID_DISCOVERY)
        self.assertEqual(set(record["applicability"]["properties"]["state"]["enum"]), VALID_APPLICABILITY)
        self.assertEqual(set(record["lifecycle"]["properties"]["state"]["enum"]), VALID_LIFECYCLE)
        self.assertEqual(set(record["lifecycle"]["properties"]["result_state"]["enum"]), VALID_RESULT_STATE)
        self.assertEqual(set(record["consequence"]["properties"]["state"]["enum"]), VALID_CONSEQUENCE)
        self.assertNotIn("enum", record["lifecycle"]["properties"]["native_status"])

    def test_source_safety_contract_is_closed_and_never_grants_trust(self) -> None:
        """The structural sidecar preserves quarantine and execution receipts."""

        source_safety = schema()["properties"]["source_safety"]
        properties = source_safety["properties"]
        dynamic = properties["dynamic_execution"]
        self.assertFalse(source_safety["additionalProperties"])
        self.assertEqual(properties["trust_state"]["const"], "untrusted")
        self.assertTrue(properties["instruction_boundary_applied"]["const"])
        self.assertEqual(
            set(properties["indicator_scan"]["properties"]["state"]["enum"]),
            VALID_INDICATOR_SCAN,
        )
        self.assertEqual(set(dynamic["properties"]["isolation_state"]["enum"]), VALID_ISOLATION_STATE)
        self.assertEqual(set(dynamic["properties"]["network_state"]["enum"]), VALID_NETWORK_STATE)
        self.assertIn("authorization_ref", dynamic["required"])

    def test_adapter_and_doctrine_receipt_contracts(self) -> None:
        """Versioned adapters preserve swarm accounting and docket history."""

        definitions = schema()["$defs"]
        self.assertEqual(definitions["swarmAdapter"]["properties"]["adapter_version"]["const"], "1.0")
        self.assertIn("subtree_accounted", definitions["swarmAdapter"]["required"])
        self.assertEqual(definitions["doctrineAdapter"]["properties"]["adapter_version"]["const"], "1.0")
        receipt = definitions["doctrineReceipt"]["properties"]
        self.assertEqual(set(receipt["phase"]["enum"]), VALID_REVIEW_PHASES)
        self.assertEqual(set(receipt["gate_state"]["enum"]), VALID_GATE_STATE)
        self.assertEqual(set(receipt["disposition"]["enum"]), VALID_REVIEW_DISPOSITION)
        self.assertEqual(set(receipt["source_completeness"]["enum"]), VALID_SOURCE_COMPLETENESS)
        self.assertNotIn("enum", receipt["native_status"])

    def test_definition_of_done_matches(self) -> None:
        """Completion vocabulary stays aligned across both validators."""

        dod = schema()["properties"]["definition_of_done"]
        self.assertEqual(set(dod["additionalProperties"]["enum"]), VALID_DOD_STATUS)


if __name__ == "__main__":
    unittest.main()
