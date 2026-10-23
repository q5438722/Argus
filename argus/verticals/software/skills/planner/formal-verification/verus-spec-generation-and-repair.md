---
name: "Verus Submodule and Proof Planning"
description: "Analyze Rust submodules first, schedule views before dependency-ordered API specs, and plan source-correctness and spec-determin-tool completeness repair with per-API artifacts."
---

# Verus Submodule and Proof Planning

Read the [shared workflow](../../verus-spec-generation-and-repair.md) and
Manager's scope before scheduling API-generation work.

## Build the module map first

Inspect actual submodules, type/impl ownership, re-exports, delegated calls, and
cross-submodule dependencies. Assign canonical API identities without counting
re-exports or comment mirrors as additional APIs. Record existing-vstd coverage
and explicitly justified exclusions without silently shrinking the task.

For each submodule, identify its source and docstrings, existing or required
views, supporting lemmas, APIs, and dependencies. The map may use an existing
project inventory; it does not require a new planning-file protocol.

## Order the work

1. Schedule required shared view definitions first and identify their source
   correspondence obligations.
   For each submodule, either name the reused view and why it is sufficient, or
   create a view-definition dependency before its API-spec tasks. Schedule
   constructor-dependent correspondence jointly with that API rather than
   introducing a circular prerequisite; require closure before acceptance.
2. Order API work bottom-up by implementation and proof dependencies. Explain
   any alternative order. Keep a mutually dependent family together and identify
   its joint obligations; an observer must not be accepted without a needed
   constructor relation.
3. Give each API task both source and docstring locations, the selected view,
   exact public signature, prerequisite contracts, and output paths. Do not hand
   Engineer only an API name or a desired postcondition.
4. Resolve the actual Verus and `spec-determin-tool` entry points. Plan two
   distinct proofs per API: source-to-contract correctness, and tool-generated
   completeness for that same contract. Include both checks in the API repair
   loop rather than postponing them to the end of the module.
5. Map each submodule to its `specs/<submodule>/` files and the module aggregate.
   Plan both proof directories and `issues/` alongside them. Every in-scope API
   needs an identifiable entry in each proof track, including reused contracts
   when they are in the requested verification scope; link applicable issues.
6. An implementation-change proposal must become an issue with strict
   independent review before an implementation-edit task can be adopted.
   Schedule minimal reproductions for suspected Verus limitations and review of
   suspected std implementation/docstring defects. Do not turn an inconclusive
   proof into an assumed upstream bug.

## Plan protocol connections before expanding a family

For a field-privacy source blocker, consider the authorized
[proof-only visibility route](../../verus-proof-only-field-visibility.md)
before treating privacy as unavoidable. Separate the adapted correctness
build from the original-library spec/completeness build. Plan the exact
field diff, type/view correspondence and independent review; missing opaque
type support or callee contracts remain distinct obligations.

Apply the [abstraction-integration reference](../../references/spec-abstraction-integration.md).
Inspect existing trait specifications, actual item/return types, consumer
contracts, and their enabling conditions before planning a parallel view.
Include constructor -> consumer -> observer dependencies and applicable
exhaustion or mutable-writeback obligations in the existing map.
Schedule a representative client composition before expanding the same model
across a larger API family. Distinguish constructor-only bridges from relations
needed after consumption; identify any unsupported obligation explicitly.
These clients are supplemental work, not a third substitute proof track.

## Carry trust boundaries into proof planning

Use [TB-PARTIAL-EQ](../../references/trust-boundaries/partial-eq.md),
revision **conditional-posts-v2**, and `trust_boundaries/TB-PARTIAL-EQ.md`.
Decide **if needed** per function, then plan all its postconditions on the
right of `T::obeys_eq_spec() ==>` for the exact receiver/Rhs pair.
Do not propagate the guard as a new API `requires` or add comparison bounds
to unrelated work. Plan original-domain correctness and explicitly conditional
uniqueness, including B-true witnesses and the legal !B cases.
Prioritize affected old premise-only contracts for bounded migration; reuse
evidence only where its candidate and claim still match. Unrestricted
nondeterminism outside the guard does not refute conditional completeness.
Missing source/content bridges and meaningful model definitions remain obligations.

## Feedback and replanning

Plan narrow verifier-feature work under the
[campaign-local toolchain policy](../../verus-campaign-local-toolchain.md),
with its own patch/test/review dependencies and without serializing unrelated
API work behind it. Apply [callback triage](../../verus-callback-api-triage.md):
schedule bounded materially different attempts, then record a callback-support
local skip and continue when broad new callback semantics would be required.

Apply [direct API postconditions](../../verus-inline-api-postconditions.md):
plan actual bindings/protocol integration and inlined guarantees, not a
helper-only milestone in place of the API. Keep all planned deliverables under
the assigned [central artifact workspace](../../spec-artifact-workspace.md);
honor relocation checkpoints and do not reopen old absolute paths as new roots.

Use the failed correctness obligation, completeness counterexample, or
inconclusive query to choose the next bounded repair. A view/helper change
reopens all dependent API checks. Preserve the intended semantics and proof
inputs; do not substitute a passing proxy or make legal inputs disappear.

Keep blocked work visible with attempted proof artifacts and issue references.
Group APIs sharing one limitation under its root-cause issue. Replan a concrete
source/tool limitation rather than repeatedly running unchanged commands, and
continue independent submodules without bypassing the issue/review requirement.
Do not convert investigation, a view-only result, or one passing dimension into
API completion. Finish with a coverage reconciliation and independent Reviewer
acceptance of both proof tracks for the module.

## Plan bounded snapshots

Resolve `storage-policy.json` and the guarded checker command in each handoff.
List the complete source/spec dependency closure and snapshot exclusions;
`targets.include` alone is not a snapshot-size control. Keep historical outputs,
downloaded trees, and unrelated experimental copies outside the selected root.
Estimate multiplication by proof attempts and witness candidates, and run
storage readiness before dispatch. Reuse hash-matching unchanged evidence,
not broad duplicate runs. Budget failure is a visible blocker, not permission
to drop a source bridge, weaken a comparison, or delete unique proof evidence.
