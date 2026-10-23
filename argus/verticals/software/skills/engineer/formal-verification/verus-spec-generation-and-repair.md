---
name: "Verus API Specification and Proof Repair"
description: "Implement view-first API specifications from source and docstrings, prove source correctness with Verus, check completeness with spec-determin-tool, and repair until both proof tracks pass."
---

# Verus API Specification and Proof Repair

Read the [shared workflow](../../verus-spec-generation-and-repair.md), Manager's
scope, and Planner's submodule/dependency map before writing API specifications.
If a direct task lacks the map, establish the necessary submodule and view
dependencies first; do not skip them.

## Per-submodule and per-API loop

Follow [direct API postconditions](../../verus-inline-api-postconditions.md):
expand whole-post wrappers into the actual API `ensures`, retain all guards,
and demonstrate the real binding rather than only proving a model predicate.
Write outputs beneath the assigned [artifact root](../../spec-artifact-workspace.md)
and keep compatibility aliases as historical references, not new output roots.

1. Reuse an adequate existing view, or define the needed view and identify its
   correspondence obligations before dependent API contracts. Discharge
   constructor-dependent obligations with the source implementation proofs
   before acceptance. Follow the planned bottom-up order or its documented
   alternative.
2. Read both source code and docstrings for each API, including delegated calls
   and edge cases. Preserve signatures and legal inputs. Write the contract in
   the module's spec files using the established views and existing borrowing
   support, including required `old`/`final` writeback and frames.
3. Build the per-API source implementation proof and run Verus on the actual
   relevant body/obligations. Retain source mappings for any faithful
   translation; executable rewrites follow the issue/review policy below.
   Calling the external API under its assumed candidate contract is only a
   client proof, not this implementation proof.
4. Run the actual `spec-determin-tool` entry point on the same current contract.
   Keep its per-API completeness proof/harness, comparison, query inputs, result,
   and replay command. Do not replace the tool or weaken the comparison.
5. If either dimension fails or is inconclusive, use that feedback to repair the
   spec, view, faithful source proof, or checker encoding, then rerun both
   affected tracks. Shared-view changes also reopen dependent APIs.
   Neither `UNKNOWN` nor a zero-obligation run is a pass.
6. Continue until both dimensions pass for the current candidate. If a concrete
   limitation prevents closure, preserve the attempts and report the blocker;
   do not mark that API complete or silently change the Verus trusted basis.

## Implement the observable protocol, not just metadata

Follow the [abstraction-integration reference](../../references/spec-abstraction-integration.md).
Implement the adequate existing specification interface and connect constructor
postconditions to the values and transitions used by its consumers.
For iterators, model actual yielded items through the standard remaining
sequence; flattened source contents alone do not specify those items.
Preserve mutable-item initial contents, final writeback, and unaffected frames
with existing borrowing support. Do not assume an auxiliary observer remains
equal to the standard state after consumption from its constructor equality.
Keep necessary helpers source-backed and connected; this does not relax an
explicit zero-UF requirement or authorize new trusted assumptions.
Add bounded clients to the repository's existing verification tests using the
actual contracts, including consumption and relevant boundary/writeback cases.

## Encode the approved equality-model boundary

Follow [TB-PARTIAL-EQ](../../references/trust-boundaries/partial-eq.md),
revision **conditional-posts-v2**, and record it in `trust_boundaries/TB-PARTIAL-EQ.md`.
**If needed**, put the entire postcondition set, not only the return relation,
on the right of `T::obeys_eq_spec() ==>`. Remove B preconditions added to the
API solely by the old policy; keep original safety preconditions, signatures,
executable bodies and unrelated functions unchanged.
Prove the conditional contract without globally assuming B. Explicitly scoped
analysis-only adapters must not impose their premise on the API or claim
unrestricted determinism. Inspect generated comparisons/reexecution and preserve
old evidence with its revision. All content and state obligations inside the
guard still need proof; do not assume target answers or rewrite fixed vstd.

## Raise issues instead of silently changing implementations

For a demonstrated unsupported Rust/verifier feature, follow the
[campaign-local Verus Skill](../../verus-campaign-local-toolchain.md):
fork the pinned commit inside this campaign, build matching vstd, retain patch
and binary provenance, and label all dependent results as local-toolchain
results. Never edit the shared official toolchain.

For callback-driven APIs, follow
[callback triage](../../verus-callback-api-triage.md). Generate a sound useful
contract when possible. If bounded source-faithful attempts still require a
large unsupported callback stack, preserve the candidate/failures as a
callback-support local skip and continue other APIs; do not narrow the callback
domain or mark the API complete.

Use the [proof-only field-visibility Skill](../../verus-proof-only-field-visibility.md)
for a privacy-blocked correctness proof. Only the isolated copy may expose
fields; preserve the body and record how the build uses that copy. Internal
proofs may inspect those fields, but exported specs and completeness must use
the original types/views without temporary field access. This visibility-only
permission is already granted; it is not permission to invent invariants,
replace the target with an unrelated mirror or change other visibility.

Raise an issue in `issues/` before changing an implementation, including
executable rewrites in a source-derived proof copy or a verifier workaround.
Keep any exploratory patch an isolated proposal, with the original/proposed
diff and source correspondence, until strict independent review and required
authorization. A passing proof of rewritten code does not certify the original
implementation. Ordinary ghost annotations or lemmas are not executable edits.

For unsupported Rust syntax or another demonstrated Verus limitation, retain a
minimal baseline reproduction and diagnostic and raise a `verus-limitation`
issue. For suspected std implementation/docstring defects, first investigate
spec/view/proof mistakes and submit the finding for independent review;
classify it as a confirmed defect only after that review. `UNKNOWN` alone is not
evidence of an upstream bug.

Follow Manager's issue-filing authorization, recording a real URL only after
external filing succeeds. Unfiled drafts remain explicit. Link failed proofs
and affected APIs, deduplicate a shared root cause, and keep unresolved APIs
incomplete rather than patching source or docs just to get a pass.

## Produce the four artifact collections

Maintain `specs/<submodule>/` files following the module map, shared views where
needed, and a buildable module aggregate; do not mix unrelated APIs into a flat
candidate file. For every in-scope API, write identifiable entries under
`proofs/correctness/` and `proofs/completeness/`, using the shared layout or an
explicitly mapped repository-native equivalent. Include `issues/INDEX.md` and
the discovered issue/proposal reports; record the reviewed scope if none exist.

Keep a compact index tying each API and source/docstring location to its spec,
views, two proof paths, commands, outcomes, and associated issue IDs. Shared proof
helpers do not replace per-API proof entries; blocked APIs retain their failing
attempts and issue status.
Typecheck the aggregate without duplicating existing vstd declarations.

## Handoff

Provide the literal contract changes and the two current proof results to
Reviewer. Supplemental clients, native tests, and negative controls can expose
semantic mistakes, but cannot stand in for either required dimension.
Run affected checks first, reuse unchanged builds, and retain precise diagnostics
instead of repeatedly running an unchanged broad suite. Do not claim module
completion from a bounded submodule result.

## Check storage before copying inputs

Use the project guarded checker entry point and `storage-policy.json` before
every discover/analyze/reexecute and witness batch. Preserve the literal
selectors, verifier flags, legal domain, and full dependency closure.
Inspect the actual snapshot manifest, not only `targets.include`; keep all old
outputs/caches/unrelated downloaded source trees excluded and new output isolated.
Record explicit budget failures and stop the batch rather than using raw
specdet to bypass the gate. Preflight-only success is not verification.
Retain unique specs/proofs/queries/receipts. Operator-authorized compaction may
replace only verified restorable duplicates, without changing old manifests.
