---
name: "Verus Proof-Only Field Visibility"
description: "Use when Rust field privacy blocks a spec-correctness proof. Permit visibility-only edits in isolated proof source copies, never in production libraries, exported specs or completeness inputs; preserve source correspondence and original API observations."
---

# Verus Proof-Only Field Visibility

[Chinese reference](references/verus-proof-only-field-visibility.zh-CN.md)

Policy: **proof-only-field-visibility-v1**, authorized on 2026-10-13.
Read the [shared specification workflow](verus-spec-generation-and-repair.md).
This is an authorized source-adaptation rule for correctness proofs, **not**
an axiom, a new semantic trust boundary, or a waiver of source correctness.

## When this permission applies

Only while proving that an implementation satisfies its specification, a
private or restricted-visibility field may become `pub` in an **isolated
correctness-proof source copy**. All such fields in that copy may be exposed
if necessary; prefer the smallest useful set, not a repository-wide rewrite.
This covers named or tuple fields whose visibility Rust permits changing,
including inherited privacy, `pub(crate)`, `pub(super)` and `pub(in ...)`.

Do not edit canonical Rust/std sources, installed/shared sysroots, the official
Verus/vstd baseline, or a production library. Keep the adapted source and any
adapted library/sysroot build under a dedicated correctness-proof location,
such as `proofs/correctness/<family>/visibility/`. A proof-only build must not
replace the library used for exported specs, integration clients or completeness.
Keep large adapted builds out of specdet input snapshots and retain the
existing storage guard.

The following field-declaration change is authorized in that copy:

```diff
-    pub(super) iter: slice::Iter<'a, T>,
+    pub iter: slice::Iter<'a, T>,
```

Only field visibility is authorized here. Preserve field names, types, order,
layout attributes, generics, bounds, lifetimes, initializers, method bodies,
dispatch and drop behavior. Do not add/remove fields or silently expose
methods, types or modules. Any other source transformation follows the
existing separate authorization and correspondence-review rules. Ordinary
ghost annotations and lemmas remain separate from the visibility-only diff.

## Keep temporary fields out of the public specification

Correctness bodies, internal invariants and source-to-view lemmas may refer
to the exposed fields. The **exported API contract must not**. It must use
the original public API and its source-backed abstractions, such as `@`,
`IteratorSpec::remaining`, return variants and applicable old/final content
relations. Exported helper definitions must not hide a dependence on the
temporary visibility.

A field that was already public in the original API remains usable normally;
the restriction concerns fields made public solely for the proof.

For `Drain::as_slice`, the exported content guarantee remains:

```rust
ensures
    returned@ == IteratorSpec::remaining(drain),
```

Do not replace it with a contract that requires access to `drain.iter`, even
if that expression typechecks in the adapted proof build. A private
source-to-view proof may establish the relationship between the two iterators;
that relationship is an obligation, not a fact granted by changing visibility.

For this Rust std specification work, pointer and ownership properties are
not required spec/completeness observations. Internal proof machinery may use
them when needed to establish the requested value/content contract, but do not
turn them into additional exported postconditions or completeness gates.
Content effects of callbacks or other operations are not excluded by this rule.

## Visibility is not type correspondence or an invariant

Changing a file that the verifier never compiles cannot fix privacy. Record
how the correctness build actually uses the adapted declarations rather than
silently importing the original precompiled std type.

A local structure with the same field names is not automatically
`std::vec::Drain`. If a local mirror or a rebuilt proof-only crate changes type
identity or compilation context, retain an explicit original-to-proof mapping
and independently check the relevant representation, call and view
correspondence. Do not assume equal layout, interchangeable trait dispatch,
or that a proof about the mirror certifies the original API.

Public fields can admit constructions or writes unavailable to original
clients. Preserve the original reachable-state domain. Any representation
invariant needed by the value/content proof must come from established
constructors/contracts or proved correspondence, not from an invented API
precondition, an assumption that private fields are automatically valid, or
the target postcondition itself.

This permission does not expose a Verus opaque datatype, remove
`external_body`, create missing callee contracts, or authorize `assume`,
`admit`, new axioms, compiler privacy bypasses or checker changes.
If a distinct limitation remains, report it precisely instead of extending
this permission or counting a skipped body as a proof.

## Evidence and independent review

Use the existing per-API source-correspondence record to retain:

- The pinned original source, original/adapted paths and hashes, and the exact
  field-visibility diff. Keep other ghost/scaffolding changes separately
  identifiable; inspect enough declaration/body context to reject hidden edits.
- The original-to-proof type/method mapping, any valid-state/view invariant,
  and the actual build command and consumed source/library paths.
- A correctness run that checks the relevant body against the unchanged
  public contract, followed by independent correspondence/proof review.
- A separate stock-library run for the exported spec and integration clients,
  plus completeness on that same public contract and selected observations,
  with **no adapted declarations, proof-only crate artifacts or newly exposed
  field accesses** in its inputs.

The operator has already authorized this visibility-only adaptation; do not
wait for another implementation-change approval solely to try it. Recording
the adaptation and independent review before counting its result remain
mandatory. A change beyond field visibility needs its own permission.

If the public contract and completeness inputs did not change, matching
existing completeness evidence may be reused; visibility permission alone
does not require rerunning it or alter its verdict. Retain the original privacy
failure and label any new source result as checked through the recorded
proof-only adaptation. Do not automatically promote earlier blocked APIs.
