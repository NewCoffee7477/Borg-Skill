#!/usr/bin/env python3
"""Validate a Borg v3.1 assessment sidecar with only the Python standard library.

The JSON Schema is the structural interchange contract.  This script is the
normative semantic validator: it closes the objects, enforces stable IDs, and
checks source-safety and collaborator truth across fields.  Version 3 is
intentionally a clean break.  A v2 collaboration object is rejected; silently
guessing a migration would turn absence or an old status label into false
applicability evidence.  Version 3.1 also requires an explicit source-safety
record so a report cannot omit the boundary protecting the model from source
instructions or imply trust merely because a heuristic scan found nothing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


# Stable IDs remain unchanged across the v3 contract break because candidate
# continuity is useful, while the collaboration envelope itself is versioned.
ASSESSMENT_ID = re.compile(r"^BORG-A-\d{8}-\d{3,}$")
CANDIDATE_ID = re.compile(r"^BORG-([PSN])\d{3,}$")
CAPABILITY_ID = re.compile(r"^CAP-\d{3,}$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

VALID_MODES = {"broad-reconnaissance", "targeted-transfer", "placement-analysis", "redundancy-review", "candidate-planning", "controlled-execution", "reassessment", "recurring-discovery"}
VALID_GRADES = {"E0", "E1", "E2", "E3", "E4"}
VALID_CONFIDENCE = {"low", "medium", "high"}
VALID_ROBUSTNESS = {"robust", "moderately-robust", "unstable", "not-assessed"}
VALID_ASSIMILATION_FORMS = {"configure", "compose", "extend", "optional-mode", "plugin-adapter", "shared-service-library", "upstream-contribution", "fork", "new-skill-component", "external", "defer", "reject"}
VALID_REASON_CODES = {"DUP", "DOM", "EXT", "INC", "COST", "RISK", "IRR", "IMM", "LOCK", "EXCL", "DEFER"}
VALID_DISCOVERY = {"present", "absent", "unknown"}
VALID_APPLICABILITY = {"required", "eligible", "not-applicable", "unknown"}
VALID_LIFECYCLE = {"not-started", "running", "complete", "degraded", "blocked", "unavailable", "failed"}
VALID_RESULT_STATE = {"none", "partial", "terminal"}
VALID_CONSEQUENCE = {"none", "scope-limited", "blocked"}
VALID_REVIEW_PHASES = {"plan", "pre-action", "execution", "response", "full-docket"}
VALID_GATE_STATE = {"satisfied", "unsatisfied", "invalid-docket"}
VALID_REVIEW_DISPOSITION = {"current", "superseded"}
VALID_SOURCE_COMPLETENESS = {"COMPLETE", "ISSUE_COMPLETE_CORPUS_PARTIAL", "INCOMPLETE"}
VALID_DOD_STATUS = {"pass", "fail", "not-applicable", "bounded-limitation"}
VALID_INDICATOR_SCAN = {"not-run", "no-indicators", "indicators", "unavailable"}
VALID_ISOLATION_STATE = {"not-applicable", "enforced", "unavailable", "failed"}
VALID_NETWORK_STATE = {"not-applicable", "disabled", "allowlisted", "unknown"}
KNOWN_COLLABORATORS = {"subagent-swarm", "doctrine-parliamentarian"}
INDEPENDENT_AUTHORITY_REF = re.compile(r"^(user|host|legal|safety):\S.+$")
SOURCE_EXECUTION_AUTHORITY_REF = re.compile(r"^(user|host):\S.+$")

# Native status is deliberately a free string in the interchange shape.  The
# adapter version, not a global installed-skill enum, determines which values
# the validator understands as terminal success.  Unknown values remain
# recordable but can never manufacture v3 completion.
ADAPTER_TERMINAL_SUCCESS = {
    ("borg.subagent-swarm", "1.0"): {"complete"},
    ("borg.doctrine-parliamentarian", "1.0"): {"complete"},
}
DOCTRINE_SATISFIED_STATUSES = {"PASS"}

TOP_LEVEL_FIELDS = {"assessment_id", "date", "mode", "source", "scope", "source_safety", "coverage", "capabilities", "candidates", "risks", "contradictions", "collaboration", "definition_of_done"}


def load_json(path: Path) -> dict[str, Any]:
    """Load one object and turn parse failures into stable command-line errors."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"File not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from None
    if not isinstance(value, dict):
        raise ValueError("Top-level value must be an object")
    return value


def require_fields(obj: dict[str, Any], required: Iterable[str], path: str, errors: list[str]) -> None:
    """Report all missing keys so one correction pass can repair a record."""

    missing = sorted(set(required) - obj.keys())
    if missing:
        errors.append(f"{path} missing required field(s): {', '.join(missing)}")


def reject_unknown_fields(obj: dict[str, Any], allowed: Iterable[str], path: str, errors: list[str]) -> None:
    """Close objects so misspellings cannot create unvalidated truth fields."""

    unknown = sorted(obj.keys() - set(allowed))
    if unknown:
        errors.append(f"{path} has unknown field(s): {', '.join(unknown)}")


def as_object(value: Any, path: str, errors: list[str]) -> dict[str, Any] | None:
    """Return an object or record one structural error without throwing."""

    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return None
    return value


def as_array(value: Any, path: str, errors: list[str]) -> list[Any] | None:
    """Return an array or record one structural error without throwing."""

    if not isinstance(value, list):
        errors.append(f"{path} must be an array")
        return None
    return value


def nonempty(value: Any, path: str, errors: list[str], nullable: bool = False) -> None:
    """Require meaningful text, optionally allowing an explicit null sentinel."""

    if nullable and value is None:
        return
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path} must be a non-empty string" + (" or null" if nullable else ""))


def string_array(value: Any, path: str, errors: list[str]) -> list[Any] | None:
    """Validate an array of non-empty strings and return it for count checks."""

    items = as_array(value, path, errors)
    if items is not None:
        for index, item in enumerate(items):
            nonempty(item, f"{path}[{index}]", errors)
    return items


def validate_simple_records(data: dict[str, Any], errors: list[str]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Validate source, scope, and coverage records shared by every mode."""

    source = as_object(data.get("source"), "source", errors)
    if source is not None:
        require_fields(source, {"name", "snapshot"}, "source", errors)
        reject_unknown_fields(source, {"name", "snapshot", "canonical_refs"}, "source", errors)
        nonempty(source.get("name"), "source.name", errors)
        nonempty(source.get("snapshot"), "source.snapshot", errors)
        if "canonical_refs" in source:
            string_array(source["canonical_refs"], "source.canonical_refs", errors)
    scope = as_object(data.get("scope"), "scope", errors)
    if scope is not None:
        fields = {"target", "in_scope", "out_of_scope", "execution_authorized"}
        require_fields(scope, fields, "scope", errors)
        reject_unknown_fields(scope, fields, "scope", errors)
        if scope.get("target") is not None and not isinstance(scope.get("target"), str):
            errors.append("scope.target must be a string or null")
        string_array(scope.get("in_scope"), "scope.in_scope", errors)
        string_array(scope.get("out_of_scope"), "scope.out_of_scope", errors)
        if not isinstance(scope.get("execution_authorized"), bool):
            errors.append("scope.execution_authorized must be a boolean")
    coverage = as_object(data.get("coverage"), "coverage", errors)
    if coverage is not None:
        fields = {"evidence_surfaces", "saturated", "limitations"}
        require_fields(coverage, fields, "coverage", errors)
        reject_unknown_fields(coverage, fields, "coverage", errors)
        string_array(coverage.get("evidence_surfaces"), "coverage.evidence_surfaces", errors)
        string_array(coverage.get("limitations"), "coverage.limitations", errors)
        if not isinstance(coverage.get("saturated"), bool):
            errors.append("coverage.saturated must be a boolean")
    return scope, coverage


def validate_source_safety(data: dict[str, Any], errors: list[str]) -> dict[str, Any] | None:
    """Validate the mandatory quarantine and dynamic-execution receipt.

    This record intentionally has no successful or trusted terminal state.
    External content remains untrusted even when the warning scanner reports
    no indicators.  The scanner fields record only coverage and evidence
    references, never copied hostile instructions.  Dynamic execution is a
    separate receipt because static inspection authority must not silently
    expand into permission to run source-controlled code.
    """

    safety = as_object(data.get("source_safety"), "source_safety", errors)
    if safety is None:
        return None
    fields = {"trust_state", "instruction_boundary_applied", "indicator_scan", "inspection_gaps", "dynamic_execution"}
    require_fields(safety, fields, "source_safety", errors)
    reject_unknown_fields(safety, fields, "source_safety", errors)
    if safety.get("trust_state") != "untrusted":
        errors.append("source_safety.trust_state must remain untrusted")
    if safety.get("instruction_boundary_applied") is not True:
        errors.append("source_safety.instruction_boundary_applied must be true")
    string_array(safety.get("inspection_gaps"), "source_safety.inspection_gaps", errors)

    # A clean scan is deliberately not a trust decision.  Evidence references
    # make positive scanner claims auditable without embedding the potentially
    # adversarial text in the assessment sidecar itself.  When the scan cannot
    # run, a human-readable reason makes the reduced coverage explicit.
    scan = as_object(safety.get("indicator_scan"), "source_safety.indicator_scan", errors)
    if scan is not None:
        scan_fields = {"state", "reason", "evidence_refs"}
        require_fields(scan, scan_fields, "source_safety.indicator_scan", errors)
        reject_unknown_fields(scan, scan_fields, "source_safety.indicator_scan", errors)
        scan_state = scan.get("state")
        if scan_state not in VALID_INDICATOR_SCAN:
            errors.append("source_safety.indicator_scan.state is invalid")
        nonempty(scan.get("reason"), "source_safety.indicator_scan.reason", errors, nullable=True)
        scan_refs = string_array(scan.get("evidence_refs"), "source_safety.indicator_scan.evidence_refs", errors)
        if scan_state in {"not-run", "unavailable"} and (not isinstance(scan.get("reason"), str) or not scan["reason"].strip()):
            errors.append("source_safety.indicator_scan not-run or unavailable requires a reason")
        if scan_state in {"no-indicators", "indicators"} and not scan_refs:
            errors.append("source_safety.indicator_scan result requires evidence_refs")

    # The receipt distinguishes permission, actual execution, and containment.
    # An authorization record alone is never execution evidence.  Conversely,
    # any executed source must prove enforced isolation, bounded network state,
    # no credential exposure, and retained evidence before acceptance passes.
    dynamic = as_object(safety.get("dynamic_execution"), "source_safety.dynamic_execution", errors)
    if dynamic is None:
        return None
    dynamic_fields = {"requested", "authorized", "authorization_ref", "executed", "isolation_state", "network_state", "credentials_exposed", "evidence_refs"}
    require_fields(dynamic, dynamic_fields, "source_safety.dynamic_execution", errors)
    reject_unknown_fields(dynamic, dynamic_fields, "source_safety.dynamic_execution", errors)
    for field in ("requested", "authorized", "executed", "credentials_exposed"):
        if not isinstance(dynamic.get(field), bool):
            errors.append(f"source_safety.dynamic_execution.{field} must be a boolean")
    authorization_ref = dynamic.get("authorization_ref")
    nonempty(authorization_ref, "source_safety.dynamic_execution.authorization_ref", errors, nullable=True)
    if dynamic.get("isolation_state") not in VALID_ISOLATION_STATE:
        errors.append("source_safety.dynamic_execution.isolation_state is invalid")
    if dynamic.get("network_state") not in VALID_NETWORK_STATE:
        errors.append("source_safety.dynamic_execution.network_state is invalid")
    execution_refs = string_array(dynamic.get("evidence_refs"), "source_safety.dynamic_execution.evidence_refs", errors)

    if dynamic.get("requested") is False:
        if dynamic.get("authorized") is not False or dynamic.get("executed") is not False:
            errors.append("source_safety.dynamic_execution not requested requires authorized=false and executed=false")
        if dynamic.get("isolation_state") != "not-applicable" or dynamic.get("network_state") != "not-applicable":
            errors.append("source_safety.dynamic_execution not requested requires not-applicable isolation and network states")
    if dynamic.get("authorized") is True:
        if dynamic.get("requested") is not True:
            errors.append("source_safety.dynamic_execution authorized=true requires requested=true")
        if not isinstance(authorization_ref, str) or not SOURCE_EXECUTION_AUTHORITY_REF.fullmatch(authorization_ref):
            errors.append("source_safety.dynamic_execution authorized=true requires a separate user or host authorization_ref")
    elif authorization_ref is not None:
        errors.append("source_safety.dynamic_execution authorized=false requires authorization_ref=null")
    if dynamic.get("isolation_state") == "enforced":
        if dynamic.get("requested") is not True or dynamic.get("authorized") is not True or not execution_refs:
            errors.append("source_safety.dynamic_execution enforced isolation requires a requested, authorized operation and evidence_refs")
    if dynamic.get("credentials_exposed") is True:
        errors.append("source_safety.dynamic_execution credentials_exposed must be false")
    if dynamic.get("executed") is True:
        if dynamic.get("requested") is not True or dynamic.get("authorized") is not True:
            errors.append("source_safety.dynamic_execution executed=true requires requested=true and authorized=true")
        if dynamic.get("isolation_state") != "enforced":
            errors.append("source_safety.dynamic_execution executed=true requires isolation_state=enforced")
        if dynamic.get("network_state") not in {"disabled", "allowlisted"}:
            errors.append("source_safety.dynamic_execution executed=true requires disabled or allowlisted network")
        if dynamic.get("credentials_exposed") is not False:
            errors.append("source_safety.dynamic_execution executed=true requires credentials_exposed=false")
        if not execution_refs:
            errors.append("source_safety.dynamic_execution executed=true requires evidence_refs")
    return dynamic


def validate_capabilities(data: dict[str, Any], errors: list[str]) -> None:
    """Validate normalized capabilities and prevent duplicate stable IDs."""

    values = as_array(data.get("capabilities"), "capabilities", errors)
    if values is None:
        return
    seen: set[str] = set()
    fields = {"capability_id", "normalized_name", "evidence_grade", "confidence"}
    for index, value in enumerate(values):
        path = f"capabilities[{index}]"
        item = as_object(value, path, errors)
        if item is None:
            continue
        require_fields(item, fields, path, errors)
        reject_unknown_fields(item, fields, path, errors)
        identifier = item.get("capability_id")
        if not isinstance(identifier, str) or not CAPABILITY_ID.fullmatch(identifier):
            errors.append(f"{path}.capability_id is invalid")
        elif identifier in seen:
            errors.append(f"Duplicate capability_id: {identifier}")
        else:
            seen.add(identifier)
        nonempty(item.get("normalized_name"), f"{path}.normalized_name", errors)
        if item.get("evidence_grade") not in VALID_GRADES:
            errors.append(f"{path}.evidence_grade must be E0-E4")
        if item.get("confidence") not in VALID_CONFIDENCE:
            errors.append(f"{path}.confidence is invalid")


def validate_candidates(data: dict[str, Any], errors: list[str]) -> list[dict[str, Any]]:
    """Validate candidate identity, evidence, scores, and classification rules."""

    values = as_array(data.get("candidates"), "candidates", errors)
    if values is None:
        return []
    allowed = {"candidate_id", "classification", "capability", "destination", "assimilation_form", "reason_codes", "hard_gates_pass", "score", "score_range", "robustness", "confidence", "evidence_refs", "promotion_test", "next_action"}
    required = {"candidate_id", "classification", "capability", "destination", "assimilation_form", "hard_gates_pass", "robustness", "confidence", "evidence_refs", "next_action"}
    seen: set[str] = set()
    candidates: list[dict[str, Any]] = []
    for index, value in enumerate(values):
        path = f"candidates[{index}]"
        item = as_object(value, path, errors)
        if item is None:
            continue
        candidates.append(item)
        require_fields(item, required, path, errors)
        reject_unknown_fields(item, allowed, path, errors)
        identifier = item.get("candidate_id")
        match = CANDIDATE_ID.fullmatch(identifier) if isinstance(identifier, str) else None
        if match is None:
            errors.append(f"{path}.candidate_id is invalid")
        else:
            expected = {"P": "primary", "S": "secondary", "N": "do-not-assimilate"}[match.group(1)]
            if identifier in seen:
                errors.append(f"Duplicate candidate_id: {identifier}")
            seen.add(identifier)
            if item.get("classification") != expected:
                errors.append(f"{identifier}: classification must be {expected}")
        nonempty(item.get("capability"), f"{path}.capability", errors)
        if item.get("destination") is not None and not isinstance(item.get("destination"), str):
            errors.append(f"{path}.destination must be a string or null")
        if item.get("assimilation_form") not in VALID_ASSIMILATION_FORMS:
            errors.append(f"{path}.assimilation_form is invalid")
        if not isinstance(item.get("hard_gates_pass"), bool):
            errors.append(f"{path}.hard_gates_pass must be a boolean")
        if item.get("robustness") not in VALID_ROBUSTNESS:
            errors.append(f"{path}.robustness is invalid")
        if item.get("confidence") not in VALID_CONFIDENCE:
            errors.append(f"{path}.confidence is invalid")
        refs = string_array(item.get("evidence_refs"), f"{path}.evidence_refs", errors)
        if refs == []:
            errors.append(f"{path}.evidence_refs must not be empty")
        nonempty(item.get("next_action"), f"{path}.next_action", errors)
        if "promotion_test" in item:
            nonempty(item.get("promotion_test"), f"{path}.promotion_test", errors, nullable=True)
        reasons = item.get("reason_codes", [])
        if not isinstance(reasons, list) or any(reason not in VALID_REASON_CODES for reason in reasons):
            errors.append(f"{path}.reason_codes contains an invalid code")
        score = item.get("score")
        if score is not None and (isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 100):
            errors.append(f"{path}.score must be 0..100 or null")
        score_range = item.get("score_range")
        if score_range is not None and (not isinstance(score_range, list) or len(score_range) != 2 or any(isinstance(number, bool) or not isinstance(number, (int, float)) or not 0 <= number <= 100 for number in score_range) or score_range[0] > score_range[1]):
            errors.append(f"{path}.score_range must be an ordered pair within 0..100 or null")
        if match and match.group(1) == "P" and item.get("hard_gates_pass") is not True:
            errors.append(f"{identifier}: Primary requires hard_gates_pass=true")
        if match and match.group(1) == "S" and not item.get("promotion_test"):
            errors.append(f"{identifier}: Secondary requires promotion_test")
        if match and match.group(1) == "N" and not reasons:
            errors.append(f"{identifier}: Do Not Assimilate requires reason_codes")
    return candidates


def validate_contract(value: Any, path: str, errors: list[str]) -> dict[str, Any] | None:
    """Validate a nullable inspected contract without inferring it from discovery."""

    if value is None:
        return None
    contract = as_object(value, path, errors)
    if contract is None:
        return None
    fields = {"source", "version_or_hash", "inspected_at"}
    require_fields(contract, fields, path, errors)
    reject_unknown_fields(contract, fields, path, errors)
    for field in fields:
        nonempty(contract.get(field), f"{path}.{field}", errors)
    return contract


def validate_doctrine_adapter(adapter: dict[str, Any], path: str, errors: list[str]) -> bool:
    """Validate correlated receipts while retaining superseded review history."""

    fields = {"adapter_id", "adapter_version", "reviews"}
    require_fields(adapter, fields, path, errors)
    reject_unknown_fields(adapter, fields, path, errors)
    if adapter.get("adapter_id") != "borg.doctrine-parliamentarian" or adapter.get("adapter_version") != "1.0":
        errors.append(f"{path} must use supported doctrine adapter borg.doctrine-parliamentarian@1.0")
    reviews = as_array(adapter.get("reviews"), f"{path}.reviews", errors)
    if reviews is None:
        return False
    receipt_fields = {"review_id", "phase_id", "phase", "native_status", "gate_state", "disposition", "superseded_by_phase_id", "source_completeness", "confidence", "result_received", "accounted", "blocker", "evidence_ref"}
    phase_ids: set[str] = set()
    current_phases: set[tuple[str, str]] = set()
    supersession_targets: list[tuple[str, str, str]] = []
    current_satisfied = True
    for index, value in enumerate(reviews):
        receipt_path = f"{path}.reviews[{index}]"
        receipt = as_object(value, receipt_path, errors)
        if receipt is None:
            current_satisfied = False
            continue
        require_fields(receipt, receipt_fields, receipt_path, errors)
        reject_unknown_fields(receipt, receipt_fields, receipt_path, errors)
        for field in {"review_id", "phase_id", "evidence_ref"}:
            nonempty(receipt.get(field), f"{receipt_path}.{field}", errors)
        phase_id = receipt.get("phase_id")
        if isinstance(phase_id, str):
            if phase_id in phase_ids:
                errors.append(f"{receipt_path}.phase_id must be unique")
            phase_ids.add(phase_id)
        if receipt.get("phase") not in VALID_REVIEW_PHASES:
            errors.append(f"{receipt_path}.phase is invalid")
        if receipt.get("gate_state") not in VALID_GATE_STATE:
            errors.append(f"{receipt_path}.gate_state is invalid")
        if receipt.get("disposition") not in VALID_REVIEW_DISPOSITION:
            errors.append(f"{receipt_path}.disposition is invalid")
        if receipt.get("source_completeness") not in VALID_SOURCE_COMPLETENESS:
            errors.append(f"{receipt_path}.source_completeness is invalid")
        if receipt.get("confidence") not in VALID_CONFIDENCE:
            errors.append(f"{receipt_path}.confidence is invalid")
        native_status = receipt.get("native_status")
        if native_status is not None and not isinstance(native_status, str):
            errors.append(f"{receipt_path}.native_status must be a string or null")
        if not isinstance(receipt.get("result_received"), bool) or not isinstance(receipt.get("accounted"), bool):
            errors.append(f"{receipt_path} result_received and accounted must be booleans")
        nonempty(receipt.get("blocker"), f"{receipt_path}.blocker", errors, nullable=True)
        if receipt.get("gate_state") == "satisfied" and native_status not in DOCTRINE_SATISFIED_STATUSES:
            errors.append(f"{receipt_path}: satisfied gate is inconsistent with native_status")
        if receipt.get("gate_state") == "satisfied" and (receipt.get("result_received") is not True or receipt.get("accounted") is not True or receipt.get("blocker") is not None):
            errors.append(f"{receipt_path}: satisfied gate requires result, accounting, and blocker=null")
        key = (str(receipt.get("review_id")), str(receipt.get("phase")))
        if receipt.get("disposition") == "current":
            if key in current_phases:
                errors.append(f"{path}: each review phase may have only one current receipt")
            current_phases.add(key)
            if receipt.get("gate_state") != "satisfied":
                current_satisfied = False
            if receipt.get("superseded_by_phase_id") is not None:
                errors.append(f"{receipt_path}: current receipt requires superseded_by_phase_id=null")
        elif receipt.get("disposition") == "superseded":
            target = receipt.get("superseded_by_phase_id")
            nonempty(target, f"{receipt_path}.superseded_by_phase_id", errors)
            if isinstance(target, str):
                supersession_targets.append((receipt_path, str(receipt.get("review_id")), target))
    for receipt_path, review_id, target in supersession_targets:
        matching = [receipt for receipt in reviews if isinstance(receipt, dict) and receipt.get("phase_id") == target]
        if not matching or matching[0].get("review_id") != review_id:
            errors.append(f"{receipt_path}: superseded_by_phase_id must reference the same review")
    return bool(reviews) and current_satisfied


def validate_swarm_adapter(adapter: dict[str, Any], path: str, errors: list[str]) -> bool:
    """Validate lead-owned lane identity and whole-subtree accounting evidence."""

    fields = {"adapter_id", "adapter_version", "agent_path", "parent_lane", "tier", "subtree_accounted", "result_evidence_refs"}
    require_fields(adapter, fields, path, errors)
    reject_unknown_fields(adapter, fields, path, errors)
    if adapter.get("adapter_id") != "borg.subagent-swarm" or adapter.get("adapter_version") != "1.0":
        errors.append(f"{path} must use supported swarm adapter borg.subagent-swarm@1.0")
    nonempty(adapter.get("agent_path"), f"{path}.agent_path", errors)
    nonempty(adapter.get("parent_lane"), f"{path}.parent_lane", errors, nullable=True)
    tier = adapter.get("tier")
    if isinstance(tier, bool) or not isinstance(tier, int) or tier < 0:
        errors.append(f"{path}.tier must be a non-negative integer")
    if not isinstance(adapter.get("subtree_accounted"), bool):
        errors.append(f"{path}.subtree_accounted must be a boolean")
    refs = string_array(adapter.get("result_evidence_refs"), f"{path}.result_evidence_refs", errors)
    return adapter.get("subtree_accounted") is True and bool(refs)


def validate_collaboration(data: dict[str, Any], errors: list[str]) -> list[dict[str, Any]]:
    """Validate exactly one truthful check for each optional collaborator."""

    collaboration = as_object(data.get("collaboration"), "collaboration", errors)
    if collaboration is None:
        return []
    fields = {"envelope_version", "checks"}
    require_fields(collaboration, fields, "collaboration", errors)
    reject_unknown_fields(collaboration, fields, "collaboration", errors)
    if collaboration.get("envelope_version") != "3.0":
        errors.append("collaboration.envelope_version must be 3.0; v2 is not accepted or migrated")
    checks = as_array(collaboration.get("checks"), "collaboration.checks", errors)
    if checks is None:
        return []
    allowed = {"skill_id", "discovery", "contract", "applicability", "lifecycle", "consequence", "adapter"}
    seen: list[str] = []
    valid_checks: list[dict[str, Any]] = []
    for index, value in enumerate(checks):
        path = f"collaboration.checks[{index}]"
        check = as_object(value, path, errors)
        if check is None:
            continue
        valid_checks.append(check)
        require_fields(check, allowed, path, errors)
        reject_unknown_fields(check, allowed, path, errors)
        skill_id = check.get("skill_id")
        if skill_id not in KNOWN_COLLABORATORS:
            errors.append(f"{path}.skill_id is not a known optional collaborator")
        elif skill_id in seen:
            errors.append(f"{path}.skill_id duplicates {skill_id}")
        else:
            seen.append(skill_id)

        discovery = as_object(check.get("discovery"), f"{path}.discovery", errors)
        if discovery is not None:
            discovery_fields = {"state", "checked_at", "evidence_refs"}
            require_fields(discovery, discovery_fields, f"{path}.discovery", errors)
            reject_unknown_fields(discovery, discovery_fields, f"{path}.discovery", errors)
            if discovery.get("state") not in VALID_DISCOVERY:
                errors.append(f"{path}.discovery.state is invalid")
            nonempty(discovery.get("checked_at"), f"{path}.discovery.checked_at", errors)
            string_array(discovery.get("evidence_refs"), f"{path}.discovery.evidence_refs", errors)
        contract = validate_contract(check.get("contract"), f"{path}.contract", errors)
        applicability = as_object(check.get("applicability"), f"{path}.applicability", errors)
        applicability_state = None
        if applicability is not None:
            app_fields = {"state", "reason", "authority_ref"}
            require_fields(applicability, app_fields, f"{path}.applicability", errors)
            reject_unknown_fields(applicability, app_fields, f"{path}.applicability", errors)
            applicability_state = applicability.get("state")
            if applicability_state not in VALID_APPLICABILITY:
                errors.append(f"{path}.applicability.state is invalid")
            nonempty(applicability.get("reason"), f"{path}.applicability.reason", errors)
            nonempty(applicability.get("authority_ref"), f"{path}.applicability.authority_ref", errors, nullable=True)
        # Installation absence supplies no contract-derived answer.  Only a
        # separately observed governing policy can normalize applicability.
        if discovery and discovery.get("state") != "present" and contract is not None:
            errors.append(f"{path}: absent or unknown discovery requires contract=null")
        if discovery and discovery.get("state") == "absent" and applicability_state != "unknown":
            errors.append(f"{path}: absent discovery requires applicability.state=unknown")
        if discovery and discovery.get("state") == "absent" and applicability and applicability.get("authority_ref") is not None:
            errors.append(f"{path}: absent discovery requires applicability.authority_ref=null")

        lifecycle = as_object(check.get("lifecycle"), f"{path}.lifecycle", errors)
        lifecycle_state = None
        native_status = None
        if lifecycle is not None:
            life_fields = {"state", "native_status", "execution_mode", "result_state", "accounted", "blocker", "evidence_refs"}
            require_fields(lifecycle, life_fields, f"{path}.lifecycle", errors)
            reject_unknown_fields(lifecycle, life_fields, f"{path}.lifecycle", errors)
            lifecycle_state = lifecycle.get("state")
            native_status = lifecycle.get("native_status")
            if lifecycle_state not in VALID_LIFECYCLE:
                errors.append(f"{path}.lifecycle.state is invalid")
            if native_status is not None and not isinstance(native_status, str):
                errors.append(f"{path}.lifecycle.native_status must be a string or null")
            if lifecycle.get("execution_mode") is not None and not isinstance(lifecycle.get("execution_mode"), str):
                errors.append(f"{path}.lifecycle.execution_mode must be a string or null")
            if lifecycle.get("result_state") not in VALID_RESULT_STATE:
                errors.append(f"{path}.lifecycle.result_state is invalid")
            if not isinstance(lifecycle.get("accounted"), bool):
                errors.append(f"{path}.lifecycle.accounted must be a boolean")
            nonempty(lifecycle.get("blocker"), f"{path}.lifecycle.blocker", errors, nullable=True)
            evidence = string_array(lifecycle.get("evidence_refs"), f"{path}.lifecycle.evidence_refs", errors)
            if lifecycle_state == "not-started" and (native_status is not None or lifecycle.get("result_state") != "none"):
                errors.append(f"{path}: not-started requires native_status=null and result_state=none")
            if lifecycle_state == "complete" and (lifecycle.get("result_state") != "terminal" or lifecycle.get("accounted") is not True or not evidence or lifecycle.get("blocker") is not None):
                errors.append(f"{path}: complete requires terminal result, accounting, evidence, and blocker=null")

        adapter = check.get("adapter")
        adapter_semantics_ok = False
        adapter_key: tuple[Any, Any] | None = None
        if adapter is not None:
            adapter_obj = as_object(adapter, f"{path}.adapter", errors)
            if adapter_obj is not None:
                adapter_key = (adapter_obj.get("adapter_id"), adapter_obj.get("adapter_version"))
                if skill_id == "subagent-swarm":
                    adapter_semantics_ok = validate_swarm_adapter(adapter_obj, f"{path}.adapter", errors)
                elif skill_id == "doctrine-parliamentarian":
                    adapter_semantics_ok = validate_doctrine_adapter(adapter_obj, f"{path}.adapter", errors)
                expected = {"subagent-swarm": "borg.subagent-swarm", "doctrine-parliamentarian": "borg.doctrine-parliamentarian"}.get(skill_id)
                if adapter_obj.get("adapter_id") != expected:
                    errors.append(f"{path}: adapter does not match skill_id")
        if lifecycle_state == "complete":
            recognized = ADAPTER_TERMINAL_SUCCESS.get(adapter_key, set())
            if adapter is None or native_status not in recognized or not adapter_semantics_ok:
                errors.append(f"{path}: complete requires a supported adapter and recognized terminal native_status")

        consequence = as_object(check.get("consequence"), f"{path}.consequence", errors)
        if consequence is not None:
            consequence_fields = {"state", "affected_outputs", "reason", "authority_ref"}
            require_fields(consequence, consequence_fields, f"{path}.consequence", errors)
            reject_unknown_fields(consequence, consequence_fields, f"{path}.consequence", errors)
            effect = consequence.get("state")
            authority_ref = consequence.get("authority_ref")
            affected = string_array(consequence.get("affected_outputs"), f"{path}.consequence.affected_outputs", errors)
            if effect not in VALID_CONSEQUENCE:
                errors.append(f"{path}.consequence.state is invalid")
            if effect == "none":
                if authority_ref is not None or consequence.get("reason") is not None or affected != []:
                    errors.append(f"{path}: consequence none requires affected_outputs=[], reason=null, authority_ref=null")
            else:
                nonempty(consequence.get("reason"), f"{path}.consequence.reason", errors)
                nonempty(authority_ref, f"{path}.consequence.authority_ref", errors)
                if not isinstance(authority_ref, str) or not INDEPENDENT_AUTHORITY_REF.fullmatch(authority_ref):
                    errors.append(f"{path}: consequence authority_ref must identify user, host, legal, or safety authority")
                if not affected:
                    errors.append(f"{path}: scope-limited or blocked requires independent authority_ref and affected outputs")
                # A required consequence cannot be declared satisfied by a
                # native word the pinned adapter does not understand.
                if applicability_state == "required" and lifecycle_state == "complete" and native_status not in ADAPTER_TERMINAL_SUCCESS.get(adapter_key, set()):
                    errors.append(f"{path}: unknown native status cannot satisfy a required consequence")
    if len(checks) != 2 or set(seen) != KNOWN_COLLABORATORS:
        errors.append("collaboration.checks must contain exactly one check for each known optional collaborator")
    return valid_checks


def validate(data: dict[str, Any]) -> list[str]:
    """Return all v3.1 acceptance errors; an empty list is a normative PASS."""

    errors: list[str] = []
    require_fields(data, TOP_LEVEL_FIELDS, "assessment", errors)
    reject_unknown_fields(data, TOP_LEVEL_FIELDS, "assessment", errors)
    identifier = data.get("assessment_id")
    if not isinstance(identifier, str) or not ASSESSMENT_ID.fullmatch(identifier):
        errors.append("assessment_id is invalid")
    date = data.get("date")
    if not isinstance(date, str) or not ISO_DATE.fullmatch(date):
        errors.append("date must be YYYY-MM-DD")
    if data.get("mode") not in VALID_MODES:
        errors.append("mode is invalid")
    scope, coverage = validate_simple_records(data, errors)
    dynamic_execution = validate_source_safety(data, errors)
    validate_capabilities(data, errors)
    candidates = validate_candidates(data, errors)
    validate_collaboration(data, errors)
    string_array(data.get("risks"), "risks", errors)
    string_array(data.get("contradictions"), "contradictions", errors)
    dod = as_object(data.get("definition_of_done"), "definition_of_done", errors)
    if dod is not None:
        if not dod:
            errors.append("definition_of_done must not be empty")
        for key, value in dod.items():
            nonempty(key, "definition_of_done key", errors)
            if value not in VALID_DOD_STATUS:
                errors.append(f"definition_of_done.{key} is invalid")
    if data.get("mode") == "controlled-execution" and (scope is None or scope.get("execution_authorized") is not True):
        errors.append("controlled-execution requires scope.execution_authorized=true")
    # Assimilation authority in ``scope`` and permission to run untrusted
    # source are intentionally independent grants.  A controlled reimplementation
    # can rely entirely on static evidence; it must not be forced to request or
    # execute source.  Only a positive execution claim is mode-bound here, and
    # the source-safety validator above separately proves exact authorization,
    # containment, network restriction, and credential isolation.
    if dynamic_execution is not None:
        if dynamic_execution.get("executed") is True and data.get("mode") != "controlled-execution":
            errors.append("source_safety.dynamic_execution executed=true requires mode=controlled-execution")
    if coverage and coverage.get("saturated") is False and any(candidate.get("classification") == "primary" for candidate in candidates):
        errors.append("Primary candidate conflicts with unsaturated coverage")
    return errors


def main(argv: list[str] | None = None) -> int:
    """Run the validator and emit one stable PASS or a complete error list."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assessment", type=Path, help="Path to a Borg v3.1 assessment JSON file")
    args = parser.parse_args(argv)
    try:
        data = load_json(args.assessment)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    errors = validate(data)
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
