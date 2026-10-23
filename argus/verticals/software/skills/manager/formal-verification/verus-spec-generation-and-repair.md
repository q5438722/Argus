---
name: "Verus Specification Scope and Delivery"
description: "Scope a Verus module-specification mission with submodule analysis, view-first dependencies, mandatory correctness and completeness feedback, and complete per-API proof deliverables."
---

# Verus Specification Scope and Delivery

For Verus module specification generation or repair, read the
[shared workflow](../../verus-spec-generation-and-repair.md) before setting
the mission. This Skill is Manager-owned, including front-door/SELF scoping;
it does not require the optional generic Manager grounding pass.

## Scope and handoff

Carry the [campaign-local Verus permission](../../verus-campaign-local-toolchain.md)
and [callback triage policy](../../verus-callback-api-triage.md) into the mission.
Require an immutable official baseline plus a separate mutable local toolchain
when unsupported language features need verifier work. Callback-support skips
stay in the inventory and do not block unrelated ready APIs.

Require [direct, effectively bound API postconditions](../../verus-inline-api-postconditions.md)
and assign the [central artifact root](../../spec-artifact-workspace.md).
Do not treat helper-only delivery as completion of the remaining API-spec queue.
Use supported lifecycle/workdir controls for approved relocations and retain
historical evidence and the same project identity.

1. Identify the requested module, intended Rust source and docstrings, existing
   vstd contracts, output location, and fixed Verus baseline. Preserve the
   requested public API scope; expose ambiguities instead of silently excluding
   difficult APIs or changing signatures.
2. Require initial submodule and dependency analysis before API generation.
   Delegate the detailed map to Planner rather than duplicating its repository
   exploration. Each submodule must state whether it reuses an existing view or
   needs a new view before its API specs.
3. Require bottom-up dependency ordering, or an explicitly justified alternative.
   Views and their correspondence obligations must precede dependent contracts.
   Keep source code and docstrings as joint semantic inputs throughout repair.
4. Establish both acceptance dimensions: source implementation correctness
   verified by Verus, and completeness checked through `spec-determin-tool`.
   Have Planner identify the actual project commands; do not substitute client
   proofs, typechecking, source review, or a different checker.
5. Carry four deliverables into the handoff: specs organized by submodule, a
   correctness-proof directory with per-API entries, a separate completeness-proof
   directory, and `issues/` with an index of findings/proposals and their status.
   Require a compact coverage index linking each API's artifacts, two proof
   results, and any associated issues.
6. Establish the issue-reporting destination and external-filing authorization.
   Require an issue proposal and strict independent review before any
   implementation change; review alone does not authorize canonical Rust/std
   or Verus changes. Preserve the intended source until an explicit change is
   approved.

## Require usable library integration

Carry the [proof-only field-visibility permission](../../verus-proof-only-field-visibility.md)
into source-proof tasks when field privacy is a blocker. It permits only an
isolated correctness-copy adaptation, not edits to the real std/vstd or an
expanded public interface. Require correspondence review and stock-library
spec/completeness checks; do not wait for new approval solely for field
visibility or automatically relabel old failures.

Use the [abstraction-integration reference](../../references/spec-abstraction-integration.md)
to require reuse of adequate existing specification protocols, or a justified
bridge when they are insufficient. For stateful families in scope, include
constructor/consumer interoperability and representative repository clients in
the delivery requirements. Do not prescribe a new view or exact representation;
delegate that analysis to Planner. A detached model's unique output is not
evidence that callers can use the API through the library's existing contracts.
Integration clients supplement, never replace, either proof dimension.

## Declare the verification trust boundary

Apply [TB-PARTIAL-EQ](../../references/trust-boundaries/partial-eq.md),
revision **conditional-posts-v2**. **If needed**, require all postconditions of
the affected function on the right of `T::obeys_eq_spec() ==>`; do not assume
the flag globally or add it as an API `requires`. Unrelated functions and the
original Rust calling domain remain unchanged.
Maintain `trust_boundaries/TB-PARTIAL-EQ.md` with the reason, exact type pairs,
complete guarded guarantees and conditional analysis scope.
Update conflicting project guidance through normal planning, preserve old
premise-only evidence as history, and schedule migration checks rather than
relabeling old successes. Report conditional completeness separately from
unrestricted determinism; no other trust boundary is authorized by this change.

## Completion and escalation

Keep unsuccessful APIs in the repair loop with explicit failures or blockers.
Do not declare the module complete from a generated declaration count, a local
subtask's `done`, or only one passing feedback dimension. The independent
Reviewer must reconcile the requested coverage, both proof tracks, and issues.

Require issues for demonstrated Verus limitations (including unsupported Rust
syntax) and independently reviewed std implementation/docstring defects.
Proof failure alone is not such a diagnosis. Keep unconfirmed findings marked
as needing review and distinguish a local issue draft from an externally filed
issue; resolve missing filing permission without claiming publication occurred.

Preserve the distinction between completing a planning/view subtask and
certifying an API. A tool limitation does not authorize verifier or lifecycle
engine changes: request a separate, explicitly approved tool task when needed.
Keep versions, paths, scope decisions, and current progress in the project.

## Storage readiness and retention

Set the project `storage-policy.json`, bounded input roots, and guarded checker
entry point before dispatch. Require the same preflight for Engineer and
Reviewer, including minimum free space on the actual output filesystem.
Do not dispatch oversized inputs or resume an operator-paused campaign because
cleanup freed space. Keep the full API goal while storage is blocked.
Authorize archival scope explicitly; preserve unique spec/proof/query/review
evidence and a verified restore path for compacted duplicate inputs. Storage
cleanup neither changes acceptance counts nor authorizes checker/source edits.
