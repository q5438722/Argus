---
name: "Verus Correctness and Completeness Review"
description: "Independently accept Rust module specs only with source-and-docstring fidelity, Verus implementation proofs, spec-determin-tool completeness proofs, and complete per-API artifact coverage."
---

# Verus Correctness and Completeness Review

Read the [shared workflow](../../verus-spec-generation-and-repair.md) before
reviewing a Verus specification task. Use this OWN Skill, not only the
Engineer's methodology or self-reported results.

## Inspect the real scope and semantics

Enforce [direct API postconditions](../../verus-inline-api-postconditions.md):
an `ensures` forwarding the entire contract to one predicate is not the requested
deliverable, and helper/projection proofs do not establish a real API binding.
Verify [artifact-root and migration boundaries](../../spec-artifact-workspace.md)
without rewriting historical evidence or expanding read access.

Check the submodule/API inventory, dependency order, view definitions, and
source correspondence. Confirm required views preceded dependent specs and
that a different API ordering has a real justification. Do not promote a
missing constructor relation or an arbitrary observer to a complete family.

Compare every changed contract with both its implementation and docstring.
Inspect signatures, legal inputs, return branches, contents, mutation frames,
consumed iterator states, and relevant callback behavior. Check shared
dependencies and representative compositions, not only isolated declarations.

## Check integration through actual consumers

Use the [abstraction-integration reference](../../references/spec-abstraction-integration.md).
Independently check the constructor -> consumer -> observer chain through the
existing specification interface and actual loaded contracts.
Inspect yielded contents/order, applicable exhaustion and mutable writeback,
and any enabling conditions or auxiliary-state bridge.
Reject a metadata-only client or a constructor-only equality offered as proof
of later-state behavior. Judge helpers by justified semantic connections, not
merely by whether they use uninterpreted syntax; enforce explicit task limits.
Client verification supports integration review but certifies neither required
proof dimension on its own.

## Independently check both proof dimensions

For correctness, replay the affected source implementation proofs with the
intended Verus baseline. Verify that the relevant bodies/obligations are checked
against the current candidate, and that source-derived transformations have
their correspondence obligations discharged. Reject circular use of the target
assumption, skipped bodies, synthetic placeholders, newly trusted answers, and
zero-obligation runs. Typechecking, native tests, and client proofs do not
replace this dimension.

For completeness, run the actual `spec-determin-tool` path on the current
contracts and inspect its generated proof/query, selected output relation,
premises, and result. Reject success based on weakened comparisons,
answer-bearing inputs, false preconditions, `UNKNOWN`, or a replacement checker.
Check relevant lawful witnesses. A deterministic wrong answer is not correct;
an implementation proof alone does not show completeness.

Replay changed APIs and affected dependencies. Reuse unchanged evidence only
after establishing that its candidate, proof inputs, and baseline still match.
Do not infer either result from Engineer's prose.

## Review within the declared trust boundary

Read [TB-PARTIAL-EQ](../../references/trust-boundaries/partial-eq.md),
revision **conditional-posts-v2**, and `trust_boundaries/TB-PARTIAL-EQ.md`.
Verify the **if needed** justification and that all postconditions of each
selected function are on the right of `T::obeys_eq_spec() ==>`.
Reject a lingering API `requires B`, global B assumption, partially guarded
postcondition set or new bounds on unrelated APIs. Preserve original preconditions.
Inspect original-domain source correctness and the exact conditional
completeness/reexecution claim; !B calls remain legal, not promised deterministic.
Do not accept a B-false vacuity check as proof of the B-true guarantees.
Require migration evidence before calling an old premise-only result a current
revision success. Source/content bridges, state effects and actual model
definitions remain obligations; additional trust requires separate approval.

## Strict implementation-change and issue review

For a [campaign-local Verus](../../verus-campaign-local-toolchain.md) result,
review the exact verifier/vstd patch, original reproducer, generated
obligations, positive and negative regressions, build manifest and binary
digest. Reject relabeling it as an official-baseline result or any patch that
assumes/deletes the failed obligation.

For [callback triage](../../verus-callback-api-triage.md), verify that a skip
follows real bounded attempts, preserves the original callback domain and
remains explicitly incomplete. Accepting a local skip only lets the module
continue; it is not API correctness/completeness acceptance.

Apply the [proof-only field-visibility checklist](../../verus-proof-only-field-visibility.md)
to this pre-authorized adaptation. Confirm only field modifiers changed in
the source diff, the verifier consumed the intended copy, and type/view
correspondence and original reachable-state assumptions are justified.
Reject temporary-field dependencies in exported specs or completeness, which
must still use the unmodified library. A public mirror compiling is not a
source proof or approval for other executable/visibility changes.

Require an issue proposal before any implementation change, including
executable rewrites in source-derived proof copies. Independently inspect the
original/proposed implementation diff, source and docstrings, observable and
safety effects, source-to-proof correspondence, and affected proofs. Do not
approve a different implementation merely because it makes the spec provable.
Record the review decision in the issue; canonical std or Verus changes still
require explicit operator authorization.

Reproduce reported Verus limitations on the intended baseline, including
unsupported Rust syntax. Before confirming a std implementation/docstring
defect, rule out a faulty spec/view/proof or checking encoding and identify the
actual source/docstring error. A failed proof or `UNKNOWN` is not sufficient.
Unconfirmed diagnoses stay `needs-review`.

Check that required findings and change proposals appear in `issues/`, link
their affected APIs/proofs, and have honest review and filing status. A local
draft is not an upstream issue URL. A reviewed issue does not by itself pass
either proof track or repair an affected API.

## Delivery and verdict

Reconcile specs organized by submodule, the per-API Verus correctness-proof
directory, the separate completeness-proof directory, and the `issues/`
collection with its index. Every in-scope API must map to its spec, both proofs,
two explicit outcomes/replay commands, and any related issues. If no issues were
found, require an explicit statement of the reviewed scope rather than invented
reports. Status labels, missing proof files, or duplicated helper entries are
not API proof coverage.

Accept an API only when both dimensions pass for the same candidate. Module
completion additionally requires complete coverage and a usable aggregate.
Planning/view-only tasks may finish their narrower scope without certifying
dependent APIs. For unsuccessful API work, state the smallest failed obligation
and next repair, or a concrete blocker/replan reason; do not lower the gate.
Verifier changes remain separately authorized tool work.

## Apply the same storage gate independently

Read `storage-policy.json` and use the guarded checker entry point inside the
existing read-only project/input and writable scratch boundaries. Check actual
snapshot size, dependency closure, and free space before replay; do not bypass
the gate through the raw checker or expand mount permissions.
Inspect comparisons, source links, and original receipts after compaction as
before. Missing archived inputs require verified materialization, not an
assumption that an old run replayed. Request materialization within approved
roots when necessary. Preflight or archive success never substitutes for either
proof dimension, and cleanup must not erase failures or change API acceptance.
