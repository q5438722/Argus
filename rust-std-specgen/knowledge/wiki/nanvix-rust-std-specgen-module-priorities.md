---
title: Nanvix Rust Std Specgen Module Priorities
description: Review examples and a module-first prioritization strategy for Rust std specifications not already covered by Verus vstd.
---

# Nanvix Rust Std Specgen Module Priorities

## Why change to a module-first workflow

The provisional lane proved that many skipped APIs can be made to typecheck and
pass the determinism checker after introducing trusted state or representation
views. That is useful feasibility evidence, but it is not a good review order:

- `machine_checked_provisional` proves only that the trusted contract is
  well-formed and deterministic under its assumptions.
- It does not prove that an uninterpreted view is the right semantic abstraction.
- Reviewing unrelated filesystem, pointer, atomic, socket, and collection models
  together makes assumption consistency difficult to judge.
- A reusable abstraction should be reviewed against every operation in one module,
  not accepted one target at a time.

The working rule should therefore be:

> Freeze one module, subtract exact vstd-covered targets, define that module's
> semantic model, generate its remaining contracts, and review the module as one
> coherent unit before moving to the next module.

The earlier cross-module continuous generation and its monitor were paused on
2026-08-11. Existing provisional artifacts remain evidence, but they are not a
module acceptance decision and do not modify the canonical 128 accepted / 1,993
skip tree.

## Two provisional examples for review

### Example A: `std::fs::Metadata::len`

Lane: `runtime_or_hidden_state`

```rust
#[verifier::external_type_specification]
#[verifier::external_body]
pub struct ExMetadata(Metadata);

pub uninterp spec fn runtime_metadata_len(metadata: &Metadata) -> u64;

pub assume_specification[ Metadata::len ](
    metadata: &Metadata,
) -> (result: u64)
    ensures
        result == runtime_metadata_len(metadata),
;
```

Recorded assumptions:

- `hidden_state_view_relation`
- `hidden_value_view_vocabulary`
- `runtime_effect_trace_observable`

Recorded state models:

- `hidden_mutable_object_state`
- `runtime_os_state`

Machine evidence:

- typecheck: pass
- determinism: `ok`, `R0 = unsat`
- anti-vacuity issues: none

Intended meaning: the result is the size captured in the private platform
`Metadata` value. It does not claim that the live filesystem still has this size.

Review concern: by itself, this contract is close to renaming the return value.
It becomes useful only if `runtime_metadata_len` is part of a coherent
`Metadata` model shared by constructors and the other `Metadata` accessors. A
module review should require congruence laws tying `len`, `file_type`,
`permissions`, and timestamp observations to the same metadata snapshot.

### Example B: `core::ptr::NonNull::addr`

Lane: `unsafe_or_representation_sensitive`

```rust
#[verifier::external_type_specification]
#[verifier::external_body]
#[verifier::reject_recursive_types(T)]
pub struct ExNonNull<T: core::marker::PointeeSized>(NonNull<T>);

pub uninterp spec fn nonnull_raw_ptr<T: core::marker::PointeeSized>(
    ptr: NonNull<T>,
) -> *mut T;

pub assume_specification<T: core::marker::PointeeSized>[
    NonNull::<T>::addr
](ptr: NonNull<T>) -> (result: NonZero<usize>)
    ensures
        result@ == nonnull_raw_ptr(ptr)@.addr,
    opens_invariants none
    no_unwind
;
```

Recorded assumptions:

- `pointer_provenance_token`
- `representation_metadata_view`
- `layout_alignment_well_formed`
- `nonnull_representation_view`

Recorded state models:

- `pointer_provenance_state`
- `layout_alignment_state`

Machine evidence:

- typecheck: pass
- determinism: `ok`, `R0 = unsat`
- anti-vacuity issues: none

Intended meaning: `NonNull::addr` returns the address component of the wrapped
raw pointer. It deliberately says nothing about dereference validity, ownership,
aliasing, allocation liveness, or the full provenance token.

Review concern: this is more useful than the `Metadata::len` example if
`nonnull_raw_ptr` is the single reviewed representation view used consistently
by `as_ptr`, `with_addr`, `cast`, and slice construction. It should not be
accepted as an isolated helper with no cross-operation laws.

## Data basis for module ranking

The table below is derived from the canonical 2,121-target
`final_candidates.csv` and `final_skip_rationale_audit.csv`.

- `Strict accepted` means the current canonical accepted set.
- `Already vstd` means exact `duplicate_existing_vstd_spec` rows and should be
  removed from new work.
- `Remaining gap` means not strictly accepted and not already covered by vstd.
- Counts are canonical target counts, not the larger source-wide module API
  counts in `results/modules.csv`.

The ranking is not sorted by gap count alone. It also weights:

1. semantic usefulness to downstream verification;
2. whether contracts can state real relations rather than merely name hidden
   values;
3. reuse of one abstraction across the module;
4. Nanvix production usage;
5. review and unsoundness cost.

## Proposed verification order

### Wave 1: pure sequence and container semantics

These modules should be reviewed first. They have concrete mathematical views,
high reuse, and comparatively low trusted-state risk.

| Rank | Module | Canonical targets | Strict accepted | Already vstd | Remaining gap | Reason |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `core::slice` | 120 | 37 | 0 | 83 | Central `Seq` semantics; large uncovered surface; many contracts can be relational and source-backed. |
| 2 | `alloc::vec` | 30 | 3 | 5 | 22 | Extremely high production use; shares the slice/sequence model; bounded ownership/capacity review. |
| 3 | `core::str` | 74 | 17 | 2 | 55 | High-value UTF-8 and substring semantics. Review ordinary methods before generic `Pattern` APIs. |
| 4 | `alloc::string` | 44 | 15 | 11 | 18 | Builds directly on the reviewed `str` model and mutation relations. |
| 5 | `core::array` | 11 | 5 | 0 | 6 | Small, useful, and a good closure point for slice/array conversion semantics. |

Recommended first concrete project: finish `core::slice` as one module, but
separate its review sections into pure sequence operations, mutable operations,
search/ordering, higher-order closure APIs, and pointer-facing APIs.

### Wave 2: algebraic types and collections

| Rank | Module | Canonical targets | Strict accepted | Already vstd | Remaining gap | Reason |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 6 | `core::option` | 27 | 8 | 0 | 19 | Fundamental proof glue; remaining higher-order and adapter laws should share one Option model. |
| 7 | `core::result` | 26 | 6 | 0 | 20 | Fundamental error-flow semantics; review branch-forwarding and panic-domain contracts together. |
| 8 | `alloc::collections::btree` | 56 | 15 | 0 | 41 | Ordered-map/set semantics are valuable and can reuse key-order and collection views. |
| 9 | `std::collections::hash` | 38 | 7 | 0 | 31 | High-value map/set operations, but requires one reviewed hash/key-model contract. |
| 10 | `alloc::collections::vec_deque` | 38 | 1 | 16 | 21 | Useful after sequence semantics; ring-buffer split state must be reviewed once for the module. |

`BinaryHeap` and `LinkedList` should not lead this wave: 19/23 BinaryHeap rows
and 13/20 LinkedList rows in the canonical target set are already exact vstd
duplicates.

### Wave 3: memory, ownership, and representation foundations

These modules are valuable but should be reviewed only after their shared
trusted vocabulary is explicit. Passing determinism is not sufficient.

| Rank | Module | Canonical targets | Strict accepted | Already vstd | Remaining gap | Review boundary |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 11 | `core::cell` | 51 | 0 | 0 | 51 | Hidden value and mutation-state laws; avoid one uninterpreted function per accessor. |
| 12 | `core::mem` | 19 | 3 | 0 | 16 | Move, initialization, discriminant, replacement, and layout semantics. |
| 13 | `core::ptr` | 109 | 0 | 1 | 108 | Review in sublayers: representation/address, metadata, provenance, then memory effects. |
| 14 | `alloc::boxed` | 15 | 0 | 0 | 15 | Allocation ownership and raw-handle conversion after pointer model approval. |
| 15 | `alloc::rc` | 28 | 0 | 0 | 28 | Allocation identity, counts, raw conversion, and Weak sentinel semantics. |
| 16 | `alloc::sync` | 30 | 0 | 0 | 30 | Arc/Weak version of the reviewed shared-allocation model. |

For `core::ptr`, representation-only contracts such as `NonNull::addr` should
be reviewed separately from dereference, copy, drop, read/write, and allocation
validity. The latter require a memory permission/ownership model, not just
pointer views.

### Wave 4: concurrency semantics

| Rank | Module | Canonical targets | Strict accepted | Already vstd | Remaining gap | Reason |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 17 | `core::sync::atomic` | 179 | 0 | 0 | 179 | High systems value, but needs reviewed value/transition/order models rather than per-method assumptions. |
| 18 | `std::sync` | 125 | 0 | 5 | 120 | Mutex/RwLock/Once/Condvar state and poison/result semantics. |
| 19 | `std::sync::mpsc` | 10 | 0 | 0 | 10 | Small coherent channel module after a queue/endpoint state model exists. |
| 20 | `std::thread` | 72 | 1 | 5 | 66 | Thread handles, joins, TLS, scheduling and blocking effects; high assumption cost. |

The existing provisional atomic results are useful prototypes, but the module
should be re-reviewed around a small set of shared laws: stored-value view,
operation transition, ordering/effect model, and pointer-storage relation.

### Wave 5: in-memory adapters before external systems

Start with APIs whose behavior can be modeled from owned in-memory state.

| Rank | Module | Canonical targets | Strict accepted | Already vstd | Remaining gap | Order inside module |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 21 | `std::io` | 62 | 0 | 0 | 62 | `Cursor`, `BufReader`, `BufWriter`, `LineWriter`, error wrappers; trait-driven external I/O later. |
| 22 | `std::ffi` | 33 | 0 | 0 | 33 | Encoded byte/string views before platform identity or leak/capacity claims. |
| 23 | `std::path` | 66 | 0 | 0 | 66 | Pure path/encoded-view operations before filesystem resolution. |

### Wave 6: OS/runtime-facing modules

These are worth specifying only after deciding the desired effect/state model.
Weak contracts that merely introduce one new uninterpreted result function per
API should not count as module verification.

Proposed order:

1. `std::fs` — 68 gaps; review snapshot metadata separately from filesystem
   transitions.
2. `std::process` — 32 gaps; builder/configuration before spawn/wait effects.
3. `std::env` — 15 gaps; process-state snapshot and mutation semantics.
4. `std::time` — 13 gaps; clock observation and duration arithmetic.
5. `std::net` — 60 gaps; socket option/state model before send/receive/bind.
6. `std::os::unix::*` — platform-specific extensions only after portable
   modules are reviewed.
7. Windows-only modules — defer unless a concrete Nanvix build path uses them.

## Modules to deprioritize

- `core::fmt` / `alloc::fmt`: most gaps are formatting side effects; 86
  non-vstd gaps in `core::fmt`, but weak hidden-option views have limited proof
  value without a formatter output model.
- `core::iter`: 78 non-vstd gaps, dominated by trait integration,
  higher-order callbacks, and prophetic iterator state.
- blanket trait modules (`core::ops`, conversion/borrow traits): define
  trait-level laws first; per-method trusted specs are not a scalable solution.
- `core::net`: all 56 canonical rows are exact existing-vstd duplicates.
- `core::time`: all 36 canonical rows are exact existing-vstd duplicates.
- duplicate-heavy modules such as `BinaryHeap`, `LinkedList`, and `alloc::ffi`
  should run exact target subtraction before any generation.
- compiler intrinsics, panic-only functions, and APIs with no modeled
  observable output should be handled only when a downstream proof requires
  them.

## Module completion contract

A module is complete only when all of the following are reviewed together:

1. A frozen module target manifest exists.
2. Exact existing-vstd targets are removed.
3. Public semantic views and trusted assumptions are listed once for the module.
4. Every remaining target has a contract or a concrete unsupported-reason record.
5. Typecheck, determinism, target binding, signature/generic shape,
   source-fidelity, and anti-vacuity checks pass.
6. Cross-operation laws are reviewed, including constructor/accessor,
   mutation/read, and conversion round trips.
7. Weak/provisional contracts remain separate from strict canonical acceptance.
8. The operator accepts or rejects the module as a unit.

## Recommended next decision

Stop treating the current 866-row provisional catalog as a queue to exhaust.
Use it as a source of candidate contracts and counterexamples. Start a fresh
module-first review with `core::slice`, followed by `alloc::vec`, then
`core::str` / `alloc::string`. These modules provide the best ratio of semantic
value to trusted-assumption risk and will establish reusable views for later
collections.
