# Capability and Fit Model

## Contents

- Capability records and atomicity
- Comparison and feature relationships
- Methodology profiles and compatibility
- Fit dimensions
- Placement logic

## 1. Capability record

Create one record per normalized capability:

| Field | Meaning |
|---|---|
| capability_id | Stable `CAP-###` identifier |
| source_name | Source's own feature or method name |
| normalized_name | Neutral outcome-oriented name |
| user_outcome | What becomes possible or materially better |
| observable_behavior | What a user or system can observe |
| mechanism | How the behavior is achieved |
| implementation | Relevant code, workflow, model, or service |
| preconditions | Required state, configuration, skills, or infrastructure |
| inputs_outputs | Data and interaction contract |
| permissions | Access and authority required |
| state_memory | Persistence, memory, and data ownership |
| dependencies | Required components and external services |
| quality_effects | Improvements and degradations by quality attribute |
| failure_model | Failure, recovery, fallback, and blast radius |
| lifecycle | Install, operate, monitor, update, migrate, remove |
| maturity | Prototype, emerging, operational, mature, declining, unknown |
| interactions | Requires, excludes, conflicts, modifies, or amplifies other features |
| evidence | Claim IDs and evidence grades |
| confidence | High, medium, or low |

## 2. Atomicity rule

A capability is too broad when its parts could receive different destinations or verdicts. It is too narrow when it describes an internal function that has no independent outcome or decision consequence.

Split a bundle when:

- parts solve different user jobs;
- parts have different dependencies or permissions;
- parts map to different targets;
- one part is valuable and another is not;
- parts embody different methodologies;
- parts can be adopted independently.

Merge records when differences are only naming, visual presentation, minor configuration, or equivalent implementation detail.

## 3. Comparison relationships

Use one or more explicit relationships:

- **Exact equivalent:** materially same outcome, behavior, and relevant quality.
- **Functional equivalent:** same outcome through a different mechanism.
- **Source superset:** source includes target capability plus material additions.
- **Target superset:** target already covers and exceeds the source.
- **Partial overlap:** shared core with distinct uncovered portions.
- **Complementary:** improves or enables an existing capability without replacing it.
- **Enabling prerequisite:** useful mainly because another candidate requires it.
- **Alternative methodology:** same problem, incompatible or substantially different operating assumptions.
- **Contradictory:** cannot coexist under the same constraints or governance.
- **Novel:** no adequate current or planned equivalent in the verified scope.
- **Planned:** absent now but already committed in the roadmap.
- **Deliberately excluded:** absent by conscious architectural or policy decision.
- **Unknown:** baseline or evidence is insufficient.

## 4. Feature relationships

Model:

- `requires`;
- `recommends`;
- `enables`;
- `enhances`;
- `excludes`;
- `conflicts-with`;
- `replaces`;
- `duplicates`;
- `interacts-with`;
- `changes-behavior-of`;
- `shares-state-with`;
- `shares-permissions-with`.

Any primary candidate with material interactions needs joint testing with affected features.

## 5. Methodology profile

Compare source and target on:

1. **Purpose:** what is optimized and what is willingly sacrificed?
2. **Unit of work:** task, event, conversation, document, code change, workflow, or persistent agent.
3. **Control locus:** user, central orchestrator, distributed agents, policy engine, or emergent process.
4. **Autonomy:** advisory, approval-gated, delegated, or self-directed.
5. **State:** stateless, session, persistent memory, event-sourced, shared, or isolated.
6. **Trust:** trusted component, zero-trust, verifier-gated, consensus, reputation, or user review.
7. **Evidence:** what counts as completion or truth?
8. **Failure:** fail-open, fail-closed, retry, compensate, roll back, isolate, or escalate.
9. **Human role:** operator, approver, reviewer, exception handler, or observer.
10. **Governance:** permissions, audit, policy hierarchy, accountability, and appeals.
11. **Interfaces:** synchronous, asynchronous, event, API, plugin, file, message, or tool call.
12. **Lifecycle:** create, configure, learn, update, deprecate, migrate, and remove.

## 6. Methodology compatibility classes

- **M1 Direct:** assumptions align; capability can be incorporated without a new control boundary.
- **M2 Adapter:** behavior fits after translation at a clear interface.
- **M3 Optional mode:** both methods are valuable but should not be active simultaneously by default.
- **M4 Sidecar or external service:** useful capability should remain operationally separate.
- **M5 Architectural prerequisite:** assimilation requires a prior structural change.
- **M6 Mutually degrading:** combining them weakens both or creates unacceptable ambiguity.
- **M7 Irreconcilable:** core assumptions cannot coexist within the allowed target.

## 7. Fit dimensions

Score and explain fit across:

- semantic and requirements fit;
- architectural cohesion and boundary fit;
- data and state fit;
- interface and integration fit;
- methodology and control fit;
- security, privacy, and permission fit;
- operations and observability fit;
- maintenance and ownership fit;
- user interaction and accessibility fit;
- license, ecosystem, and supply-chain fit;
- roadmap and timing fit;
- reversibility and exit fit.

A high average cannot hide a failed hard constraint.

## 8. Placement logic

### Extend an existing skill or component when

- the capability reinforces its existing purpose;
- the same users, inputs, outputs, permissions, and lifecycle apply;
- adding it does not make the target incoherent;
- the target can test and own it.

### Create a plugin or adapter when

- the capability belongs at a stable external boundary;
- independent release or permissions are useful;
- the core should not absorb source-specific dependencies;
- failure should be isolatable.

### Create a shared service or library when

- multiple targets need the same primitive;
- central consistency outweighs coupling risk;
- the service has clear ownership and an interface contract.

### Fork when

- the capability requires upstream changes unavailable through supported extension;
- upstream contribution is infeasible or rejected;
- divergence, security updates, rebasing, and exit can be owned;
- the value exceeds the permanent maintenance tax.

### Create a new skill or component when

- the responsibility is distinct and reusable;
- it needs separate triggers, permissions, state, lifecycle, governance, or tests;
- forcing it into an existing target would violate cohesion.

### Keep external when

- value is available through a stable contract;
- internalization creates unnecessary maintenance or legal risk;
- source specialization is part of its strength;
- replacement and exit are manageable.

### Reject when

- it is redundant, dominated, incompatible, unsafe, uneconomic, unsupported, irrelevant, or violates a deliberate exclusion.
