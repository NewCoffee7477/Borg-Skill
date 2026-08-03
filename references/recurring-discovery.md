# Recurring Discovery

## 1. Purpose

Recurring Borg discovery is a capability-scouting process. It is not a generic technology-news feed. It finds new or materially changed capabilities that may warrant assimilation into the collective.

## 2. Inputs

Maintain:

- collective capability registry;
- known gaps and strategic priorities;
- watch domains and source classes;
- previously assessed sources and candidate IDs;
- rejected and intentionally excluded capability patterns;
- query packs and trusted-source lists;
- last-seen releases, commits, papers, and announcements;
- user-defined noise and exclusion rules.

## 3. Discovery stages

### D0 — Scope and collaborator applicability

At initial setup and whenever priorities change, define the scouting boundary, acceptable sources, privacy and safety limits, attention budget, and what must never trigger automatic action. Record a v3 check for each optional collaborator. Invoke `doctrine-parliamentarian` only when discovery is `present` and its inspected contract applies. Continue baseline discovery when it is `absent`; scope-limit or block only an output governed by an independent user, host, legal, or safety requirement.

### D1 — Parallel search

When `subagent-swarm` is installed and its inspected contract applies, use it to cover distinct domains, repositories, releases, research, and practitioner evidence. Do not add a Borg-specific usefulness threshold or lane count. When it is absent, search serially and keep applicability unknown unless another governing authority supplies a classification. Search for capability changes, not merely mentions.

### D2 — Identity and change verification

Confirm the source, version, date, and what actually changed. Reject reposts, rumors, cosmetic releases, and duplicate announcements.

### D3 — Fast capability normalization

Extract the new capability, outcome, mechanism, maturity, and likely collective relevance. Compare against known capabilities and prior Borg records.

### D4 — Triage

Classify discoveries:

- **Immediate assessment candidate:** credible novelty and material likely value.
- **Watch:** potentially relevant but immature, weakly evidenced, or dependent on future needs.
- **Change to prior decision:** new evidence, version, license, security, or target change that could alter an existing verdict.
- **Reviewed and dismissed:** duplicate, cosmetic, irrelevant, dominated, unsafe, or marketing-only.

### D5 — Deduplication and attention control

Do not resurface an item unless:

- a material capability changed;
- evidence quality improved;
- the target or collective changed;
- a prior blocker was removed;
- risk, license, maintenance, or availability changed materially.

Invalidate and refresh the relevant collaborator check when discovery state/check time, contract version or hash, host policy, adapter version, native-status semantics, consequence authority reference, or retained lifecycle evidence changes. Do not reuse a prior `not-applicable`, `complete`, `scope-limited`, or `blocked` outcome across such a change without reinspection.

### D6 — Output

Report only high-signal items with:

- source and dated change;
- normalized capability;
- why it may matter;
- likely destination or named target;
- novelty and evidence confidence;
- recommended action: full Borg assessment, watch, reassess, or dismiss.

## 4. Automation boundaries

Recurring discovery may search, read, compare, and prepare assessments. It must not install, fork, modify, purchase, subscribe, publish, or execute assimilation without explicit user authorization.

## 5. Discovery definition of done

- [ ] Search domains and time window are explicit.
- [ ] Source identity and dates are verified.
- [ ] Results are deduplicated against the seen registry.
- [ ] Capabilities are normalized rather than copied from announcements.
- [ ] Relevance is tied to a known gap, priority, or destination.
- [ ] Evidence and maturity are labeled.
- [ ] Marketing-only and cosmetic items are filtered.
- [ ] Prior assessments are updated when material facts changed.
- [ ] No automatic execution occurred.
- [ ] Both optional collaborator checks are current, and contract, adapter, lifecycle, and consequence changes triggered reinspection.
