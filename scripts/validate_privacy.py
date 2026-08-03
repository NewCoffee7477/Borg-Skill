#!/usr/bin/env python3
"""Fail-closed privacy scanning for Borg source and staged release files.

The scanner is deliberately local and inert: it reads ordinary file bytes and
non-secret process/account labels, but never contacts a network, credential
store, browser profile, or macOS Keychain.  Findings are masked so the tool can
be used in logs without repeating the sensitive value it detected.
"""

from __future__ import annotations

import argparse
import getpass
import os
import re
import socket
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

try:
    # ``pwd`` is Unix-only.  Borg's common runtime must still import and run on
    # Windows-hosted Codex/OpenClaw environments, so account-record discovery
    # is an optional enhancement rather than an import-time dependency.
    import pwd
except ImportError:  # pragma: no cover - exercised only on non-Unix hosts
    pwd = None


TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".py", ".txt", ".toml", ".ini", ".cfg"}
EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@(?:[\w-]+\.)+[A-Za-z]{2,}(?![\w.-])")
PHONE = re.compile(r"(?<!\d)(?:\+?1[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]\d{3}[ .-]\d{4}(?!\d)")
HOME_PATH = re.compile(r"(?i)(?:/Users|/home)/[A-Za-z0-9._-]+(?:/[^\s\"'<>]*)?|[A-Z]:\\Users\\[A-Za-z0-9._-]+(?:\\[^\s\"'<>]*)?")
PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")
CREDENTIAL = re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password|passwd)\s*[:=]\s*[\"']?([^\s\"',}{]{6,})")
PRIVATE_IPV4 = re.compile(r"(?<!\d)(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|127\.\d{1,3}\.\d{1,3}\.\d{1,3})(?!\d)")
LOCAL_HOST = re.compile(r"(?i)\b(?:localhost|[a-z0-9][a-z0-9-]*\.(?:local|lan|internal|home|test))\b")  # privacy-fixture
UUID = re.compile(r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b")
HASH_LINE = re.compile(r"(?i)\b(?:sha256|digest|hash)\b[^\n]{0,20}\b[0-9a-f]{64}\b")
PUBLIC_IDENTIFIER_CONTEXT = re.compile(r"(?i)(?:urn:|schema|identifier|example|fixture|synthetic)")


@dataclass(frozen=True, order=True)
class Finding:
    """A stable, safely printable privacy result."""

    path: str
    line: int
    rule: str
    masked: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.rule}: {self.masked}"


def mask(value: str) -> str:
    """Retain just enough shape to distinguish findings without disclosure."""

    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}…{value[-2:]} ({len(value)} chars)"


def _discover_tokens() -> set[str]:
    """Collect exact non-secret machine labels; short generic labels are unsafe.

    Environment values are intentionally limited to HOME/USER/LOGNAME/HOSTNAME.
    No broad environment dump occurs, and tokens under five characters are
    ignored because names such as ``root`` create excessive false positives.
    """

    values = {os.environ.get(key, "") for key in ("HOME", "USER", "LOGNAME", "HOSTNAME")}
    values.update({getpass.getuser(), socket.gethostname(), socket.getfqdn()})
    if pwd is not None and hasattr(os, "getuid"):
        try:
            record = pwd.getpwuid(os.getuid())
            values.update({record.pw_dir, record.pw_name, record.pw_gecos.split(",", 1)[0]})
        except (KeyError, OSError):
            pass
    return {value for value in values if len(value.strip()) >= 5}


def _portable_exception(rule: str, value: str, line: str, label: str) -> bool:
    """Apply narrow rule-specific exceptions rather than a global allowlist."""

    # Test source must contain synthetic examples to prove rejection.  Requiring
    # a same-line marker, and only honoring it in Python under tests/scripts,
    # avoids turning a whole fixture directory into an unscanned privacy hole.
    if label.endswith(".py") and (label.startswith("tests/") or label.startswith("scripts/")) and "privacy-fixture" in line:
        return True
    if rule == "home-path" and value == "/usr/bin/env":
        return True
    if rule == "uuid-event-id" and (value == "00000000-0000-4000-8000-000000000000" or PUBLIC_IDENTIFIER_CONTEXT.search(line)):
        return True
    if rule == "email" and value.lower().endswith(("@example.com", "@example.org", "@example.net")):
        return True
    if rule == "private-host" and PUBLIC_IDENTIFIER_CONTEXT.search(line):
        return True
    if rule == "credential-assignment" and PUBLIC_IDENTIFIER_CONTEXT.search(line):
        return True
    if rule == "content-hash" and HASH_LINE.search(line):
        return True
    return False


def scan_text(text: str, label: str, *, deny_tokens: Iterable[str] = (), machine_tokens: Iterable[str] | None = None) -> list[Finding]:
    """Scan decoded text with deterministic ordering and line-level evidence."""

    findings: list[Finding] = []
    tokens = set(_discover_tokens() if machine_tokens is None else machine_tokens)
    tokens.update(token for token in deny_tokens if token)
    rules = (("home-path", HOME_PATH), ("email", EMAIL), ("phone", PHONE),
             ("private-host", PRIVATE_IPV4), ("private-host", LOCAL_HOST),
             ("uuid-event-id", UUID), ("private-key", PRIVATE_KEY))
    for number, line in enumerate(text.splitlines(), 1):
        if line.strip() == "#!/usr/bin/env python3":
            continue
        for rule, pattern in rules:
            for match in pattern.finditer(line):
                value = match.group(0)
                if not _portable_exception(rule, value, line, label):
                    findings.append(Finding(label, number, rule, mask(value)))
        for match in CREDENTIAL.finditer(line):
            value = match.group(0)
            if not _portable_exception("credential-assignment", value, line, label):
                findings.append(Finding(label, number, "credential-assignment", mask(value)))
        for token in sorted(tokens, key=lambda item: (-len(item), item.casefold())):
            if token.casefold() in line.casefold():
                findings.append(Finding(label, number, "machine-token", mask(token)))
    return sorted(set(findings))


def _default_source_paths(root: Path) -> list[Path]:
    """Enumerate worktree content without reading root Git internals.

    A root ``.git`` directory is local transport state: it is never included in
    a commit or release, and it can eventually contain author identity, remote
    configuration, reflogs, and binary object data. Privacy validation belongs
    on the publishable worktree, while Git metadata is checked separately with
    Git-aware commands before commit or push.

    The pruning rule is deliberately limited to an actual, non-symlinked root
    directory. Nested ``.git`` directories and a root ``.git`` file remain in
    scope so an attacker cannot hide publishable content behind the exception.
    Ignored files also remain in scope because ``.gitignore`` is not a privacy
    boundary.
    """

    root = Path(root)
    git_directory = root / ".git"
    skip_root_git = git_directory.is_dir() and not git_directory.is_symlink()
    selected: list[Path] = []
    for directory, child_directories, filenames in os.walk(root, topdown=True, followlinks=False):
        current = Path(directory)
        if current == root and skip_root_git:
            child_directories[:] = [name for name in child_directories if name != ".git"]
        child_directories.sort()
        filenames.sort()
        selected.extend(current / name for name in child_directories)
        selected.extend(current / name for name in filenames)
    return sorted(selected, key=lambda item: item.relative_to(root).as_posix())


def scan_paths(root: Path, paths: Iterable[Path] | None = None, *, deny_tokens: Iterable[str] = ()) -> list[Finding]:
    """Scan source-owned text plus every supplied path/archive name.

    Callers may pass an exact staged payload. The default source walk includes
    manifest/configuration/development text and ignored worktree files but
    excludes only root Git transport internals. Binary contents are left to the
    package hygiene validator and only their names are privacy-scanned.
    """

    selected = sorted(paths, key=lambda p: str(p)) if paths is not None else _default_source_paths(root)
    findings: list[Finding] = []
    machine = _discover_tokens()
    for path in selected:
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            relative = path.name
        findings.extend(scan_text(relative, relative, deny_tokens=deny_tokens, machine_tokens=machine))
        if path.is_file():
            # Source hygiene separately forbids opaque binaries.  Reading every
            # regular file here closes gaps for extensionless metadata such as
            # ``.gitignore`` and future text formats not yet in a suffix list.
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                findings.append(Finding(relative, 0, "unreadable-text", mask(type(exc).__name__)))
            else:
                findings.extend(scan_text(text, relative, deny_tokens=deny_tokens, machine_tokens=machine))
    return sorted(set(findings))


def main() -> int:
    """Run the scanner without mutating files or revealing matched values."""

    parser = argparse.ArgumentParser(description="Scan Borg source or a staged payload for private data")
    parser.add_argument("path", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--deny-token", action="append", default=[], help="additional exact token to reject (masked in output)")
    args = parser.parse_args()
    root = args.path.resolve()
    findings = scan_paths(root, deny_tokens=args.deny_token)
    if findings:
        print(f"FAILED: {len(findings)} privacy finding(s)")
        for finding in findings:
            print(f"- {finding.render()}")
        return 1
    print("PASS: no privacy findings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
