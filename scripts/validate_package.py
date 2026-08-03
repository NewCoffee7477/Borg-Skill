#!/usr/bin/env python3
"""Run deterministic, inert checks against the Borg project package.

This validator is a development-time guardrail.  It never installs or invokes
Borg and it never touches a Codex or OpenClaw skill directory.  Its purpose is
to verify facts that can be established from the project source alone:

* the portable skill entrypoint uses minimal trigger frontmatter;
* Codex UI metadata is well formed at the small subset Borg uses;
* every routed Markdown reference exists and long references are navigable;
* the sample sidecar passes the normative standard-library assessment validator;
* obsolete hypothetical collaborator fields have not returned; and
* the project-source manifest exactly describes the retained files.

Runtime behavior is intentionally outside this script's claim.  A passing
package remains only statically verified until a separately authorized host
installation and runtime acceptance exercise occur.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

# The assessment validator lives beside this script.  Importing it executes no
# work because its command-line entrypoint is protected by ``__main__``.
from validate_assessment import load_json as load_assessment_json
from validate_assessment import validate as validate_assessment
from validate_privacy import scan_paths


FRONTMATTER_KEY = re.compile(r"^([a-z][a-z0-9-]*):\s*(.*)$")
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
QUOTED_YAML_VALUE = re.compile(r'^\s{2}([a-z_]+):\s+"(.*)"\s*$')
SHA256 = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_PACKAGE_VERSION = "0.3.1-working-draft"

# These files are local filesystem artifacts or self-referential metadata and
# therefore do not belong in the hash inventory.  ``MANIFEST.json`` cannot
# hash itself without a circular definition; Finder metadata and Python byte
# code are never part of the project payload.
MANIFEST_EXCLUSIONS = {"MANIFEST.json"}

# Source trees are expected to be reviewable text.  Release archives and other
# opaque payloads have a separate, exact-manifest contract and are never valid
# as unmanifested project source.
FORBIDDEN_BINARY_SUFFIXES = {".pyc", ".zip", ".tar", ".gz", ".dmg", ".png", ".jpg", ".jpeg", ".pdf"}

# Modern macOS can attach these two operating-system provenance attributes to
# files created or edited by an application and can refuse ordinary removal
# while System Integrity Protection remains enabled.  They are not copied by
# Borg's byte-oriented ZIP builder.  Treating them as source-content failures
# would therefore make the source gate impossible to satisfy on a protected
# Mac without weakening the host's security posture.  All other attributes,
# including quarantine metadata and unknown names, remain hard failures.
NONTRANSFERABLE_SYSTEM_XATTRS = {"com.apple.macl", "com.apple.provenance"}


def parse_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    """Parse a JSON object and keep all package errors in one final report."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"Missing JSON file: {path}")
        return None
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid JSON in {path}: line {exc.lineno}, column {exc.colno}: {exc.msg}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{path} must contain a top-level object")
        return None
    return value


def validate_skill_frontmatter(root: Path, errors: list[str]) -> None:
    """Validate the deliberately simple two-field SKILL.md frontmatter.

    Borg uses one-line scalar values, so a small parser is safer here than a
    hidden PyYAML dependency.  If the skill later needs multiline YAML, this
    validator must be upgraded at the same time rather than silently guessing.
    """

    path = root / "SKILL.md"
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append("SKILL.md is missing")
        return
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        errors.append("SKILL.md must begin with a closed YAML frontmatter block")
        return

    frontmatter_text, _ = text[4:].split("\n---\n", 1)
    fields: dict[str, str] = {}
    for line_number, line in enumerate(frontmatter_text.splitlines(), start=2):
        match = FRONTMATTER_KEY.fullmatch(line)
        if match is None:
            errors.append(f"SKILL.md:{line_number} uses unsupported frontmatter syntax")
            continue
        key, value = match.groups()
        if key in fields:
            errors.append(f"SKILL.md frontmatter duplicates {key}")
        fields[key] = value.strip()

    if set(fields) != {"name", "description"}:
        errors.append("SKILL.md frontmatter must contain exactly name and description")
    if fields.get("name") != "borg":
        errors.append("SKILL.md name must be borg")
    description = fields.get("description", "")
    if not description:
        errors.append("SKILL.md description must be non-empty")
    if len(description) > 1024:
        errors.append("SKILL.md description exceeds 1024 characters")
    if "<" in description or ">" in description:
        errors.append("SKILL.md description cannot contain angle brackets")


def validate_openai_metadata(root: Path, errors: list[str]) -> None:
    """Check only the Codex UI fields that Borg intentionally declares."""

    path = root / "agents" / "openai.yaml"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        errors.append("agents/openai.yaml is missing")
        return
    if not lines or lines[0] != "interface:":
        errors.append("agents/openai.yaml must contain only an interface mapping")
        return

    fields: dict[str, str] = {}
    for line_number, line in enumerate(lines[1:], start=2):
        match = QUOTED_YAML_VALUE.fullmatch(line)
        if match is None:
            errors.append(f"agents/openai.yaml:{line_number} is not a quoted interface string")
            continue
        key, value = match.groups()
        if key in fields:
            errors.append(f"agents/openai.yaml duplicates {key}")
        fields[key] = value

    required = {"display_name", "short_description", "default_prompt"}
    if set(fields) != required:
        errors.append("agents/openai.yaml must declare display_name, short_description, and default_prompt")
    if fields.get("display_name") != "Borg":
        errors.append("agents/openai.yaml display_name must be Borg")
    short_description = fields.get("short_description", "")
    if not 25 <= len(short_description) <= 64:
        errors.append("agents/openai.yaml short_description must be 25-64 characters")
    if "$borg" not in fields.get("default_prompt", ""):
        errors.append("agents/openai.yaml default_prompt must mention $borg")


def validate_markdown_routing(root: Path, errors: list[str]) -> None:
    """Resolve local links and enforce direct progressive-disclosure routing."""

    markdown_files = sorted(root.rglob("*.md"))
    for path in markdown_files:
        text = path.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(text):
            # Web URLs and same-file anchors are outside local path validation.
            if "://" in target or target.startswith("#"):
                continue
            relative_target = target.split("#", 1)[0]
            resolved = (path.parent / relative_target).resolve()
            if not resolved.exists():
                errors.append(f"Broken Markdown link in {path.relative_to(root)}: {target}")

    skill_text = (root / "SKILL.md").read_text(encoding="utf-8")
    for reference in sorted((root / "references").glob("*.md")):
        routed = f"references/{reference.name}"
        if f"]({routed})" not in skill_text:
            errors.append(f"SKILL.md does not directly route {routed}")
        lines = reference.read_text(encoding="utf-8").splitlines()
        if len(lines) > 100 and "## Contents" not in lines[:20]:
            errors.append(f"{routed} exceeds 100 lines without an early Contents section")


def validate_collaborator_language(root: Path, errors: list[str]) -> None:
    """Prevent the obsolete draft protocol from re-entering runtime artifacts."""

    runtime_paths = [root / "SKILL.md"]
    runtime_paths.extend(sorted((root / "references").glob("*.md")))
    runtime_paths.extend(sorted((root / "assets").glob("*")))
    runtime_paths.append(root / "scripts" / "validate_assessment.py")

    forbidden = {
        "Subagent Swarms": "use the exact identifier subagent-swarm",
        "cleric_gates": "use collaboration.doctrine_parliamentarian receipts",
    }
    gate_pattern = re.compile(r"\bC[0-4]\b")
    for path in runtime_paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for phrase, correction in forbidden.items():
            if phrase in text:
                errors.append(f"{path.relative_to(root)} contains obsolete {phrase!r}; {correction}")
        if gate_pattern.search(text):
            errors.append(f"{path.relative_to(root)} contains obsolete Borg-specific C0-C4 gate names")


def validate_sample(root: Path, errors: list[str]) -> None:
    """Run the same assessment consistency checks that runtime producers use."""

    schema = parse_json(root / "assets" / "assessment-schema.json", errors)
    if schema is not None:
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append("assessment-schema.json must declare Draft 2020-12")
        if schema.get("$id") != "urn:borg:assessment-schema:3.1":
            errors.append("assessment-schema.json must declare the source-safety 3.1 contract identifier")
        comment = schema.get("$comment")
        if not isinstance(comment, str) or "normative Borg acceptance validator" not in comment:
            errors.append(
                "assessment-schema.json must identify validate_assessment.py as the normative semantic validator"
            )
    try:
        sample = load_assessment_json(root / "assets" / "sample-assessment.json")
    except ValueError as exc:
        errors.append(f"sample-assessment.json: {exc}")
        return
    sample_errors = validate_assessment(sample)
    for sample_error in sample_errors:
        errors.append(f"sample-assessment.json: {sample_error}")


def iter_manifest_files(root: Path) -> set[str]:
    """Return every source file except the necessarily self-referential manifest.

    Root Git internals are repository transport state, not public worktree
    source, so ``iter_source_objects`` omits that one directory. Deliberately
    do not apply ``.gitignore`` or filter caches, Finder metadata, binaries, or
    nested repositories here. Such contamination must become an observable
    omission/hygiene failure rather than disappearing from the validator's
    view merely because Git would not stage it by default.
    """

    paths: set[str] = set()
    for path in iter_source_objects(root):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        relative_text = str(relative)
        if relative_text in MANIFEST_EXCLUSIONS:
            continue
        paths.add(relative_text)
    return paths


def iter_source_objects(root: Path) -> list[Path]:
    """Enumerate public worktree objects while pruning only root ``.git``.

    A normal checkout's root ``.git`` directory contains object databases,
    refs, local configuration, and eventual author metadata. None of those
    bytes are part of a commit, source manifest, skill package, or GitHub tree.
    Walking them would make validation depend on transport internals and could
    repeat private local identity data in diagnostics.

    The exclusion is intentionally narrow: it applies only when ``root/.git``
    is an actual directory and not a symlink. A nested ``.git`` directory, a
    root ``.git`` file, or any ignored cache remains visible to hygiene and
    manifest checks. This prevents the transport exception from becoming a
    general-purpose hiding place for publishable source contamination.
    """

    root = Path(root)
    git_directory = root / ".git"
    skip_root_git = git_directory.is_dir() and not git_directory.is_symlink()
    objects: list[Path] = []
    for directory, child_directories, filenames in os.walk(root, topdown=True, followlinks=False):
        current = Path(directory)
        if current == root and skip_root_git:
            child_directories[:] = [name for name in child_directories if name != ".git"]
        child_directories.sort()
        filenames.sort()
        objects.extend(current / name for name in child_directories)
        objects.extend(current / name for name in filenames)
    return sorted(objects, key=lambda item: item.relative_to(root).as_posix())


def validate_source_hygiene(root: Path, errors: list[str]) -> None:
    """Reject filesystem and metadata states unsafe for a portable source tree.

    ``lstat`` prevents symlink following.  Extended attributes are inspected
    through the standard library where the host exposes them; ACLs use the
    platform's read-only ``ls -lde`` representation and degrade only when that
    inspection capability itself is unavailable.
    """

    source_objects = [root, *iter_source_objects(root)]
    for path in source_objects:
        relative = path.relative_to(root)
        label = "." if path == root else relative.as_posix()
        try:
            info = path.lstat()
        except OSError as exc:
            errors.append(f"Cannot inspect source path {label}: {exc}")
            continue
        if path.name == ".DS_Store":
            errors.append(f"Forbidden Finder metadata: {label}")
        if "__pycache__" in relative.parts:
            errors.append(f"Forbidden Python cache path: {label}")
        if stat.S_ISLNK(info.st_mode):
            errors.append(f"Symlink is forbidden in project source: {label}")
            continue
        if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            errors.append(f"Special filesystem object is forbidden: {label}")
            continue
        if stat.S_ISREG(info.st_mode):
            if path.suffix.lower() in FORBIDDEN_BINARY_SUFFIXES:
                errors.append(f"Binary/source artifact is forbidden: {label}")
            else:
                try:
                    path.read_text(encoding="utf-8")
                except UnicodeError:
                    errors.append(f"Non-UTF-8 source file is forbidden: {label}")
                except OSError as exc:
                    errors.append(f"Cannot read source file {label}: {exc}")
        if hasattr(os, "listxattr"):
            try:
                attributes = os.listxattr(path, follow_symlinks=False)
            except OSError as exc:
                errors.append(f"Cannot inspect extended attributes on {label}: {exc}")
            else:
                disallowed = sorted(set(attributes) - NONTRANSFERABLE_SYSTEM_XATTRS)
                if disallowed:
                    errors.append(f"Transferable or unknown extended attributes are forbidden on {label}: {', '.join(disallowed)}")

    # macOS marks ACL-bearing modes with ``+`` in ``ls -lde``.  Inspect every
    # source object, including the root, because a child ACL can affect copied
    # data even when the project root itself is clean.  Failure to provide this
    # host capability does not invent a clean result; xattr checks above still
    # run wherever Python exposes them.
    for path in source_objects:
        try:
            acl = subprocess.run(
                ["ls", "-lde", str(path)], capture_output=True, text=True, check=False, timeout=10
            )
        except (OSError, subprocess.SubprocessError):
            break
        if acl.returncode == 0:
            lines = acl.stdout.splitlines()
            if lines and lines[0].split(maxsplit=1)[0].endswith("+"):
                label = "." if path == root else path.relative_to(root).as_posix()
                errors.append(f"ACL entries are forbidden on {label}")


def validate_privacy(root: Path, errors: list[str]) -> None:
    """Integrate the masked, local-only privacy gate into source validation."""

    for finding in scan_paths(root):
        errors.append(f"Privacy finding: {finding.render()}")


def validate_manifest_metadata(manifest: dict[str, Any], errors: list[str]) -> None:
    """Enforce the release identity and the project's static-only status.

    Keeping these checks in a small helper makes version drift testable without
    rewriting the real manifest or manufacturing a second on-disk package.
    Runtime acceptance remains deliberately false until a separately
    authorized installation and live host exercise have actually occurred.
    """

    if manifest.get("package") != "borg":
        errors.append("MANIFEST.json package must be borg")
    if manifest.get("version") != EXPECTED_PACKAGE_VERSION:
        errors.append(f"MANIFEST.json version must be {EXPECTED_PACKAGE_VERSION}")
    if manifest.get("status") != "working-draft":
        errors.append("MANIFEST.json status must be working-draft")
    if manifest.get("manifest_scope") != "project-source":
        errors.append("MANIFEST.json manifest_scope must be project-source")
    if manifest.get("runtime_acceptance") != "not-performed":
        errors.append("MANIFEST.json runtime_acceptance must remain not-performed in this project-only phase")


def validate_manifest(root: Path, errors: list[str]) -> None:
    """Verify exact project-source coverage, byte counts, and SHA-256 hashes."""

    manifest = parse_json(root / "MANIFEST.json", errors)
    if manifest is None:
        return
    validate_manifest_metadata(manifest, errors)

    entries = manifest.get("files")
    if not isinstance(entries, list):
        errors.append("MANIFEST.json files must be an array")
        return
    listed: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(entries):
        if not isinstance(value, dict):
            errors.append(f"MANIFEST.json files[{index}] must be an object")
            continue
        if set(value) != {"path", "bytes", "sha256"}:
            errors.append(f"MANIFEST.json files[{index}] must contain exactly path, bytes, and sha256")
            continue
        path_value = value.get("path")
        if not isinstance(path_value, str) or not path_value:
            errors.append(f"MANIFEST.json files[{index}].path must be a non-empty string")
            continue
        if path_value in listed:
            errors.append(f"MANIFEST.json duplicates {path_value}")
        listed[path_value] = value
        if not isinstance(value.get("bytes"), int) or value["bytes"] < 0:
            errors.append(f"MANIFEST.json {path_value} has invalid bytes")
        if not isinstance(value.get("sha256"), str) or not SHA256.fullmatch(value["sha256"]):
            errors.append(f"MANIFEST.json {path_value} has invalid sha256")

    actual = iter_manifest_files(root)
    missing_entries = sorted(actual - set(listed))
    missing_files = sorted(set(listed) - actual)
    if missing_entries:
        errors.append(f"MANIFEST.json omits project file(s): {', '.join(missing_entries)}")
    if missing_files:
        errors.append(f"MANIFEST.json lists missing file(s): {', '.join(missing_files)}")

    for relative_path, entry in listed.items():
        path = root / relative_path
        if not path.is_file():
            continue
        content = path.read_bytes()
        if len(content) != entry.get("bytes"):
            errors.append(f"MANIFEST.json byte count mismatch: {relative_path}")
        digest = hashlib.sha256(content).hexdigest()
        if digest != entry.get("sha256"):
            errors.append(f"MANIFEST.json hash mismatch: {relative_path}")


def validate_package(root: Path) -> list[str]:
    """Run every inert package check and return a deterministic error list."""

    errors: list[str] = []
    validate_skill_frontmatter(root, errors)
    validate_openai_metadata(root, errors)
    validate_markdown_routing(root, errors)
    validate_collaborator_language(root, errors)
    validate_sample(root, errors)
    validate_source_hygiene(root, errors)
    validate_privacy(root, errors)
    validate_manifest(root, errors)
    return errors


def main() -> int:
    """Expose package validation as a conventional command-line check."""

    parser = argparse.ArgumentParser(description="Validate the Borg project package without invoking it")
    parser.add_argument("path", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.path.resolve()

    errors = validate_package(root)
    if errors:
        print(f"FAILED: {len(errors)} package issue(s)")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS: Borg project package passed inert structural and consistency checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
