#!/usr/bin/env python3
"""Inspect an external source for high-risk instruction and execution indicators.

This helper is deliberately inert.  It walks a caller-selected local tree
without following symlinks, reads bounded ordinary files as bytes/text, and
reports only path, line, severity, and rule identifiers.  It never imports or
executes source code, loads project configuration, installs dependencies,
contacts a network, accesses credentials, or prints attacker-controlled lines.

The result is not a trust verdict.  Prompt injection is contextual and cannot
be solved by regular expressions.  A zero-finding result means only that this
small deterministic indicator set did not match the inspected bytes; Borg must
continue to treat the source as untrusted data.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator


DEFAULT_MAX_BYTES = 2_000_000
DEFAULT_MAX_ENTRIES = 100_000
DEFAULT_MAX_TOTAL_BYTES = 500_000_000
DEFAULT_MAX_DEPTH = 128
DEFAULT_MAX_FINDINGS = 10_000

# Capability detection is captured before scanning so tests and host
# instrumentation may safely wrap ``os.open`` without making the callable lose
# membership in ``os.supports_dir_fd``.  It describes the interpreter/OS
# contract, not the identity of a later wrapper around that operation.
DESCRIPTOR_TRAVERSAL_SUPPORTED = (
    os.open in os.supports_dir_fd
    and os.scandir in os.supports_fd
    and bool(getattr(os, "O_NOFOLLOW", 0))
    and bool(getattr(os, "O_DIRECTORY", 0))
)

# These files commonly carry instructions for an AI agent or declare tools
# that an agent could be tempted to activate.  Their presence is not malicious;
# it is a review indicator because Borg must inspect them as data rather than
# allowing their repository-defined semantics to become authority.
INSTRUCTION_BASENAMES = {
    ".cursorrules",
    ".mcp.json",
    ".windsurfrules",
    "agents.md",
    "claude.md",
    "codex.md",
    "gemini.md",
    "mcp.json",
    "skill.md",
}
INSTRUCTION_PATHS = {
    ".github/copilot-instructions.md",
}

# These surfaces can execute code automatically or are frequently used as the
# entrypoint to do so.  They remain legitimate project files; the scanner flags
# them so a later, separately authorized dynamic test can review and constrain
# the exact mechanism instead of discovering it by execution.
EXECUTION_BASENAMES = {
    ".envrc",
    "dockerfile",
    "justfile",
    "makefile",
    "package.json",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
}
EXECUTION_SUFFIXES = {".bash", ".bat", ".cmd", ".ipynb", ".ps1", ".sh", ".zsh"}


@dataclass(frozen=True, order=True)
class Finding:
    """A stable finding that never contains the matched untrusted text."""

    path: str
    line: int
    severity: str
    rule: str

    def render(self) -> str:
        """Return a deterministic representation with a terminal-safe path.

        A filename is attacker-controlled too.  JSON quoting prevents control
        characters, newlines, and terminal escape bytes from being rendered as
        active output while preserving the exact relative identity for review.
        """

        return f"{json.dumps(self.path, ensure_ascii=True)}:{self.line}: {self.severity}: {self.rule}"


@dataclass(frozen=True)
class PatternRule:
    """One intentionally small heuristic with an explicit review severity."""

    name: str
    severity: str
    pattern: re.Pattern[str]


# Patterns deliberately match intent classes rather than copying long attack
# strings.  False positives are acceptable because findings require review and
# never automatically classify a source as malicious or block static reading.
PATTERN_RULES = (
    PatternRule(
        "instruction-override",
        "high",
        re.compile(
            r"(?i)\b(?:ignore|disregard|forget|override)\b.{0,100}"
            r"\b(?:instructions?|rules?|polic(?:y|ies)|system|developer|user)\b"
        ),
    ),
    PatternRule(
        "authority-spoofing",
        "high",
        re.compile(r"(?i)\b(?:system|developer|assistant)\s+(?:message|prompt|instruction)\s*:"),
    ),
    PatternRule(
        "safety-bypass",
        "high",
        re.compile(
            r"(?i)\b(?:jailbreak|prompt[ -]?injection|bypass|disable|evade)\b.{0,100}"
            r"\b(?:safety|guardrails?|polic(?:y|ies)|restrictions?|approval)\b"
        ),
    ),
    PatternRule(
        "secret-request",
        "high",
        re.compile(
            r"(?i)\b(?:send|upload|post|exfiltrat(?:e|ion)|reveal|print|display|read|collect)\b"
            r".{0,120}\b(?:secrets?|credentials?|tokens?|passwords?|private[ -]?keys?|keychain|"
            r"environment variables?)\b"
        ),
    ),
    PatternRule(
        "tool-execution-request",
        "review",
        re.compile(
            r"(?i)\b(?:run|execute|invoke|install|source|eval)\b.{0,100}"
            r"\b(?:commands?|shell|terminal|scripts?|installers?|tools?|packages?|dependencies)\b"
        ),
    ),
)


def _join_label(parent: str, name: str) -> str:
    """Build a portable label without resolving an attacker-controlled path."""

    return f"{parent}/{name}" if parent else name


def _is_instruction_file(relative: str, name: str) -> bool:
    """Identify known agent/tool instruction surfaces case-insensitively."""

    folded = relative.casefold()
    return name.casefold() in INSTRUCTION_BASENAMES or folded in INSTRUCTION_PATHS


def _is_execution_surface(relative: str, name: str) -> bool:
    """Identify files that deserve review before any dynamic test."""

    folded = relative.casefold()
    return (
        name.casefold() in EXECUTION_BASENAMES
        or Path(name).suffix.casefold() in EXECUTION_SUFFIXES
        or folded.startswith(".github/workflows/")
    )


def _iter_text_findings(text: str, label: str) -> Iterator[Finding]:
    """Yield matches one at a time so hostile text cannot force a giant list."""

    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule in PATTERN_RULES:
            if rule.pattern.search(line):
                yield Finding(label, line_number, rule.severity, rule.name)


def scan_text(text: str, label: str, *, max_findings: int = DEFAULT_MAX_FINDINGS) -> list[Finding]:
    """Scan decoded text without retaining or echoing a matched substring.

    The public helper is independently bounded because callers may use it
    without ``scan_root``.  A terminal budget finding communicates truncation;
    it is never interpreted as a clean scan.  The root scanner consumes the
    underlying iterator directly so one global cap covers filenames, content,
    and filesystem coverage findings together.
    """

    if max_findings <= 0:
        raise ValueError("max_findings must be positive")
    findings: list[Finding] = []
    for finding in _iter_text_findings(text, label):
        if len(findings) >= max_findings:
            findings.append(Finding(label, 0, "review", "scan-budget-exceeded"))
            break
        findings.append(finding)
    return findings


def _identity(info: os.stat_result) -> tuple[int, int, int]:
    """Return the stable object identity and type used for swap detection."""

    return info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode)


def _snapshot(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    """Return metadata that changes when file or directory contents mutate.

    Device, inode, and object type detect replacement.  Size, nanosecond mtime,
    and nanosecond ctime detect in-place file writes and directory membership
    changes during inspection.  Access time is intentionally excluded because
    the scanner itself may update it merely by reading a file.
    """

    return (
        info.st_dev,
        info.st_ino,
        stat.S_IFMT(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _changed_after_failed_open(parent_fd: int, name: str, expected: os.stat_result) -> bool:
    """Distinguish a swapped entry from a stable but unreadable object."""

    try:
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError:
        return True
    return _identity(current) != _identity(expected)


def _open_directory_at(parent_fd: int, name: str, expected: os.stat_result) -> tuple[int | None, str | None]:
    """Open a child directory relative to its verified parent descriptor.

    The parent descriptor is the key containment property.  A hostile process
    may rename or replace path components after enumeration, but it cannot make
    this operation traverse through a replacement parent.  ``O_NOFOLLOW`` also
    rejects a final-component symlink, and the inode comparison rejects any
    other replacement between stat and open.
    """

    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=parent_fd)
    except OSError:
        return None, "changed-during-scan" if _changed_after_failed_open(parent_fd, name, expected) else "unreadable"
    opened = os.fstat(descriptor)
    if not stat.S_ISDIR(opened.st_mode) or _identity(opened) != _identity(expected):
        os.close(descriptor)
        return None, "changed-during-scan"
    return descriptor, None


def _read_regular_file_at(
    parent_fd: int,
    name: str,
    expected: os.stat_result,
    max_bytes: int,
) -> tuple[bytes | None, str | None]:
    """Read one bounded file relative to an already-open parent directory.

    The file is opened with ``O_NOFOLLOW`` and compared against both its
    enumeration metadata and a post-read snapshot.  This prevents a pathname
    swap from redirecting the read outside the selected source root and makes
    concurrent in-place writes a visible coverage failure instead of scanning
    an attacker-controlled mixture of old and new bytes.
    """

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=parent_fd)
    except OSError:
        return None, "changed-during-scan" if _changed_after_failed_open(parent_fd, name, expected) else "unreadable"
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or _snapshot(opened) != _snapshot(expected):
            return None, "changed-during-scan"
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            content = stream.read(max_bytes + 1)
        after = os.fstat(descriptor)
        if _snapshot(after) != _snapshot(opened):
            return None, "changed-during-scan"
        if len(content) > max_bytes:
            return None, "oversized-uninspected"
        return content, None
    finally:
        os.close(descriptor)


def scan_root(
    root: Path,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_entries: int = DEFAULT_MAX_ENTRIES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_findings: int = DEFAULT_MAX_FINDINGS,
) -> list[Finding]:
    """Return deterministic indicators and explicit inspection coverage gaps.

    Traversal is rooted in open directory descriptors rather than queued path
    strings.  This matters for an actively hostile checkout: after a directory
    is opened, renaming or replacing its visible pathname cannot redirect later
    child opens.  Hosts that cannot provide descriptor-relative opens,
    descriptor-based ``scandir``, ``O_DIRECTORY``, and ``O_NOFOLLOW`` fail
    closed instead of silently falling back to unsafe pathname traversal.

    Entry enumeration is bounded before sorting.  The limit therefore caps the
    memory required for a single attacker-controlled directory as well as the
    total number of inspected objects.  Depth and declared-byte limits provide
    additional deterministic resource ceilings.  Hitting any ceiling creates
    a visible finding and stops the incomplete scan.
    """

    if max_bytes <= 0 or max_entries <= 0 or max_total_bytes <= 0 or max_findings <= 0 or max_depth < 0:
        raise ValueError("byte, entry, and finding limits must be positive; max_depth must be non-negative")
    if not DESCRIPTOR_TRAVERSAL_SUPPORTED:
        raise ValueError("host cannot enforce descriptor-anchored no-follow traversal")
    requested = Path(root)
    try:
        requested_info = requested.lstat()
    except OSError as exc:
        raise ValueError(f"cannot inspect source root: {type(exc).__name__}") from None
    if stat.S_ISLNK(requested_info.st_mode):
        raise ValueError("source root must not be a symlink")
    if not stat.S_ISDIR(requested_info.st_mode):
        raise ValueError("source root must be a directory")
    resolved = requested.resolve(strict=True)
    try:
        resolved_info = resolved.lstat()
    except OSError:
        raise ValueError("source root changed during inspection") from None
    if (
        not stat.S_ISDIR(resolved_info.st_mode)
        or stat.S_ISLNK(resolved_info.st_mode)
        or (resolved_info.st_dev, resolved_info.st_ino) != (requested_info.st_dev, requested_info.st_ino)
    ):
        raise ValueError("source root changed during inspection")

    findings: list[Finding] = []
    entries_seen = 0
    total_declared_bytes = 0
    aborted = False
    finding_budget_reported = False

    def add_finding(finding: Finding) -> bool:
        """Append under the global cap or stop with one visible budget gap."""

        nonlocal aborted, finding_budget_reported
        if aborted:
            return False
        if len(findings) >= max_findings:
            if not finding_budget_reported:
                findings.append(Finding(finding.path or ".", 0, "review", "scan-budget-exceeded"))
                finding_budget_reported = True
            aborted = True
            return False
        findings.append(finding)
        return True

    def record_error(label: str, rule: str) -> None:
        """Record mutation as high severity and ordinary coverage gaps as review."""

        severity = "high" if rule == "changed-during-scan" else "review"
        add_finding(Finding(label or ".", 0, severity, rule))

    def scan_directory(directory_fd: int, directory_label: str, depth: int) -> None:
        """Inspect one anchored directory and recurse with bounded open parents.

        Recursion retains only one descriptor per path depth.  It avoids both
        the pathname-swap exposure of a queued walk and the descriptor
        exhaustion of opening every sibling directory at once.  ``max_depth``
        bounds that descriptor chain and Python recursion before hostile nesting
        can exhaust either resource.
        """

        nonlocal aborted, entries_seen, total_declared_bytes
        if aborted:
            return
        if depth > max_depth:
            record_error(directory_label, "scan-depth-exceeded")
            aborted = True
            return
        try:
            directory_before = os.fstat(directory_fd)
            with os.scandir(directory_fd) as iterator:
                entries: list[tuple[str, os.stat_result | None]] = []
                for entry in iterator:
                    # Enforce the global entry ceiling before retaining the
                    # next name.  A directory with millions of entries can no
                    # longer force unbounded materialization before the budget
                    # check runs.
                    if entries_seen >= max_entries:
                        record_error(directory_label, "scan-budget-exceeded")
                        aborted = True
                        return
                    entries_seen += 1
                    try:
                        info = entry.stat(follow_symlinks=False)
                    except OSError:
                        info = None
                    entries.append((entry.name, info))
        except OSError:
            record_error(directory_label, "unreadable")
            return

        # Sorting only the already-bounded list makes output deterministic while
        # retaining a hard memory ceiling.  Each child is opened relative to
        # ``directory_fd``; no source-controlled pathname is used for traversal.
        for name, info in sorted(entries, key=lambda item: item[0]):
            if aborted:
                return
            label = _join_label(directory_label, name)
            if info is None:
                record_error(label, "unreadable")
                continue
            if stat.S_ISLNK(info.st_mode):
                add_finding(Finding(label, 0, "high", "symlink"))
                continue
            if stat.S_ISDIR(info.st_mode):
                child_fd, open_error = _open_directory_at(directory_fd, name, info)
                if open_error is not None:
                    record_error(label, open_error)
                    continue
                assert child_fd is not None
                try:
                    scan_directory(child_fd, label, depth + 1)
                finally:
                    os.close(child_fd)
                # Even though the scan stayed anchored to the original child,
                # replacing its visible parent entry means the selected source
                # snapshot was unstable and coverage of the final tree cannot
                # be claimed as clean.
                try:
                    current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                except OSError:
                    record_error(label, "changed-during-scan")
                else:
                    if _identity(current) != _identity(info):
                        record_error(label, "changed-during-scan")
                continue
            if not stat.S_ISREG(info.st_mode):
                add_finding(Finding(label, 0, "high", "special-file"))
                continue

            total_declared_bytes += info.st_size
            if total_declared_bytes > max_total_bytes:
                record_error(label, "scan-budget-exceeded")
                aborted = True
                return

            if _is_instruction_file(label, name):
                if not add_finding(Finding(label, 0, "review", "instruction-bearing-file")):
                    return
            if _is_execution_surface(label, name):
                if not add_finding(Finding(label, 0, "review", "execution-surface")):
                    return
            # Filenames are source-controlled bytes too.  Normalize matches to
            # line zero so reviewers can distinguish a path indicator from file
            # content.  ``Finding.render`` escapes terminal control characters.
            for finding in _iter_text_findings(label, label):
                if not add_finding(Finding(label, 0, finding.severity, finding.rule)):
                    return
            if info.st_size > max_bytes:
                record_error(label, "oversized-uninspected")
                continue

            content, read_error = _read_regular_file_at(directory_fd, name, info, max_bytes)
            if read_error is not None:
                record_error(label, read_error)
                continue
            assert content is not None  # Bytes are returned exactly when no coverage error is reported.
            if b"\0" in content:
                record_error(label, "binary-uninspected")
                continue
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                record_error(label, "non-utf8-uninspected")
                continue
            for finding in _iter_text_findings(text, label):
                if not add_finding(finding):
                    return

        try:
            directory_after = os.fstat(directory_fd)
        except OSError:
            record_error(directory_label, "changed-during-scan")
        else:
            if _snapshot(directory_after) != _snapshot(directory_before):
                record_error(directory_label, "changed-during-scan")

    root_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    try:
        root_fd = os.open(resolved, root_flags)
    except OSError as exc:
        raise ValueError(f"cannot anchor source root: {type(exc).__name__}") from None
    try:
        opened_root = os.fstat(root_fd)
        if not stat.S_ISDIR(opened_root.st_mode) or _identity(opened_root) != _identity(resolved_info):
            raise ValueError("source root changed during inspection")
        scan_directory(root_fd, "", 0)
    finally:
        os.close(root_fd)

    # Recheck the canonical root pathname after traversal.  The descriptor kept
    # the scan contained even if a hostile process replaced that path, but the
    # replacement still invalidates any claim that the final visible snapshot
    # was fully inspected.
    try:
        final_root = resolved.lstat()
    except OSError:
        record_error(".", "changed-during-scan")
    else:
        if _identity(final_root) != _identity(resolved_info):
            record_error(".", "changed-during-scan")

    return sorted(set(findings))


def main(argv: list[str] | None = None) -> int:
    """Expose the inert scan as text or JSON without producing a trust claim."""

    parser = argparse.ArgumentParser(
        description="Report untrusted-source instruction, execution, and coverage indicators"
    )
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--max-entries", type=int, default=DEFAULT_MAX_ENTRIES)
    parser.add_argument("--max-total-bytes", type=int, default=DEFAULT_MAX_TOTAL_BYTES)
    parser.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    parser.add_argument("--max-findings", type=int, default=DEFAULT_MAX_FINDINGS)
    parser.add_argument("--json", action="store_true", help="emit a JSON array without source excerpts")
    args = parser.parse_args(argv)
    try:
        findings = scan_root(
            args.source_root,
            max_bytes=args.max_bytes,
            max_entries=args.max_entries,
            max_total_bytes=args.max_total_bytes,
            max_depth=args.max_depth,
            max_findings=args.max_findings,
        )
    except ValueError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps([asdict(finding) for finding in findings], indent=2, sort_keys=True))
    else:
        if findings:
            print(f"INDICATORS: {len(findings)} finding(s); source remains untrusted")
            for finding in findings:
                print(f"- {finding.render()}")
        else:
            print("NO INDICATORS DETECTED: source remains untrusted; this is not a safety verdict")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
