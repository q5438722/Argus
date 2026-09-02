---
title: Nanvix Rust Std Specgen Current Progress
description: Deliverable progress snapshot for the canonical 2,121-target Rust std exec-spec rerun, accepted/skip counts, skip taxonomy, recovered surface, remaining risks, and rerun scope.
---

# Nanvix Rust Std Specgen Current Progress

## Current canonical scope

The canonical delivery is `/home/chentianyu/nanvix-rust-std-specgen-rerun-2026-08-06/specgen/all-2121-gpt56sol-fresh-20260806-0453`. It is the fresh rerun for the 2,121 pre-abstraction Nanvix-used Rust std executable API targets derived from `results/coverage-before-abstractions.csv` plus production-module membership in `results/modules.csv`; it is not the later 1,910-target post-abstraction uncovered set.

`final_verification.json`, `delivery_metadata.json`, and the wiki delivery metadata use the same current count surface:

| Metric | Count / status |
| --- | ---: |
| Manifest targets | 2,121 |
| Result rows | 2,121 |
| Final candidate rows | 2,121 |
| Missing / extra / duplicate result targets | 0 / 0 / 0 |
| Raw final `add_spec` decisions | 128 |
| Accepted semantic-gated candidates | 128 |
| Skip rows | 1,993 |
| Empty skip rationales | 0 |
| Raw non-accepted `add_spec` rows | 0 |

The 128 accepted rows all pass typecheck, guarded determinism, semantic gates, target-binding audit, signature-shape audit, generic/bounds audit, accepted contract-text safety, and accepted ensures source-fidelity audit. The 48 accepted rows with non-empty `requires` are all source-justified.

## Skip reason layering

The 1,993 skipped rows are not default failures: all have non-empty rationales, zero unclassified rows, zero unjustified rows, zero empty issue-tag rows, and zero empty combined issue/taxonomy rows. The current full skip-rationale taxonomy groups the remaining surface as follows:

| Layer | Rows | What it means for rerun/recovery |
| --- | ---: | --- |
| `runtime_or_hidden_state` | 599 | Runtime, OS, call-site, hidden mutable state, or implementation state is not publicly modeled. |
| `unsafe_or_representation_sensitive` | 267 | Contracts would need raw pointer, provenance, layout, or representation guarantees beyond current vstd vocabulary. |
| `duplicate_existing_vstd_spec` | 226 | Exact target already has trusted vstd `assume_specification`; keep as inventory skip, not a duplicate generated spec. |
| `higher_order_behavior_unmodeled` | 210 | Closure/comparator/key-extraction observations or generic callable behavior are not representable deterministically. |
| `needs_new_vstd_abstraction` | 155 | A useful contract requires adding a reusable abstraction first, such as panic-location receiver state. |
| `trait_contract_integration_gap` | 146 | Trait contract integration or projection shape is not ready for an exec-function contract. |
| `determinism_unsupported_contract_form` | 84 | The candidate shape is source-backed but the current determinism checker cannot support the required form. |
| `formatting_effect_unmodeled` | 68 | Formatting/output side effects are not modeled. |
| `iterator_or_adapter_result_gap` | 65 | Iterator/adapter result semantics need additional result-state models. |
| `no_modeled_observable_output` | 48 | The function has no useful modeled observable result in the current spec vocabulary. |
| `representation_or_allocator_model_gap` | 29 | Allocator or representation state is missing. |
| `ownership_or_uninitialized_model_gap` | 28 | Ownership, uninitialized memory, or move-state vocabulary is missing. |
| `complex_result_or_pattern_model_gap` | 26 | Complex pattern/result models are missing. |
| `associated_type_or_projection_gap` | 19 | Associated type/projection constraints cannot yet be normalized into the contract shape. |
| `clone_semantics_unmodeled` | 12 | Clone/payload behavior is not modeled tightly enough. |
| `source_unspecified_after_exhaustion` | 9 | Rust source/docs permit unspecified values after exhaustion, so deterministic contracts would over-specify. |
| `compiler_intrinsic_model_gap` | 1 | Compiler intrinsic behavior is outside the current model. |
| `one_sided_range_split_point_underdetermined` | 1 | `OneSidedRange` direction/split-index state is not modeled for `core::slice::split_off`. |

The largest active issue tags are consistent with that taxonomy: `determinism_unsupported_contract_form` (611), `classification:runtime_or_hidden_state` (494), `duplicate_vstd_assume_specification` (226), `classification:trait_contract_integration` (201), `classification:concurrency_or_hidden_state` (179), `classification:unsafe_or_representation_sensitive` (178), and `classification:needs_new_vstd_abstraction` (174). `classification:suitable_now` is inactive and should not be counted as an active issue.

## Recovered surface

The canonical rerun has no remaining unaccepted raw `add_spec` rows. Recent source-backed recoveries include ASCII and Unicode trim rows, `core::cmp::{min,max}`, `alloc::collections::BTreeSet::{last,pop_first}`, `core::result::Result::and`, `std::thread::Result::flatten`, UTF-8 checked and unchecked constructors, mutable slice/string split families, direct mutable-view adapters, Option mutable slice-array rows, mutable split-chunk tuple rows, safe slice chunk rows, map lookups/removals, `std::collections::HashMap::get_disjoint_mut`, `alloc::collections::VecDeque::binary_search`, `core::slice::binary_search`, `core::slice::reverse`, `alloc::string::String::replace_range`, `alloc::collections::LinkedList::back_mut`, and `core::array::each_mut`.

The prior-vs-fresh delta audit still needs a refresh after the `HashMap::get_disjoint_mut` recovery; the current accepted/skip counts above are authoritative for the canonical tree.

## Module-first second-pass gates

The active `core::array` module-first workspace is
`/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-array-option-string-modules-2026-08-21`.
Its accepted Array gate remains unchanged by the Option campaign.

The fresh `core::option` specification candidate is isolated under
`core/option/` in that workspace. Its live Rust 1.96 inventory contains 85
stable executable rows, including unsafe, trait, iterator, and helper APIs.
The inventory-derived partition is 26 exact-vstd, 59 generated, zero
genuinely-impossible, and zero pending rows, for 100.00% candidate strict
specification coverage. All 59 generated contracts pass standalone and merged
Verus `--no-verify`; generated feedback records 19 UNSAT, 37 UNKNOWN, and 3
unsupported/no-SMT outcomes with zero SAT. One unsupported row,
`Option::FromIterator::from_iter`, retains its raw associated-projection AIR
encoder `verus_error` while separately recording the successful standalone
typecheck.

All 85 Option targets currently use `exact-output-v1` outcome equivalence.
The generated declarations contain zero direct `external_body`; the shared
vocabulary has eight external type-specification boundaries and 43 explicit
review-candidate view/model/dependency helpers.

Independent review rejected the prior packet at SHA-256
`42e15f6f23257fc0a0de9bd9df581bc2965295b750643a7be9cf0220b0099bc8`.
That rejection is preserved unchanged in
`core/option/catalog/independent_reviewer_decision.json` at SHA-256
`0a9f802d7e5be69b23804983c5408a1a8ad25cdbbd4ca438da0f600720d77a35`.

The repaired Reviewer-ready packet is
`core/option/catalog/OPTION_SPEC_PACKET_MANIFEST.json` at SHA-256
`d0f602397d2d475eaf9454f55c29cc46c34e10a4619c363cc445016a10c41f45`.
Fresh reconstruction confirms
`85 = 26 exact-vstd + 59 generated + 0 impossible + 0 pending`. Standalone
Verus `--no-verify` passes 59/59 and the merged generated closure passes.
Feedback records 19 UNSAT, 37 UNKNOWN, three unsupported/no-SMT, and zero SAT.
Two unsupported rows are mutable-reference checker boundaries. The remaining
raw `verus_error`, `FromIterator::from_iter`, is accepted by the packet only as
an exact allowlisted AIR `IntoIterator::Item` projection encoder boundary after
its standalone declaration and semantic audits pass.

The repaired semantic gate passes 39/39 direct-postcondition target checks,
4/4 item-local Rust/vstd source comparisons, and 4/4 negative probes for
opaque-helper substitution, missing alias identity, source-branch mutation,
and exact-audit schema mutation. Both task-native structural checks pass; Array
is unchanged, the prior rejection is byte-identical, and no Option
implementation or semantic-completeness proof harness exists.

Independent review accepted the repaired packet in
`core/option/catalog/independent_reviewer_acceptance_mission-5199bd1a07e6.json`
at SHA-256
`b93e930f1a032b069e0a424ae7ce2089a1e9959d1f663c6cde2ffecd05c5a52b`.
Reviewer-fresh evidence re-derived all 85 inventory rows and 26 exact-vstd
matches, passed all 59 standalone plus the merged Verus `--no-verify`
typechecks, and explicitly retained 37 solver-UNKNOWN rows, two
mutable-reference checker boundaries, and the `FromIterator::from_iter` AIR
projection encoder boundary without treating them as implementation or
completeness proofs. The preserved rejection and accepted Array record remain
byte-identical.

The ordered Option implementation-proof campaign has now started under
`implementation_proofs/core_option/`. Its fresh bootstrap freezes only the
accepted packet, Rust 1.96 source, vstd source, audits, and reviewed
equivalence; it imports zero earlier Option proof artifacts. The inventory
baseline is 85 selected targets (59 generated and 26 exact-vstd), with 85
source/contract/equivalence target directories, four derived-or-macro source
context rows, and zero imported earlier proof outcomes.

The first representative proof gate covers `expect`, `unwrap_unchecked`,
`flatten`, and `FromIterator::from_iter`. The first three source-shaped
implementation proofs and non-restating exact-output completeness proofs pass
both Verus `--no-verify` and actual Verus. `FromIterator::from_iter` passes
`--no-verify` but is blocked in actual Verus by the exact retained
`IntoIterator::Item` undeclared AIR projection signature. Its exact-output
completeness theorem also fails, while an executable permissive interpretation
of the unconstrained collection-dependency helper verifies two distinct
`Some` outputs. Rust 1.96 `try_process` source is frozen at SHA-256
`1ca887977e92e291f2d576743ad21d8f07268c2def688589c1efb01685c585ae`;
it confirms first-residual short-circuiting and otherwise returns
`Try::from_output` of the collector result. The contract therefore needs a
source-backed functional collector model including relevant dependency
pre-state, and the exact signature needs an independently reviewed verifier
lowering. All-target generation is stopped with 81 pairs not created rather
than hiding the defect. `alloc::string` remains blocked.

The target-080 intervention now has a Reviewer candidate at
`implementation_proofs/core_option/proof_inventory/target_080_repair_packet_manifest.json`,
SHA-256
`77d544bc1a5ad9019c10099cf35217df8d525d2dc6bb2fd4aeff47354636979a`.
The verifier-facing theorem erases only the unsupported
`IntoIterator::Item = Option<A>` projection, proves over the broader
`I: IntoIterator` domain, and keeps the exact Rust bound plus explicit
`Seq<Option<A>>` adapter dependency in source/transformation manifests. The
lowered target passes fresh `--no-verify` and actual Verus.

Rather than strengthening the generic collector relation with an unreviewed
law, target 080 reopens outcome equivalence as
`from-iterator-collector-payload-v1`: `None` versus `Some` remains distinct,
while only payloads selected by arbitrary `V: FromIterator<A>` implementations
are quotiented. The candidate includes reflexivity, symmetry, transitivity,
positive, negative, and completeness proofs; fresh actual Verus verifies six
proofs with zero errors. The new overlay reports 84 exact-output bindings, one
equivalence-relative candidate, 84 unchanged frozen bindings, and one pending
independent review. The prior acceptance and failing evidence remain
preserved; module acceptance is false and all-target generation remains
blocked.

## Isolated `alloc::collections::btree_map` regeneration

The isolated Rust 1.96 `alloc::collections::btree_map` campaign is under
`nanvix-rust-std-btree-map-regeneration-20260901-v011-8798`. Its live
Rustdoc/source inventory contains 151 stable executable APIs owned by
`alloc/src/collections/btree/map.rs` and `map/entry.rs`: 13 exact-vstd rows,
137 generated contracts, one independently accepted target-specific
impossibility for reference-`Extend`, and zero pending rows. Public aliases,
inherited/default bodies, unstable APIs, and BTreeSet are excluded rather than
counted as duplicate targets.

The mandatory `specs/` interface contains the generated contracts, shared
ordered-map vocabulary, complete row reconciliation, and existing-vstd
references. Each of the 150 exact-vstd or generated targets has one directly
discoverable proof-harness directory with colocated source excerpt,
source-shaped implementation proof, relational completeness proof,
target-specific mutation proof, contract/equivalence metadata,
transformation/dependency/trust records, and separate no-verify and
actual-Verus evidence.

The accepted post-authorization matrix contains 751 completed trials with zero
failed records: one generated-spec no-verify trial plus five trials for each of
150 selected targets (implementation no-verify and actual-Verus,
completeness no-verify and actual-Verus, and mutation actual-Verus). It reports
150 verified implementation proofs, 150 verified completeness proofs, and 271
rejected target-specific mutant functions. Feedback retains 57 UNSAT, 73
UNKNOWN, and 7 not-run outcomes; all 80 checker-limitation rows are separately
resolved by actual-Verus completeness evidence, with no unresolved, SAT, or
checker-error rows after reconciliation.

Trust accounting explicitly distinguishes zero target-level `external_body`
from 336 operation-local private-operation boundaries, 12 reviewed private
representation leaf exceptions, and the non-zero trusted model surface.
Independent inventory/specification, proof/completeness, and final-aggregate
reviews are all accepted. A reviewer-round Verus no-verify build completed
without diagnostics, the campaign suite reported 36 passing tests, and the
aggregate verifier reconciled all 151 inventory rows with zero pending.

## Isolated `core::cmp` regeneration

The isolated Rust 1.96 `core::cmp` campaign is under
`nanvix-rust-std-cmp-regeneration-20260901-v011-8798`. Its live inventory and
layout gates reconcile 334 stable executable identities, 138 classified as
exact-vstd and 196 with generated specifications, with exactly one proof
harness per identity. Reviewer-round Python compilation, all 203 tests and
14,138 subtests, the inventory/specification checks, and the
result-and-mutation-required implementation checker pass. Retained two-mode
implementation and completeness evidence reports 1,336 passing Verus commands
across all 334 targets, and the mutation campaign reports 768 syntax-valid
probes rejected by actual Verus across all nine required categories.

Implementation/completeness acceptance is nevertheless withheld for a
semantic completeness defect affecting 14 `f32`/`f64` comparison identities.
Their exact-vstd contracts are only the uninterpreted `eq_ensures`,
`ne_ensures`, `partial_cmp_ensures`, and relation-specific `*_ensures`
predicates. Each paired completeness theorem adds a premise asserting that the
same accepted relation is functional for the fixed operands, which is the
generalized equality conclusion the theorem is meant to establish. Passing
Verus and mutation results therefore show consistency with that added premise,
not completeness of the accepted float contract.

Rust 1.96 source directly defines the missing observable behavior:
`partial_cmp` maps `(false, false)` to `None`, the one-sided ordered cases to
`Less` or `Greater`, and `(true, true)` to `Equal`; primitive relation methods
also expose NaN-as-false behavior. A temporary reviewer probe independently
confirmed these branches, both operand orders with NaN, equality/inequality,
and all four relation methods for both float widths. This is a repairable
contract/proof defect, not evidence that float comparison is impossible to
model. Acceptance requires source-backed float contracts that expose these
branches without a whole-result uninterpreted predicate, regenerated proof and
mutation evidence, and renewed specification plus implementation review.

## Isolated `core::result` regeneration

The isolated Rust 1.96 `core::result` campaign currently enumerates 64 stable
executable rows: 37 inherent methods and 27 concrete trait methods. Its
specification candidate partitions those rows into 10 exact-vstd references
and 54 generated contracts. Reviewer-fresh Verus `--no-verify` typechecking
passes, and the task-owned suite reports 39 passed tests plus 123 passed
subtests. This is specification-stage evidence only; no Result implementation
or completeness harness has been authorized.

The current inventory/specification gate is not accepted. Its 22
projection-relative equivalence records have no explicit stable versions or
positive/negative witnesses, and the retained feedback command, run binding,
and audit do not bind results to an equivalence version. In addition, the
`FromIterator`, `Sum`, and `Product` contracts select the first Err payload but
do not expose iterator-consumption effects. A temporary Rust 1.96 reviewer
probe measured exactly two `next` calls for each operation on
`Ok(2), Err("stop"), Ok(9)`, confirming that stopping at the first Err is
observable. This finding is a repairable contract/evidence gap, not evidence
that Result short-circuiting is absent or impossible to model.

## Remaining recovery surface and risks

The next rerun should start from the 1,993 current skip rows, not from the 128 accepted rows. The accepted subset is already closed under the current gates and should only be rechecked as part of final artifact refresh.

Priority recovery/risk families:

| Family | Current status | Risk if forced into `add_spec` too early |
| --- | --- | --- |
| `alloc::collections::VecDeque::as_mut_slices` | Source-backed skip | Exact returned split point is implementation-dependent; concatenation-only postconditions underdetermine the two returned mutable slices. |
| `RangeInclusive::{start,end}` | Source-backed skip | Rust documents accessor values as unspecified after exhaustion; deterministic contracts over-specify exhausted states. |
| Duplicate existing vstd specs | Source-backed skip | Re-adding contracts for exact vstd-covered targets duplicates trusted inventory rather than recovering missing semantics. |
| Raw pointer APIs | Source-backed skip | Useful specs require pointer/provenance/metadata representation assumptions not exposed by current vstd views. |
| `select_nth_unstable*` | Source-backed skip | Rust permits alternative partition orderings; exact final-slice contracts over-specify, while weak predicates underdetermine outputs. |
| Generic `Pattern` / `Searcher` string APIs | Source-backed skip | `Pattern`, `Searcher`, and `ReverseSearcher` matching state is not modeled, leaving last-match, repeated trim, and `None` behavior underdetermined. |
| `core::slice::split_off` | Source-backed skip | `OneSidedRange` to direction/split-index state is missing. |
| Closure-observation APIs | Source-backed skip | `FnOnce`/`FnMut` observations, comparator/key extraction, and side effects need a public closure observation model. |
| `alloc::borrow::Cow::to_mut` and `core::result::Result::as_deref_mut` | Historical canonical-rerun skip | `Cow::to_mut` still needs its mutable payload model. A newer isolated Result candidate now models `as_deref_mut`, but that package remains unaccepted for separate equivalence-binding and short-circuit evidence gaps. |
| `PanicInfo` / `PanicHookInfo::location` | Source-backed `needs_new_vstd_abstraction` skip | Requires a receiver abstraction tying public `PanicInfo`/`PanicHookInfo` state to the stored `Location` reference. |

Global system-state modeling is only justified for these shared hidden-state families. Candidate models are: ring-buffer split state for `VecDeque`, generic `Pattern`/`Searcher` state, closure observation traces, `OneSidedRange` direction/split-point state, panic-info receiver/location state, and raw-pointer metadata/provenance views. Without one of those models, the safe default is to preserve source-backed skips with explicit rationales.

## Next rerun scope

The next execution pass should rerun the current 1,993 skipped rows and preserve the 128 accepted rows as the baseline accepted set. After rerun, refresh `batch_summary.json`, `targets/*/summary.json`, `final_candidates.csv`, `accepted_semantic_candidates.{csv,json}`, `final_verification.json`, `final_skip_rationale_audit.*`, `delivery_metadata.json`, `DELIVERY_INDEX.md`, and `prior_fresh_delta/` so counts and rationale taxonomy remain consistent. Acceptance should continue to require manifest/final-candidate bijection, non-empty skip rationales, zero raw unaccepted `add_spec` rows, accepted binding/signature/generic audits, and accepted requires/ensures source-fidelity gates.
