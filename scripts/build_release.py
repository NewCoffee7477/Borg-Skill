#!/usr/bin/env python3
"""Build deterministic, host-specific Borg archives from an exact allowlist.

Files are copied byte-for-byte into a caller-selected output directory (or a
fresh temporary directory), with normalized archive modes and timestamps so
equal inputs produce equal ZIP bytes on every supported host.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from validate_privacy import scan_paths


FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
PROFILE_SCHEMA = "borg-release-profiles-v1"
RELEASE_MANIFEST_SCHEMA = "borg-release-manifest-v1"


def _safe_relative(value: str) -> PurePosixPath:
    """Reject names ZIP readers could interpret outside the extraction root."""

    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value or path.as_posix() != value:
        raise ValueError(f"unsafe release path: {value!r}")
    return path


def load_profiles(root: Path) -> dict[str, Any]:
    """Load and minimally validate the versioned release-profile contract."""

    path = root / "release" / "profiles.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load {path}: {exc}") from None
    if not isinstance(data, dict) or set(data) != {"schema", "version", "common", "profiles"}:
        raise ValueError("profiles.json must contain exactly schema, version, common, and profiles")
    if data["schema"] != PROFILE_SCHEMA or not isinstance(data["version"], str):
        raise ValueError("profiles.json has an unsupported schema or version")
    if not isinstance(data["common"], list) or not isinstance(data["profiles"], dict):
        raise ValueError("profiles.json common/profiles have invalid types")
    return data


def payload_paths(root: Path, profile: str, config: dict[str, Any]) -> list[str]:
    """Resolve one profile strictly by additive common-plus-overlay selection."""

    if profile not in config["profiles"] or not isinstance(config["profiles"][profile], list):
        raise ValueError(f"unknown release profile: {profile}")
    values = config["common"] + config["profiles"][profile]
    if any(not isinstance(value, str) for value in values):
        raise ValueError("release profile paths must be strings")
    normalized = [_safe_relative(value).as_posix() for value in values]
    if len(set(normalized)) != len(normalized):
        raise ValueError("release profile contains duplicate paths")
    folded: dict[str, str] = {}
    for value in normalized:
        prior = folded.setdefault(value.casefold(), value)
        if prior != value:
            raise ValueError(f"case-fold path collision: {prior!r} and {value!r}")
    return sorted(normalized)


def inspect_payload_file(path: Path, root: Path) -> None:
    """Reject links, devices, sockets, and multiply-linked source surprises."""

    # Inspect every parent component as well as the leaf.  A regular leaf below
    # a symlinked directory would otherwise pass lstat while reading bytes from
    # outside the declared source root.
    relative = path.relative_to(root)
    cursor = root
    for component in relative.parts[:-1]:
        cursor = cursor / component
        parent_info = cursor.lstat()
        if not stat.S_ISDIR(parent_info.st_mode) or stat.S_ISLNK(parent_info.st_mode):
            raise ValueError(f"payload parent is not a real directory: {cursor.relative_to(root)}")
    try:
        info = path.lstat()
    except FileNotFoundError:
        raise ValueError(f"listed payload file is missing: {path.relative_to(root)}") from None
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"payload entry is not a regular file: {path.relative_to(root)}")
    if info.st_nlink != 1:
        raise ValueError(f"payload entry has unexpected hard links: {path.relative_to(root)}")


def common_core_digest(root: Path, config: dict[str, Any]) -> str:
    """Bind host releases to the same ordered common payload and bytes."""

    digest = hashlib.sha256()
    for relative in sorted(config["common"]):
        _safe_relative(relative)
        content = (root / relative).read_bytes()
        digest.update(relative.encode("utf-8") + b"\0" + hashlib.sha256(content).digest())
    return digest.hexdigest()


def build_release(root: Path, profile: str, output_dir: Path) -> tuple[Path, Path, Path]:
    """Create one ZIP plus external JSON manifest and checksum sidecars."""

    root = root.resolve()
    output_dir = output_dir.resolve()
    if output_dir == root or output_dir.is_relative_to(root):
        raise ValueError("release output must be outside the governed source tree")
    config = load_profiles(root)
    paths = payload_paths(root, profile, config)
    entries: list[dict[str, Any]] = []
    payload_files: list[Path] = []
    for relative in paths:
        source = root / relative
        inspect_payload_file(source, root)
        payload_files.append(source)
        content = source.read_bytes()
        mode = 0o755 if relative.startswith("scripts/") else 0o644
        entries.append({"path": relative, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(), "mode": f"{mode:04o}"})

    # Fail before creating an artifact when any allowlisted source byte or path
    # carries a declared privacy finding.  The release validator repeats this
    # check after extraction so neither construction nor round-trip validation
    # becomes a single point of trust.
    findings = scan_paths(root, payload_files)
    if findings:
        rendered = "; ".join(finding.render() for finding in findings)
        raise ValueError(f"release payload failed privacy validation: {rendered}")

    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"borg-{config['version']}-{profile}.zip"
    manifest_path = archive.with_suffix(".zip.manifest.json")
    checksum_path = archive.with_suffix(".zip.sha256")

    manifest = {
        "schema": RELEASE_MANIFEST_SCHEMA,
        "package": "borg",
        "version": config["version"],
        "profile": profile,
        "common_core_sha256": common_core_digest(root, config),
        "files": entries,
    }
    # ZIP metadata is created explicitly; source mtime, ownership, xattrs, and
    # ACLs are therefore never copied into the portable artifact.
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        directories = sorted({parent.as_posix() + "/" for entry in entries for parent in PurePosixPath(entry["path"]).parents if parent != PurePosixPath(".")})
        for directory in directories:
            info = zipfile.ZipInfo(directory, FIXED_ZIP_TIME)
            info.create_system = 3
            info.external_attr = ((stat.S_IFDIR | 0o755) & 0xFFFF) << 16
            info.compress_type = zipfile.ZIP_STORED
            bundle.writestr(info, b"")
        for entry in entries:
            relative = entry["path"]
            info = zipfile.ZipInfo(relative, FIXED_ZIP_TIME)
            info.create_system = 3
            info.external_attr = ((stat.S_IFREG | int(entry["mode"], 8)) & 0xFFFF) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, (root / relative).read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    checksum_path.write_text(f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n", encoding="ascii", newline="\n")
    return archive, manifest_path, checksum_path


def main() -> int:
    """Build locally and print artifact locations; perform no host action."""

    parser = argparse.ArgumentParser(description="Build an inert deterministic Borg release archive")
    parser.add_argument("profile", choices=("codex", "openclaw"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, help="caller-owned output directory; default is a new temporary directory")
    args = parser.parse_args()
    output = args.output.resolve() if args.output else Path(tempfile.mkdtemp(prefix="borg-release-"))
    try:
        products = build_release(args.root.resolve(), args.profile, output)
    except ValueError as exc:
        print(f"FAILED: {exc}")
        return 1
    for product in products:
        print(product)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
