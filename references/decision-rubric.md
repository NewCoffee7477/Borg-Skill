# Decision Rubric

## Contents

- Hard gates and weighted criteria
- Scoring and classification
- Rejection codes and risk
- Cost, sensitivity, and dominance
- Doctrine-review decision hinges

## 1. Hard gates

A candidate cannot be Primary while any applicable hard gate fails:

1. **User mandate:** within the user's requested scope and authority.
2. **Safety and policy:** no prohibited or unacceptable harm path.
3. **Legal and license:** no known license, intellectual-property, contractual, or use restriction that blocks the proposed form. Flag legal uncertainty for qualified review; Borg does not provide legal clearance.
4. **Security and privacy:** no unresolved critical exposure, credential path, data misuse, or unacceptable trust expansion.
5. **Architectural integrity:** destination can own the capability without violating a non-negotiable boundary.
6. **Evidence minimum:** defining behavior and consequential claims meet the required evidence level.
7. **Operational ownership:** someone or some component can test, monitor, update, support, and remove it.
8. **Non-degradation:** no unresolved critical regression to required behavior or quality.
9. **Execution authority:** implementation is not implied by analysis or planning approval.

A failed gate can produce Secondary only when the gate is plausibly resolvable and the exact resolution condition is stated. Otherwise classify Do Not Assimilate.

## 2. Default weighted criteria

Score each criterion from 0 to 5 and multiply by its weight. Normalize to 100.

| Criterion | Weight | Core question |
|---|---:|---|
| User and strategic fit | 14 | Does it serve an actual objective or known gap? |
| Unique capability gain | 14 | Is the uncovered value materially distinct? |
| Expected outcome impact | 13 | How much does it improve effectiveness, reliability, speed, safety, or reach? |
| Architectural cohesion | 10 | Does it belong naturally at the proposed boundary? |
| Methodology compatibility | 8 | Can assumptions and control models coexist? |
| Reuse and leverage | 8 | How broadly and repeatedly can the capability pay off? |
| Evidence and maturity | 8 | How well verified, stable, and production-ready is it? |
| Security and governance fit | 8 | Can permissions, audit, privacy, and accountability be controlled? |
| Maintainability and operability | 6 | Can it be tested, monitored, updated, supported, and removed? |
| Delivery economics and time-to-value | 5 | Is total lifecycle cost proportionate to benefit? |
| Reversibility and option value | 3 | Can Borg learn or exit without costly lock-in? |
| Ecosystem and supply-chain health | 3 | Is the source, provenance, release process, and support context trustworthy enough? |
| **Total** | **100** | |

Adjust weights before scoring when the user's priorities differ. Record changes and rationale.

## 3. Scoring anchors

Use consistent anchors:

- **0:** actively harmful, absent, or wholly unsupported.
- **1:** very weak; major mismatch or negligible value.
- **2:** weak; material limitations outweigh most benefit.
- **3:** adequate; useful with manageable limitations.
- **4:** strong; clear benefit and good fit.
- **5:** exceptional; decisive value, excellent fit, and strong evidence.

Use ranges such as `3–4` when evidence cannot justify a single value.

## 4. Classification defaults

These thresholds are defaults, not automatic verdicts:

### Primary

- all hard gates pass;
- normalized score normally 75 or above;
- defining behavior has E3 or E4 evidence;
- confidence is medium or high;
- no unresolved critical risk;
- sensitivity analysis does not readily reverse the recommendation.

### Secondary

- score normally 55–74; or
- potential primary value with a resolvable evidence, dependency, timing, fit, or ownership gap; or
- recommendation is sensitive to reasonable weight changes; or
- useful only after another candidate or architectural prerequisite.

State the promotion test: the exact evidence, experiment, decision, or prerequisite that would move it to Primary.

### Do Not Assimilate

- any unresolvable hard-gate failure;
- score below 55;
- target or existing option dominates it;
- methodology is mutually degrading or irreconcilable;
- lifecycle cost or lock-in is disproportionate;
- value is better obtained externally;
- it conflicts with a deliberate exclusion or user objective.

## 5. Rejection reason codes

Use one or more:

- `DUP` — exact or adequate duplicate.
- `DOM` — dominated by an existing or simpler alternative.
- `EXT` — useful, but better consumed externally.
- `INC` — incompatible methodology or architecture.
- `COST` — disproportionate delivery or lifecycle burden.
- `RISK` — unacceptable security, privacy, safety, legal, or governance risk.
- `IRR` — not relevant to current objectives.
- `IMM` — immature or insufficiently evidenced.
- `LOCK` — excessive dependency or exit cost.
- `EXCL` — deliberately excluded by policy or architecture.
- `DEFER` — potentially valuable, but timing or prerequisites make current assimilation unsound.

## 6. Risk analysis

For each material risk record:

- event or failure mode;
- cause;
- affected assets and capabilities;
- likelihood: low, medium, high, or unknown;
- impact: low, medium, high, critical;
- detectability and time-to-detection;
- mitigation;
- residual risk;
- owner;
- effect on classification.

Do not multiply vague ordinal values into pseudo-precise numbers unless the context already has a calibrated risk method.

## 7. Cost and economics

Estimate ranges for:

- research and proof of concept;
- implementation and integration;
- migration and compatibility work;
- tests and assurance;
- documentation and training;
- infrastructure and usage;
- security and compliance;
- ongoing monitoring and support;
- upstream changes and rebasing;
- deprecation, replacement, and exit.

Compare against the cost of configuration, composition, external use, deferral, and doing nothing.

## 8. Sensitivity and robustness

Perform sensitivity analysis when:

- top candidates are within five points;
- any high-weight criterion is uncertain;
- user priorities are not explicit;
- one assumption drives the result;
- cost or impact ranges overlap materially.

At minimum:

1. vary the three highest-impact uncertain weights by ±20 percent while keeping total weight normalized;
2. test pessimistic and optimistic evidence or cost cases;
3. identify the assumptions that flip placement or classification;
4. mark the recommendation `robust`, `moderately robust`, or `unstable`.

An unstable candidate should usually remain Secondary pending clarification or a T-check.

## 9. Dominance and counterfactual checks

Before recommending assimilation, ask:

- Is another option at least as good on every important criterion and better on one?
- Can configuration or composition provide the same value?
- Can the source remain external with less risk?
- What happens if nothing is added?
- Is the claimed benefit caused by packaging rather than capability?
- Would the target improve more by fixing an existing weakness instead?

## 10. Doctrine-review decision hinges

When `doctrine-parliamentarian` is eligible under its installed contract, present the material hinges rather than a preferred verdict:

- expansion versus coherence;
- novelty versus reliability;
- autonomy versus accountability;
- reuse versus coupling;
- speed versus evidence;
- local feature gain versus collective health;
- integration versus dependency;
- completeness versus reversibility;
- user convenience versus permission expansion;
- preserving a distinct methodology versus forcing a hybrid.
