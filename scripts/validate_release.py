#!/usr/bin/env python3
"""Validate a Borg release archive, sidecars, and round-trip extraction.

Validation treats both ZIP names and external metadata as hostile input.  It
does not use ``extractall``: every member is checked first, then written under a
fresh temporary root and compared byte-for-byte with the declared external
file ledger.  When source is supplied, that ledger is also anchored to the
actual allowlisted source bytes rather than trusted as self-authenticating.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from build_release import FIXED_ZIP_TIME, RELEASE_MANIFEST_SCHEMA, _safe_relative, common_core_digest, load_profiles, payload_paths
from validate_privacy import scan_paths


SHA256 = re.compile(r"^[0-9a-f]{64}$")
NORMALIZED_MODE = re.compile(r"^0[0-7]{3}$")


def validate_release(archive: Path, manifest_path: Path | None = None, checksum_path: Path | None = None, *, source_root: Path | None = None) -> list[str]:
    """Return all deterministic archive failures without modifying the source."""

    errors: list[str] = []
    manifest_path = manifest_path or archive.with_suffix(".zip.manifest.json")
    checksum_path = checksum_path or archive.with_suffix(".zip.sha256")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid release manifest: {exc}"]
    required = {"schema", "package", "version", "profile", "runtime_acceptance", "common_core_sha256", "files"}
    if not isinstance(manifest, dict) or set(manifest) != required:
        errors.append("release manifest has invalid fields")
        return errors
    if manifest.get("schema") != RELEASE_MANIFEST_SCHEMA or manifest.get("package") != "borg":
        errors.append("release manifest has invalid schema/package")
    if not isinstance(manifest.get("version"), str) or not manifest["version"]:
        errors.append("release manifest version must be a non-empty string")
    if not isinstance(manifest.get("profile"), str) or not manifest["profile"]:
        errors.append("release manifest profile must be a non-empty string")
    if not isinstance(manifest.get("common_core_sha256"), str) or not SHA256.fullmatch(manifest["common_core_sha256"]):
        errors.append("release manifest common-core digest is invalid")
    if manifest.get("runtime_acceptance") != "not-performed":
        errors.append("release manifest must not claim runtime acceptance")
    try:
        checksum_fields = checksum_path.read_text(encoding="ascii").strip().split()
        actual_archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
        if checksum_fields != [actual_archive_hash, archive.name]:
            errors.append("archive checksum sidecar mismatch")
    except OSError as exc:
        errors.append(f"cannot read archive/checksum: {exc}")
        return errors

    ledger: dict[str, dict] = {}
    files = manifest.get("files")
    if not isinstance(files, list):
        return errors + ["release manifest files must be an array"]
    for index, entry in enumerate(files):
        if not isinstance(entry, dict) or set(entry) != {"path", "bytes", "sha256", "mode"}:
            errors.append(f"release manifest files[{index}] has invalid fields")
            continue
        try:
            name = _safe_relative(entry["path"]).as_posix()
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"release manifest files[{index}] has unsafe path: {exc}")
            continue
        if isinstance(entry.get("bytes"), bool) or not isinstance(entry.get("bytes"), int) or entry["bytes"] < 0:
            errors.append(f"release manifest files[{index}] has invalid byte count")
            continue
        if not isinstance(entry.get("sha256"), str) or not SHA256.fullmatch(entry["sha256"]):
            errors.append(f"release manifest files[{index}] has invalid SHA-256")
            continue
        if not isinstance(entry.get("mode"), str) or not NORMALIZED_MODE.fullmatch(entry["mode"]):
            errors.append(f"release manifest files[{index}] has invalid mode")
            continue
        expected_mode = "0755" if name.startswith("scripts/") else "0644"
        if entry["mode"] != expected_mode:
            errors.append(
                f"release manifest files[{index}] mode is not normalized for {name}: "
                f"expected {expected_mode}"
            )
        if name in ledger:
            errors.append(f"release manifest duplicates {name}")
        ledger[name] = entry
    folded: dict[str, str] = {}
    for name in ledger:
        prior = folded.setdefault(name.casefold(), name)
        if prior != name:
            errors.append(f"case-fold path collision: {prior} and {name}")

    if source_root is not None:
        try:
            config = load_profiles(source_root)
            expected = payload_paths(source_root, manifest.get("profile", ""), config)
            if manifest.get("version") != config["version"]:
                errors.append("release version does not match profiles.json")
            if sorted(ledger) != expected:
                errors.append("release manifest does not match exact profile allowlist")
            if manifest.get("common_core_sha256") != common_core_digest(source_root, config):
                errors.append("release common-core digest does not match source")
            # The common-core digest proves that profile families share one
            # common payload, but it does not cover a host overlay by itself.
            # Bind every ledger record to source bytes so a rewritten overlay,
            # manifest, and checksum cannot validate merely through internal
            # consistency when authoritative source is available.
            for name, entry in ledger.items():
                source_path = source_root / name
                try:
                    source_bytes = source_path.read_bytes()
                except OSError as exc:
                    errors.append(f"cannot read allowlisted source file {name}: {exc}")
                    continue
                expected_mode = "0755" if name.startswith("scripts/") else "0644"
                if (
                    entry["bytes"] != len(source_bytes)
                    or entry["sha256"] != hashlib.sha256(source_bytes).hexdigest()
                    or entry["mode"] != expected_mode
                ):
                    errors.append(f"release ledger does not match source bytes/mode: {name}")
        except ValueError as exc:
            errors.append(str(exc))

    try:
        bundle = zipfile.ZipFile(archive)
    except (OSError, zipfile.BadZipFile) as exc:
        return errors + [f"invalid ZIP archive: {exc}"]
    with bundle, tempfile.TemporaryDirectory(prefix="borg-roundtrip-") as temporary:
        destination = Path(temporary)
        names: list[str] = []
        expected_directories = sorted({parent.as_posix() + "/" for name in ledger for parent in PurePosixPath(name).parents if parent != PurePosixPath(".")})
        observed_directories: list[str] = []
        for info in bundle.infolist():
            try:
                # Directory members conventionally carry a trailing slash;
                # validate the underlying relative path, then restore it for
                # exact comparison with the derived directory allowlist.
                raw_name = info.filename[:-1] if info.is_dir() and info.filename.endswith("/") else info.filename
                name = _safe_relative(raw_name).as_posix() + ("/" if info.is_dir() else "")
            except ValueError as exc:
                errors.append(str(exc))
                continue
            names.append(name)
            if info.is_dir():
                observed_directories.append(info.filename)
                if info.filename not in expected_directories:
                    errors.append(f"ZIP contains unlisted directory: {info.filename}")
                if ((info.external_attr >> 16) & 0o7777) != 0o755:
                    errors.append(f"ZIP directory mode mismatch: {info.filename}")
                if info.date_time != FIXED_ZIP_TIME:
                    errors.append(f"ZIP timestamp is not normalized: {info.filename}")
                directory_target = destination.joinpath(*PurePosixPath(name).parts)
                directory_target.mkdir(parents=True, exist_ok=True)
                directory_target.chmod(0o755)
                continue
            # Membership is an independent allowlist fact.  Report an
            # unlisted file before evaluating its metadata so an attacker
            # cannot obscure payload injection merely by choosing malformed
            # or platform-default ZIP attributes for the injected member.
            entry = ledger.get(name)
            if entry is None:
                errors.append(f"ZIP contains unlisted file: {name}")
            if stat.S_IFMT(info.external_attr >> 16) != stat.S_IFREG:
                errors.append(f"ZIP member is not a regular file: {name}")
                continue
            if info.date_time != FIXED_ZIP_TIME:
                errors.append(f"ZIP timestamp is not normalized: {name}")
            if entry is None:
                continue
            mode = (info.external_attr >> 16) & 0o7777
            if mode != int(entry["mode"], 8):
                errors.append(f"ZIP mode mismatch: {name}")
            content = bundle.read(info)
            if len(content) != entry["bytes"] or hashlib.sha256(content).hexdigest() != entry["sha256"]:
                errors.append(f"ZIP bytes/hash mismatch: {name}")
            target = destination.joinpath(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            target.write_bytes(content)
            os_mode = int(entry["mode"], 8)
            target.chmod(os_mode)
        if len(names) != len(set(names)):
            errors.append("ZIP contains duplicate member names")
        file_names = [name for name in names if not name.endswith("/")]
        if sorted(file_names) != sorted(ledger):
            errors.append("ZIP members do not exactly match release manifest")
        if sorted(observed_directories) != expected_directories:
            errors.append("ZIP directories do not exactly match derived payload directories")
        folded_names: dict[str, str] = {}
        for name in names:
            prior = folded_names.setdefault(name.casefold(), name)
            if prior != name:
                errors.append(f"ZIP case-fold path collision: {prior} and {name}")
        for finding in scan_paths(destination):
            errors.append(f"privacy: {finding.render()}")
    return sorted(set(errors))


def main() -> int:
    """Expose archive validation as an inert command-line gate."""

    parser = argparse.ArgumentParser(description="Validate a deterministic Borg release archive")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args()
    errors = validate_release(args.archive.resolve(), source_root=args.source_root.resolve() if args.source_root else None)
    if errors:
        print(f"FAILED: {len(errors)} release issue(s)")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: deterministic release archive validated; runtime acceptance not performed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
