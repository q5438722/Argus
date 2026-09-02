---
title: Nanvix Rust Std Slice Module Contract
description: Operator requirements for an isolated, module-first verification pass over Rust 1.96 core::slice.
---

# Nanvix Rust Std Slice Module Contract

## Operator decision

Stop the cross-module provisional queue. The next project is only
`core::slice`. Do not automatically continue to another Rust module after this
one.

The goal is to produce one coherent, reviewable slice specification module
that follows the existing Verus vstd style:

- one shared `[T]@ -> Seq<T>` semantic model;
- real sequence, subrange, permutation, membership, ordering, and state-change
  relations;
- `old(...)` / `final(...)` for mutable operations;
- source-backed panic and unsafe domains;
- shared helpers and axioms, rather than one unconstrained uninterpreted result
  function per executable API.

## Isolation and source provenance

Create a new isolated experiment root:

```text
/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-slice-specgen-2026-08-11
```

Copy, without modifying the source snapshot:

```text
/home/chentianyu/nanvix-rust-std-spec-survey/rust-1.96/library/core/src/slice/**
```

The copy must include `mod.rs` and all slice submodules used to define the
public API, including indexing, iteration, sorting, rotation, ASCII, raw, and
specialization files. Record source paths and content hashes in a provenance
manifest.

Also copy the relevant existing vstd baseline files for reference:

```text
/home/chentianyu/nanvix-rust-std-spec-survey/verus/source/vstd/slice.rs
/home/chentianyu/nanvix-rust-std-spec-survey/verus/source/vstd/std_specs/slice.rs
```

Do not edit the Rust 1.96 checkout, the Verus vstd checkout, the canonical
2,121-target result tree, or previously generated provisional lanes. Do not
commit, push, publish, or apply contracts upstream.

## Target inventory must be completed before generation

Create these durable inventory artifacts first:

```text
inventory/SLICE_EXEC_FN_INVENTORY.md
inventory/slice_exec_fn_inventory.csv
inventory/slice_exec_fn_inventory.json
```

The inventory authority is the 132 stable unique executable APIs reported for
`core::slice` by `results/modules.csv`:

- 12 already covered by exact vstd contracts;
- 120 currently uncovered stable APIs.

Use canonical API paths to deduplicate reexports such as `std::slice`.
Exclude unstable APIs, non-executable specification helpers, private
implementation functions, and duplicate aliases from the 132-target completion
count. Supporting contracts such as `SliceIndex` or `Index` trait machinery
may be copied when needed, but must be labeled separately if they are not one
of the 132 stable module targets.

Every inventory row must contain:

- canonical target;
- Rust declaration/source location;
- kind, signature, generic bounds, safety, and stability;
- existing-vstd status and provenance;
- planned specification status;
- semantic family;
- source-observable inputs, outputs, and mutations;
- required shared model/helper;
- decisive validation command;
- final contract or justified-no-spec status.

The inventory must be delivered and checked before bulk generation starts.

## Existing vstd baseline

Copy and preserve the semantics of these 12 exact stable API contracts:

1. `core::slice::len`
2. `core::slice::is_empty`
3. `core::slice::get`
4. `core::slice::iter`
5. `core::slice::first`
6. `core::slice::last`
7. `core::slice::first_mut`
8. `core::slice::last_mut`
9. `core::slice::split_at`
10. `core::slice::split_at_mut`
11. `core::slice::copy_from_slice`
12. `core::slice::copy_within`

These contracts establish the baseline style:

- `len` and `is_empty` are tied directly to `slice@.len()`;
- indexing/get contracts return the corresponding sequence element or `None`;
- first/last contracts describe exact empty/non-empty branches;
- mutable reference contracts connect the returned reference to the old
  sequence and describe the final slice update;
- split contracts use exact `subrange` relations;
- mutation contracts state complete final sequence transformations;
- iterator contracts connect the iterator's remaining elements to the slice
  sequence.

Copying these contracts is not enough: their exact target binding, signatures,
generic bounds, and typecheck behavior must be revalidated in the isolated
module.

## Requirements for the remaining 120 APIs

The default is to add a useful specification for every remaining stable exec
API. Work by semantic family inside the slice module, not by the old global
skip taxonomy.

Recommended internal order:

1. basic observations and conversions;
2. prefix/suffix, comparison, search, and membership;
3. immutable splitting and chunking;
4. mutable splitting, chunking, swapping, rotation, copying, and filling;
5. ASCII operations;
6. ordering, binary search, sorting, selection, and partitioning;
7. iterator/adaptor constructors;
8. generic `Pattern`, closure/comparator, and higher-order APIs;
9. raw pointer, unchecked, and representation-sensitive APIs.

### Required specification style

- Reuse `Seq<T>`, `View`, `DeepView`, `subrange`, `update`, concatenation,
  permutation, membership, and ordering predicates whenever applicable.
- Add one shared helper when multiple APIs express the same concept.
- Define helper laws or broadcast axioms that make the helper useful across
  operations.
- Use exact source-backed branch behavior for `Option`, `Result`, tuples, and
  returned references.
- For mutations, describe both the changed region and the unchanged frame.
- Preconditions may express only documented panic/unsafe requirements or
  semantic laws genuinely required to connect Rust traits to specification
  predicates.
- Do not add a stronger precondition merely to make determinism or typechecking
  pass.
- Do not use `ensures true`, `requires false`, `arbitrary()`, or an
  unconstrained result.
- A contract of the form `result == fresh_uninterp_function(inputs)` is not
  accepted unless that function is a reviewed module-level abstraction with
  independent laws connecting it to other slice operations.
- Weak specs are allowed only when they state a useful necessary property in
  the shared slice model, such as length, subrange, prefix/suffix, membership,
  permutation, partition, sortedness, mutation frame, or preserved metadata.

### Higher-order and source-nondeterministic APIs

For closure/comparator/predicate APIs, first decide whether a reusable
module-level call-observation relation can be modeled. Do not create a unique
opaque closure-result function for each target.

If Rust explicitly permits multiple results or implementation-dependent
ordering, do not invent a unique result to satisfy the determinism checker.
State the strongest source-backed relation that is useful, record the
determinism result honestly, and justify why a deterministic complete contract
is unavailable.

## Justification contract for APIs without a spec

An exec API may remain without a generated spec only when the inventory row and
the human-readable report provide all of:

1. the exact target and source behavior;
2. the strongest weak spec that was considered;
3. why that weak spec would be vacuous, unsound, source-unjustified, or
   unusable;
4. the missing shared abstraction or checker feature;
5. why existing vstd slice/sequence vocabulary is insufficient;
6. evidence from typecheck, determinism, or source analysis;
7. the concrete prerequisite that would make the target specifiable;
8. an operator-review disposition.

Generic labels such as `runtime`, `unsafe`, `complex`, `unsupported`, or
`needs abstraction` are not sufficient justification.

## Required output structure

At minimum, produce:

```text
rust-core-slice/                       # copied Rust 1.96 module
vstd-baseline/                         # copied existing vstd slice files
inventory/SLICE_EXEC_FN_INVENTORY.md
inventory/slice_exec_fn_inventory.csv
inventory/slice_exec_fn_inventory.json
specs/existing_vstd_slice_specs.rs
specs/generated_slice_specs.rs
specs/all_slice_specs.rs
catalog/slice_spec_catalog.csv
catalog/slice_spec_catalog.json
catalog/SLICE_SPEC_REVIEW.md
verification/
```

Each catalog row must include:

- target and semantic family;
- existing/new/justified-no-spec status;
- complete contract text;
- requires and ensures;
- shared helpers and assumptions;
- source reference and excerpt;
- strength and known risks;
- typecheck result;
- determinism result;
- target-binding, signature-shape, and generic-bounds results;
- reviewer notes.

## Validation

Run the smallest existing Verus/specgen checks that establish:

- exactly 132 unique stable executable targets;
- exactly 12 existing-vstd target rows;
- every other target has a new spec or complete justification;
- no missing, extra, duplicate, or alias-counted targets;
- exact target binding, argument order, receiver mutability, result binding,
  generic parameters, bounds, and feature gates;
- contract typechecking;
- determinism status recorded without converting `UNKNOWN` into success;
- anti-vacuity and source-fidelity checks;
- copied Rust/vstd baseline provenance;
- original Rust, vstd, canonical, and provisional trees remain unchanged.

## Completion criteria

The slice module task is complete only when:

1. the inventory is reviewed and internally consistent;
2. all 132 stable exec APIs are accounted for;
3. the 12 existing vstd specs are integrated and revalidated;
4. each of the remaining 120 APIs has either a generated spec or a detailed
   target-specific justification;
5. the module shares a coherent semantic vocabulary rather than target-local
   opaque views;
6. all machine evidence and the operator review catalog are present;
7. no other Rust std module has been started.

Final acceptance remains an operator decision.
