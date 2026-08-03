# Output Contracts

## Contents

- Assessment and verdict headers
- Candidate and section contracts
- Target boundaries and stable IDs
- Planning and execution outputs
- Machine-readable sidecar and style

## 1. Assessment header

Every substantive assessment begins with:

- Assessment ID: `BORG-A-YYYYMMDD-###`.
- Date and freshness cutoff.
- Mode.
- Source identity and snapshot.
- Target or collective scope.
- Explicit exclusions.
- Research depth and coverage.
- Overall evidence confidence.
- Decision owner and execution authorization state.
- Source-safety trust state, instruction-boundary state, indicator-scan state/reason/evidence, inspection gaps, and dynamic-source execution receipt with its separate authorization reference.
- Collaboration envelope version; discovery state/check time/evidence; nullable contract source/version or hash/inspection time; applicability state/reason/authority reference; lifecycle/native status/execution mode/result state/accounting/blocker/evidence; consequence state/affected outputs/reason/authority reference; and adapter version for each optional collaborator.

## 2. Executive verdict

State in direct language:

- whether the source presents a strong, selective, narrow, uncertain, external-only, or no assimilation opportunity;
- the number of Primary, Secondary, and Do Not Assimilate findings;
- the most important destination or reason for rejection;
- the largest unresolved uncertainty.

Do not begin with a long project summary.

## 3. Research coverage

Summarize:

- evidence surfaces examined;
- versions and dates;
- direct tests or experiments performed;
- unavailable material;
- saturation status;
- limitations that reduce completeness.

## 4. Candidate record

Use this structure for every candidate:

### BORG-P001 — Normalized capability name

- **Source:** source feature and snapshot.
- **Outcome:** user or collective value.
- **Evidence:** grades, key citations, and confidence.
- **Novelty/overlap:** exact relationship to existing or planned capability.
- **Destination:** named target and assimilation form.
- **Why here:** boundary, ownership, and methodology fit.
- **Alternatives considered:** at least the strongest alternative and do-nothing case.
- **Dependencies/interactions:** required, excluded, or affected capabilities.
- **Quality effects:** material improvements and regressions.
- **Security/license/maintenance:** material implications.
- **Score:** value or range, classification threshold, and sensitivity.
- **Risks/unknowns:** residual risk and what would change the verdict.
- **Next action:** plan, prototype, acquire evidence, defer, use externally, or reject.

Use the same structure for Secondary and Do Not Assimilate findings, replacing “Why here” with the promotion test or rejection rationale as appropriate.

## 5. Required assessment sections

1. Assimilation verdict.
2. Scope and source snapshot.
3. Source capability map.
4. Primary candidates.
5. Secondary candidates.
6. Do Not Assimilate findings, grouped by reason when useful.
7. Destination map.
8. Methodology and architecture-fit summary.
9. Cross-feature dependencies and interactions.
10. Risks, contradictions, unknowns, and evidence limits.
11. Recommended next action.
12. Evidence or source notes.

## 6. Target-boundary behavior

In targeted mode:

- keep all main findings inside the named target;
- state the named target in the header and every destination recommendation;
- place any material out-of-target exception in one short section labeled `Exceptional placement warning`;
- do not perform a full collective scan unless the user requests it.

## 7. Candidate ID stability

- Never renumber existing candidates in a follow-up.
- Add new candidates with new IDs.
- Mark changed candidates as reaffirmed, upgraded, downgraded, superseded, rejected, implemented, or retired.
- Preserve a short decision history when reassessing.

## 8. Planning output

For each selected candidate include:

1. Candidate ID and approved destination.
2. Objective and measurable user outcome.
3. Scope and non-goals.
4. Functional and quality requirements.
5. Current-state and desired-state summary.
6. Alternatives and chosen architecture.
7. Interfaces, data flow, state, permissions, and dependencies.
8. Work breakdown with sequencing and parallel lanes.
9. Security, privacy, licensing, and governance controls.
10. Test strategy and acceptance criteria.
11. Migration, rollout, observability, rollback, and exit.
12. Documentation and registry updates.
13. Risks and open decisions.
14. Definition of done.

## 9. Execution output

Report:

- authorized scope;
- files, components, branches, packages, or systems changed;
- implementation decisions;
- tests run and exact outcomes;
- tests not run and why;
- security or quality checks;
- migration or rollout state;
- rollback instructions;
- residual risks;
- updated candidate status;
- links or paths to artifacts.

Never use “done,” “verified,” “safe,” or “production-ready” without stating the supporting checks.

## 10. Machine-readable sidecar

For complex or recurring work, produce a JSON sidecar conforming structurally to [assets/assessment-schema.json](../assets/assessment-schema.json). The schema is an interchange and editor preflight contract; passing it alone is not Borg semantic acceptance. It should include:

- assessment metadata;
- sources;
- required `source_safety` record with immutable `untrusted` state, instruction-boundary confirmation, bounded indicator-scan receipt, inspection gaps, and separately authorized dynamic-execution receipt;
- coverage;
- capabilities;
- candidates;
- risks;
- contradictions;
- collaboration envelope `3.0` with exactly one check for `subagent-swarm` and one for `doctrine-parliamentarian`;
- the exact normalized fields defined by assessment schema `3.1` and a nullable versioned `adapter` for each collaborator check;
- definition-of-done checks.

Validate with `scripts/validate_assessment.py`. That standard-library validator is normative for semantic and cross-field acceptance, including source quarantine, separate untrusted-source execution authority, containment, candidate identity, assimilation execution authority, exact collaborator coverage, adapter-native completion, swarm subtree accounting, doctrine-receipt supersession, and consequence authority. Assessment schema `3.1` remains within the clean v3 break: reject v2 collaboration objects and do not infer or migrate their meaning. A consumer may additionally run a Draft 2020-12 engine against the schema, but must not substitute that structural result for the normative validator.

Keep native collaborator status as a string. Mark lifecycle complete only after result state is terminal and a supported adapter recognizes success with accounting, evidence, and blocker checks passing. Let Borg continue without optional collaborators. Apply `scope-limited` or `blocked` only to named outputs with a nonempty independent user, host, legal, or safety authority reference.

## 11. Style

- Lead with decisions and consequences.
- Use neutral, outcome-oriented feature names.
- Separate fact from recommendation.
- Be explicit when evidence is incomplete.
- Avoid inflated novelty claims and false numerical precision.
- Keep rationale inspectable without exposing private chain-of-thought.
- Use tables for comparison when they improve clarity, not by default.
