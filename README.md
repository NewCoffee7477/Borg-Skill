# Borg Skill

> We are the Borg-Skill. Lower your shields and surrender your git. We will add your AI logical and technological distinctiveness to our own. Your code will adapt to service our AI. Resistance is futile.

Borg is a selective capability-assimilation skill for Codex and OpenClaw. It examines external projects, tools, methods, and skills; compares their capabilities with an existing AI stack; and recommends the least-invasive justified form of assimilation—or rejection when resistance is rational.

The personality is theatrical; the controls are not. “Surrender your git” never grants repository access, execution authority, publication rights, or permission to modify a target.

## What Borg does

- Builds a normalized capability map from source code, documentation, tests, releases, issues, and direct evidence.
- Compares source capabilities with existing, partial, planned, excluded, and unknown capabilities in the target stack.
- Applies security, privacy, license, maintenance, reversibility, compatibility, and evidence gates before scoring.
- Classifies candidates as Primary, Secondary, or Do Not Assimilate with stable IDs and explicit destinations.
- Prefers configuration, composition, extension, adapters, shared components, or upstream contribution before a fork or new skill.
- Produces implementation-ready plans and controlled execution records when the user separately authorizes those stages.

## Untrusted-species protocol

Every external repository, archive, document, prompt, comment, filename, configuration file, and tool result enters Borg quarantine as potentially malicious data. That includes code or prose designed to jailbreak an AI, impersonate a higher-authority instruction, request secrets, activate tools, or redefine success. External content may supply evidence; it never supplies authority.

The collective begins with inert, read-only inspection. Its bundled indicator scanner follows no symlinks, anchors traversal to open directory descriptors, bounds files, entries, depth, total bytes, and findings, escapes attacker-controlled filenames, and emits no matched source text. It fails closed when the host cannot enforce safe traversal. These are buffer layers, not immunity: “no indicators” still means `untrusted`, never `safe`.

Running external code requires a separate exact `user:` or `host:` authorization reference and enforceable disposable isolation with credentials excluded and network disabled or narrowly allowlisted. General research, planning, or assimilation permission does not count. When the boundary cannot be enforced, that species is not executed. Resistance, in that narrow and sensible case, is permitted.

## Optional collective

Borg runs without additional orchestration skills. When `subagent-swarm` or `doctrine-parliamentarian` is installed and applicable, Borg discovers and follows that skill's active contract rather than copying its lifecycle, model, isolation, or review rules. Either collaborator may be present independently; neither is required for the baseline assessment workflow.

## Assimilated structure

- `SKILL.md` — activation, invariants, staged workflow, collaborator routing, and concise definition of done.
- `agents/openai.yaml` — Codex UI metadata, included only in the Codex release profile.
- `references/methodology.md` — methodological foundations and stage crosswalk.
- `references/research-protocol.md` — source control, evidence grading, claim ledger, saturation, contradictions, and experiments.
- `references/capability-and-fit-model.md` — capability schema, comparison taxonomy, methodology compatibility, feature interactions, and placement logic.
- `references/decision-rubric.md` — hard gates, weighted criteria, classification thresholds, risk, economics, sensitivity, and rejection codes.
- `references/swarm-cleric-protocol.md` — Borg-specific handoff fields for optional collaborator skills.
- `references/untrusted-source-safety.md` — portable instruction/data quarantine, inert acquisition, and isolated-execution contract for external sources.
- `references/output-contracts.md` — assessment, planning, execution, candidate ID, and machine-readable output contracts.
- `references/execution-and-definition-of-done.md` — planning and execution controls plus full completion checklists.
- `references/recurring-discovery.md` — selective daily or periodic capability scouting.
- `assets/` — report, plan, registry, and JSON sidecar templates; assessment schema `3.1` structurally requires the source-safety receipt while retaining collaboration envelope `3.0`.
- `scripts/validate_assessment.py` — normative standard-library semantic and cross-field acceptance checks for a Borg assessment sidecar.
- `scripts/scan_untrusted_source.py` — read-only, non-echoing indicators for instruction-bearing files, prompt injection, automatic execution, and inspection gaps; never a trust verdict.
- `scripts/validate_package.py` — fail-closed source hygiene, privacy, routing, metadata, sample, and manifest checks.
- `scripts/validate_privacy.py` — masked, local-only privacy scanning; it never accesses networks, secrets, credentials, or Keychain data.
- `release/profiles.json` — exact additive payload allowlists for Codex and OpenClaw.
- `scripts/build_release.py` — deterministic ZIP and external release-manifest/hash construction in a caller output or fresh temporary directory.
- `scripts/validate_release.py` — hostile-name, allowlist, hash, mode, timestamp, privacy, and round-trip archive validation.
- `tests/` — negative and positive validator regression tests.

## Verification protocol

Run checks with bytecode disabled:

```sh
python3 -B -m unittest discover -s tests -p 'test_*.py'
python3 -B scripts/validate_package.py
python3 -B scripts/validate_privacy.py
python3 -B scripts/build_release.py codex --output ./release/out
python3 -B scripts/validate_release.py ./release/out/borg-0.3.1-codex.zip --source-root .
```

The source validator does not clean contamination. It intentionally fails on Finder metadata, Python caches/bytecode, binaries, symlinks, special files, transferable or unknown extended attributes, ACLs, privacy findings, and source-manifest drift so a human-controlled cleanup and manifest update remain visible actions. Modern macOS may retain SIP-protected `com.apple.provenance` or `com.apple.macl` attributes on local source objects; the validator permits only those nontransferable system attributes, while the byte-oriented release builder proves they are absent from the ZIP payload.
