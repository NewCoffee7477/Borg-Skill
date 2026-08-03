# Optional Collaborator Protocol

Treat `subagent-swarm` and `doctrine-parliamentarian` as optional collaborators. Keep Borg's baseline assessment usable when neither, either, or both are installed. Never treat absence as proof that an installed contract classified the task as not applicable.

## Inspect and classify

For each known collaborator, perform exactly one check:

1. Record discovery as `present`, `absent`, or `unknown`, with `checked_at` and evidence references.
2. If present, inspect the active entrypoint and record its source, `version_or_hash`, and inspection time. Otherwise set `contract` to null.
3. Normalize the inspected contract's outcome as `required`, `eligible`, `not-applicable`, or `unknown`, and record a concrete reason and nullable authority reference.
4. Record lifecycle state, native status, execution mode, result state, whole-lifecycle accounting, blocker, and evidence separately. Use lifecycle states `not-started`, `running`, `complete`, `degraded`, `blocked`, `unavailable`, or `failed`, and result states `none`, `partial`, or `terminal`.
5. Record the consequence separately from applicability and lifecycle.
6. Attach a supported native adapter only when native evidence exists.

When discovery is absent, require contract null and applicability `unknown`. Do not use separate authority to relabel absence as not applicable.

## Consequences

Use consequence state `none` by default, with empty affected outputs and null reason and authority reference. Borg continues its baseline work after an optional collaborator is absent, unavailable, or incomplete.

Use `scope-limited` or `blocked` only when an independently governing user, host, legal, or safety requirement requires that state. Cite that requirement with a nonempty `authority_ref`, explain it in `reason`, and list only the affected outputs. A collaborator's own absence, error, or unfamiliar native status is not an independent authority.

Do not convert an unsatisfied optional review into a universal stop. Narrow or stop the affected output only when the separately governing requirement says to do so.

## Lifecycle completion

Mark lifecycle `complete` only when all of these are true:

- the native adapter version is supported;
- native status is a terminal-success value recognized by that adapter version;
- `result_state` is `terminal`;
- the entire started lifecycle and descendants were accounted;
- lifecycle and adapter evidence are retained; and
- blocker is null.

Keep native status as the exact string returned by the installed skill. Do not force it into a portable installed-skill enum. Record unfamiliar strings truthfully, set lifecycle to `degraded` unless native evidence establishes another non-complete state, and do not use them to satisfy a required consequence.

## Swarm handoff and adapter

When the inspected `subagent-swarm` contract applies, pass bounded, non-duplicative lanes containing the objective, source and target snapshots, scope, exclusions, permissions, context policy, evidence requirements, return contract, stop condition, lifecycle owner, and nested-delegation policy.

Use adapter `borg.subagent-swarm@1.0`. Preserve:

- `agent_path`, `parent_lane`, and `tier`;
- `subtree_accounted` for the entire delegated subtree; and
- terminal result evidence references.

Consume only returned and accounted results. Preserve conflicts and missing evidence. Borg owns normalization, synthesis, and the final verdict. If the installed contract permits a serial fallback, label that work serial and do not manufacture a swarm result or adapter.

## Doctrine handoff and adapter

When the inspected `doctrine-parliamentarian` contract applies, use one fresh-context, read-only Cleric lane and retain it across applicable phases. Pass the raw request, current artifact, evidence, authority mapping, uncertainties, boundaries, and requested decision. Do not pass the preferred verdict as evidence.

Use adapter `borg.doctrine-parliamentarian@1.0`. Preserve every receipt's `review_id`, `phase_id`, phase, exact native status, gate state, disposition, supersession target, source completeness, confidence, result collection, accounting, blocker, and evidence reference.

Keep only one `current` receipt for each review ID and phase. Preserve replaced receipts as `superseded`; point `superseded_by_phase_id` to a receipt with the same review ID. A current receipt must not point to a successor. Treat only a correlated, complete, received, accounted, blocker-free current `PASS` as satisfied. Do not turn malformed, stale, partial, mismatched, or unfamiliar native output into approval.

The Cleric advises. It does not supply source evidence, grant authority, execute action, or replace the user's decision.

## Merge and report

Before reporting:

1. Inventory every started lane and doctrine phase.
2. Collect actual terminal results rather than notifications.
3. Reconcile and deduplicate evidence while retaining contradictions.
4. Account for every lifecycle and descendant.
5. Emit the v3 collaboration envelope with exactly one check for each known collaborator.
6. Distinguish contract-verified, structurally prepared, runtime-verified, and unknown states.

Ask the user only when a missing answer is authoritative and user-specific, reasonable alternatives materially diverge, and proceeding would create unacceptable risk or waste.
