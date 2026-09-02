---
title: Nanvix Rust Std Slice/Vec Implementation Proof Evidence
description: Measured freeze, source-body extraction, completed live 180-target scope, active final aggregate certification and package/delivery-doc admission guards after the Slice/Vec repairs, latest trust-surface reductions and retained-boundary adjudications including the accepted RawVec shrink initialized-prefix reduction, RawVec reserve post-type-invariant reduction, Vec len/capacity type-invariant production reduction, raw-slice construction current-consumer scan, Vec raw-copy storage-model, raw-read retained-boundary, RawMutSlice tail-drop, MaybeUninit-storage current consumers, fresh flattened checked-mul normal-return reduction, flattened unchecked-mul retained-boundary evidence, flattened len-overflow panic retained-boundary evidence, and get-disjoint retained-boundary evidence, Vec::extend_from_slice iterator-view, overflow-aware RawVec grow_one lowering, Vec capacity-overflow eight-helper source-panic adjudication, core::slice::align_to_mut ZST/overflow no-production-change adjudication and aligned-branch raw-parts narrowing, Vec dedup mutable pointer-add token reduction, RawVec start-pointer Vec::as_slice, Vec::as_mut_slice, Vec::as_mut_ptr, Vec::as_ptr, and the remaining Vec consumers production seeds, raw slice root `as_ptr`/`as_mut_ptr` executable start-pointer seed plus pointer-range, fixed-prefix, tail-consumer, pointer-accessor, and unchecked chunk-array retained-boundary reductions/probes with no remaining raw Slice start-pointer consumers, raw-pointer/mutable-reference/callback-trace/unstable-sort-selection UNKNOWN current-consumer bindings, Vec::clear as_mut_slice dependency, Vec::pop_if last_mut lowering, Vec retain, insert, dedup wrapper dependency, Vec::dedup PartialEq bridge, drain pointer-add, and ExtractIf constructor reductions, PartialEq observation, raw slice pointer-domain, align_to offsets view bridge, reusable raw slice/Vec pointer-model probes, raw-parts constructor, retain_mut lower-boundary probes, dedup_by reversed-callback/effect probes, sort/select private algorithm probes, and iterator as-slice/into-slice raw-parts probes, UNKNOWN evidence matrix validation, current 108/219 direct external-body surface, and CSV/JSON inventory consistency for the isolated Rust 1.96 Slice/Vec implementation-proof campaign.
---

# Nanvix Rust Std Slice/Vec Implementation Proof Evidence

The isolated implementation-proof workspace is
`/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-slice-vec-implproof-2026-08-12`.
It is separate from the canonical Rust/vstd/source checkouts and from the
completed module-first Slice, Vec, and Str workspaces.

The prerequisite `core::str` module-first task `180cfdc34b6c` is independently
reviewer-accepted, so the Slice/Vec implementation-proof campaign dependency is
satisfied.

The repaired freeze records 93 input files for the completed Slice/Vec generated
contract set. The frozen categories are 45 Rust 1.96 source body files, 4 vstd
definition files, 8 contract/vocabulary files, 10 catalog files, 10
module-inventory files, 4 source-provenance files, 4 canonical survey snapshot
files, and 8 verification-audit files. The additional source-body coverage
includes adjacent Rust source references outside the copied slice subtree.

The original proof inventory contained 144 generated targets: 120 generated
`core::slice` contracts and 24 generated `alloc::vec` contracts. The current
manager-corrected live scope is reconciled to 180 implementation-proof
obligations: those 144 generated rows plus 36 exact existing-vstd rows (12 Slice
and 24 Vec). `Vec::splice` remains outside the count because it has no contract.
`proof_inventory/targets_180.{json,csv}` is the explicit live alias, while the
legacy `targets_144.{json,csv}` filenames are compatibility mirrors with the same 180
rows. The 36 exact-vstd rows are appended after the generated rows; after
`alloc::vec::Vec::with_capacity`, no Rust-body implementation proof remains pending.

All 180 live targets have source-backed body extraction, a bottom-up proof-order
row, a source-to-harness transformation manifest, a dependency/assumption
manifest, and a target-local harness artifact preserving the Rust 1.96 body and
contract intent. The local post-proof aggregate gate currently reports 180
targets, including 36 exact-vstd obligations; after the Slice mutable-iterator
final-frame repair, reverse-chunk exact-empty refresh, exact-empty artifact
refresh, fixed-array chunk elementwise refresh, post-sync executable
declaration refresh, mutable fixed-array final-subrange refresh, immutable
exact-chunk constructor-invariant reduction, mutable exact-chunk remainder
adjudication, unchecked-split `unchecked_sub` arithmetic reduction, and the
reviewed singleton-array, unreachable-panic, and prefix fixed-array
retained-boundary no-production-change adjudications, the Slice PartialEq
observation bridge adjudication, and the Vec reserve-caller initialized-prefix
reduction, it reports B=180, pending=0, and no next pending target.
The current active aggregate certification is `20260817T1200Z`, selected by
`proof_inventory/active_aggregate_certification.json` and backed by
`proof_inventory/rangebounds_normalization_retry_20260817T0613Z/summary.json`
plus later selected-certification evidence including
`proof_inventory/vec_pop_capacity_invariant_reduction_20260817T0823Z/summary.json`,
`proof_inventory/vec_capacity_overflow_eight_helper_adjudication_20260817T1012Z/summary.json`,
`proof_inventory/vec_dedup_ptr_add_token_reduction_20260817T1104Z/summary.json`,
and `proof_inventory/flattened_checked_mul_expect_reduction_20260817T1133Z/summary.json`.
The capacity-overflow packet is reviewed no-production-change evidence for the
retained Vec abort helpers; the dedup ptr-add packet removes the Vec dedup-family
mutable pointer-add token helper; and the flattened checked-mul packet removes
the checked-multiply normal-return helper while preserving the overflow-panic
edge. The aggregate admission
gate also validates the active Slice feedback determinism run, B16/B20/A7
package manifests and CROSSWALKs, and the paired incompleteness delivery package
against that active certification. The package-local saved validation capture
has been refreshed with no failures, empty stderr, and exit code `0`. Older
paragraphs on this page may mention the active certification that was current at
their individual admission point.
The integrated admission evidence over the B16/B20/A7 package validators, their
package spec typechecks, actual Verus `--crate-type=lib` copied-harness checks,
live-scope reconcile, aggregate gate, incompleteness build/validate/classify/
UNKNOWN/package chain, and original Slice catalog/integrity checks remains
passing. After the Vec dedup mutable pointer-add token reduction, the later
`alloc::vec::Vec::{as_slice,as_mut_slice,as_mut_ptr,as_ptr}` plus remaining-consumer RawVec start-pointer production seeds,
and the raw Slice root, pointer-range, fixed-prefix, tail-consumer, and
pointer-accessor executable start-pointer reductions, the
current aggregate gate reports B=180, pending=0, exact-vstd=36,
direct external-body surface 108/219,
144 generated incompleteness rows, checker split 63 UNSAT / 81
UNKNOWN, and no unsupported, no-target, missing-artifact, or semantic-mismatch
drift.

The later `raw_slice_start_pointer_tail_consumers_20260818T0802Z` packet ports the executable raw Slice start-pointer model into the remaining 15 `rust_1_96_slice_as_ptr_cast` / `rust_1_96_slice_as_mut_ptr_cast` consumers (`as_chunks`, `as_chunks_mut`, `as_chunks_unchecked`, `as_chunks_unchecked_mut`, `as_flattened`, `as_flattened_mut`, `element_offset`, `rotate_left`, `rotate_right`, `split_at_checked`, `split_at_mut_checked`, `split_at_mut_unchecked`, `split_at_unchecked`, `subslice_range`, and `swap_with_slice`). All changed harnesses pass both Verus modes; lower raw-parts, array-cast, pointer-add, rotate/swap, intrinsic/panic, pointer-domain, and final-frame boundaries remain retained. At that packet's admission point, the direct external-body surface was 108/224 with Slice 77/154 and Vec 31/70. Evidence: `proof_inventory/raw_slice_start_pointer_tail_consumers_20260818T0802Z/summary.json`.

The later `raw_parts_helper_current_consumer_refresh_20260818T0847Z` packet rechecks the live raw-parts constructor and split helper family after the post-start-pointer reductions. Representative no-external probes for `core::slice::{from_raw_parts,from_raw_parts_mut,split_at_unchecked,split_at_mut_unchecked}` still fail during `--crate-type=lib --no-verify`: constructors hit unsupported raw-pointer dereference through `core::ptr::slice_from_raw_parts(_mut)`, and split helpers hit unsupported immutable/mutable `ptr.add`. Production representatives pass both Verus modes with public contracts unchanged, so the raw-parts/provenance boundaries remain retained and the then-current direct external-body surface stayed 108/224. Evidence: `proof_inventory/raw_parts_helper_current_consumer_refresh_20260818T0847Z/summary.json`.

The later `slice_pointer_accessor_current_reduction_20260818T1005Z` packet ports the accepted raw Slice null-provenance len-address start-pointer model into the remaining `rust_1_96_slice_as_ptr` / `rust_1_96_slice_as_mut_ptr` helpers in `core::slice::{align_to,align_to_mut,copy_from_slice,copy_within}`. Public contracts are unchanged; lower `align_offset`, `ptr.add`, raw-copy, raw-parts, and final-frame/effect boundaries remain retained. Harnesses 008, 009, 145, and 146 pass both `--crate-type=lib --no-verify` and actual `--crate-type=lib`, and the current direct external-body surface is 108/219 with Slice 77/149 and Vec 31/70. Evidence: `proof_inventory/slice_pointer_accessor_current_reduction_20260818T1005Z/summary.json`.

The later `align_to_mut_raw_parts_branch_reduction_20260818T1127Z` packet narrows `core::slice::align_to_mut`'s aligned-branch boundary: `rust_1_96_align_to_mut_split_offsets_raw_parts` is no longer `external_body` and now executes `split_at_mut(offset)`, `rest.len()`, and the executable mutable Slice start-pointer model with the already computed `offset`, `us_len`, and `ts_len`. The retained lower helper `rust_1_96_align_to_mut_from_split_raw_parts` covers only `from_raw_parts_mut`, raw-pointer provenance/aliasing, and generated-contract final-frame facts; public contract, `ptr_align_offset`, `align_to_offsets_mul_fits`, and ZST/overflow handling are unchanged. The harness passes both Verus modes with actual `8 verified, 0 errors`, the refreshed incompleteness package validates, and the aggregate remains B=180, pending=0, exact-vstd=36, external_body_surface=108/219, and unused external-body declarations 0. Evidence: `proof_inventory/align_to_mut_raw_parts_branch_reduction_20260818T1127Z/summary.json`.

The later `fixed_array_cast_reference_probe_20260818T1048Z` packet rechecks the retained fixed-prefix array cast/reference helpers after the accepted raw Slice start-pointer model reached `core::slice::{as_array,as_mut_array,first_chunk,first_chunk_mut,split_first_chunk,split_first_chunk_mut}`. Evidence-local no-external copies for the six prefix consumers still fail `--crate-type=lib --no-verify` on unsupported raw pointer dereference at `unsafe { &*ptr }` / `unsafe { &mut *ptr }`; a representative cast-only probe also fails on unsupported `ptr.cast_array` unless a new assume-specification is introduced. Production is unchanged, all six production harnesses pass both Verus modes, and the aggregate remains B=180, pending=0, exact-vstd=36, external_body_surface=108/219, and unused_external_body_decls=0. The optional `as_flattened` / `as_flattened_mut` array-cast relation helpers were left unchanged because the shared source-shaped fixed-array cast/reference step did not typecheck. Evidence: `proof_inventory/fixed_array_cast_reference_probe_20260818T1048Z/summary.json`.

The later `unchecked_chunk_array_current_reduction_20260818T1105Z` packet rechecks the retained unchecked chunk-array helpers for `core::slice::{as_chunks,as_chunks_mut,as_chunks_unchecked,as_chunks_unchecked_mut,as_rchunks,as_rchunks_mut}`. Evidence-local no-external copies for `as_chunks_unchecked`, `as_chunks_unchecked_mut`, `rust_1_96_as_chunks_unchecked_view`, `rust_1_96_as_chunks_unchecked_mut_view`, `rust_1_96_ptr_cast_array_chunks`, `rust_1_96_mut_ptr_cast_array_chunks`, `rust_1_96_from_raw_parts_array_chunks`, and `rust_1_96_from_raw_parts_mut_array_chunks` still fail during `--crate-type=lib --no-verify` on unsupported direct unchecked chunk calls, raw pointer casts, raw pointer dereference, or mutable array raw-parts construction. Production is unchanged, all six affected production harnesses pass both Verus modes, and the aggregate checker now validates the packet while preserving B=180, pending=0, exact-vstd=36, external_body_surface=108/219, and unused_external_body_decls=0. Evidence: `proof_inventory/unchecked_chunk_array_current_reduction_20260818T1105Z/summary.json`.

The later `vec_raw_read_current_consumer_refresh_20260818T0900Z` packet rechecks the live `alloc::vec::Vec::{pop_if,pop,remove,swap_remove}` raw `ptr::read` consumers after the later trust-surface reductions. Evidence-local copies generated from the current production harnesses remove only the target-local `#[verifier::external_body]` annotation on the unsafe `read<T>` helper; all four copies still fail both Verus modes before proof obligations on unsupported `core::ptr::read`. The unchanged production representatives pass both `--crate-type=lib --no-verify` and actual `--crate-type=lib` with `13/8/12/10 verified, 0 errors`; at that packet's admission point the aggregate gate reported B=180, pending=0, exact-vstd=36, direct external-body surface 108/224, and unused external-body declarations 0. Evidence: `proof_inventory/vec_raw_read_current_consumer_refresh_20260818T0900Z/summary.json`.

The later `get_disjoint_current_consumer_refresh_20260818T0957Z` packet rechecks `core::slice::{get_disjoint_mut,get_disjoint_unchecked_mut}` against the then-active 108/224 retained external-body surface. Evidence-local copies generated from the current production harnesses remove only the target-local `get_disjoint_check_valid` or `rust_1_96_fill_disjoint_mut_array_and_assume_init` annotation under test; all three copies pass `--crate-type=lib --no-verify` but fail actual Verus: `get_disjoint_check_valid` cannot prove the abstract Ok postcondition, and both fill/assume-init consumers fail the `MaybeUninit::assume_init` precondition. The unchanged production representatives pass both Verus modes with `5 verified, 0 errors` for harness 051 and `4 verified, 0 errors` for harness 052; at that packet's admission point the aggregate gate reported B=180, pending=0, exact-vstd=36, direct external-body surface 108/224, and unused external-body declarations 0. Evidence: `proof_inventory/get_disjoint_current_consumer_refresh_20260818T0957Z/summary.json`.
The later reviewed Vec callback/Clone determinism retry
`callback-trace-retry-20260818T0315Z` preserves
`alloc::vec::Vec::{dedup,dedup_by,dedup_by_key,extend_from_within,pop_if,resize_with,retain,retain_mut}`
as real feedback-pipeline `status=ok` / `r0_z3=unknown` evidence, with
candidate dictionaries, `__rust_std_candidate` synthetic specs, det
specs/harnesses, Verus output, schema-search evidence, SMT files, and full
result JSON for all eight focused targets. The associated reviewer rerun kept
the regenerated incompleteness package and native gates passing: 144 analysis
rows, 144 classification rows, 81 UNKNOWN rows, package `failures=[]`,
implproof aggregate B=180/pending=0/exact-vstd=36, and Vec inventory,
provenance, catalog, contracts, and artifact-integrity gates all exited 0.
The later `proof_inventory/flattened_checked_mul_expect_reduction_20260817T1133Z/summary.json`
packet removes `#[verifier::external_body]` from `rust_1_96_checked_mul_expect`
in `core::slice::{as_flattened,as_flattened_mut}` and
`alloc::vec::Vec::into_flattened`; the checked-multiply normal return is
executable, only the source overflow panic edge remains isolated, `unchecked_mul`
and raw pointer/provenance boundaries are unchanged. At that packet's admission
point the aggregate gate remained B=180, pending=0, exact-vstd=36,
external_body_surface=113/264, and unused_external_body_decls=0; after the later
`Vec::{as_slice,as_mut_slice,as_mut_ptr,as_ptr}` RawVec start-pointer production
seeds, the then-live surface was 111/260 before the later remaining-consumer
reduction moved the surface to 110/249 and the later raw Slice root,
pointer-range, fixed-prefix, and tail-consumer reductions moved the current
surface to 108/224.
The later `proof_inventory/flattened_unchecked_mul_reduction_20260817T1220Z/summary.json`
packet is a no-production-change adjudication for the same three flattened
targets. Removing only `#[verifier::external_body]` from each
`rust_1_96_unchecked_mul` helper while preserving the executable
`unsafe { lhs.unchecked_mul(rhs) }` body fails Verus `--crate-type=lib
--no-verify` for all three target harnesses because executable
`core::num::<impl usize>::unchecked_mul` is outside the current Verus std
surface and Verus suggests an `assume_specification` for that std function.
Production remains restored with public contracts unchanged: the three
flattened harnesses pass `--crate-type=lib --no-verify` and actual
`--crate-type=lib` Verus, with actual proofs reporting 6/0, 6/0, and 5/0
verified/errors respectively. At that packet's admission point the aggregate
gate remained B=180, pending=0, exact-vstd=36, external_body_surface=113/264,
and unused_external_body_decls=0; after the later `Vec::{as_slice,as_mut_slice}` RawVec
start-pointer production seeds and the later pointer-accessor projection seed,
the then-live surface was 111/260 before the later remaining-consumer reduction
moved the surface to 110/249 and the later raw Slice root, pointer-range,
fixed-prefix, and tail-consumer reductions moved the current surface to
108/224.
The later `proof_inventory/flattened_len_overflow_panic_adjudication_20260817T1241Z/summary.json`
packet is a no-production-change adjudication for the remaining source
overflow-panic edge in those three flattened targets. Evidence-local copies that
remove only `#[verifier::external_body]` from
`rust_1_96_slice_len_overflow_panic` / `rust_1_96_vec_len_overflow_panic` and
preserve the exact `panic!("slice len overflow")` / `panic!("vec len overflow")`
bodies fail Verus `--crate-type=lib --no-verify` and actual
`--crate-type=lib` before proof obligations run because `panic!` lowers to
unsupported `core::panicking::panic_fmt`,
`std::fmt::Arguments::from_str`, and `core::fmt::Arguments`. Production remains
unchanged with public contracts unchanged: the three flattened harnesses pass
`--crate-type=lib --no-verify` and actual `--crate-type=lib` Verus, with actual
proofs reporting 6/0, 6/0, and 5/0 verified/errors respectively. At that
packet's admission point the aggregate gate remained B=180, pending=0,
exact-vstd=36, external_body_surface=113/264, and unused_external_body_decls=0;
after the later `Vec::{as_slice,as_mut_slice}` RawVec start-pointer production
seeds the then-live surface was 113/262, and the later pointer-accessor seed
moved the then-live surface to 111/260 before the later remaining-consumer
reduction moved the surface to 110/249 and the later raw Slice root,
pointer-range, fixed-prefix, and tail-consumer reductions moved the current
surface to 108/224.
The later `proof_inventory/rawvec_start_pointer_model_seed_20260817T1306Z/summary.json`
packet is a no-production-change model seed for
`alloc::vec::Vec::{as_slice,as_mut_slice,pop}`. Its evidence-local combined probe
does more than remove the old empty RawVec start-pointer bridge: it defines
`raw_ptr_initialized_seq` / `raw_mut_ptr_initialized_seq`, closed
`raw_vec_initialized_seq` and `raw_vec_capacity` field projections, and
`vec_start_ptr` / `vec_start_mut_ptr` relations derived from those projections.
The probe keeps the lower raw aggregate-slice and `ptr::read` boundaries
unchanged, passes Verus `--crate-type=lib --no-verify` and actual
`--crate-type=lib` with `verification results:: 12 verified, 0 errors`, and the
unchanged aggregate gate remained B=180, pending=0, exact-vstd=36,
external_body_surface=113/264, and unused_external_body_decls=0.

The later
`proof_inventory/rawvec_start_pointer_as_slice_production_seed_20260817T1316Z/summary.json`
packet ports that closed RawVec start-pointer projection into the production
`alloc::vec::Vec::as_slice` harness. It removes the local
`rust_1_96_rawvec_start_ptr_boundary` external-body helper while retaining the
lower aggregate raw-pointer slice boundary and preserving the public contract.
Reviewer-rerun Verus `--crate-type=lib --no-verify`, actual Verus
`--crate-type=lib`, and `python3 tools/check_implproof_aggregate.py --root ..`
all exit 0; actual Verus reports 2 verified / 0 errors. At that packet's
admission point the aggregate reported B=180, pending=0, exact-vstd=36,
external_body_surface=113/263, unused_external_body_decls=0, split Slice 79/179
and Vec 34/84; the later as_mut_slice seed below moved the then-current surface
to 113/262, and the pointer-accessor seed moved the then-current surface to
111/260 before the remaining-consumer reduction moved the current surface to
110/249.

The later
`proof_inventory/rawvec_start_pointer_as_mut_slice_production_seed_20260818T0400Z/summary.json`
packet ports the same closed mutable RawVec start-pointer projection into the
production `alloc::vec::Vec::as_mut_slice` harness. It removes the local
`rust_1_96_rawvec_start_mut_ptr_boundary` external-body helper while retaining
the lower aggregate raw-pointer mutable-slice boundary and preserving the
existing-vstd public contract. Verus `--crate-type=lib --no-verify`, actual
Verus `--crate-type=lib`, and the aggregate gate all exit 0; actual Verus
reports 2 verified / 0 errors, and at that packet's admission point the
aggregate reported B=180,
pending=0, exact-vstd=36, external_body_surface=113/262,
unused_external_body_decls=0, split Slice 79/179 and Vec 34/83.

The later
`proof_inventory/rawvec_start_pointer_vec_pointer_accessors_20260818T0430Z/summary.json`
packet ports the same RawVec field-projection model into production
`alloc::vec::Vec::{as_mut_ptr,as_ptr}`. It removes both retained
`RawVecInner::ptr` external-body helpers while preserving the generated public
start-pointer contracts. Verus `--crate-type=lib --no-verify`, actual Verus
`--crate-type=lib`, and the aggregate gate all exit 0; each actual Verus run
reports 1 verified / 0 errors, and the live aggregate reports B=180,
pending=0, exact-vstd=36, external_body_surface=111/260,
unused_external_body_decls=0, split Slice 79/179 and Vec 32/81.

The later
`proof_inventory/rawvec_start_pointer_remaining_consumers_20260818T0512Z/summary.json`
packet ports the accepted RawVec start-pointer projection into the remaining
current consumers `alloc::vec::Vec::{clear,insert,insert_mut,pop,pop_if,push,
push_mut,spare_capacity_mut,split_off}`. It removes the local
`rust_1_96_rawvec_start_ptr_boundary` / `rust_1_96_rawvec_start_mut_ptr_boundary`
bridge stubs, preserves public contracts, keeps `split_off` on the reviewed
ghost copy-storage model with a capacity-derived start relation, and reruns
each changed harness through Verus `--crate-type=lib --no-verify` and actual
`--crate-type=lib` with 0 errors. At that packet's admission point, the
aggregate gate exited 0 with B=180, pending=0, exact-vstd=36,
external_body_surface=110/249, unused external-body declarations 0, split Slice
79/179 and Vec 31/70.

The later
`proof_inventory/raw_slice_start_pointer_root_seed_20260818T0628Z/summary.json`
packet ports an executable null-provenance, length-address model into the root
`core::slice::{as_ptr,as_mut_ptr}` harnesses. It removes the target-local
`#[verifier::external_body]` annotations from
`rust_1_96_slice_as_ptr_cast` and `rust_1_96_slice_as_mut_ptr_cast` only in
those two root targets, preserves the public start-pointer contracts, and keeps
the unsupported literal slice-to-thin-pointer cast out of production. Both root
harnesses pass `--crate-type=lib --no-verify` and actual `--crate-type=lib`.
After the later pointer-range consumer reduction, the then-current aggregate
gate exited 0 with B=180, pending=0, exact-vstd=36,
external_body_surface=108/245, unused external-body declarations 0, split Slice
77/175 and Vec 31/70, with 10 immutable and 11 mutable raw Slice
start-pointer consumers remaining.

The later
`proof_inventory/raw_slice_start_pointer_range_consumers_20260818T0711Z/summary.json`
packet ports the same executable root start-pointer model into
`core::slice::{as_ptr_range,as_mut_ptr_range}`. It removes only the local
`rust_1_96_slice_as_ptr_cast` / `rust_1_96_slice_as_mut_ptr_cast`
`#[verifier::external_body]` markers in those two range consumers; their lower
pointer-add range-end helpers remain retained, public contracts are unchanged,
and both harnesses pass `--crate-type=lib --no-verify` and actual
`--crate-type=lib`.

The later
`proof_inventory/raw_slice_start_pointer_fixed_prefix_consumers_20260818T0733Z/summary.json`
packet ports the same executable null-provenance, length-address start-pointer
model into `core::slice::{as_array,as_mut_array,first_chunk,first_chunk_mut,split_first_chunk,split_first_chunk_mut}`.
It removes only those six targets' local
`rust_1_96_slice_as_ptr_cast` / `rust_1_96_slice_as_mut_ptr_cast`
`#[verifier::external_body]` markers. The lower array-cast, array-reference,
split/raw-parts, and mutable final-frame boundaries remain retained, public
contracts are unchanged, and all six harnesses pass `--crate-type=lib
--no-verify` and actual `--crate-type=lib`. After the later tail-consumer and
pointer-accessor packets, the current aggregate gate exits 0 with B=180,
pending=0, exact-vstd=36, external_body_surface=108/219, unused external-body
declarations 0, and no remaining raw Slice start-pointer consumers.

The active implproof aggregate checker treats the audit `current` and
`current_external_body_surface` objects, the active aggregate selector
`selection_reason`, the root/proof-inventory `*.latest.stdout` and
`*.latest.stderr` aliases, the `TRUST_BOUNDARY_AUDIT.md` headline table, and
active audit verification prose as current-facing. It rejects stale 120/280,
115/270, 115/272, 113/264, Vec 41/101, Vec 36/91, Vec 36/93, or Vec 34/85 claims in those active
fields/prose/captures, and also rejects stale current 111/260 or Vec 32/81
claims after the remaining-consumer RawVec start-pointer reduction, stale
current 110/249 or Slice 79/179 claims after the raw Slice root start-pointer
seed, stale current 108/245 or Slice 77/175 claims after the fixed-prefix
consumer reduction, and stale current 108/239, 108/247, or Slice 77/177 claims
after the tail-consumer reduction, while
preserving stale surface references only when
explicitly framed as historical evidence; Markdown line wrapping across
adjacent lines is normalized before the current-facing stale-surface check.

The reviewed no-production-change
`proof_inventory/array_chunk_subslice_views_probe_20260817T0205Z/summary.json`
packet confirms the `array_chunk_subslice_views` subgroup needs no additional
production edit: `core::slice::{as_chunks,as_chunks_mut,as_chunks_unchecked,
as_chunks_unchecked_mut,as_rchunks,as_rchunks_mut}` all retain executable
source-shaped public target bodies, not `external_body` or
`assume_specification` stubs. The probe reruns each affected harness with Verus
`--crate-type=lib --no-verify` and actual `--crate-type=lib`; actual Verus
reports 5 verified / 0 errors for the four `as_chunks*` targets and 1 verified /
0 errors for the two `as_rchunks*` targets. The same packet records clean
live-scope reconcile and aggregate admission at B=180, pending=0, exact-vstd=36,
external_body_surface=118/278, and unused_external_body_decls=0.

The superseded `20260816T2331Z` aggregate certification is preserved as historical evidence; the later `20260817T0016Z` promotion adds the reviewed d88 raw-slice `as_mut_ptr` start-pointer binding for `core::slice::{rotate_left,rotate_right,swap_with_slice}` without changing contracts, proof dispositions, or checker counts.
That promotion preserved the then-recorded 121/290 external-body surface; the later `vec_len_capacity_type_invariant_production_20260817T0103Z` reduction moved the surface to 121/281, `rawvec_reserve_exact_try_reserve_invariant_reduction_20260817T0340Z` moved it to 118/278 after the intervening `rawvec_reserve_grow_capacity_post_type_invariant_20260817T0240Z` reserve/grow reduction, and the RawVec shrink plus Vec reserve-caller initialized-prefix reductions moved it to 115/275.
The `20260817T0613Z` aggregate first incorporated the RangeBounds normalization retry and moved the surface to 115/272.
The later overflow-aware RawVec grow-one production reduction kept the surface at 115/272 while replacing the four whole `RawVec::grow_one` external bodies in `alloc::vec::Vec::{insert_mut,push_mut,insert,push}` with executable normal-return capacity increments plus a narrower retained `capacity_overflow` abort boundary; the later Vec pop/pop_if capacity-boundary reduction moved the surface to 115/270, `proof_inventory/vec_tail_raw_slice_constructor_reduction_20260817T0845Z/summary.json` moved the surface to 113/267 by making the three Vec tail `ptr::slice_from_raw_parts_mut` wrappers executable, and `proof_inventory/vec_dedup_ptr_add_token_reduction_20260817T1104Z/summary.json` moved the then-current surface to 113/264 by making the three Vec dedup-family `rust_1_96_ptr_add_mut` wrappers executable.
The subsequent flattened checked-mul reduction kept the literal surface at 113/264 because each target replaces the checked-multiply external body with an executable helper plus a narrow source overflow-panic helper.
The subsequent flattened len-overflow panic adjudication kept that same surface because direct `panic!` formatting remains outside the current Verus std surface, so the target-local panic helpers stay as the narrow retained boundary. The later RawVec start-pointer `Vec::{as_slice,as_mut_slice,as_mut_ptr,as_ptr}` production seeds moved the then-live surface to 111/260 before the remaining-consumer reduction moved the surface to 110/249 and the later raw Slice root, pointer-range, fixed-prefix, and tail-consumer reductions moved the current
surface to 108/224.

The `raw_slice_construction_current_consumers_20260817T0136Z` packet refreshes the live raw-slice construction consumer view.
The historical packet used the then-recorded 121/281 surface. It scans `proof_harnesses/*/harness.rs` for direct `core::slice::from_raw_parts` / `core::slice::from_raw_parts_mut` call sites and related constructor, split, and Vec aggregate raw-slice helpers; records 17 direct call-site harnesses plus the two public constructor boundary harnesses; reruns all 19 affected production harnesses with Verus `--crate-type=lib --no-verify` and actual `--crate-type=lib`; leaves production harnesses and public contracts unchanged; and preserves packet-local historical reconcile/aggregate captures at B=180, pending=0, exact-vstd=36, external_body_surface=121/281, and unused_external_body_decls=0.

The superseded `20260817T0016Z` certification refresh additionally binds the
reviewed evidence directories through the post-1550 set and the rchunks
unchecked source-fidelity repair:
`vec_append_initialized_prefix_bridge_adjudication_20260816T0811Z`,
`vec_push_mut_len_capacity_invariant_adjudication_20260816T0822Z`,
`vec_spare_capacity_raw_parts_boundary_reduction_20260816T0831Z`,
`split_off_raw_copy_effect_adjudication_20260816T0843Z`,
`is_sorted_by_key_source_shaped_reduction_20260816T0938Z`,
`vec_into_flattened_rawparts_boundary_reduction_20260816T0955Z`,
`vec_retain_readonly_callback_bridge_adjudication_20260816T1011Z`,
`vec_return_ref_reconstruction_boundary_20260816T1020Z`,
`raw_slice_pointer_provenance_model_adjudication_20260816T1028Z`,
`vec_pop_lower_boundary_narrowing_20260816T1038Z`,
`vec_extend_from_slice_iter_view_reduction_20260816T1116Z`,
`vec_grow_one_capacity_growth_adjudication_20260816T1144Z`,
`rawvec_start_pointer_boundary_current_consumers_20260816T1158Z`,
`raw_slice_start_pointer_current_consumers_20260816T1227Z`,
`vec_raw_copy_storage_model_probe_20260816T1253Z`,
`vec_rawmut_tail_drop_boundary_reduction_20260816T1310Z`,
`vec_compaction_storage_drop_bridge_probe_20260816T1426Z`,
`vec_push_insert_raw_write_token_reduction_20260816T1506Z`,
`slice_partialeq_observed_bridge_adjudication_20260816T1550Z`,
`immutable_split_raw_parts_helper_adjudication_20260816T1712Z`,
`mutable_split_raw_parts_helper_adjudication_20260816T1728Z`,
`vec_raw_read_storage_model_boundary_adjudication_20260816T1823Z`,
`raw_parts_constructor_boundary_refresh_20260816T1841Z`,
`vec_reserve_capacity_current_consumers_20260816T1936Z`,
`raw_copy_current_consumers_20260816T1957Z`,
`fixed_array_current_consumers_20260816T2008Z`,
`iterator_subslice_unknown_current_consumers_20260816T2037Z`,
`raw_pointer_provenance_unknown_current_consumers_20260816T2053Z`,
`mutable_reference_view_unknown_current_consumers_20260816T2112Z`,
`callback_trace_unknown_current_consumers_20260816T2123Z`,
`unstable_sort_selection_unknown_current_consumers_20260816T2133Z`,
`maybeuninit_storage_current_consumers_20260816T2246Z`, and
`rchunks_unchecked_source_fidelity_20260816T2306Z`: B=180, pending=0,
exact-vstd=36, generated rows=144, checker split 63 UNSAT / 81 UNKNOWN, and
then-direct external-body surface 121 harnesses / 290 occurrences.
Historical `20260815T0501Z`
certification paths are allowed only in preserved historical-certification
lists; active surfaces reject stale `0501`, unsupported/no-target, and
`0 exec ensures targets` markers.

The current aggregate admission surface is 113 harnesses / 262
`external_body` occurrences, split Slice 79/179 and Vec 34/83, after the
RawVec start-pointer `Vec::{as_slice,as_mut_slice}` production seeds. The earlier Vec dedup
mutable pointer-add token reduction
`proof_inventory/vec_dedup_ptr_add_token_reduction_20260817T1104Z/summary.json`
removes the harness-local `rust_1_96_ptr_add_mut` external-body annotations from
`alloc::vec::Vec::{dedup,dedup_by,dedup_by_key}` while preserving the source-shaped
dedup control flow, callback ordering, and retained lower raw-pointer/copy/drop/
effect-summary boundaries. The preceding Vec tail raw-slice constructor reduction
`proof_inventory/vec_tail_raw_slice_constructor_reduction_20260817T0845Z/summary.json`
removes the harness-local `ptr::slice_from_raw_parts_mut` external-body
annotations from `alloc::vec::Vec::{resize_with,resize,truncate}` while leaving
their `RawMutSlice { ptr, len }` construction executable. The preceding
RangeBounds normalization retry
`proof_inventory/rangebounds_normalization_retry_20260817T0613Z/summary.json`
removes the target-local `slice::range` external-body annotations from
`alloc::vec::Vec::{drain,extend_from_within,extract_if}` and makes all four
affected helpers, including `core::slice::copy_within`, execute the Rust 1.96
checked `start_bound` / `end_bound` normalization. The four production harnesses
pass both Verus modes; `copy_within` keeps only a narrow proof bridge back to the
existing `slice_range_start` / `slice_range_end` contract vocabulary. The preceding
RawVec shrink initialized-prefix/type-invariant packet
`proof_inventory/rawvec_shrink_initialized_prefix_reduction_20260817T0410Z/summary.json`
ports the Ghost initialized-prefix/type-invariant model into
`alloc::vec::Vec::{into_boxed_slice,shrink_to,shrink_to_fit}` production
harnesses: their target-local `RawVec::shrink_to_fit` helpers now execute by
shrinking modeled capacity while preserving the Ghost initialized-prefix/storage
model, with no public contract changes. The affected harnesses 134, 173, and
174 pass both Verus `--crate-type=lib --no-verify` and actual
`--crate-type=lib`, and its live reconcile/aggregate gate reported B=180,
pending=0, exact-vstd=36, unused external bodies zero, and
external_body_surface=115/275. The preceding
Vec reserve-caller initialized-prefix packet
`proof_inventory/vec_reserve_callers_initialized_prefix_reduction_20260817T0455Z/summary.json`
removes the target-local whole-method `Vec::reserve` `external_body`
annotations from `alloc::vec::Vec::{extend_from_within,append,extend_from_slice}`:
each caller now executes a RawVec Ghost initialized-prefix/capacity update and
retains only the source-shaped `capacity_overflow` abort boundary plus existing
lower raw/storage/clone boundaries. Harnesses 130, 157, and 162 pass both
Verus `--crate-type=lib --no-verify` and actual `--crate-type=lib`
(`9`, `9`, and `14` verified, respectively), and the then-current direct external-body
surface remains 115/275. The later eight-helper source-panic adjudication
`proof_inventory/vec_capacity_overflow_eight_helper_adjudication_20260817T1012Z/summary.json`
probes all retained capacity-overflow abort helpers in harnesses 130, 133,
139, 157, 162, 163, 168, and 171: removing only
`#[verifier::external_body]` and using the Rust 1.96
`panic!("capacity overflow")` body fails `--crate-type=lib --no-verify` for all
eight copies because Verus rejects `core::panicking::panic_fmt` and
`core::fmt::Arguments::from_str` / `core::fmt::Arguments`. The production
harnesses were left unchanged and rerun in both Verus modes; all eight pass
actual verification (`12`, `12`, `7`, `9`, `14`, `12`, `8`, and `2` verified,
respectively), and at that point the aggregate gate remained B=180, pending=0,
exact-vstd=36, external_body_surface=113/267, and
unused_external_body_decls=0; later Vec dedup mutable pointer-add and RawVec
start-pointer `Vec::{as_slice,as_mut_slice}` reductions move the current active surface to
113/262. The earlier
four-helper packet
`proof_inventory/vec_capacity_overflow_abort_probe_20260817T0602Z/summary.json`
is the predecessor evidence for harnesses 130, 157, 162, and 171. A separate
Slice `align_to_mut` ZST/overflow adjudication
`proof_inventory/align_to_mut_zst_overflow_adjudication_20260817T1046Z/adjudication_result.json`
copies the target harness and replaces only
`rust_1_96_align_to_mut_zst_or_overflow` with the Rust 1.96-shaped
`(slice, &mut [], &mut [])` branch. The probe typechecks with
`--crate-type=lib --no-verify`, but actual Verus rejects the
`slice_align_to_mut_result` postcondition, so the production harness keeps the
narrow retained boundary. The restored production harness passes both Verus
modes (`5` verified under actual Verus), and at that point the aggregate gate
remained B=180, pending=0, exact-vstd=36, external_body_surface=113/267, and
unused_external_body_decls=0; later Vec dedup mutable pointer-add and RawVec
start-pointer `Vec::{as_slice,as_mut_slice}` reductions move the current active surface to
113/262. The preceding
RawVec reserve-family initialized-prefix/type-invariant packet
`proof_inventory/rawvec_reserve_exact_try_reserve_invariant_reduction_20260817T0340Z/summary.json`
ports the Ghost initialized-prefix model into
`alloc::vec::Vec::{reserve_exact,try_reserve,try_reserve_exact}` production
harnesses: `reserve_exact` retains only the source-shaped capacity-overflow
abort boundary, while `try_reserve` and `try_reserve_exact` remove their whole
RawVec external bodies. The preceding RawVec reserve/grow capacity
post-type-invariant packet
`proof_inventory/rawvec_reserve_grow_capacity_post_type_invariant_20260817T0240Z/summary.json`
removed the target-local `RawVec::reserve` `external_body` from
`alloc::vec::Vec::reserve`; remaining `RawVec::grow_one` and reserve-caller
initialized-prefix/capacity-overflow boundaries stay retained where actual Verus
still fails, without changing public contracts. The preceding Vec len/capacity type-invariant production reduction
`proof_inventory/vec_len_capacity_type_invariant_production_20260817T0103Z/summary.json`
removes the old target-local len/capacity invariant external-body marker from
`alloc::vec::Vec::{insert_mut,push_mut,insert,push,split_off,into_boxed_slice,into_flattened,shrink_to,shrink_to_fit}`
by using a target-local Verus `type_invariant` and call-site
`use_type_invariant` proofs while retaining lower raw storage, provenance, and
field-mutating boundaries. The earlier Vec push/insert raw-write token reduction
`proof_inventory/vec_push_insert_raw_write_token_reduction_20260816T1506Z/summary.json`
removed four empty target-local `ptr::write` `external_body` markers from
`alloc::vec::Vec::{insert_mut,push_mut,insert,push}`.
The latest no-production-change Slice PartialEq observation adjudication
`proof_inventory/slice_partialeq_observed_current_refresh_20260818T0934Z/summary.json`
keeps the generic `rust_1_96_partial_eq_observed` bridge for
`core::slice::{contains,ends_with,starts_with,strip_circumfix,strip_prefix,strip_suffix}`;
bridge-free probes typecheck with `--no-verify` but fail actual Verus at the
PartialEq-observation postcondition, while unchanged production harnesses pass
both Verus modes; at that packet's admission point the aggregate remained B=180,
pending=0, exact-vstd=36, external_body_surface=108/224, and
unused_external_body_decls=0.
The no-production-change
`proof_inventory/maybeuninit_storage_current_consumers_20260816T2246Z/summary.json`
packet binds the five current `maybeuninit-storage-boundary` UNKNOWN rows:
`core::slice::{assume_init_drop,assume_init_mut,write_clone_of_slice,write_copy_of_slice}`
and `alloc::vec::Vec::spare_capacity_mut`. The packet preserves all production
harnesses and public contracts, records current determinism artifacts with
`status=ok` / `r0_z3=unknown`, binds the exact current proof consumers and
prior no-external/source-shaped probe failures, and reruns harnesses 025, 026,
119, 120, and 144 in both Verus modes. At that admission point, the live
reconcile plus aggregate gate reported B=180, pending=0, exact-vstd=36,
external_body_surface=121/290, and unused external-body declarations at zero.
The source-fidelity repair
`proof_inventory/rchunks_unchecked_source_fidelity_20260816T2306Z/summary.json`
updates `core::slice::{as_rchunks,as_rchunks_mut}` harnesses 023 and 024 so
their retained unchecked chunk-view external-body helpers call the Rust 1.96
source-shaped `slice.as_chunks_unchecked()` and
`slice.as_chunks_unchecked_mut()` APIs instead of returning empty slice stubs.
Both harnesses pass `--crate-type=lib --no-verify` and actual
`--crate-type=lib`; at that admission point, live-scope reconcile and the
aggregate gate reported B=180, pending=0, exact-vstd=36,
external_body_surface=121/290, and unused_external_body_decls=0. The incompleteness UNKNOWN matrix/package
provenance references were refreshed only for the two proof-harness rows; checker counts,
UNKNOWN reason classes, and semantic classifications are unchanged.
The latest no-production-change immutable split raw-parts helper adjudication
`proof_inventory/immutable_split_raw_parts_helper_adjudication_20260816T1712Z/summary.json`
keeps `rust_1_96_split_at_unchecked_raw_parts` for
`core::slice::{as_chunks,split_at_checked,split_at_unchecked,split_first_chunk}`;
evidence-local copies that remove only that helper's `external_body` annotation
fail even `--no-verify` on unsupported `*const T::add`, while unchanged
production harnesses pass both Verus modes and the aggregate remains B=180,
pending=0, exact-vstd=36, with no unused external-body declarations.
The matching no-production-change mutable split raw-parts helper adjudication
`proof_inventory/mutable_split_raw_parts_helper_adjudication_20260816T1728Z/summary.json`
keeps `rust_1_96_split_at_mut_unchecked_raw_parts` for
`core::slice::{as_chunks_mut,split_at_mut_checked,split_at_mut_unchecked,split_first_chunk_mut}`;
evidence-local copies that remove only that helper's `external_body` annotation
fail even `--no-verify` on unsupported `*mut T::add`, while unchanged
production harnesses pass both Verus modes and the aggregate remains B=180,
pending=0, exact-vstd=36, with no unused external-body declarations.
The no-production-change
`proof_inventory/fixed_array_current_consumers_20260816T2008Z/summary.json`
round binds the live Slice fixed-array current consumers: 22 prefix, suffix,
unchecked chunk-array, and flattened array-cast helper names across 26
`external_body` definitions and exactly 18 production Slice targets. The round
reuses the still-current prefix/suffix diagnostic adjudications, records the
fresh scan in
`proof_inventory/fixed_array_current_consumers_20260816T2008Z/current_scan.json`,
reruns every affected production harness with `--crate-type=lib --no-verify`
and actual `--crate-type=lib`, leaves production unchanged, and kept the
then-recorded direct external-body surface at 121/290.
The no-production-change
`proof_inventory/iterator_subslice_unknown_current_consumers_20260816T2037Z/summary.json`
round binds all 24 `iterator-or-subslice-state-boundary` checker UNKNOWN rows to
their current source-backed array-chunk, mutable iterator, predicate split, and
mutable split/subslice proof consumers. Its
`current_scan.json` preserves the exact target set and determinism/proof
artifact links; all 24 production harnesses pass fresh
`--crate-type=lib --no-verify` and actual `--crate-type=lib` reruns, the rows
remain `status=ok` / `r0_z3=unknown` with no semantic omission, and production
contracts were unchanged with the then-recorded direct external-body surface at 121/290.
The no-production-change
`proof_inventory/mutable_reference_view_unknown_current_consumers_20260816T2112Z/summary.json`
round binds all 9 `mutable-reference-view-boundary` checker UNKNOWN rows to their
current proof consumers: Slice mutable array/chunk views, SliceIndex mutable
reference return, and Vec mutable return-reference updates. Its
`current_scan.json` records the exact target set, determinism artifacts, B proof
status, and no row-specific semantic omission; all 9 production harnesses pass
fresh `--crate-type=lib --no-verify` and actual `--crate-type=lib` reruns, and
production contracts remain unchanged with the then-current direct external-body
surface at 121/290.
The no-production-change
`proof_inventory/callback_trace_unknown_current_consumers_20260816T2123Z/summary.json`
round binds all 8 `callback-trace-boundary` checker UNKNOWN rows for
`alloc::vec::Vec::{dedup,dedup_by,dedup_by_key,extend_from_within,pop_if,resize_with,retain,retain_mut}`
to current proof consumers. Its `current_scan.json` records exact row binding to
the active Vec determinism artifacts, B proof status, and no row-specific
semantic omission. All 8 production harnesses pass fresh
`--crate-type=lib --no-verify` and actual `--crate-type=lib` reruns; the checker
status remains `ok` / `r0_z3=unknown`, production contracts remain unchanged,
and the then-recorded direct external-body surface remained 121/290.
The no-production-change
`proof_inventory/unstable_sort_selection_unknown_current_consumers_20260816T2133Z/summary.json`
round binds all 6 `unstable-sort-or-selection-boundary` checker UNKNOWN rows for
`core::slice::{select_nth_unstable,select_nth_unstable_by,select_nth_unstable_by_key,sort_unstable,sort_unstable_by,sort_unstable_by_key}`.
Its `current_scan.json` records the exact live matrix rows, active Slice
determinism artifacts, B proof status, and no row-specific semantic omission.
All 6 unchanged production harnesses pass fresh `--crate-type=lib --no-verify`
and actual `--crate-type=lib` reruns; the retained proof consumers are the
source-backed private `sort::select::partition_at_index` /
`sort::unstable::sort` boundaries plus Ord/FnMut comparator/key callback
observations and Verus closure-lowering boundaries, not strengthened
unique-output or stability contracts.
The bounded `vec_remove_raw_copy_storage_model_reduction_20260816T1533Z` removes `rust_1_96_try_remove_shift_effect` from `alloc::vec::Vec::remove` by adapting the Ghost-backed raw-copy storage model used by `split_off` and `swap_remove`. The Rust 1.96 `try_remove` flow is unchanged: len branch, `ptr::read`, overlapping `ptr::copy`, `set_len(len - 1)`, and `Some(ret)`. Target Verus `--crate-type=lib --no-verify` and actual `--crate-type=lib` both pass with `verification results:: 12 verified, 0 errors`; the then-then-recorded direct external-body surface was 121 harnesses / 290 occurrences, split Slice 79/179 and Vec 42/111.

The no-production-change
`raw_copy_current_consumers_20260816T1957Z` evidence binds the current direct
`copy_nonoverlapping` consumers in
`core::slice::{write_copy_of_slice,copy_from_slice}` and
`alloc::vec::Vec::append`. The live scan is saved under
`proof_inventory/raw_copy_current_consumers_20260816T1957Z/live_raw_copy_scan/`.
Evidence-local copies remove only the narrow raw-copy/effect bridge for each
target: `rust_1_96_maybe_uninit_copy_from_slice_effect`,
`rust_1_96_copy_nonoverlapping_establishes_dst`, and
`rust_1_96_append_elements_copy_effect`. All three probes pass
`--crate-type=lib --no-verify` and fail actual Verus at the corresponding
raw-copy storage/effect postcondition, while unchanged production harnesses
120/145/157 pass both Verus modes with 4/2/7 verified and 0 errors. At that
admission point, the live scope reconcile and aggregate gate remained clean:
B=180, pending=0, exact-vstd=36, then-active certification `20260816T1550Z`,
external-body surface 121/290.

The no-production-change
`vec_raw_read_storage_model_boundary_adjudication_20260816T1823Z` confirms the
remaining generic `pub unsafe fn read<T>` helpers in
`alloc::vec::Vec::{pop_if,pop,remove,swap_remove}` are lower raw-read/value
bridges rather than missing target-local sequence effects. Evidence-local copies
remove only the `#[verifier::external_body]` annotation while preserving the
existing Ghost initialized-sequence/raw-copy storage models; all four copies fail
both Verus `--crate-type=lib --no-verify` and actual `--crate-type=lib` on the
unsupported `core::ptr::read` call before proof obligations. The unchanged
production harnesses pass both Verus modes (`13/8/12/10 verified, 0 errors` for
`pop_if`/`pop`/`remove`/`swap_remove`), and the then-live gates remained B=180,
pending=0, exact-vstd=36, direct external-body surface 121/290, and unused
external-body declarations at zero.

The no-production-change
`vec_reserve_capacity_current_consumers_20260816T1936Z` ties the current
reserve/capacity consumers
`alloc::vec::Vec::{extend_from_within,append,extend_from_slice,reserve}` to the
existing RawVec reservation initialized-prefix blocker. Evidence-local
source-shaped probes remove the local reserve/capacity external boundary and
route through an executable RawVec capacity update; all four probes pass Verus
`--crate-type=lib --no-verify` but fail actual Verus on the RawVec
initialized-prefix preservation postcondition, with the append and
extend-from-slice probes also exposing the production-compatible overflow /
capacity guard. The unchanged production harnesses pass both Verus modes
(`7/7/12/1 verified, 0 errors` respectively), and the then-live gates remained
B=180, pending=0, exact-vstd=36, direct external-body surface 121/290, and
unused external-body declarations at zero.

Older
per-reduction paragraphs on this page may retain the then-current surface count
from their individual admission point; use this aggregate admission count for
the active certification state.

The no-production-change
`flattened_mul_arithmetic_boundary_adjudication_20260816T1523Z` refreshes the
current retained arithmetic boundary for `core::slice::{as_flattened,
as_flattened_mut}` and `alloc::vec::Vec::into_flattened`. Evidence-local copies
remove `external_body` from `rust_1_96_checked_mul_expect` and
`rust_1_96_unchecked_mul` by using a source-shaped `checked_mul` match plus
executable multiplication under `usize::MAX` product preconditions. All three
probes pass `--crate-type=lib --no-verify` but actual Verus fails at the non-ZST
unchecked-multiply product-bound preconditions (`chunk_len * N`, `len * N`, and
`cap * N`), so production retains the source-backed arithmetic boundary. The
unchanged production harnesses pass both Verus modes (5/5/4 verified), and the
aggregate remained B=180, pending=0, external_body surface=121/290, then-active
certification=20260816T1506Z.

The fresh no-production-change
`get_disjoint_boundary_reduction_20260816T1454Z` replayed the remaining
`core::slice::{get_disjoint_mut,get_disjoint_unchecked_mut}` lower-boundary
reduction attempt without changing the active certification or package-facing
provenance. The source-shaped checker-loop probe typechecks with
`--crate-type=lib --no-verify` but actual Verus fails three postconditions
connecting source `is_in_bounds` / `is_overlapping` observations to the abstract
`slice_disjoint_indices_valid` result. The source-shaped mutable-reference-array
fill probe typechecks with `--crate-type=lib --no-verify` but actual Verus fails
the `MaybeUninit::<[&mut I::Output; N]>::uninit().assume_init()` precondition.
The production 051/052 harnesses retain those boundaries and still pass actual
Verus with `verification results:: 5 verified, 0 errors` and `verification
results:: 4 verified, 0 errors`; the aggregate gate then remained B=180,
pending=0, exact-vstd=36, direct external-body surface 121/290, and then-active
certification `20260816T1506Z`.

The active certification now also incorporates
`vec_compaction_storage_drop_bridge_probe_20260816T1426Z`: the production
harnesses for `alloc::vec::Vec::{dedup,dedup_by,dedup_by_key,retain,retain_mut}`
remove the target-local raw drop/copy storage helper `external_body`
annotations while preserving callback order/effects and the retained
callback/result bridges. All five affected harnesses pass both Verus
`--crate-type=lib --no-verify` and actual `--crate-type=lib`, and the paired
incompleteness delivery package validates against the `20260816T1506Z`
certification.

The active certification and aggregate admission gate now enforce
`rawvec_start_pointer_boundary_current_consumers_20260816T1158Z` as a standalone
current-consumer assertion inside the selected final certification payload: all
current production consumers of `rust_1_96_rawvec_start_ptr_boundary` /
`rust_1_96_rawvec_start_mut_ptr_boundary` in harnesses 133, 138, 139, 144, 158,
159, 161, 163, 167, 168, and 175 retain the narrow RawVec start/provenance
bridge. Evidence-local no-external copies for all 13 helper occurrences
typecheck under `--crate-type=lib --no-verify` but fail actual Verus at the
`vec_start_ptr` / `vec_start_mut_ptr` postconditions, while the unchanged
production harnesses pass both required Verus modes. At that admission point,
aggregate counts remained B=180, pending=0, exact-vstd=36, and direct
external-body surface 121/290
(Slice 79/179, Vec 42/111).

The fresh bounded reduction attempt
`rawvec_start_pointer_provenance_reduction_20260817T0220Z` reruns the same live
RawVec start-pointer family after the then-selected 121/281 aggregate refresh. It
preserves production contracts and source checkouts, copies the 11 current
consumer probes with the named RawVec start-pointer helper annotations removed,
and also reruns the reusable `RawVecInner::{ptr,mut_ptr}` no-external model
probe. All production consumers pass both `--crate-type=lib --no-verify` and
actual `--crate-type=lib`; all no-external consumer probes typecheck but fail
actual Verus on the named `vec_start_ptr` / `vec_start_mut_ptr` postconditions,
and the reusable model probe has the same blocker. The Verus-supported retained
boundary is therefore still the exact 11-harness / 13-helper occurrence RawVec
start/provenance bridge, with the then-current direct external-body surface
unchanged at 121/281 (Slice 79/179, Vec 42/102).

The post-0512 current probe
`proof_inventory/rawvec_start_pointer_post_0512_current_probe_20260817T0535Z/summary.json`
rechecked the same 11 RawVec start-pointer consumers against the active
`20260817T0512Z` aggregate surface. It removed only the
`rust_1_96_rawvec_start_ptr_boundary` /
`rust_1_96_rawvec_start_mut_ptr_boundary` annotations in evidence-local copies,
leaving production harnesses unchanged. All 11 production harnesses pass both
Verus `--crate-type=lib --no-verify` and actual `--crate-type=lib`; all 11
no-external probes typecheck but fail actual Verus on the named
`vec_start_ptr` / `vec_start_mut_ptr` postconditions, and the reusable RawVec
pointer model probe has the same blocker. That live reconcile plus aggregate gate
reports B=180, pending=0, exact-vstd=36, unused external-body declarations zero,
and external_body_surface=115/275, so the RawVec start/provenance bridge remains
the retained minimal boundary without increasing the then-active surface.

The then-active certification and aggregate admission gate enforced
`raw_slice_start_pointer_current_consumers_20260816T1227Z`: the live harness scan
binds `rust_1_96_slice_as_ptr_cast` to exactly 12 immutable consumers and
`rust_1_96_slice_as_mut_ptr_cast` to exactly 13 mutable consumers, including
the 012/084 immutable and 013/085 mutable unchecked-split users plus
`rotate_left`, `rotate_right`, and `swap_with_slice`. Fresh
production reruns for the bound harnesses pass both `--crate-type=lib
--no-verify` and actual `--crate-type=lib`; at that admission point, production
semantics and aggregate counts remained B=180, pending=0, exact-vstd=36, direct
external-body surface 121/290, and unused external-body declarations at zero.

The then-active aggregate admission gate also enforced
`vec_aggregate_raw_slice_current_consumers_20260816T1407Z`: the live 180-harness
scan binds `rust_1_96_aggregate_raw_ptr_slice` only to `Vec::as_slice`,
`rust_1_96_aggregate_raw_ptr_mut_slice` only to `Vec::{as_mut_slice,pop_if,clear}`,
and `rust_1_96_as_mut_slice_raw_ptr` only to `Vec::clear` (10 helper tokens: 5
external-body definitions and 5 calls/references). Evidence-local source-shaped
copies for `Vec::{as_slice,as_mut_slice,pop_if,clear}` remove those helper
annotations but fail both `--crate-type=lib --no-verify` and actual Verus at the
unsupported `core::slice::from_raw_parts` / `from_raw_parts_mut` boundary. The
unchanged production harnesses passed both required Verus modes, so at that
admission point production semantics and the direct external-body surface remained
B=180, pending=0, exact-vstd=36, and 121/290.

The historical certification and aggregate admission gate once enforced
`vec_grow_one_capacity_growth_adjudication_20260816T1144Z` as a standalone
retained-boundary assertion because the no-external RawVec::grow_one probes for
harnesses 133, 139, 163, and 168 typechecked under `--crate-type=lib
--no-verify` but failed actual Verus at the documented
`raw_vec_capacity(old(self)) < usize::MAX` precondition. The current
`rawvec_grow_one_overflow_reduction_20260817T0750Z` production round superseded
that blocker by proving `grow_one` itself executable with an internal
normal-return/overflow-abort split; only the impossible capacity-overflow abort
edge remained external at that admission point, with B=180, pending=0,
exact-vstd=36, direct external-body surface 115/272, and unused external-body
declarations at zero. Later Vec pop/pop_if, Vec tail raw-slice constructor, Vec
dedup mutable pointer-add token, and RawVec start-pointer `Vec::{as_slice,as_mut_slice}`
reductions plus the RawVec pointer-accessor projection seed moved the
then-current direct external-body surface to 111/260 before the
remaining-consumer reduction moved the surface to 110/249 and the later raw
Slice root, pointer-range, fixed-prefix, and tail-consumer reductions moved the
then-current surface to 108/224. The later Slice pointer-accessor reduction
moved the current surface to 108/219.

The active certification now also incorporates
`vec_extend_from_slice_iter_view_reduction_20260816T1116Z`:
`alloc::vec::Vec::extend_from_slice` no longer keeps target-local
`SliceReceiver::iter` as an `external_body`. The helper constructs `SliceIter`
directly and proves the source-view equality; the public
`self.spec_extend(other.iter())` flow and exact existing-vstd cloned-suffix
contract are unchanged. Harness 162 reports `12 verified, 0 errors`; at that
admission point, the direct external-body surface was 121/290 (Slice 79/179, Vec
42/111), while the later pointer-accessor aggregate admission surface was
111/260 before the remaining-consumer reduction moved the current surface to
110/249.

The active certification now also incorporates
`vec_into_flattened_rawparts_boundary_reduction_20260816T0955Z`:
`alloc::vec::Vec::into_flattened` no longer keeps the target-local
`Vec<[T; N], A>::into_raw_parts_with_alloc` or `Vec::<T, A>::from_raw_parts_in`
wrappers as whole `external_body` assumptions. Those wrappers now execute the
Rust 1.96-shaped raw-parts field movement and RawVec reconstruction/Vec assembly;
retained trust is limited to lower Vec length-capacity, flattened raw-storage
view/provenance, RawVec reconstruction, arithmetic/panic, and pointer-cast
boundaries. Harness 135 reports `4 verified, 0 errors`.

The active certification now also incorporates
`is_sorted_by_key_source_shaped_reduction_20260816T0938Z`:
`core::slice::is_sorted_by_key` no longer keeps the target-local
`Iter::is_sorted_by_key` whole-method `external_body`. The iterator method now
executes the Rust 1.96-shaped first-key / adjacent-key traversal and proves
`slice_sorted_by_partial_key_result` from the generated key trace. Retained trust
is limited to lower source-backed `FnMut(&T) -> K` key-output, `PartialOrd <=`
comparison, and trace-shape observation boundaries. Harness 059 reports
`8 verified, 0 errors`; at that admission point, the aggregate gate reported
external-body surface 121/290 (Slice 79/179, Vec 42/111), while the current
aggregate admission surface is 113/262.

The active certification now also incorporates
`slice_layout_concrete_sizeof_boundary_reduction_20260816T0910Z`:
`core::slice::{element_offset,subslice_range}` no longer keep the
`rust_type_is_zst`/spec-bridged size helpers as `external_body` boundaries. The
harnesses prove the ZST test as concrete `core::mem::size_of::<T>() == 0` and
prove the post-panic nonzero divisor from concrete `core::mem::size_of::<T>()`.
They still retain the source-backed ZST panic, raw slice start-pointer,
`ptr::from_ref` for `element_offset`, and pointer-domain/provenance result
bridges. Harness 039 reports `8 verified, 0 errors`; harness 111 reports
`9 verified, 0 errors`.

The active certification incorporates `vec_into_boxed_slice_box_assume_init_boundary_reduction_20260816T0307Z`.
`alloc::vec::Vec::into_boxed_slice` no longer keeps the target-local `RawVec::into_box(len)` or `BoxedMaybeUninitSlice::assume_init` `external_body` annotations. The harness carries boxed view/capacity through Ghost fields, preserves the Rust source `len <= capacity` safety side condition at the raw conversion, and transfers the initialized prefix into `Box<[T]>` by construction. The target passes both `--crate-type=lib --no-verify` and actual Verus (`verification results:: 9 verified, 0 errors`); its then-recorded direct external-body surface was 121/290 (Slice 79/179, Vec 42/111).

The active certification now also incorporates the final no-production-change
adjudications `iter_as_slice_view_boundaries_adjudication_20260816T0346Z`,
`swap_raw_pointer_boundary_adjudication_20260816T0400Z`,
`binary_search_by_key_delegate_closure_adjudication_20260816T0412Z`, and
`align_to_offsets_view_bridge_adjudication_20260816T0717Z`. The retained
iterator raw-slice constructor, swap raw-pointer, binary_search_by_key
delegate-closure, and align_to offsets-view boundaries remain source-backed
after source-equivalent no-external probes fail in this Verus build; production
harnesses 003, 004, 005, 112, 030, 008, and 009 still pass both required Verus modes.
Aggregate admission remains B=180, pending=0, exact-vstd=36, generated rows=144,
and checker counts unsat=63 / unknown=81.

The historical `20260816T1550Z` certification also incorporated the Vec::clear
as_mut_slice dependency reduction. `alloc::vec::Vec::clear` preserves the Rust
1.96 `self.as_mut_slice(); self.len = 0; ptr::drop_in_place(elems)` flow while
the target-local `Vec::as_mut_slice` callee is source-shaped through
`as_mut_ptr`, `self.len`, and aggregate raw mutable-slice construction. Retained
trust is limited to lower raw pointer/provenance, raw mutable-slice construction,
implicit raw-slice pointer coercion, and `drop_in_place`; actual Verus reports
`verification results:: 3 verified, 0 errors`, and the then-current direct
external-body surface was 121/315 (Slice 79/181, Vec 42/134) after the later
Vec::extend_from_within proof-lemma reduction.

The historical `20260816T1550Z` certification incorporated `write_copy_copy_from_slice_boundary_reduction_20260815T1443Z`: `core::slice::write_copy_of_slice` no longer keeps the whole `rust_1_96_copy_from_slice` call as an `external_body`. The harness now executes an equal-length copy_from_slice wrapper/private-helper lowering adapted from the reviewed `core::slice::copy_from_slice` proof, reaches `ptr::copy_nonoverlapping`, and retains only the same-layout transmute, lower raw pointer/copy/MaybeUninit storage-effect bridge, and reviewed `assume_init_mut` raw-cast boundaries. The target passes both `--crate-type=lib --no-verify` and actual Verus (`verification results:: 4 verified, 0 errors`).
Historical aggregate counts remained B=180, pending=0, exact-vstd=36, with then-recorded direct external-body surface 121/315 (Slice 79/181, Vec 42/134) after the later Vec::retain wrapper reduction.

The no-production-change
`write_copy_maybeuninit_raw_ptr_adjudication_20260816T0324Z` keeps
`core::slice::write_copy_of_slice` unchanged after a focused probe removed
`#[verifier::external_body]` from the target-local
`rust_1_96_maybe_uninit_slice_as_ptr` and
`rust_1_96_maybe_uninit_slice_as_mut_ptr` wrappers while preserving their Rust
1.96 raw slice-start cast bodies and postconditions. Both `--no-verify` and
actual Verus reject the probe during typecheck as unsupported implicit pointer
dereferences at the immutable and mutable `slice as *[MaybeUninit<T>]` casts.
The retained production harness still passes both required modes
(`verification results:: 4 verified, 0 errors`), and the aggregate gate remained
B=180, pending=0, exact-vstd=36 with the then-current unchanged direct
external-body surface 121/315.


The active certification now also incorporates `vec_extend_from_within_private_helper_reduction_20260816T0013Z` and `vec_extend_from_within_pure_prefix_complete_lemmas_20260816T0220Z`: `alloc::vec::Vec::extend_from_within` no longer keeps the whole private `ExtendFromWithinSpec::spec_extend_from_within` external-body boundary, and the proof-only `rust_1_96_extend_from_within_initial_prefix` / `rust_1_96_extend_from_within_complete` lemmas now verify directly from `vec_extend_from_within_prefix_result` / `vec_extend_from_within_result`. The public wrapper still executes `slice::range`, `reserve(range.len())`, and the unsafe helper call; the helper follows a source-shaped split-spare / clone-write / per-element initialized-prefix length-commit loop. Retained trust is limited to the already-adjudicated RangeBounds and reserve boundaries plus lower spare-storage/provenance, unchecked-source Clone/write, per-step initialized-prefix, and `source_range_matches_contract` boundaries. The target passes both `--crate-type=lib --no-verify` and actual Verus (`verification results:: 7 verified, 0 errors`).
Historical then-recorded direct external-body surface was 121/315 (Slice 79/181, Vec 42/134).

The active certification now also incorporates `vec_extract_if_constructor_boundary_reduction_20260816T0059Z`: `alloc::vec::Vec::extract_if` no longer keeps the whole private `ExtractIf::new` constructor as an external-body boundary. The public wrapper still delegates to `ExtractIf::new`, while the constructor executes the Rust 1.96-shaped `old_len = vec.len()`, `slice::range(range, ..old_len)`, leak-amplification `vec.set_len(0)`, and `ExtractIf { vec, idx: start, del: 0, end, old_len, pred }` initialization. Retained trust is narrowed to the already-adjudicated RangeBounds normalization plus the lower `vec_extract_if_created` relation over stored `FnMut`, mutable-borrow lifetime, future iterator/removal trace, and Drop hole-filling state. The target passes both `--crate-type=lib --no-verify` and actual Verus (`verification results:: 4 verified, 0 errors`).
Historical then-recorded direct external-body surface was 121/315 (Slice 79/181, Vec 42/134) after the later Vec::extend_from_within proof-lemma reduction.

The active certification also incorporates
`copy_within_bounds_bridge_reduction_20260815T1814Z`: `core::slice::copy_within` no longer keeps the target-local `rust_1_96_copy_within_bounds_bridge` as an `external_body`. The helper now proves the resolved source-order, count, `count <= len`, `dest <= len - count`, and destination-fit arithmetic facts directly from `copy_within_domain`; RangeBounds normalization, same-loan pointer provenance, `ptr.add`, and overlapping raw-copy final-slice effects remain retained boundaries. The target passes both `--crate-type=lib --no-verify` and actual Verus (`verification results:: 5 verified, 0 errors`).
The active certification incorporates `vec_from_raw_parts_private_constructor_boundary_reduction_20260815T2011Z`.
`alloc::vec::Vec::from_raw_parts` no longer keeps the private allocator-aware `Vec::from_raw_parts_in` wrapper as an `external_body`. The harness executes the Rust 1.96-shaped `RawVec::from_raw_parts_in(ptr, capacity, alloc)` call and `Vec { buf, len: length }` reconstruction directly; retained trust is narrowed to the lower `RawVec::from_raw_parts_in` allocator/raw-pointer provenance, capacity, and initialized-prefix model. The target passes both `--crate-type=lib --no-verify` and actual Verus (`verification results:: 2 verified, 0 errors`); its then-recorded aggregate admission surface was 121/290 (Slice 79/179, Vec 42/111).

The follow-up `copy_within_overlapping_copy_boundary_adjudication_20260815T1906Z`
keeps production unchanged after a focused no-external-body probe for
`rust_1_96_overlapping_ptr_copy_establishes_slice`: the probe passes
`--crate-type=lib --no-verify` but actual Verus fails at the final-slice
postcondition (`verification results:: 5 verified, 1 errors`). The diagnostic is
preserved under
`proof_inventory/copy_within_overlapping_copy_boundary_adjudication_20260815T1906Z/`;
the unchanged production harness still passes both required modes
(`verification results:: 5 verified, 0 errors`) and the aggregate gate remains
B=180, pending=0, exact-vstd=36 with active certification `20260816T1506Z`.

The bounded `vec_push_wrapper_dependency_reduction_20260815T2128Z` follows the
same active certification line: `alloc::vec::Vec::push` now proves through the
source-shaped `push_mut` skeleton rather than a whole-body dependency, while the
public wrapper body remains exactly `let _ = self.push_mut(value);`.

The focused no-production-change
`vec_push_mut_len_capacity_invariant_adjudication_20260816T0822Z` confirms that
the separated source-backed Vec `len <= capacity` invariant remains a retained
boundary for `alloc::vec::Vec::{push_mut,push}`. Probe harnesses for 139 and 168
removed only `#[verifier::external_body]` from
`rust_1_96_vec_len_capacity_invariant`; both typechecked with
`--crate-type=lib --no-verify` and actual Verus failed exactly at the invariant
postcondition `vec@.len() <= vec.spec_capacity()`. The unchanged production
harnesses still pass both requested Verus modes, and the aggregate gate remains
`B=180`, `pending=0`, `exact-vstd=36`, with `unused_external_body_decls=0`.
The later evidence-local
`proof_inventory/vec_len_capacity_type_invariant_probe_20260817T0040Z/summary.json`
round tried a changed model for the seed consumers
`alloc::vec::Vec::{insert_mut,push_mut}`: a target-local Verus
`type_invariant` ties `Vec.len` to `RawVec` capacity, the proof uses
`use_type_invariant` inline at executable call sites, the private `RawVec::grow_one`
stub is marked `no_unwind`, and the probe copies remove the
`rust_1_96_vec_len_capacity_invariant` external body. Both probe copies pass
`--crate-type=lib --no-verify` and actual `--crate-type=lib` (`insert_mut`:
`verification results:: 11 verified, 0 errors`; `push_mut`: `verification
results:: 6 verified, 0 errors`). This probe became the accepted production shape in
`proof_inventory/vec_len_capacity_type_invariant_production_20260817T0103Z/summary.json`.
The production reduction removes the old len-capacity invariant symbol from the
nine target-local Vec harnesses
`alloc::vec::Vec::{insert_mut,push_mut,insert,push,split_off,into_boxed_slice,into_flattened,shrink_to,shrink_to_fit}`.
The later `rawvec_grow_one_overflow_reduction_20260817T0750Z` round uses the
same inline type-invariant opening to discharge the `len == capacity` callers
while making the four private `RawVec::grow_one` bodies executable; it does not
add public non-overflow preconditions and retains only a source-shaped
`capacity_overflow` abort boundary.
`split_off` proves the incoming initialized model length from the opened Vec type
invariant before assigning `self.model` in `commit_initialized_model`, and
`into_flattened` uses the existing vstd multiplication inequality lemma to prove
the flattened `new_len <= new_cap` side condition. All nine production harnesses
pass `--crate-type=lib --no-verify` and actual `--crate-type=lib`, and the
live-scope reconcile plus aggregate gate report B=180, pending=0, exact-vstd=36,
unused external-body declarations at zero, and then-recorded surface 121/281
(Slice 79/179, Vec 42/102).

The earlier production propagation attempt
`proof_inventory/vec_len_capacity_type_invariant_production_20260817T0054Z`
is superseded failure evidence for the pre-repair `split_off`
`commit_initialized_model` assignment-order bug.

The bounded `vec_dedup_by_key_source_shaped_reduction_20260816T0234Z` updates
`alloc::vec::Vec::dedup_by_key`: the target no longer keeps the whole
`rust_1_96_dedup_by_key_delegate` / reviewed `Vec::dedup_by` dependency
boundary. The harness expands Rust 1.96
`self.dedup_by(|a, b| key(a) == key(b))` through a local source-shaped
dedup loop adapted from harness 127, preserving key(current) then
key(previous) callback order and PartialEq key comparison. Retained trust is
limited to lower raw-pointer/drop/copy/provenance, ordered FnMut key callback
observation, and `vec_dedup_by_key_result` effect summary. The target passes
both `--crate-type=lib --no-verify` and actual Verus (`verification results::
9 verified, 0 errors`); the then-current direct external-body surface was 121
harnesses / 318 occurrences, split Slice 79/181 and Vec 42/134.

The bounded `vec_dedup_wrapper_dependency_reduction_20260815T2150Z` updates
`alloc::vec::Vec::dedup`: the public wrapper still executes the Rust 1.96
`self.dedup_by(|a, b| a == b)` semantics, but the target-local `dedup_by`
callee is now the source-shaped skeleton adapted from harness 127 instead of a
whole-method dependency boundary. Retained trust is limited to the lower
raw-pointer/drop/copy/provenance, reversed `FnMut` callback observation,
`vec_dedup_by_result` effect-summary, and PartialEq bridge boundaries. The
target passes both `--crate-type=lib --no-verify` and actual Verus
(`verification results:: 10 verified, 0 errors`). Historical then-recorded
aggregate counts remained B=180, pending=0, exact-vstd=36 with direct
external-body surface 121/315 (Slice 79/181, Vec 42/134).

The no-production-change
`vec_dedup_partial_eq_bridge_adjudication_20260816T0743Z` preserves those two
wrapper-specific PartialEq boundaries. A focused probe removed only
`#[verifier::external_body]` from `rust_1_96_partial_eq_callback_observation`
and `rust_1_96_dedup_by_partial_eq_bridge` while keeping the executable
`self.dedup_by(|a, b| a == b)` wrapper and local source-shaped `dedup_by`
skeleton unchanged. Actual Verus fails exactly at the two uninterpreted
postconditions, `partial_eq_same_bucket_callback::<T,F>(same_bucket)` and
`vec_dedup_partial_eq_result(source, result)`. The unchanged production harness
still passes `--crate-type=lib --no-verify` and actual Verus, and the aggregate
gate remains B=180, pending=0, exact-vstd=36 with no unused external-body
declarations.

The no-production-change
`vec_retain_readonly_callback_bridge_adjudication_20260816T1011Z` preserves the
two wrapper-specific `alloc::vec::Vec::retain` read-only callback bridge
boundaries after the earlier source-shaped retain_mut dependency reduction. A
focused probe removed only `#[verifier::external_body]` from
`rust_1_96_retain_readonly_callback_observation` and
`rust_1_96_retain_result_bridge` while keeping the executable
`self.retain_mut(|elem| f(elem))` wrapper and local retain_mut skeleton
unchanged. Actual Verus fails at the generic callback-token postconditions
`predicate == retain_readonly_as_mut_predicate(f)` and
`retain_readonly_as_mut_callback::<T,F>(f,predicate)`, plus the
`vec_retain_result(source,f,result)` bridge. The unchanged production harness
still passes `--crate-type=lib --no-verify` and actual Verus, preserving Rust
1.96 callback semantics without strengthening callback outcomes.


The active certification now also incorporates `is_sorted_by_arraywindows_all_reduction`: `core::slice::is_sorted_by` keeps the public `self_slice.array_windows::<2>().all(compare)` flow while `ArrayWindows::all` executes an adjacent-pair traversal loop rather than a whole-method external body. Retained trust is limited to lower source-backed `FnMut(&T, &T) -> bool` comparator output/trace observation boundaries. The target passes both `--crate-type=lib --no-verify` and actual Verus (`verification results:: 9 verified, 0 errors`).
Historical then-recorded direct external-body surface was 121/315 (Slice 79/181, Vec 42/134).

The no-production-change
`sort_select_private_boundary_adjudication_20260815T2100Z` keeps the retained
private `sort::select::partition_at_index*` and `sort::unstable::sort*`
boundaries for proof harnesses 077-082. Probe copies that removed only the
private-boundary `#[verifier::external_body]` annotations all passed
`--crate-type=lib --no-verify`, but actual Verus failed the partition or sorted
postconditions for all six targets; the unchanged production harnesses passed
both modes (`verification results:: 1 verified, 0 errors` each). The probe
does not strengthen unstable sort/selection semantics, callback observations,
uniqueness, or stability; diagnostics are preserved under
`proof_inventory/sort_select_private_boundary_adjudication_20260815T2100Z/`.
The aggregate gate remains B=180, pending=0, exact-vstd=36 with active
certification `20260815T1443Z`.

The active certification also incorporates
`write_clone_clone_write_boundary_20260815T1636Z`: `core::slice::write_clone_of_slice`
no longer keeps the full per-iteration
`guard.slice[i].write(src[i].clone())` expression behind one external-body helper.
The production harness verifies the source-side index bound, executes
`src[i].clone()` in the wrapper, retains only the lower destination
`slice[i].write(value)` MaybeUninit slot-write/indexing/provenance boundary, and
replaces the former whole-loop written-from bridge with a per-iteration
`rust_1_96_write_clone_iteration_effect` prefix bridge carried by the executable
loop invariant. The target passes both `--crate-type=lib --no-verify` and actual
Verus (`verification results:: 7 verified, 0 errors`); the then-current direct
external-body surface was 121/290.
The follow-up
`write_clone_iteration_prefix_bridge_adjudication_20260816T0528Z` confirms that
removing only that per-iteration prefix bridge is not currently source-faithful:
the isolated probe typechecks but actual Verus fails the
`maybe_uninit_prefix_written_from(..., i + 1)` postcondition. Production is
unchanged, the bridge is retained as the remaining relational effect between the
lower MaybeUninit slot-write/provenance boundary and the loop-carried
initialized/value prefix, refreshed actual Verus still reports 7 verified and 0
errors, and the aggregate gate remains B=180, pending=0, exact-vstd=36.
The paired incompleteness analysis/classification/UNKNOWN artifacts regenerate
cleanly: the native chain reports 144 analysis rows, 144 classification rows,
81 UNKNOWN-matrix rows, no missing artifacts, no unsupported mutable-reference
targets, no semantic spec-mismatch targets, no legacy no-target markers, and no
candidate-shape or SMT2 failures. The delivery package manifest is refreshed
against those regenerated artifacts: package validation reports 144 analysis
rows, 144 classification rows, 81 UNKNOWN-matrix rows, 11 preserved artifacts,
7 validator scripts, no stale active-certification surface references, and no
failures.

The historical `20260816T1550Z` certification also incorporated
`vec_pop_if_last_mut_boundary_reduction_20260816T0504Z`: harness 138 removes
the target-local whole-method `#[verifier::external_body] fn last_mut`
effect model from `alloc::vec::Vec::pop_if` by executing the local callee
through the reviewed `Vec::as_mut_slice` raw mutable-slice construction and
the reviewed `core::slice::last_mut` split_at_mut lowering. The earlier
`vec_pop_if_pop_boundary_reduction_20260815T1546Z` remains incorporated: the
true predicate branch uses an executable source-shaped pop analogue adapted
from the verified `Vec::pop` harness. At that point retained trust was limited
to lower raw mutable-slice provenance/construction, the `FnOnce` predicate
observation, RawVec start-pointer/provenance, the then-narrowed RawVec
storage-context pop capacity fact, and in-capacity `ptr::read` value
boundaries. The follow-up
`vec_pop_lower_boundary_narrowing_20260816T1038Z` applies the same narrowing to
both `alloc::vec::Vec::pop` and the pop analogue inside `pop_if`: the capacity
boundary is tied to `raw_vec_initialized_seq(buf, old_len)` and
`raw_vec_capacity(buf)`, while the read bridge requires a `vec_slot_ptr`
produced by the modeled `as_ptr().add(len)` call. A stronger old-source
start-pointer precondition remains blocked because `as_ptr()` is called after
the Rust 1.96 length decrement and therefore exposes the shortened initialized
view. Both targets pass `--crate-type=lib --no-verify` and actual Verus
(`Vec::pop`: `verification results:: 8 verified, 0 errors`; `Vec::pop_if`:
`verification results:: 13 verified, 0 errors`); the then-current direct
external-body surface was 121/317 (Slice 79/179, Vec 42/138).

The current `vec_pop_capacity_invariant_reduction_20260817T0823Z` evidence
removes `rust_1_96_pop_capacity_boundary` from production in both
`proof_harnesses/167_alloc_vec_Vec_pop/harness.rs` and
`proof_harnesses/138_alloc_vec_Vec_pop_if/harness.rs`. The post-decrement
`new_len < capacity` fact now verifies from the target-local Vec type invariant
`self.len as nat <= raw_vec_capacity(&self.buf)`, `old_len > 0`, and the
executable `capacity()` result. Both harnesses still pass `--crate-type=lib
--no-verify` and actual `--crate-type=lib`; after later reductions including the
RawVec start-pointer `Vec::{as_slice,as_mut_slice}` production seeds, the live aggregate reports
B=180, pending=0, exact-vstd=36, and direct external-body surface 113/262 (Slice
79/179, Vec 34/83).

The active certification now also incorporates
`vec_resize_extend_with_loop_reduction_20260815T1719Z` and
`vec_resize_truncate_shrink_reduction_20260816T0606Z`: harness 172 removes both
the whole private `#[verifier::external_body] fn extend_with` growth effect
model and the target-local whole `Vec::truncate` shrink-effect stub from
`alloc::vec::Vec::resize`. The growth helper executes the Rust 1.96-shaped
`reserve`, `as_mut_ptr().add(self.len())`, clone/write loop, final value write,
and `SetLenOnDrop`-style length accounting. The shrink helper executes the
source-shaped len/no-op guard, `remaining_len` computation, raw tail slice
construction, prefix length commit, and tail drop. Retained trust is limited to
lower raw tail slice/drop construction and the lower
`rust_1_96_extend_with_clone_write_effect` cloned-suffix observation boundary.
The target passes both `--crate-type=lib --no-verify` and actual Verus
(`verification results:: 15 verified, 0 errors`); the then-current direct
external-body surface was 121/318 (Slice 79/181, Vec 42/137).

The active certification now also incorporates
`vec_resize_with_extend_trusted_loop_reduction_20260815T2257Z` and the later
`vec_resize_with_truncate_boundary_reduction_20260816T0547Z`: harness 140
removes both the whole private `#[verifier::external_body] fn extend_trusted`
growth effect model and the target-local whole `Vec::truncate` shrink-effect
stub from `alloc::vec::Vec::resize_with`. The public Rust 1.96 branch still
calls `extend_trusted(iter::repeat_with(f).take(additional))` on growth and
`self.truncate(new_len)` on shrink. The growth helper executes the
source-shaped `reserve`, `as_mut_ptr().add(self.len())`, write-observation loop,
and `SetLenOnDrop`-style length accounting adapted from `Vec::resize`; the
shrink helper is adapted from harness 177 and performs the len no-op guard,
`remaining_len` computation, raw tail slice construction, prefix length/model
commit, and tail drop. Retained trust is limited to lower raw tail
slice/drop construction, repeat_with/take wrapper token, zero-argument `FnMut`
output trace, and reserve/as_mut_ptr/add/write lower growth operations. The
target passes both `--crate-type=lib --no-verify` and actual Verus
(`verification results:: 15 verified, 0 errors`); the then-current direct
external-body surface was 121/318 (Slice 79/181, Vec 42/137).

The active certification now also incorporates
`vec_retain_wrapper_dependency_reduction_20260815T2315Z`: harness 141 removes
the whole `alloc::vec::Vec::retain_mut` dependency/delegate boundary from
`alloc::vec::Vec::retain`. The public Rust 1.96 wrapper semantics
`self.retain_mut(|elem| f(elem))` are preserved through a source-shaped local
retain_mut skeleton adapted from harness 142 and specialized to the read-only
callback token. Retained trust is limited to lower raw-pointer/copy/drop,
read-only `FnMut` callback observation, `mem::forget`, effect-summary, and
result-bridge boundaries. The target passes both `--crate-type=lib --no-verify`
and actual Verus (`verification results:: 9 verified, 0 errors`). Historical
then-recorded aggregate counts reported B=180, pending=0, exact-vstd=36, and
direct external-body surface 121/315 (Slice 79/181, Vec 42/134).

The historical `20260816T1550Z` certification additionally incorporated the earlier
`vec_into_boxed_slice_shrink_boundary_20260815T1443Z` and
`vec_into_boxed_slice_ptr_read_boundary_reduction_20260816T0250Z` reductions
before the later boxed-conversion reduction: harness 134 keeps the Rust 1.96
`into_boxed_slice` flow, replaces the whole-call `Vec::shrink_to_fit` external
boundary with the already-reviewed executable capacity-branch shape from harness
174, and verifies `ptr::read(&me.buf)` as an executable RawVec field-copy model.
The subsequent `vec_into_boxed_slice_box_assume_init_boundary_reduction_20260816T0307Z`
also removes the former lower `RawVec::into_box(len)` and boxed-slice
`assume_init` external-body boundaries through Ghost-backed boxed
view/capacity/initialized-prefix conversions. The target currently passes both
`--crate-type=lib --no-verify` and actual Verus (`verification results:: 9
verified, 0 errors`). Historical then-recorded aggregate counts reported B=180,
pending=0, exact-vstd=36, and direct external-body surface 121/315 (Slice
79/181, Vec 42/134).


The historical `20260816T1550Z` certification incorporated
`partition_point_result_bridge_reduction_20260815T0501Z`, which proves
`core::slice::partition_point`'s private `rust_1_96_partition_point_result_bridge`
as an executable Ok/Err proof over `slice_partition_point_binary_search_result`
and `slice_partition_point_result` while retaining the reviewed
`binary_search_by` dependency and FnMut predicate observation boundaries. It also incorporated the
`prefix_suffix_scan_reduction_20260814T2334Z`, which proves
`core::slice::{starts_with,ends_with,strip_prefix,strip_suffix,strip_circumfix}`
prefix/suffix `PartialEq` checks as source-shaped executable element scans,
retaining only the lower `PartialEq` observation bridge and `SlicePattern::as_slice`
where applicable. It also incorporates the
`reverse_revswap_loop_result_reduction_20260814T2302Z`, which proves
`core::slice::reverse`'s private `rust_1_96_revswap_loop_result` helper as
executable source-shaped loop/permutation code while retaining only the raw-half
construction and whole-slice final-frame bridges. It also incorporates the
`slicecontains_default_partialeq_reduction_20260814T2114Z`, which proves the
generic `core::slice::contains` SliceContains default PartialEq scan while
retaining only the lower PartialEq observation bridge plus primitive memchr/SIMD
specialization boundary. A later no-production-change
`partial_eq_observed_bridge_adjudication_20260815T1238Z` attempted to
remove the remaining target-local `rust_1_96_partial_eq_observed` bridge across
`core::slice::{contains,starts_with,ends_with,strip_prefix,strip_suffix,strip_circumfix}`.
The bridge-free probe copies all passed `--crate-type=lib --no-verify` but failed
actual Verus at `b <==> partial_eq_observed(*left, *right)`, while unchanged
production harnesses passed both modes. The round therefore preserves the lower
bridge as the source-honest generic `PartialEq` observation boundary and does not
claim primitive `SliceContains` specializations as proved. A fresh bounded replay
`slice_partialeq_observed_current_refresh_20260818T0934Z` repeated that attempt
on the then-current production harnesses and then-current 108/224 external-body surface
for the same six targets: all bridge-free probes again passed
`--crate-type=lib --no-verify`, all failed actual Verus at the same
postcondition, all unchanged production harnesses passed both modes, and the
aggregate gate remained B=180, pending=0, exact-vstd=36,
unused_external_body_decls=0, so the bridge remains retained without changing
production.
It also incorporates the prior
`20260814T2016Z` unchecked-subtraction reduction, which reran and passed both
`--no-verify` and actual Verus for
`proof_harnesses/{086_core_slice_split_at_mut_unchecked,087_core_slice_split_at_unchecked}/harness.rs`
after removing the two target-local `unchecked_sub` `external_body`
annotations and verifying executable `len - mid` under `mid <= len`. Raw
pointer, raw-parts, and split final-frame boundaries remain retained. It also
incorporates the reviewed no-production-change
`singleton_array_boundary_reduction_20260814T2032Z` and
`unreachable_panic_boundary_reduction_20260814T2043Z` adjudications: the
production harnesses still pass `--no-verify` and actual Verus while retaining
the narrow source-backed singleton-array and unreachable-panic/assert helper
boundaries. It also incorporates the bounded
`split_unchecked_helper_reduction_20260815T0026Z`, which removes the high-level target-local
`split_at_unchecked` / `split_at_mut_unchecked` `external_body` wrappers from
harnesses 012, 013, 084, 085, 089, and 090. Those dependent harnesses now carry
the same source-shaped helper skeleton as the already reviewed 086/087
unchecked split implementations: compute `len`, establish the `mid <= len`
unsafe precondition, obtain the start pointer through the retained raw-pointer
boundary, execute `unchecked_sub` as `len - mid`, and then cross only the named
raw-parts/provenance/final-frame split boundary. All six changed harnesses pass
both `--crate-type=lib --no-verify` and actual `--crate-type=lib` Verus, with
evidence under
`proof_inventory/split_unchecked_helper_reduction_20260815T0026Z/verus/`; the
paired UNKNOWN matrix was refreshed and the aggregate gate remains `B=180`,
`pending=0`, `exact-vstd=36`.
It also incorporates `ascii_whitespace_vtab_repair_20260815T0127Z`: the project-local `core::slice` trim vocabulary and trim harness byte helpers now match Rust `u8::is_ascii_whitespace` for `0x09`, `0x0a`, `0x0c`, `0x0d`, and `0x20` only, explicitly excluding vertical tab `0x0b`; the refreshed Slice feedback run keeps 120 `ok` rows with 58 UNSAT / 62 UNKNOWN, and `trim_ascii`, `trim_ascii_end`, and `trim_ascii_start` remain real `status=ok` / `r0_z3=unsat`.
It also incorporates `binary_search_by_loop_result_reduction_20260815T0235Z`:
`core::slice::binary_search_by` no longer retains
`rust_1_96_binary_search_by_loop_result` as a proof-only `external_body`;
source-shaped base/size loop invariants discharge the generated relational
Ok/Err result while preserving arbitrary `FnMut` callback observations and
duplicate-search semantics. The dependent `binary_search`,
`binary_search_by_key`, and `partition_point` harness evidence was refreshed.
The later no-production-change
`binary_search_result_bridge_adjudication_20260815T1017Z` keeps the two wrapper
bridges for `core::slice::{binary_search,binary_search_by_key}`: bridge-free
diagnostic probes typecheck with `--crate-type=lib --no-verify` but fail actual
Verus exactly at the generated result-predicate postconditions, while both
unchanged production harnesses pass actual Verus and the aggregate gate remains
`B=180`, `pending=0`, `exact-vstd=36`.
The follow-up no-production-change
`binary_search_by_key_delegate_closure_adjudication_20260816T0412Z` keeps the
target-local by-key delegate boundary after the source-equivalent wrapper
`binary_search_by(slice, |k| f(k).cmp(b))` was rejected during Verus
`--crate-type=lib --no-verify` because the closure captures the mutable `FnMut`
key callback. The production harness remains executable at the public target,
retains the existing result bridge and duplicate-search/callback semantics, and
passes both production Verus modes with the aggregate still at `B=180`,
`pending=0`, `exact-vstd=36`.
It also incorporates `partition_point_result_bridge_reduction_20260815T0501Z`,
which removes the proof-only partition-point result bridge `external_body` while
preserving the reviewed dependency and callback boundaries. It also incorporates
`copy_from_slice_len_mismatch_reduction_20260815T0730Z`, which removes
`core::slice::copy_from_slice`'s target-local `len_mismatch_fail` helper by
proving the length-mismatch branch unreachable from the exact-vstd equal-length
precondition while preserving raw pointer exposure and copy_nonoverlapping
destination-write boundaries. It also incorporates
`copy_within_dest_assert_reduction_20260815T0800Z`, which removes
`core::slice::copy_within`'s target-local
`rust_1_96_copy_within_dest_assert_failed` helper by proving the
`dest > len - count` branch unreachable from `copy_within_domain` and the
existing bounds bridge while preserving the RangeBounds, pointer-provenance, and
overlapping raw-copy boundaries. It also records
`swap_remove_unreachable_assert_reduction_20260815T0812Z`, which removes
`alloc::vec::Vec::swap_remove`'s target-local
`rust_1_96_swap_remove_assert_failed` helper by proving the `i >= len` branch
unreachable from `i < old(vec).len()` and the executable len/view equality while
preserving raw pointer read/copy/provenance and `set_len(len - 1)` behavior. It
now also incorporates the reviewed bounded `core::slice::is_sorted` Windows
traversal reduction: `Windows::all` and `Windows::fold` execute
adjacent-window traversal loops, leaving only the individual PartialOrd
comparison observation bridge.
The raw slice pointer-domain bridge adjudication
`raw_slice_pointer_domain_reduction_20260815T1049Z` preserves production
`core::slice::{element_offset,subslice_range}` harnesses unchanged. Source-equivalent
probe copies removed only the three pointer-domain result bridge
`external_body` annotations per target; both probes typechecked with
`--crate-type=lib --no-verify`, but actual Verus failed the generated
Seq-view option-result postconditions with three errors per probe. The
production harnesses reran successfully in both `--no-verify` and actual
`--crate-type=lib` modes (`element_offset`: 6 verified / 0 errors,
`subslice_range`: 7 verified / 0 errors), so the provenance/domain bridges
remain the minimal retained boundary. That round refreshed the then-active
`20260815T1326Z` certification's measured active-selector metadata and regenerated
the paired incompleteness package metadata; the package validator and aggregate
gate passed with `B=180`, `pending=0`, `exact-vstd=36`, and the then-current
external-body surface `124/291`.
The raw-parts constructor boundary adjudication
`raw_parts_constructor_boundary_adjudication_20260815T1124Z` preserves production
`core::slice::{from_raw_parts,from_raw_parts_mut}` harnesses unchanged. Direct
no-external-body probe copies removed only
`rust_1_96_from_raw_parts_ub_checked_raw_slice` and
`rust_1_96_from_raw_parts_mut_ub_checked_raw_slice` while retaining the generated
raw-domain preconditions and Rust 1.96
`core::ptr::slice_from_raw_parts` / `core::ptr::slice_from_raw_parts_mut`
dereference shape. Both probes fail in `--crate-type=lib --no-verify` and actual
Verus with unsupported raw pointer dereference before proof obligations, while
the unchanged production harnesses pass both modes; the narrow
UB-precondition/raw-pointer/provenance helpers therefore remain the minimal
retained boundary.
The current refresh
`raw_parts_constructor_current_boundary_adjudication_20260816T1705Z` rechecks the
same retained constructor boundary against the live 180-harness tree. The scan
records 2 constructor-helper harnesses, 8 named unchecked-split raw-parts helper
harnesses, and 17 direct `core::slice::from_raw_parts(_mut)` callsite harnesses;
the 048/049 no-external constructor probes still fail before verification on
unsupported raw pointer dereference, unchanged production 048/049 verifies in
both Verus modes, and the aggregate gate then remained `B=180`, `pending=0`,
`exact-vstd=36`, `external_body_surface=121/290`, and
`unused_external_body_decls=0` under then-active certification `20260816T1550Z`.
The follow-up refresh
`raw_parts_constructor_boundary_refresh_20260816T1841Z` reran the same direct
constructor no-external probes plus unchanged production 048/049 in both
`--crate-type=lib --no-verify` and actual Verus. The source-equivalent probes
still fail on unsupported `core::ptr::slice_from_raw_parts(_mut)` raw-pointer
dereference, production still verifies with 1 verified / 0 errors per target,
and `reconcile_live_scope_180.py` plus `check_implproof_aggregate.py` confirmed
180 targets, B=180, pending=0, exact-vstd=36, and then-current external-body
surface 121/290.
The retain-mut lower-boundary adjudication
`retain_mut_lower_boundary_adjudication_20260815T1140Z` preserves production
`alloc::vec::Vec::retain_mut` unchanged. Source-shaped no-external probes for
the lower helpers fail before production proof obligations: callback helpers
need unsupported raw-pointer dereference to construct `&mut T`, and the raw
copy/drop helpers need unsupported `*mut T::add`, `drop_in_place`,
`copy_nonoverlapping`, and `copy`. The isolated whole-effect bridge typechecks
with `--no-verify` but fails actual Verus at the abstract
`vec_retain_mut_result` postcondition. The production harness still passes both
`--crate-type=lib --no-verify` and actual Verus, so the narrow raw-pointer,
copy/drop, callback, `mem::forget`, and effect-summary boundaries are retained.
The dedup-by reversed-callback/effect adjudication
`dedup_by_reversed_callback_effect_boundary_adjudication_20260815T1148Z`
preserves production `alloc::vec::Vec::dedup_by` unchanged. The source-shaped
callback probe retains the documented reversed `same_bucket(&mut *current, &mut
*previous)` order and fails under both `--no-verify` and actual Verus at
unsupported raw pointer dereference. The isolated no-external-body
`rust_1_96_dedup_by_effect_boundary` probe typechecks with `--no-verify` but
fails actual Verus at `vec_dedup_by_result`; the unchanged production harness
still passes both modes, and the aggregate gate remains `B=180`, `pending=0`,
`exact-vstd=36`.
The Vec::drain NonNull and pointer-add wrapper reductions remove the target-local
`NonNull<Vec<T,A>>::from` and `rust_1_96_vec_drain_ptr_add` `external_body`
annotations from `proof_harnesses/129_alloc_vec_Vec_drain/harness.rs`. The
NonNull wrapper now verifies as an executable PhantomData token constructor
preserving `final(reference)@ == old(reference)@`, and the drain pointer
offset uses the same executable `ConstPtr::add` token-wrapper pattern as the
existing pointer-add reductions. The retained boundaries are RangeBounds
normalization, raw-parts provenance, iterator/drop state, and the generated
`vec_drain_created` relation. Evidence is under
`proof_inventory/vec_drain_nonnull_from_boundary_20260815T1104Z/` and
`proof_inventory/vec_drain_ptr_add_boundary_reduction_20260816T0116Z/`.
The
previous `is_sorted` range/suffix rerun for
`proof_harnesses/057_core_slice_is_sorted/harness.rs`, the previous pointer-address
rerun for
`proof_harnesses/{039_core_slice_element_offset,111_core_slice_subslice_range}/harness.rs`,
the previous get-disjoint rerun for
`proof_harnesses/{051_core_slice_get_disjoint_mut,052_core_slice_get_disjoint_unchecked_mut}/harness.rs`
and the earlier pointer-add
helper rerun
`proof_harnesses/{133_alloc_vec_Vec_insert_mut,139_alloc_vec_Vec_push_mut,144_alloc_vec_Vec_spare_capacity_mut,146_core_slice_copy_within,167_alloc_vec_Vec_pop,175_alloc_vec_Vec_split_off,176_alloc_vec_Vec_swap_remove,177_alloc_vec_Vec_truncate}/harness.rs` and
`proof_harnesses/{127_alloc_vec_Vec_dedup_by,129_alloc_vec_Vec_drain,131_alloc_vec_Vec_extract_if,133_alloc_vec_Vec_insert_mut,142_alloc_vec_Vec_retain_mut,157_alloc_vec_Vec_append,175_alloc_vec_Vec_split_off,176_alloc_vec_Vec_swap_remove}/harness.rs`,
`proof_harnesses/165_alloc_vec_Vec_len/harness.rs`,
`proof_harnesses/063_core_slice_make_ascii_lowercase/harness.rs`,
`proof_harnesses/064_core_slice_make_ascii_uppercase/harness.rs`, and
`proof_harnesses/{041_core_slice_eq_ignore_ascii_case,133_alloc_vec_Vec_insert_mut,173_alloc_vec_Vec_shrink_to,174_alloc_vec_Vec_shrink_to_fit,175_alloc_vec_Vec_split_off,154_core_slice_len}/harness.rs`
reruns remain preserved in superseded evidence. It also passed
`python3 -m py_compile tools/reconcile_live_scope_180.py tools/check_implproof_aggregate.py`,
`python3 tools/reconcile_live_scope_180.py`, and
`python3 tools/check_implproof_aggregate.py` in the implproof workspace. The
measured live state is
`existing-vstd=36`, `generated-new-real-relation-spec=144`, `B=180`,
`pending=0`, and no next pending target. The later
`prefix_fixed_array_cast_boundary_adjudication_20260815T0004Z` adjudication for
`core::slice::{as_array,as_mut_array,first_chunk,first_chunk_mut,split_first_chunk,split_first_chunk_mut}`
preserved the reviewed `as_ptr`/`as_mut_ptr` and checked/unchecked split
boundaries, then removed only the target-local fixed-array cast helper and
corresponding immutable/mutable array-reference helper `external_body`
annotations in source-shaped probe copies. All six probes fail during both
`--crate-type=lib --no-verify` and actual `--crate-type=lib` Verus at
unsupported raw pointer dereference through `unsafe { &*ptr }` or
`unsafe { &mut *ptr }`, before proof obligations can reduce the boundary. The
production harnesses therefore retain the narrow source-backed
`rust_1_96_ptr_cast_array`, `rust_1_96_mut_ptr_cast_array`, and fixed-array
reference/final-frame helper boundaries and still pass both production Verus
modes; the aggregate gate remains B=180, pending=0, exact-vstd=36, with active
certification `20260815T1443Z`. That active certification also reran and passed the matching
incompleteness gate:
`python3 -m py_compile tools/build_analysis_inventory.py tools/validate_analysis_inventory.py tools/classify_incompleteness.py tools/validate_incompleteness_classification.py tools/build_unknown_evidence_matrix.py tools/validate_unknown_evidence_matrix.py`,
`python3 tools/build_analysis_inventory.py`,
`python3 tools/validate_analysis_inventory.py`,
`python3 tools/classify_incompleteness.py`, and
`python3 tools/validate_incompleteness_classification.py`,
`python3 tools/build_unknown_evidence_matrix.py`, and
`python3 tools/validate_unknown_evidence_matrix.py`, plus
`python3 delivery_package/validate_delivery_package.py --root .`; it covers
`total_rows=144`, Slice `ok=120`, Vec `ok=24`, checker counts `unsat=63` /
`unknown=81`, `missing_artifact_count=0`, no semantic spec-mismatch targets, and
no unsupported mutable-reference-return targets. After the latest native
regeneration, the delivery package validator reports 144 analysis rows,
144 classification rows, 81 UNKNOWN-matrix rows, 11 preserved artifacts,
7 validator scripts, no stale active-certification surface references, and an
empty failures list. The UNKNOWN/incompleteness
scripts are native to the paired
`nanvix-rust-std-slice-vec-incompleteness-2026-08-12` workspace, not the
implproof `tools/` directory.

The submission candidates
`submission_candidates/B16_LOW_BOUNDARY_SUBSET`,
`submission_candidates/B20_LOW_BOUNDARY_SUBSET`, and
`submission_candidates/A7_NO_BOUNDARY_SUBSET` are package-level subsets tied to
the historical `20260816T1550Z` aggregate certification. B16 contains a
machine-readable `package_manifest.json` and concise `CROSSWALK.md` binding 16
generated `core::slice` contracts, a 20-item copied helper closure, copied
proof/evidence paths, fresh package-local actual-Verus rerun evidence under
`verification/evidence/actual_verus/`, and package validation outputs.
Review-side package validation passed the source-subset script, Verus
`--no-verify` typecheck from the implproof root, actual Verus on all 16 copied
harnesses with return code 0 and `0 errors`, and an independent structural
assertion for 16 target directories, 16 generated declarations, 20 helpers, zero
copied-harness `#[verifier::external_body]` annotations, and present validation
evidence. B20
contains the analogous manifest/crosswalk binding 20 generated `core::slice`
contracts, the same 20-item helper closure plus four copied iterator external
type specs, copied proof/evidence paths, fresh package-local actual-Verus rerun
evidence under `verification/evidence/actual_verus/`, and package validation
outputs.
Review-side validation passed the package-local source-subset script, Verus
`--no-verify` typecheck from the implproof root, actual Verus on all 20 copied
harnesses with return code 0 and `0 errors`, and an independent structural
assertion for 20 documented targets, 20 target directories, 20 generated
declarations, 20 helpers, four external type specs, copied evidence with
positive `0 errors` Verus results, and exactly six documented retained
copied-harness raw split-construction annotations with no unexpected
annotations. The immutable trio is bound to
`immutable_split_raw_parts_helper_adjudication_20260816T1712Z`, and the mutable
trio is bound to
`mutable_split_raw_parts_helper_adjudication_20260816T1728Z`. A7 contains
all seven `actual_verus_verified_no_trusted_boundary` targets:
`core::slice::{make_ascii_lowercase,make_ascii_uppercase,is_empty}` and
`alloc::vec::Vec::{is_empty,len,new,with_capacity}`. It binds two generated
Slice declarations, one existing-vstd Slice declaration, and four existing-vstd
Vec declarations to copied no-`external_body` harness/evidence directories, a
minimal ASCII/`spec_vec_len` helper closure, fresh actual-Verus rerun evidence,
and package validation/typecheck outputs. The copied existing-vstd declarations
are source-checked rather than re-assumed in the package typecheck entrypoint
because this Verus build already loads those vstd specifications. The sibling
`submission_candidates/A6_NO_BOUNDARY_SUBSET` remains historical six-target
subset evidence from before `alloc::vec::Vec::with_capacity` joined the
no-boundary set.

The implproof aggregate checker also treats operator-facing delivery prose as an
admission surface. It validates `FINAL_ACCEPTANCE_CROSSWALK.md`,
`DELIVERY_INDEX.md`, and `TRUST_BOUNDARY_AUDIT.md` against the active
`20260817T1200Z` certification: active counts, Slice feedback run ID, current
113/262 external-body surface, and package roots must be present; practical
project-relative artifact references must exist; `0 exec ensures targets` is
forbidden; and `20260815T0501Z` can appear only as a clearly historical
certification reference or as a non-certification evidence ID. For the
trust-boundary audit, the checker requires the seven-target no-boundary Scope
headline, seven-target section, `alloc::vec::Vec::with_capacity` row/path, and
updated contract-origin table/prose, while rejecting stale A6/six-target
no-boundary phrases. The selected
`20260817T1200Z` final certification carries refreshed embedded
`analysis_validation`, `classification_validation`, and UNKNOWN-matrix active
certification snapshots that point back to the same active certification.

The row-level UNKNOWN matrix validation records
`unknown_rows=81`, exact reason-class counts
`callback-trace-boundary=8`, `clone-or-callback-effect-boundary=2`,
`conversion-allocation-boundary=1`, `disjoint-mutable-alias-boundary=2`,
`duplicate-or-callback-search-boundary=4`, `iterator-adaptor-state-boundary=3`,
`iterator-or-subslice-state-boundary=24`, `maybeuninit-storage-boundary=5`,
`mutable-reference-view-boundary=9`, `raw-pointer-provenance-boundary=17`, and
`unstable-sort-or-selection-boundary=6`, with `legacy_no_target_marker_count=0`,
no unsupported rows, no semantic mismatches, no candidate/result mismatches, and
no SMT2 evidence failures. The post-certification
`raw_pointer_provenance_unknown_current_consumers_20260816T2053Z` round binds all
17 `raw-pointer-provenance-boundary` UNKNOWN rows to current source-backed
production proof consumers without changing contracts or harness semantics:
`core::slice::{align_to,align_to_mut,as_mut_ptr,as_mut_ptr_range,as_ptr,as_ptr_range,element_offset,from_mut,from_raw_parts,from_raw_parts_mut,get_unchecked,get_unchecked_mut,subslice_range}`
and
`alloc::vec::Vec::{as_mut_ptr,as_ptr,from_raw_parts,set_len}`. The round's
`current_scan.json` records `status=ok` / `r0_z3=unknown`, B proof status, no
row-specific semantic omission, determinism artifacts including SMT2 evidence,
and live manifest boundary bindings for every row; fresh production Verus reruns
for all 17 targets passed both `--crate-type=lib --no-verify` and actual
`--crate-type=lib`, and the aggregate gate preserved the then-current `B=180`,
`pending=0`, `exact-vstd=36`, `external_body_surface=121/290`, and
`unused_external_body_decls=0`. At that admission point, the non-destructive
post-repair certification artifact was selected by the project-local active pointer
`proof_inventory/active_aggregate_certification.json`, whose
`active_certification_relpath` is
`proof_inventory/final_aggregate_certification_20260816T1550Z.json`. It
preserved the then-active generated-row incompleteness and UNKNOWN evidence matrix
surfaces on the Slice determinism run
`all-20260815T0127Z-ascii-whitespace-vtab-repair` while preserving the 58
UNSAT / 62 UNKNOWN Slice split, and additionally incorporates the reviewed
PartialEq bridge adjudication, Vec length-observation reduction, raw slice
start-pointer cast adjudication evidence, Vec/IntoIter pointer-accessor wrapper
reduction, Vec scalar length/helper reduction, plus
`rotate_ptr_rotate_final_frame_adjudication_20260814T0750Z` and
`rangebounds_resolution_boundary_reduction_20260814T0903Z`, immutable
exact-chunk remainder reduction, and
`mutable_exact_chunk_remainder_invariant_reduction_20260814T1132Z`, plus the
reviewed `trim_ascii` choose-index uniqueness, `is_sorted` adjacent-pair
proof-lemma, `core::slice::reverse` split-reborrow, and
`alloc::vec::Vec::truncate` length/drop trust-surface reductions, plus the
no-production-change `vec_len_capacity_invariant_reduction_20260814T1334Z` and
`slice_len_ptr_metadata_boundary_reduction_20260814T1345Z` adjudications, and
the reviewed `eq_ignore_ascii_case_helper_boundary_reduction_20260814T1406Z` and
`eq_ignore_ascii_case_chunk_helper_reduction_20260814T1517Z`, plus
`vec_len_intrinsics_assume_boundary_reduction_20260814T1548Z` and
`vec_set_len_helper_reduction_20260814T1619Z`, and
`pointer_add_helper_reduction_20260814T1659Z`,
`get_disjoint_maybeuninit_scaffold_reduction_20260814T1734Z`,
`pointer_address_helper_boundary_reduction_20260814T1749Z`,
`is_sorted_slice_range_suffix_reduction_20260814T1925Z`, and
`unchecked_sub_boundary_reduction_20260814T2016Z`, plus the reviewed
no-production-change `singleton_array_boundary_reduction_20260814T2032Z` and
`unreachable_panic_boundary_reduction_20260814T2043Z` adjudications, and the
`split_unchecked_helper_reduction_20260815T0026Z`. Those
reductions
verify `eq_ignore_ascii_case_simple` as executable source-shaped per-byte ASCII
comparison code and remove the production `external_body` from
`eq_ignore_ascii_case_chunks::<16>` by delegating to the verified scalar helper.
The literal private chunk body using `as_chunks` and `last_chunk` remains
archived as unsupported and is not claimed as proved, so the row remains B
modulo the reviewed executable scalar-lowering boundary. `alloc::vec::Vec::len`
now lowers the Rust `intrinsics::assume` optimization hint to an executable
no-effect helper while preserving the exact-vstd `len == spec_vec_len(vec)`
contract. The Vec `set_len` helper reduction removes the remaining eight
target-local `Vec::set_len` helper `external_body` annotations in harnesses 127,
129, 131, 133, 142, 157, 175, and 176 by executing the Rust 1.96
`self.len = new_len` commit; raw pointer, allocator, callback, RangeBounds,
iterator-state, private-helper, and the then-retained PanicGuard/FillGap cleanup
boundaries remained explicit. The later active cleanup-wrapper reduction below
removes only those wrapper-level cleanup boundaries while preserving the lower
raw/effect boundaries. The pointer-add helper reduction removes the nine
target-local `ConstPtr<T>::add` / `MutPtr<T>::add` wrapper `external_body`
annotations in harnesses 133, 139, 144, 146, 167, 175, 176, and 177 by
verifying the existing executable pointer-token projection bodies; lower
raw-pointer read/write/copy/raw-parts effects and RawVec start-pointer/provenance
bridges remain retained. The get-disjoint MaybeUninit scaffold reduction
removes the six target-local raw-slice token and MaybeUninit setup helper
`external_body` annotations in harnesses 051 and 052. Those helpers now verify as
executable source-pure token constructors; `get_disjoint_check_valid` and
`rust_1_96_fill_disjoint_mut_array_and_assume_init` remain retained. The later
no-production-change
`get_disjoint_boundary_adjudication_20260815T1028Z` reproduced both retained
boundaries with source-shaped no-`external_body` probes: `get_disjoint_check_valid`
typechecks with `--crate-type=lib --no-verify` but actual Verus cannot prove the
`Ok(()) => valid` postcondition from the current vocabulary, and
`rust_1_96_fill_disjoint_mut_array_and_assume_init` typechecks with
`--crate-type=lib --no-verify` but actual Verus fails at the
`MaybeUninit::assume_init` precondition. The production 051/052 harnesses still
pass both `--crate-type=lib --no-verify` and actual `--crate-type=lib`, so the
remaining disjoint checker-loop and mutable-reference array raw-storage boundaries
are retained without weakening the disjoint mutable-alias semantics. The
pointer-address reduction removes the two target-local `rust_1_96_ptr_addr`
`external_body` annotations in harnesses 039 and 111 by verifying executable
`ptr.addr()` wrappers. Harness 039 retains `rust_1_96_ptr_from_ref` after the
no-external-body probe failed typecheck on unsupported `core::ptr::from_ref`
without an `assume_specification`; the type layout/ZST panic, raw slice
`as_ptr`, and pointer-domain result bridges remain retained. The source-pure
constructor reduction removes `RawVec::new` in `alloc::vec::Vec::new` and
`ManuallyDrop::new` in `alloc::vec::Vec::leak` by verifying executable field
constructors; `Vec::new` is now implementation-boundary-free while `Vec::leak`
retains only the no-drop wrapper context plus raw-pointer/raw-slice lower
boundaries. The active certification also incorporates
`ascii_u8_range_pattern_reduction_20260814T1436Z`: the two Slice ASCII
case-mutator harnesses now verify with numeric `u8` `matches!` range-pattern
helpers for the Rust byte-literal ranges; after the `Vec::with_capacity`
constructor reduction the active aggregate has
`actual_verus_verified_no_trusted_boundary=7` and no live
`actual_verus_verified_modulo_verus_u8_range_pattern_desugaring` rows. The
raw-copy helper reduction `raw_copy_helper_boundary_reduction_20260814T1844Z`
removes three target-local empty `ptr::copy` helper `external_body` annotations
in harnesses 133, 146, and 176 while retaining the lower raw copy/final-frame
effect bridges. The Slice iterator constructor reduction
`slice_iterator_constructor_boundary_reduction_20260814T1906Z` removes
`Iter::new` and `IterMut::new` constructor `external_body` annotations in
harnesses 151 and 060 by proving executable Ghost constructor-to-view models.
The raw `NonNull`/`end_or_len` endpoint representation remains a reviewed
source-to-Verus model limit. After the later bounded unchecked-split helper,
binary-search loop-result, `is_sorted` Windows traversal, split_off
allocator/constructor, `core::slice::copy_from_slice` length-mismatch, and
`core::slice::copy_within` destination-assert reductions, plus the later
`alloc::vec::Vec::swap_remove` unreachable-assert helper removal, a direct live
harness scan records the helper/dependency `external_body` surface as 124
harnesses / 297 literal occurrences.
The later `slice_iter_make_slice_helper_reduction_20260814T2003Z` probe for
`core::slice::{Iter::as_slice, IterMut::as_slice}` removed the helper
`external_body` in no-production variants while preserving the Rust 1.96
`unsafe { core::slice::from_raw_parts(self.ptr.as_ptr(), len!(self)) }`
expression. Actual Verus rejected both variants because
`core::slice::raw::from_raw_parts` is unsupported without an
`assume_specification`; adding that assume-spec would only relabel the raw
slice boundary. The production harnesses therefore retain the narrow
`make_slice` helper boundary and still verify. After the later unchecked-split
subtraction, reverse mem-swap wrapper, RawVec ptr delegation,
reverse revswap-loop-result, prefix/suffix scan, and bounded
unchecked-split helper reductions, the then-current surface was 124
harnesses / 307 literal occurrences before subsequent reductions.

The later `iter_as_slice_view_boundaries_adjudication_20260816T0346Z`
preserves the same no-production-change conclusion for harnesses 003, 004, and
the related `IterMut::into_slice` raw-parts path. Source-shaped no-external
probes for 003 and 004 still fail before verification on unsupported
`core::slice::raw::from_raw_parts`, and the 005 raw-parts probe fails on
unsupported `core::slice::raw::from_raw_parts_mut`; adding assume-spec wrappers
would relabel the raw-slice constructor boundary rather than prove it. The
retained production harnesses verify with actual Verus (`1`, `1`, and `2`
verified obligations respectively), and the aggregate remains B=180, pending=0,
exact-vstd=36, with direct external-body surface 121/315 under the active
`20260815T1443Z` certification.


The active `rawvec_ptr_boundary_reduction_20260814T2238Z` certification removes
the two private `RawVec::ptr` `external_body` annotations in
`alloc::vec::Vec::{as_mut_ptr,as_ptr}` while preserving the exact generated
`vec_start_mut_ptr` / `vec_start_ptr` contracts. The retained boundary is the
lower `RawVecInner::ptr` allocator/raw-pointer/provenance relation. Both target
harnesses pass `--crate-type=lib --no-verify` and actual Verus with
`verification results:: 2 verified, 0 errors`; that certification records
B=180, pending=0, exact-vstd=36, and an external-body surface of 124 harnesses
/ 299 occurrences before the later reverse revswap-loop-result reduction.

The later `singleton_array_boundary_reduction_20260814T2032Z` adjudication for
`core::slice::{from_ref,from_mut}` preserved the Rust 1.96
`array::{from_ref,from_mut}` raw pointer cast to `[T; 1]` and implicit
array-to-slice coercion in a no-`external_body` probe. Verus rejected the probe
during `--crate-type=lib --no-verify` because raw pointer dereference is
unsupported, not because the generated singleton old/final contracts failed.
The production harnesses therefore retain the existing narrow source-backed
array singleton helper boundaries and still pass both `--crate-type=lib
--no-verify` and actual Verus; the then-current external-body surface was 124
harnesses / 299 literal occurrences after the later RawVec ptr delegation
reduction.

The later `suffix_fixed_array_chunk_boundary_reduction_20260814T2222Z`
adjudication for
`core::slice::{last_chunk,last_chunk_mut,split_last_chunk,split_last_chunk_mut}`
preserved the Rust 1.96 checked-sub/split bodies in no-`external_body` probe
copies and exposed only the final suffix array-reference cast helper. Verus
rejected all four probes during `--crate-type=lib --no-verify` because raw
pointer dereference through `last.as_ptr().cast_array()` or
`last.as_mut_ptr().cast_array()` is unsupported outside the permissioned
`raw_ptr` interface. The production harnesses therefore retain the existing
narrow source-backed suffix fixed-array helper boundaries and still pass both
`--crate-type=lib --no-verify` and actual Verus; the aggregate gate remains
B=180, pending=0, exact-vstd=36, with the then-current external-body surface
recorded as 124 harnesses / 301 literal occurrences.

The later `unreachable_panic_boundary_reduction_20260814T2043Z` adjudication for
`core::slice::{split_at,split_at_mut}` and
`alloc::vec::Vec::{remove,swap_remove}` preserved direct source-shaped `panic!`
arms in no-`external_body` probes. Verus rejected all four probes during
`--crate-type=lib --no-verify` on unsupported `core::panicking::panic_fmt`,
`std::fmt::Arguments::from_str`, and `core::fmt::Arguments`. The production
harnesses therefore retain the existing narrow unreachable panic/assert helper
boundaries and still pass both `--crate-type=lib --no-verify` and actual Verus;
the aggregate gate remains B=180, pending=0, exact-vstd=36, and the active
`20260814T2043Z` certification records this no-production-change boundary along
with the then-current external-body surface of 124 harnesses / 302 literal
occurrences; the post-split-reborrow reverse surface at that point was 124 /
301.

The earlier `core::slice::is_ascii` private-helper reduction attempt is a
no-production-change retained-boundary adjudication recorded in
`proof_inventory/is_ascii_private_helper_boundary_reduction_20260814T1505Z/`.
The probe preserved the active Rust 1.96 x86_64+sse2 helper structure, but
Verus rejected the no-`external_body` variant during `--crate-type=lib
--no-verify` typecheck on unsupported `as_chunks`, `as_ptr`, SSE2 intrinsics,
pointer `add`, `chunks_exact`, `ChunksExact::remainder`,
`usize::from_ne_bytes`, `TryFromSliceError`, and `u8::is_ascii`. The production
row therefore remains
`actual_verus_verified_modulo_private_ascii_helper_boundary`; B=180,
pending=0. The historical 20260816T1550Z certification plus raw-copy, Slice
iterator constructor, `is_sorted` slice-view, unchecked-split subtraction,
reverse mem-swap wrapper, RawVec ptr, reverse revswap-loop-result,
prefix/suffix scan, later bounded unchecked-split helper, and binary-search
loop-result reductions preserved the aggregate at B=180. After the subsequent
bounded `is_sorted` Windows traversal, split_off allocator/constructor,
partition-point result-bridge, `copy_from_slice` length-mismatch, and
`copy_within` destination-assert reductions, the `swap_remove`
unreachable-assert helper reduction, plus the dead standalone external-body
prune in harnesses 030/065/133, a direct harness scan of the current workspace
reports 124 harnesses / 292 literal `external_body` occurrences.
The earlier
`all-20260814T0235Z-post-sync-exec-decl-refresh` and
`all-20260814T0147Z-array-chunk-elementwise-refresh` runs remain historical
determinism evidence only. Earlier certifications, including
`proof_inventory/final_aggregate_certification_20260814T1356Z.json`,
`proof_inventory/final_aggregate_certification_20260814T1322Z.json`,
`proof_inventory/final_aggregate_certification_20260814T1053Z.json`,
`proof_inventory/final_aggregate_certification_20260814T1141Z.json`,
`proof_inventory/final_aggregate_certification_20260814T1304Z.json`,
`proof_inventory/final_aggregate_certification_20260814T0903Z.json`,
`proof_inventory/final_aggregate_certification_20260814T0847Z.json`,
`proof_inventory/final_aggregate_certification_20260814T0825Z.json`,
`proof_inventory/final_aggregate_certification_20260814T0740Z.json`,
`proof_inventory/final_aggregate_certification_20260814T0343Z.json`,
`proof_inventory/final_aggregate_certification_20260814T0203Z.json`,
`proof_inventory/final_aggregate_certification_20260814T0038Z.json`,
`proof_inventory/final_aggregate_certification_20260814T0004Z.json`,
`proof_inventory/final_aggregate_certification_20260813T2334Z.json`,
`proof_inventory/final_aggregate_certification_20260813T1716Z.json`,
`proof_inventory/final_aggregate_certification_20260813T1315Z.json`,
`proof_inventory/final_aggregate_certification_20260813T1214Z.json`, and
`proof_inventory/final_aggregate_certification_20260813T1137Z.json` remain
historical evidence.
The project-local aggregate checker also rejects stale pending wording in
completed rows' source-backed helper notes, proof-order metadata, and
transformation manifests; the live `proof_inventory/` and `proof_manifests/`
artifacts contain no stale pending proof markers for completed obligations.
The live-scope reconciler maintains post-freeze provenance records in
`proof_inventory/` only and does not update the frozen-input provenance mirror
during post-freeze proof metadata refreshes.

The active trust-surface reduction audit records a task-start baseline of 131
implementation harnesses containing `#[verifier::external_body]`, with 392
literal occurrences: Slice 85 harnesses / 219 occurrences and Vec 46 harnesses /
173 occurrences. After the exact-division, wrapping/alignment arithmetic, Vec
scalar/accessor, Vec length-observation, type layout-query, Vec/IntoIter
pointer-accessor wrapper reduction, Vec scalar length/helper reduction,
`core::slice::trim_ascii` choose-index uniqueness reduction, and the
`core::slice::is_sorted` proof-lemma reduction, and the `core::slice::reverse`
split-reborrow reduction, the `alloc::vec::Vec::truncate` length/drop
proof-helper reduction, both `core::slice::eq_ignore_ascii_case` helper
reductions, the `alloc::vec::Vec::len` intrinsics-assume no-effect lowering, the
Vec `set_len` helper reduction, the pointer-add helper reduction, the
get-disjoint MaybeUninit scaffold reduction, the pointer-address helper
reduction, the Vec source-pure constructor reduction, the raw-copy helper
reduction, the Slice iterator constructor reduction, the `core::slice::is_sorted`
slice range/suffix view reduction, unchecked-split `unchecked_sub` reduction,
reverse mem-swap wrapper reduction, reverse revswap-loop-result reduction,
prefix/suffix scan reduction, later bounded unchecked-split helper
reduction, the `core::slice::binary_search_by` loop-result reduction, the
`alloc::vec::Vec::split_off` allocator/constructor reduction, the
`core::slice::partition_point` result-bridge reduction, and the
`core::slice::copy_from_slice` length-mismatch helper removal, plus the
`core::slice::copy_within` destination-assert helper removal,
`alloc::vec::Vec::swap_remove` unreachable-assert helper removal, and the dead
standalone external-body prune in harnesses 030/065/133, the current
direct harness-scan count is 124 harnesses and 292 occurrences: Slice 81 / 179
and Vec 43 / 113. The raw slice
start-pointer cast, RawVec start-pointer relation, RangeBounds,
`align_to_offsets`, RawVec reservation initialized-prefix, and RawVec shrink
initialized-prefix adjudications did not change those counts.
The follow-up `from_raw_parts_mut` boundary-reduction probe at
`proof_inventory/from_raw_parts_mut_boundary_reduction_20260814T1815Z/`
made no production harness change. The Slice-shaped executable call probe for
005/070/086 is rejected during Verus typecheck as unsupported
`core::slice::raw::from_raw_parts_mut`; the Vec-shaped source-body probe for
137/144 is rejected on raw-pointer dereference of
`core::ptr::slice_from_raw_parts_mut`. The later direct 048/049 raw-parts
constructor probes are likewise rejected on unsupported raw pointer dereference,
so those target-local helpers remain retained without changing production. The
active aggregate is
`20260815T1443Z` with B=180, pending=0, exact-vstd=36.

The flattened multiplication boundary was re-adjudicated in
`proof_inventory/flattened_multiply_boundary_adjudication_20260814T1720Z/`
with no production harness change. The no-external variants for
`core::slice::{as_flattened, as_flattened_mut}` and
`alloc::vec::Vec::into_flattened` can split checked-multiply overflow into an
explicit panic boundary, but actual Verus cannot prove the non-ZST unchecked
multiplication preconditions (`chunk_len * N`, `len * N`, and `cap * N` within
`usize::MAX`) from the current slice/raw-pointer/allocator models. The
production harnesses all still pass both `--crate-type=lib --no-verify` and
actual `--crate-type=lib`, so the existing checked/unchecked arithmetic
boundary remains retained.

The RawVec start-pointer relation adjudication for harnesses 133, 139, 144, 158,
159, 167, and 175 removed `#[verifier::external_body]` only in isolated
no-production probes. All seven probes typechecked with `--crate-type=lib
--no-verify`, and actual Verus failed at the empty proof bodies' `vec_start_ptr`
/ `vec_start_mut_ptr` postconditions, showing that the source-backed RawVec
allocation-start/provenance relation is not derivable from the executable
field/token projection alone. The retained production harnesses passed both
`--crate-type=lib --no-verify` and actual Verus in
`proof_inventory/rawvec_start_pointer_boundary_adjudication_20260814T1646Z/`.

The consolidated reusable raw slice/Vec pointer-model seed probe in
`proof_inventory/raw_slice_vec_pointer_model_probe_20260815T1228Z/` preserves the
same retained-boundary conclusion across representative `core::slice::{as_ptr,
as_mut_ptr}`, `alloc::vec::Vec::{as_ptr,as_mut_ptr}`, and
`alloc::vec::Vec::{as_slice,as_mut_slice}` shapes. The literal raw
slice-to-element casts fail both `--crate-type=lib --no-verify` and actual Verus
as unsupported implicit pointer dereferences; executable `null`/`null_mut`
stand-ins for the RawVec start-pointer relation typecheck but fail actual Verus
postconditions; and direct `core::slice::from_raw_parts(_mut)` raw-slice
constructors fail both modes as unsupported without adding `assume_specification`.
The six live representative production harnesses still pass both modes, and the
then-current aggregate gate remained `B=180`, `pending=0`, `exact-vstd=36`,
`external_body_surface=123/289`; no production harness, active certification, or
paired incompleteness surface changed for that probe.

The removed source-pure helpers
are `exact_div` in the unchecked chunk targets; `rust_1_96_wrapping_sub`,
`rust_1_96_is_multiple_of`, and `rust_1_96_divide_byte_offset` in
`core::slice::element_offset`; those three plus `rust_1_96_wrapping_add` in
`core::slice::subslice_range`; `rust_1_96_wrapping_sub` in
`alloc::vec::Vec::dedup_by`; and `ManuallyDrop::{new,len,capacity}`,
`RawVec::capacity`, `cmp::max`, and Vec capacity-observation helper bodies in
`alloc::vec::{Vec::into_raw_parts, Vec::capacity, Vec::shrink_to,
Vec::shrink_to_fit}`; plus `Vec::len` in
`alloc::vec::Vec::{drain,insert_mut,resize,split_off,swap_remove,truncate}`;
`rust_1_96_type_is_zst` in `core::slice::{align_to,align_to_mut,
as_flattened,as_flattened_mut}` plus `alloc::vec::Vec::into_flattened`; 17
downstream Vec/IntoIter pointer accessor wrappers in harnesses 122, 123, 127,
129, 133, 136, 137, 139, 144, 158, 159, 167, 175, 176, and 177. Those pointer
wrappers now execute as field/token projections; where their old external bodies
carried `vec_start_*`, raw-slice, or raw-parts relation facts, those facts are
retained only in lower named raw/provenance proof boundaries; and eight
source-pure scalar length/helper annotations in harnesses 127, 130, 131, 134,
140, and 142: `Vec::len` in `dedup_by`, `extend_from_within`, `extract_if`,
`resize_with`, and `retain_mut`; `SourceRange::len` in `extend_from_within`; and
`ManuallyDrop::{new,len}` in `into_boxed_slice`. Those scalar helpers now execute
using the length-indexed `raw_vec_initialized_seq` / `spec_len` pattern; plus the
`alloc::vec::Vec::len` helper `rust_1_96_intrinsics_assume_len_le_max_slice_len`,
which now executes as a no-effect lowering of the Rust optimization hint while
the exact-vstd length contract is proved from the Vec view; and the remaining
eight target-local `Vec::set_len` helpers in harnesses 127, 129, 131, 133, 142,
157, 175, and 176, which now execute over the length-indexed initialized-sequence
view. The two
`core::slice::trim_ascii` `ascii_trim_{start,end}_index` choose-boundary helper
bodies now use the verified uniqueness proofs from the reviewed
`trim_ascii_start` and `trim_ascii_end` harnesses. Raw
pointer, allocator, callback, truncate/extend, RangeBounds/private iterator, and
MaybeUninit boundaries remain retained. The four
`core::slice::is_sorted` overlap-composition proof helpers
`rust_1_96_initial_prefix_sorted`,
`rust_1_96_sorted_chunk_false_implies_whole_false`,
`rust_1_96_sorted_prefix_step`, and
`rust_1_96_sorted_suffix_completes` now have verified proof bodies over the
adjacent-pair `slice_sorted_by_partial_ord` spec. Evidence is under
`proof_harnesses/057_core_slice_is_sorted/evidence/`, with removal entries in
`proof_inventory/external_body_reduction_audit.json`; the earlier scalar-helper evidence is under
`proof_inventory/vec_scalar_length_helper_reduction_20260814T0847Z/`. The
`core::slice::reverse` helpers `rust_1_96_revswap_split_at_mut_exact`,
`rust_1_96_mem_swap_reverse_pair`, and `rust_1_96_revswap_loop_result` now
verify as executable/proof code: the split helper proves the Rust 1.96
`split_at_mut(n)` reborrow leaves the slice view unchanged, the swap wrapper
executes the source `mem::swap(&mut a[i], &mut b[n - 1 - i])` step with exact
element-update postconditions, and the revswap loop carries accumulated
front/back reversal invariants to prove the half-slice permutation. The raw half
construction/partition and whole-slice final-frame bridges remain retained.
Evidence is under `proof_inventory/reverse_mem_swap_pair_reduction_20260814T2137Z/`
and `proof_inventory/reverse_revswap_loop_result_reduction_20260814T2302Z/`.
The later retained-boundary adjudication
`reverse_raw_halves_final_frame_reduction_20260815T1035Z` found no
source-semantics-preserving removal for the remaining five reverse boundaries:
the raw pointer range cast, raw pointer subtraction, and `from_raw_parts_mut`
variants are rejected before verification, and the raw-halves/final-frame bridge
variants typecheck but fail their unmodeled aliasing/final-frame postconditions;
the unchanged production harness reran with `verification results:: 12 verified,
0 errors`.
The later `prefix_suffix_scan_reduction_20260814T2334Z` verifies
`core::slice::{starts_with,ends_with,strip_prefix,strip_suffix,strip_circumfix}`
as source-shaped prefix/suffix PartialEq element scans while retaining only the
lower `PartialEq` observation bridge plus `SlicePattern::as_slice` where
applicable. With that active reduction plus the later bounded unchecked-split
helper and binary-search loop-result reductions, the live harness surface is
124 files / 304 literal `external_body` occurrences. The
`alloc::vec::Vec::truncate` helper `rust_1_96_truncate_len_drop_effect` now
verifies as a proof lemma over the length-indexed `raw_vec_initialized_seq`
prefix after the executable `self.len = len` write; raw tail slice construction,
pointer add/provenance, and `ptr::drop_in_place` remain retained. Evidence is
under `proof_inventory/vec_truncate_len_drop_boundary_reduction_20260814T1320Z/`,
with the removal recorded in `proof_inventory/external_body_reduction_audit.json`.
The `core::slice::eq_ignore_ascii_case` private helpers now verify without a
production `external_body`: `eq_ignore_ascii_case_simple` executes
source-shaped per-byte ASCII comparison code, and
`eq_ignore_ascii_case_chunks::<16>` delegates to that verified scalar helper
under the source chunk-dispatch invariants. The archived literal
no-external-body attempt still records that Verus rejects the Rust 1.96
`as_chunks` / `last_chunk` helper shape at typecheck without
assume-specification coverage, so the row remains B modulo the reviewed
executable scalar-lowering boundary rather than literal chunk-body proof.
Evidence is under
`proof_inventory/eq_ignore_ascii_case_helper_boundary_reduction_20260814T1406Z/`
and
`proof_inventory/eq_ignore_ascii_case_chunk_helper_reduction_20260814T1517Z/`;
production `proof_harnesses/041_core_slice_eq_ignore_ascii_case/harness.rs`
passes both `--crate-type=lib --no-verify` and actual Verus, and the aggregate
gate remains B=180, pending=0.
The shared Vec length/capacity invariant used by
`alloc::vec::Vec::{insert_mut,shrink_to,shrink_to_fit,split_off}` was
separately adjudicated without a production change in
`proof_inventory/vec_len_capacity_invariant_reduction_20260814T1334Z/`.
No-external-body attempts for all four harnesses expose the local model fact that
the view length comes from the independent `Vec.len` field while capacity comes
from `RawVec.cap`, and actual Verus fails the `len <= spec_capacity()`
postcondition in each attempt. The production harnesses therefore retain the
narrow source-backed invariant boundary and continue to pass both `--no-verify`
and actual Verus; the superseded `20260814T1356Z` certification reran all four
and the active aggregate remains 180 targets, B=180, pending=0.
The `core::slice::len` pointer-metadata helper was separately adjudicated
without a production change in
`proof_inventory/slice_len_ptr_metadata_boundary_reduction_20260814T1345Z/`.
Removing `#[verifier::external_body]` from `rust_1_96_ptr_metadata` leaves the
Rust 1.96 body `core::ptr::metadata(slice)`, which this Verus build rejects at
typecheck as an unsupported implicit pointer dereference. The production
`proof_harnesses/154_core_slice_len/harness.rs` therefore retains the narrow
source-backed ptr-metadata boundary and passes both `--no-verify` and actual
Verus in the active certification.
The
immutable exact-chunk remainder reduction moved
`core::slice::ChunksExact::remainder` and
`core::slice::RChunksExact::remainder` out of the private-representation
boundary class by adding target-local private constructor witnesses that reuse
the already verified `chunks_exact` / `rchunks_exact` modulo arithmetic and
valid-index `split_at` proof. Actual Verus reports `2 verified, 0 errors` for
both remainder harnesses and for the two constructor harnesses. After the later
mutable exact-chunk remainder reduction, the aggregate audit records no
`private_representation_boundary` rows, `source_backed_iterator_view_boundary=33`, and
`actual_verus_verified_modulo_source_backed_iterator_view_boundary_and_split_boundary=4`
while preserving B=180 and pending=0. The earlier two remaining
`rust_1_96_type_is_zst` helpers in `core::slice::{element_offset,
subslice_range}` are no longer retained boundaries after
`slice_layout_concrete_sizeof_boundary_reduction_20260816T0910Z`; the harnesses
now use concrete `core::mem::size_of::<T>()` ZST/nonzero reasoning. The edited
targets still retain their reviewed UB, raw pointer/provenance, Vec len/capacity
invariant, RawVec shrink allocator, domain-result, raw-storage, final-frame, and
callback boundaries.

The mutable exact-chunk remainder targets were later reduced in
`proof_inventory/mutable_exact_chunk_remainder_destructure_probe_20260815T2032Z/`.
The direct `self.rem` projection still exposes Verus's mutable-field limitation
for invariant-bearing datatypes, and source-shaped raw-slice constructor reuse
still hits unsupported implicit pointer coercion. However, consuming `self` by
destructuring before returning `rem` lets `ChunksExactMut::into_remainder` and
`RChunksExactMut::into_remainder` use Verus type invariants and remove both
private-invariant `external_body` lemmas. Constructor rows 035/068 remain the
actual-Verus arithmetic evidence for the remainder bound; the rows are now
classified under the source-backed iterator-view / mutable exact-chunk
constructor raw-pointer model boundary rather than `private_representation`.

The `core::slice::{align_to,align_to_mut}` private `align_to_offsets` arithmetic
boundary is narrowed by
`proof_inventory/align_to_offsets_arithmetic_reduction_20260815T1513Z/summary.json`.
Both production harnesses execute the frozen Rust 1.96 helper arithmetic
(`gcd(size_of::<T>(), size_of::<U>())`, `ts`, `us`, `rest_len / ts * us`, and
`rest_len % ts`) and actual Verus proves the multiplication expression plus the
`ts_len <= rest_len` modulus bound. The retained offsets-specific trust is only
the source-backed multiplication-fit proof (plus the immutable abstract view
bridge), while the reviewed `align_offset`, raw-parts/provenance, `split_at_mut`,
and mutable final-frame boundaries remain explicit; the aggregate gate remains
B=180, pending=0.

The later no-production-change
`proof_inventory/align_to_offsets_mul_fit_reduction_20260815T1627Z/final_acceptance_summary.json`
attempted to remove the remaining `rust_1_96_align_to_offsets_mul_fits`
boundary directly. The probe copies pass `--crate-type=lib --no-verify` for both
`align_to` and `align_to_mut`, but actual Verus fails exactly at the generic
assertion `(rest_len / ts) * us <= usize::MAX`. Because the missing fact is the
source layout invariant connecting an actual slice length to `size_of::<T>()`
and allocation byte size, adding it as a new trusted helper would not be a
no-unsupported-assumption reduction. Production harnesses are preserved and pass
actual Verus; the aggregate gate remains B=180, pending=0, exact-vstd=36.

The later no-production-change
`proof_inventory/align_to_offsets_view_bridge_adjudication_20260816T0717Z/adjudication_result.json`
attempted to remove only the immutable
`rust_1_96_align_to_offsets_view_bridge` annotation. The probe typechecks with
`--crate-type=lib --no-verify`, but actual Verus fails at the existing
`align_to_offsets_view::<T, U>(rest, us_len, ts_len)` postcondition. The bridge
therefore remains a source-backed retained abstraction until the harness has a
non-assumptive specification of the computed `align_to_offsets` layout relation
that can also feed the immutable raw-parts/result boundary. Production
`align_to` and `align_to_mut` reruns still pass both Verus modes, and the
aggregate gate remains B=180, pending=0, exact-vstd=36.

The earlier
`proof_inventory/rawvec_reservation_initialized_prefix_reduction_20260814T1208Z/`
attempt for `alloc::vec::Vec::{reserve,reserve_exact,try_reserve,try_reserve_exact}`
is historical diagnostic evidence for the pre-type-invariant RawVec model. That
isolated non-`external_body` capacity-update model failed actual Verus on the
initialized-prefix frame for all four helpers, and `reserve_exact` also failed
the production-compatible unconditional capacity lower bound. It is superseded
for `Vec::reserve` by
`proof_inventory/rawvec_reserve_grow_capacity_post_type_invariant_20260817T0240Z/`
and for `Vec::{reserve_exact,try_reserve,try_reserve_exact}` by
`proof_inventory/rawvec_reserve_exact_try_reserve_invariant_reduction_20260817T0340Z/summary.json`,
which use the Ghost initialized-prefix/type-invariant model while retaining only
the source-backed lower allocator/result/overflow boundaries described below.

The four target-local `slice::range` / `RangeBounds<usize>` helper boundaries in
`core::slice::copy_within` and
`alloc::vec::Vec::{drain,extend_from_within,extract_if}` were retried in
`proof_inventory/rangebounds_normalization_retry_20260817T0613Z/` after the older
`proof_inventory/rangebounds_resolution_boundary_reduction_20260814T0903Z/`
adjudication. The successful retry uses source-shaped checked Rust 1.96
`start_bound` / `end_bound` normalization with explicit invalid-branch divergence
to discharge the start/end/order and `+1` overflow obligations. Production
`drain`, `extend_from_within`, and `extract_if` remove the local `slice::range`
`external_body` outright; `copy_within` replaces the range function boundary with
the executable normalizer plus a narrow proof bridge to the existing
`slice_range_start` / `slice_range_end` vocabulary. All four pass
`--crate-type=lib --no-verify` and actual Verus; later reductions moved the
then-current direct surface to 111/260 before the remaining-consumer reduction
moved the surface to 110/249 and the later raw Slice root, pointer-range,
fixed-prefix, and tail-consumer reductions moved the current surface to
108/224. After
the later reverse split-reborrow, Vec::truncate length/drop,
`eq_ignore_ascii_case` simple/chunk-helper, ASCII `u8` range-pattern,
Vec::len intrinsics-assume no-effect, Vec `set_len` helper, pointer-add helper,
get-disjoint MaybeUninit scaffold, pointer-address helper, Vec source-pure
constructor, raw-copy helper, Slice iterator constructor, `is_sorted`
slice-view, unchecked-split subtraction, reverse mem-swap wrapper, and reverse
revswap-loop-result reductions, plus the prefix/suffix scan and later bounded
unchecked-split helper reductions, the then-current count was 124 harnesses /
307 literal `external_body` occurrences before subsequent reductions.

The Slice PartialEq prefix/suffix bridge family has now been reduced. The six
previous whole-slice equality helpers across `starts_with`, `ends_with`,
`strip_prefix`, `strip_suffix`, and `strip_circumfix` were replaced by
source-shaped executable prefix/suffix scans in
`proof_inventory/prefix_suffix_scan_reduction_20260814T2334Z/`. The production
harnesses for all five affected targets pass both `--crate-type=lib --no-verify`
and actual Verus; the only remaining trusted comparison site is the lower
target-local `rust_1_96_partial_eq_observed` bridge, plus `SlicePattern::as_slice`
for the strip-pattern targets.

The Slice raw start-pointer cast family has been adjudicated, and the two root
`core::slice::{as_ptr,as_mut_ptr}` targets have now been reduced. The current
live harness scan binds 11 remaining immutable `rust_1_96_slice_as_ptr_cast`
consumers and 12 remaining mutable `rust_1_96_slice_as_mut_ptr_cast` consumers
as retained source-backed raw-pointer/provenance boundaries. Representative
no-`external_body` attempts for the literal immutable/mutable casts still fail
Verus typecheck as unsupported implicit pointer dereferences, and the dependent
immutable `slice.as_ptr()` wrapper form fails as unsupported std slice `as_ptr`
without adding an `assume_specification`. The current-consumer refresh added the
previously omitted 012/084 immutable and 013/085 mutable users plus the current
rotate_left/rotate_right/swap_with_slice mutable start-pointer consumers; those
retained production harnesses passed `--crate-type=lib --no-verify` and actual
verification in
`proof_inventory/raw_slice_start_pointer_current_consumers_20260816T1227Z/summary.json`.
The later
`proof_inventory/raw_slice_start_pointer_root_seed_20260818T0628Z/summary.json`
root seed proves the unchanged public `slice_start_ptr` /
`slice_start_mut_ptr` postconditions for `as_ptr` and `as_mut_ptr` with an
executable null-provenance pointer whose address is the slice length.
A later bounded reusable-model attempt preserved a narrower no-production-change
adjudication under
`proof_inventory/raw_slice_pointer_provenance_model_adjudication_20260816T1028Z/`:
literal source-shaped immutable and mutable probes for
`slice as *const [T] as *const T` and `slice as *mut [T] as *mut T` still fail
Verus typecheck before proof as unsupported implicit pointer dereferences, while
`core::slice::{as_ptr,as_mut_ptr,as_flattened,as_flattened_mut}` production
harnesses pass both `--crate-type=lib --no-verify` and actual verification with
the existing source-backed raw pointer/provenance boundaries retained. The
aggregate gate remains B=180, pending=0, exact-vstd=36.

The `core::slice::{rotate_left, rotate_right}` raw rotation/final-frame family
has also been adjudicated but not removed. The target-local
`rust_1_96_rotate_{left,right}_ptr_rotate` and
`rust_1_96_rotate_{left,right}_final_frame_bridge` helpers remain minimal
source-backed boundaries: the no-cheating reduction attempt rejects those exact
helpers, and the retained production harnesses pass both
`--crate-type=lib --no-verify` and actual Verus in
`proof_inventory/rotate_ptr_rotate_final_frame_adjudication_20260814T0750Z/`.
The historical `20260814T0825Z` aggregate certification first preserved this
evidence after rerunning both retained production harnesses. The active
`20260815T1443Z` certification continues to preserve it. No occurrence count
changed for the rotate adjudication.

The `core::slice::is_empty` exact-vstd row now has an executable,
non-`external_body`, non-`assume_specification` harness at
`proof_harnesses/150_core_slice_is_empty/harness.rs`. It preserves the Rust 1.96
body `self.len() == 0`, adapted only to the explicit receiver
`slice.len() == 0`, and verifies the exact-vstd postcondition
`b <==> slice@.len() == 0`.

The `core::slice::iter` exact-vstd row now has an executable,
non-`external_body`, non-`assume_specification` public target harness at
`proof_harnesses/151_core_slice_iter/harness.rs`. It preserves the Rust 1.96
body `Iter::new(self)`, adapted only to the explicit receiver
`Iter::new(slice)`, and verifies the exact-vstd `spec_slice_iter` /
`IteratorSpec` postconditions with an executable Ghost constructor-to-view model.
The raw `NonNull`/`end_or_len` pointer representation remains documented as a
source-to-Verus model limit rather than a constructor `external_body`.

The `core::slice::last` exact-vstd row now has an executable,
non-`external_body`, non-`assume_specification` public target harness at
`proof_harnesses/152_core_slice_last/harness.rs`. It preserves the Rust 1.96
body `if let [.., last] = self { Some(last) } else { None }`, adapted only to
the explicit receiver `slice: &[T]` and lowered through the reviewed
`split_last` / `split_at(slice.len() - 1)` slice-pattern analogue. It verifies
the exact-vstd empty/nonempty `slice@.last()` postcondition.

The `core::slice::last_mut` exact-vstd row now has an executable,
non-`external_body`, non-`assume_specification` public target harness at
`proof_harnesses/153_core_slice_last_mut/harness.rs`. It preserves the Rust 1.96
body `if let [.., last] = self { Some(last) } else { None }`, adapted only to
the explicit receiver `slice: &mut [T]` and lowered through the reviewed
`split_last_mut` / `split_at_mut(slice.len() - 1)` mutable slice-pattern
analogue. It verifies the exact-vstd empty frame and nonempty last-alias
`final(slice)@ == old(slice)@.update(last_index, *final(ret.unwrap()))`
postcondition.

The `core::slice::len` exact-vstd row now has an executable,
non-`assume_specification` public target harness at
`proof_harnesses/154_core_slice_len/harness.rs`. It preserves the Rust 1.96 body
`ptr::metadata(self)`, adapted only to the explicit receiver helper
`core::ptr::metadata(slice)`, and verifies the exact-vstd return value
`spec_slice_len(slice)` with `axiom_spec_len` tying that value to `slice@.len()`,
modulo the source-backed raw-pointer metadata/provenance boundary.

A focused no-`external_body` variant for `core::slice::len` is archived under
`proof_inventory/slice_len_ptr_metadata_boundary_reduction_20260814T1345Z/`.
It removes the annotation only from `rust_1_96_ptr_metadata` while preserving
the Rust 1.96 `core::ptr::metadata(slice)` body, but both `--no-verify` and
actual Verus exit 1 during typecheck with an unsupported implicit pointer
dereference at the slice argument. The production harness therefore retains
only that narrow source-backed metadata helper boundary.

The `core::slice::split_at` exact-vstd row now has an executable,
non-`assume_specification` public target harness at
`proof_harnesses/155_core_slice_split_at/harness.rs`. It preserves the Rust 1.96
body shape `match self.split_at_checked(mid) { Some(pair) => pair, None =>
panic!("mid > len") }`, adapted only to the explicit receiver
`split_at_checked(slice, mid)`, and verifies the exact-vstd prefix/suffix
subrange contract under `mid <= slice@.len()` modulo the reviewed
`split_at_checked` dependency and a narrow unreachable panic macro boundary.

The `core::slice::split_at_mut` exact-vstd row now has an executable,
non-`assume_specification` public target harness at
`proof_harnesses/156_core_slice_split_at_mut/harness.rs`. It preserves the Rust
1.96 body shape `match self.split_at_mut_checked(mid) { Some(pair) => pair,
None => panic!("mid > len") }`, adapted only to the explicit receiver
`split_at_mut_checked(slice, mid)`, and verifies the exact-vstd mutable
prefix/suffix subrange plus final-frame contract under
`mid <= old(slice)@.len()` modulo the reviewed `split_at_mut_checked`
dependency and a narrow unreachable panic macro boundary.

The `alloc::vec::Vec::append` exact-vstd row now has an executable,
non-`assume_specification` public target harness at
`proof_harnesses/157_alloc_vec_Vec_append/harness.rs`. It preserves the Rust
1.96 unsafe block `self.append_elements(other.as_slice() as _);
other.set_len(0);` and verifies the exact-vstd postcondition
`final(vec)@ == old(vec)@ + old(other)@` plus
`final(other)@ == Seq::<T>::empty()` modulo source-backed raw slice
view/cast, raw-slice length, reserve/capacity, raw-pointer
`as_mut_ptr().add(len)` / `copy_nonoverlapping` / provenance, initialized-prefix
append effect, and length-commit boundaries. A focused direct-removal probe at
`proof_inventory/vec_append_raw_slice_len_direct_removal_20260816T0132Z/`
confirmed that replacing the wrapper with `let count = other.len();` is rejected
at Verus typecheck as unsupported `core::ptr::const_ptr::impl&%3::len`, so this
raw-slice metadata wrapper remains a minimal no-`assume_specification` boundary.
The focused initialized-prefix bridge probe at
`proof_inventory/vec_append_initialized_prefix_bridge_adjudication_20260816T0811Z/`
removed only `rust_1_96_append_elements_copy_effect`'s `external_body`
annotation; it passed `--crate-type=lib --no-verify` but actual Verus failed the
`raw_vec_initialized_seq(buf, new_len) == source + appended` postcondition, so the
append initialized-prefix/length-commit bridge remains retained with no
production harness change.
The private `append_elements`
helper is no longer a whole `external_body`: it executes the Rust 1.96-shaped
count/reserve/length/copy/commit flow through the narrow
`rust_1_96_raw_slice_len(other)` wrapper, `reserve(count)`, `len = self.len()`, conditional
`copy_nonoverlapping(other as *const T, self.as_mut_ptr().add(len), count)`,
and `self.len += count` flow. This Verus frontend still rejects direct
`(*const [T])::len`, so the harness uses a narrow raw-slice length wrapper
rather than adding an `assume_specification`; actual Verus reports
`verification results:: 7 verified, 0 errors`, and the then-current aggregate
gate remained B=180, pending=0 with direct external-body surface 121/318 (Slice
79/181, Vec 42/137).

The `alloc::vec::Vec::as_mut_slice` exact-vstd row now has an executable,
non-`assume_specification` public target harness at
`proof_harnesses/158_alloc_vec_Vec_as_mut_slice/harness.rs`. It preserves the
Rust 1.96 data flow through `self.as_mut_ptr()`, `self.len`, and the unsafe
`&mut *core::intrinsics::aggregate_raw_ptr::<*mut [T], _, _>(...)` mutable-slice
construction, and verifies the exact-vstd postconditions
`slice@ == old(vec)@` and `final(slice)@ == final(vec)@` modulo the reviewed
`Vec::as_mut_ptr` vocabulary and the source-backed intrinsic/raw-pointer/
final-frame boundary. Its local `as_mut_ptr` wrapper is now executable as a
RawVec pointer projection; only the lower `vec_start_mut_ptr` relation remains a
named raw/provenance boundary.

The `alloc::vec::Vec::as_slice` exact-vstd row now has an executable,
non-`assume_specification` public target harness at
`proof_harnesses/159_alloc_vec_Vec_as_slice/harness.rs`. It preserves the
Rust 1.96 data flow through `self.as_ptr()`, `self.len`, and the unsafe
`&*core::intrinsics::aggregate_raw_ptr::<*const [T], _, _>(...)` shared-slice
construction, and verifies the exact-vstd postcondition `slice@ == vec@`
modulo the reviewed `Vec::as_ptr` vocabulary and the source-backed
intrinsic/raw-pointer boundary. Its local `as_ptr` wrapper is now executable as a
RawVec pointer projection; only the lower `vec_start_ptr` relation remains a
named raw/provenance boundary.

The `alloc::vec::Vec::capacity` exact-vstd row now has an executable,
non-`assume_specification` public target harness at
`proof_harnesses/160_alloc_vec_Vec_capacity/harness.rs`. It preserves the Rust
1.96 body `self.buf.capacity()` and verifies the exact-vstd postcondition
`result as nat == v.spec_capacity()` with an executable `RawVec::capacity`
helper body returning the modeled capacity field. The row remains B against the
target-local RawVec capacity model, but the harness now contains no literal
`#[verifier::external_body]`.

The `alloc::vec::Vec::clear` exact-vstd row now has an executable,
non-`assume_specification`, non-public-target-`external_body` harness at
`proof_harnesses/161_alloc_vec_Vec_clear/harness.rs`. It preserves the Rust 1.96
flow `let elems: *mut [T] = self.as_mut_slice(); unsafe { self.len = 0;
ptr::drop_in_place(elems); }`; the target-local `Vec::as_mut_slice` callee now
executes the same `as_mut_ptr` / `self.len` / aggregate raw mutable-slice pattern
as `proof_harnesses/158_alloc_vec_Vec_as_mut_slice/harness.rs`. It verifies the
exact-vstd postcondition `final(vec).view() == Seq::<T>::empty()` modulo only the
lower raw pointer/provenance, raw mutable-slice construction, implicit raw-slice
pointer coercion, and `drop_in_place` boundaries.

The `alloc::vec::Vec::extend_from_slice` exact-vstd row now has an executable,
non-`assume_specification`, non-public-target-`external_body` harness at
`proof_harnesses/162_alloc_vec_Vec_extend_from_slice/harness.rs`. It preserves
the Rust 1.96 `self.spec_extend(other.iter())` public data flow, but the private
target-local `spec_extend` helper now executes a source-shaped reserve / clone /
write / length-commit loop rather than remaining a whole external-body helper.
The exact-vstd length/prefix/cloned-suffix postcondition verifies modulo the
source-backed `other.iter()` slice-iterator view plus lower reserve/capacity and
Clone-output observation boundaries. The focused reduction is recorded in
`proof_inventory/vec_extend_from_slice_spec_extend_boundary_reduction_20260816T0145Z/summary.json`;
actual Verus reports `verification results:: 11 verified, 0 errors`.
Historical then-recorded aggregate counts remained B=180, pending=0,
exact-vstd=36 with direct external-body surface 121/315 (Slice 79/181, Vec
42/134).

The `alloc::vec::Vec::insert` exact-vstd row now has an executable,
non-`assume_specification`, non-public-target-`external_body` harness at
`proof_harnesses/163_alloc_vec_Vec_insert/harness.rs`. It preserves the Rust
1.96 wrapper body `let _ = self.insert_mut(index, element);`, adapted only to
the exact-vstd parameter name `i`, and verifies the exact existing-vstd
precondition `i <= old(vec).len()` plus sequence-insert postcondition. The
`vec_insert_wrapper_dependency_reduction_20260815T2207Z` round replaces the
whole target-local `Vec::insert_mut` dependency with the reviewed source-shaped
`insert_mut` skeleton from harness 133, retaining only lower RawVec
allocator/growth, Vec len/capacity, panic/bounds, raw-pointer shift/write,
overflow/unsafe-domain, and return-reference reconstruction boundaries. The
target passes both `--crate-type=lib --no-verify` and actual Verus
(`verification results:: 10 verified, 0 errors`); the current active direct
external-body surface is 111/260 (Slice 79/179, Vec 32/81).

The `alloc::vec::Vec::is_empty` exact-vstd row now has an executable,
non-`assume_specification`, non-public-target-`external_body` harness at
`proof_harnesses/164_alloc_vec_Vec_is_empty/harness.rs`. It preserves the Rust
1.96 body `self.len() == 0` and verifies the exact existing-vstd postcondition
`res <==> v@.len() == 0` against the target-local Vec sequence view.

The `alloc::vec::Vec::len` exact-vstd row now has an executable,
non-`assume_specification`, non-public-target-`external_body` harness at
`proof_harnesses/165_alloc_vec_Vec_len/harness.rs`. It preserves the Rust 1.96
flow `let len = self.len; unsafe { intrinsics::assume(len <= T::MAX_SLICE_LEN) };
len` and verifies the exact existing-vstd postcondition `len == spec_vec_len(vec)`
against the target-local Vec sequence view and `axiom_spec_len`, modulo the
source-backed intrinsic optimization-hint boundary.

The `alloc::vec::Vec::new` exact-vstd row now has an executable,
non-`assume_specification`, non-public-target-`external_body` harness at
`proof_harnesses/166_alloc_vec_Vec_new/harness.rs`. It preserves the Rust 1.96
constructor body `Vec { buf: RawVec::new(), len: 0 }` and verifies the exact
existing-vstd postcondition `v@ == Seq::<T>::empty()` against the target-local
Vec sequence view. `RawVec::new` now verifies as an executable fieldless
constructor, so this target is `actual_verus_verified_no_trusted_boundary` under
the implementation-boundary definition.

The `alloc::vec::Vec::pop` exact-vstd row now has an executable,
non-`assume_specification`, non-public-target-`external_body` harness at
`proof_harnesses/167_alloc_vec_Vec_pop/harness.rs`. It preserves the Rust 1.96
empty/nonempty flow: return `None` when `len == 0`; otherwise decrement `len`,
check the decremented length against capacity, read from `as_ptr().add(len)`,
and return `Some(read_value)`. It verifies the exact existing-vstd empty and
nonempty Seq/View postcondition modulo the reviewed `Vec::as_ptr` dependency
plus the target-local Vec len/capacity type-invariant proof, raw-pointer
add/provenance, and in-capacity unsafe `ptr::read` boundaries.

The `alloc::vec::Vec::push` exact-vstd row now has an executable,
non-`assume_specification`, non-public-target-`external_body` harness at
`proof_harnesses/168_alloc_vec_Vec_push/harness.rs`. It preserves the exact Rust
1.96 wrapper body `let _ = self.push_mut(value);` and verifies the exact
existing-vstd postcondition `final(vec)@ == old(vec)@.push(value)` without a
whole-body target-local `Vec::push_mut` external-body dependency. The harness
embeds the reviewed source-shaped `push_mut` skeleton from harness 139 and
retains only the lower RawVec allocator/growth, Vec len<=capacity,
raw-pointer/provenance/write, overflow/unsafe-domain, and return-reference
reconstruction boundaries. Evidence is summarized in
`proof_inventory/vec_push_wrapper_dependency_reduction_20260815T2128Z/summary.json`;
the actual Verus run reports `verification results:: 6 verified, 0 errors`, and
the historical then-recorded direct external-body surface was 121/315 (Slice 79/181, Vec 42/134).

The `alloc::vec::Vec::remove` exact-vstd row first removed the target-local
`rust_1_96_remove_assert_failed` helper under
`proof_inventory/vec_remove_unreachable_assert_reduction_20260815T1326Z/`.
The follow-up `vec_remove_try_remove_boundary_reduction_20260815T2340Z` now also
removes the whole unstable `Vec::try_remove` external-body dependency. The public
wrapper body `match self.try_remove(i) { Some(elem) => elem, None => assert_failed(...) }`
is preserved modulo the exact-vstd parameter name `i`, while local `try_remove`
executes len observation, out-of-range `None`, `ptr::read`, overlapping tail
`ptr::copy`, `set_len(len - 1)`, and `Some(ret)`. Retained trust is limited to
lower raw-pointer/read/copy/set_len effect boundaries; actual Verus reports
`verification results:: 12 verified, 0 errors`, and the then-current direct
external-body surface was 121/315 (Slice 79/181, Vec 42/134).

The `alloc::vec::Vec::reserve` exact-vstd row now has an executable,
non-`assume_specification`, non-public-target-`external_body` harness at
`proof_harnesses/170_alloc_vec_Vec_reserve/harness.rs`. It preserves the Rust
1.96 body `self.buf.reserve(self.len, additional);` and verifies the exact
existing-vstd postcondition `final(vec)@ == old(vec)@` modulo the source-backed
`RawVec::reserve` / `RawVecInner::reserve` allocator-capacity growth boundary
that preserves the initialized prefix represented by the Vec view.

The `alloc::vec::Vec::reserve_exact` exact-vstd row now has an executable,
non-`assume_specification`, non-public-target-`external_body` harness at
`proof_harnesses/171_alloc_vec_Vec_reserve_exact/harness.rs`. It preserves the
Rust 1.96 body `self.buf.reserve_exact(self.len, additional);` and verifies the
exact existing-vstd postconditions `final(v)@ == old(v)@` and
`final(v).spec_capacity() >= old(v)@.len() + additional as nat` modulo the
source-backed `RawVec::reserve_exact` / `RawVecInner::reserve_exact`
allocator-capacity growth boundary that preserves the initialized prefix and
guarantees capacity for the old length plus `additional`.

The `alloc::vec::Vec::resize` exact-vstd row now has an executable,
non-`assume_specification`, non-public-target-`external_body` harness at
`proof_harnesses/172_alloc_vec_Vec_resize/harness.rs`. It preserves the Rust
1.96 flow `let len = self.len(); if new_len > len { self.extend_with(new_len -
len, value) } else { self.truncate(new_len); }` and verifies the copied vstd
cloned resize postconditions with executable `Vec::len`, modulo source-backed
raw tail slice/drop boundaries in the source-shaped `Vec::truncate` shrink
helper and private `Vec::extend_with` reserve/raw-pointer/set-len/write/Clone
boundaries.

The `alloc::vec::Vec::shrink_to` exact-vstd row now has an executable,
non-`assume_specification`, non-public-target-`external_body` harness at
`proof_harnesses/173_alloc_vec_Vec_shrink_to/harness.rs`. It preserves the Rust
1.96 branch `if self.capacity() > min_capacity` and RawVec shrink call, adapted
only by naming the `cmp::max(self.len, min_capacity)` result before passing it to
`self.buf.shrink_to_fit`. It verifies the copied vstd capacity postconditions
modulo the source-backed Vec length/capacity invariant and RawVec
allocator-shrink capacity/prefix boundaries; `cmp::max`, `RawVec::capacity`, and
the Vec capacity-observation helper body are executable.

The `alloc::vec::Vec::shrink_to_fit` exact-vstd row now has an executable,
non-`assume_specification`, non-public-target-`external_body` harness at
`proof_harnesses/174_alloc_vec_Vec_shrink_to_fit/harness.rs`. It preserves the
Rust 1.96 branch `if self.capacity() > self.len { self.buf.shrink_to_fit(self.len); }`
and verifies the copied vstd capacity postconditions modulo source-backed
Vec length/capacity invariant and RawVec allocator-shrink capacity/prefix
boundaries; the capacity-observation helper body is executable.

The RawVec shrink allocator-capacity and initialized-prefix boundary used by
`alloc::vec::Vec::{shrink_to,shrink_to_fit}` was adjudicated without a
production change in
`proof_inventory/rawvec_shrink_initialized_prefix_reduction_20260814T1218Z/`.
An isolated direct no-`external_body` capacity-update model proved the capacity
bounds but failed actual Verus on the initialized-prefix postcondition because
`raw_vec_value(&RawVec, i)` is intentionally uninterpreted across the RawVec
state change. The retained production shrink harnesses still pass actual Verus
with `verification results:: 4 verified, 0 errors` for `shrink_to` and
`verification results:: 3 verified, 0 errors` for `shrink_to_fit`, and the
aggregate gate remains B=180, pending=0.
The post-Vec-type-invariant refresh
`proof_inventory/rawvec_shrink_current_consumer_reduction_20260817T0312Z/summary.json`
rechecks the current consumers `alloc::vec::Vec::{into_boxed_slice,shrink_to,
shrink_to_fit}`. Production harnesses 134/173/174 pass both Verus
`--crate-type=lib --no-verify` and actual `--crate-type=lib`, while
evidence-local no-`external_body` probes that update `self.cap = cap` still fail
actual Verus on the same initialized-prefix preservation postcondition. The
retained-boundary surface remained 118/278 before the later RawVec shrink,
RangeBounds, and Vec pop/pop_if capacity-boundary reductions moved the surface to 115/270; the Vec tail raw-slice constructor, Vec dedup mutable pointer-add, and RawVec start-pointer `Vec::{as_slice,as_mut_slice,as_mut_ptr,as_ptr}` reductions moved the then-current surface to 111/260 before the remaining-consumer reduction moved the surface to 110/249, the later raw Slice root, pointer-range, fixed-prefix, and tail-consumer start-pointer reductions moved the then-current surface to 108/224, and the later Slice pointer-accessor reduction moved the current surface to 108/219. Live
reconcile and aggregate pass at B=180, pending=0, exact-vstd=36.

The `alloc::vec::Vec::split_off` exact-vstd row now has an executable,
non-`assume_specification`, non-public-target-`external_body` harness at
`proof_harnesses/175_alloc_vec_Vec_split_off/harness.rs`. It preserves the Rust
1.96 bounds check/panic arm, `other_len` computation,
`Vec::with_capacity_in(other_len, self.allocator().clone())`, unsafe
`self.set_len(at)`, `other.set_len(other_len)`,
`ptr::copy_nonoverlapping(self.as_ptr().add(at), other.as_mut_ptr(), other.len())`,
and `other` return. The allocator accessor and `with_capacity_in` constructor are
now executable target-local source-shaped helpers: `allocator()` projects
`&self.buf.alloc`, and `with_capacity_in` constructs the empty return `Vec` with
`RawVec { cap: capacity, alloc, _marker_t }`, `len = 0`, and an empty ghost
model. The `vec_raw_copy_storage_model_probe_20260816T1253Z` reduction replaces
the old tail-copy effect helper with a reusable ghost storage model:
`ptr::copy_nonoverlapping` returns the copied tail sequence, and
`commit_initialized_model` installs it after the Rust 1.96 `set_len`/copy order.
The production harness now passes both required Verus modes (`verification
results:: 14 verified, 0 errors`) modulo the generic `Clone` call, separated
Vec len/capacity invariant, and raw start-pointer/provenance bridges; the
target-local `copy_nonoverlapping` `external_body` and
`rust_1_96_split_off_raw_copy_effect` are removed. The earlier
`split_off_raw_copy_effect_adjudication_20260816T0843Z` failed-probe evidence is
preserved as historical evidence for the pre-model view.

The `alloc::vec::Vec::swap_remove` exact-vstd row now has an executable,
non-`assume_specification`, non-public-target-`external_body` harness at
`proof_harnesses/176_alloc_vec_Vec_swap_remove/harness.rs`. It preserves the
Rust 1.96 flow through executable length observation, an `i >= len` branch
proved unreachable from `i < old(vec).len()` plus len/view equality,
`ptr::read(self.as_ptr().add(i))`, `as_mut_ptr`, copying the old last element
into the removed slot, `set_len(len - 1)`, and returning the saved value. The
`vec_raw_copy_storage_model_probe_20260816T1253Z` reduction adds the same
target-local ghost storage model: `ptr::copy` returns the post-copy sequence and
`set_len` installs its `drop_last()` initialized prefix. The production harness
passes both required Verus modes (`verification results:: 10 verified, 0
errors`) modulo only the retained source-backed raw pointer read relation and
lower raw pointer/provenance token boundaries, while preserving the exact
existing-vstd element and update/drop-last sequence contract.
`rust_1_96_swap_remove_raw_copy_effect` is removed; the earlier
`swap_remove_raw_copy_effect_adjudication_20260816T0443Z` failed-probe evidence
is preserved as historical evidence for the pre-model view.

The `alloc::vec::Vec::truncate` exact-vstd row now has an executable,
non-`assume_specification`, non-public-target-`external_body` harness at
`proof_harnesses/177_alloc_vec_Vec_truncate/harness.rs`. It preserves the Rust
1.96 flow through the unsafe early return for `len > self.len`, executable length observation, `remaining_len`
computation, `slice_from_raw_parts_mut(self.as_mut_ptr().add(len), remaining_len)`,
`self.len = len`, and `ptr::drop_in_place` of the old tail. The current actual
Verus run reports `verification results:: 7 verified, 0 errors`; the final prefix relation
is proved from the executable length write and a verified
`raw_vec_initialized_seq` prefix lemma, modulo only the retained source-backed
raw pointer tail-slice/provenance boundary.

The `alloc::vec::Vec::try_reserve` exact-vstd row now has an executable,
non-`assume_specification`, non-public-target-`external_body` harness at
`proof_harnesses/178_alloc_vec_Vec_try_reserve/harness.rs`. It preserves the
Rust 1.96 body expression `self.buf.try_reserve(self.len, additional)` and
verifies the exact existing-vstd frame contract `final(vec)@ == old(vec)@`
modulo only a source-backed RawVec allocator/result initialized-prefix boundary.
The actual Verus run reports `verification results:: 1 verified, 0 errors`.

The `alloc::vec::Vec::try_reserve_exact` exact-vstd row now has an executable,
non-`assume_specification`, non-public-target-`external_body` harness at
`proof_harnesses/179_alloc_vec_Vec_try_reserve_exact/harness.rs`. It preserves
the Rust 1.96 body expression `self.buf.try_reserve_exact(self.len, additional)`
and verifies the exact existing-vstd frame plus Ok-result capacity contract
modulo only a source-backed RawVec allocator/result-capacity initialized-prefix
boundary. The actual Verus run reports `verification results:: 1 verified, 0
errors`.

The `alloc::vec::Vec::with_capacity` exact-vstd row now has an executable,
non-`assume_specification`, non-public-target-`external_body` harness at
`proof_harnesses/180_alloc_vec_Vec_with_capacity/harness.rs`. It preserves the
Rust 1.96 wrapper body expression `Self::with_capacity_in(capacity, Global)` and
verifies the exact existing-vstd postcondition `v@ == Seq::<T>::empty()` with
the reviewed split_off-style executable RawVec/Global empty-constructor model,
not a retained constructor `external_body`. The actual Verus run reports
`verification results:: 2 verified, 0 errors`, the direct external-body surface
is `121/315`, and the aggregate gate reports pending=0 across all 180
obligations.

One hundred thirty-two generated proof-order rows, plus the exact-vstd
`core::slice::copy_from_slice`, `core::slice::copy_within`,
`core::slice::first`, `core::slice::first_mut`, `core::slice::get`,
`core::slice::is_empty`, `core::slice::iter`, `core::slice::last`,
`core::slice::last_mut`, `core::slice::len`, `core::slice::split_at`, and
`core::slice::split_at_mut`, `alloc::vec::Vec::append`,
`alloc::vec::Vec::as_mut_slice`, `alloc::vec::Vec::as_slice`,
`alloc::vec::Vec::capacity`, `alloc::vec::Vec::clear`,
`alloc::vec::Vec::extend_from_slice`, `alloc::vec::Vec::insert`, and
`alloc::vec::Vec::is_empty`, `alloc::vec::Vec::len`,
`alloc::vec::Vec::new`, `alloc::vec::Vec::pop`,
`alloc::vec::Vec::push`, `alloc::vec::Vec::remove`,
`alloc::vec::Vec::reserve`, `alloc::vec::Vec::reserve_exact`,
`alloc::vec::Vec::resize`, `alloc::vec::Vec::shrink_to`, and
`alloc::vec::Vec::shrink_to_fit`, `alloc::vec::Vec::split_off`,
`alloc::vec::Vec::swap_remove`, `alloc::vec::Vec::truncate`, and
`alloc::vec::Vec::try_reserve`, `alloc::vec::Vec::try_reserve_exact`, and
`alloc::vec::Vec::with_capacity` rows,
have actual Verus runs and honest **B** dispositions, not unconditional
implementation verification:
`ChunksExact::remainder`, `ChunksExactMut::into_remainder`,
`Iter::as_slice`, `IterMut::as_slice`, `IterMut::into_slice`,
`RChunksExact::remainder`, and `RChunksExactMut::into_remainder`, plus
`array_windows`, `chunks`,
`chunks_exact`, `eq_ignore_ascii_case`, `escape_ascii`, `core::slice::from_mut`,
`core::slice::from_raw_parts`, `core::slice::from_raw_parts_mut`,
`core::slice::get_disjoint_mut`, `core::slice::get_disjoint_unchecked_mut`,
`core::slice::from_ref`,
`core::slice::get_mut`, `core::slice::is_ascii`,
`core::slice::iter`, `core::slice::iter_mut`, `core::slice::make_ascii_lowercase`,
`core::slice::make_ascii_uppercase`, `core::slice::rchunks`,
`core::slice::rchunks_exact`, `core::slice::split_first`,
`core::slice::split_first_mut`, `core::slice::split_last`,
`core::slice::split_last_chunk_mut`, `core::slice::split_last_mut`,
`core::slice::split_off`, `core::slice::split_off_first`,
`core::slice::split_off_first_mut`, `core::slice::split_off_last`,
`core::slice::split_off_last_mut`,
`core::slice::align_to`, `core::slice::align_to_mut`, `core::slice::as_array`,
`core::slice::as_chunks_unchecked`, `core::slice::as_chunks_unchecked_mut`,
`core::slice::as_flattened`, `core::slice::as_flattened_mut`,
`core::slice::as_mut_array`,
`core::slice::as_mut_ptr`, `core::slice::as_mut_ptr_range`,
`core::slice::as_ptr`, `core::slice::as_ptr_range`,
`core::slice::first_chunk`, `core::slice::first_chunk_mut`,
`core::slice::binary_search_by`, `core::slice::binary_search`,
`core::slice::binary_search_by_key`,
`core::slice::as_rchunks`, `core::slice::as_rchunks_mut`,
`core::slice::assume_init_drop`,
`core::slice::assume_init_mut`, `core::slice::assume_init_ref`,
`core::slice::write_clone_of_slice`, `core::slice::write_copy_of_slice`,
`core::slice::trim_ascii_end`, `core::slice::trim_ascii_start`,
`core::slice::utf8_chunks`, `core::slice::windows`,
`core::slice::chunk_by`, `core::slice::clone_from_slice`,
`core::slice::contains`, `core::slice::element_offset`,
`core::slice::ends_with`, `core::slice::starts_with`,
`core::slice::strip_prefix`, `core::slice::strip_suffix`,
`core::slice::strip_circumfix`, `core::slice::swap`,
`core::slice::swap_with_slice`,
`core::slice::fill`,
`core::slice::fill_with`, `core::slice::is_sorted`,
`core::slice::is_sorted_by`, `core::slice::is_sorted_by_key`,
`core::slice::last_chunk`, `core::slice::last_chunk_mut`,
`core::slice::partition_point`, `core::slice::reverse`,
`core::slice::rotate_left`, `core::slice::rotate_right`,
`core::slice::rsplit`, `core::slice::rsplitn`,
`core::slice::split_at_mut_unchecked`, `core::slice::as_chunks_mut`,
`core::slice::split_at_mut_checked`, `core::slice::split_at_unchecked`,
`core::slice::split_at_checked`, `core::slice::split_first_chunk`,
`core::slice::split_first_chunk_mut`,
`core::slice::as_chunks`,
`core::slice::select_nth_unstable`,
`core::slice::select_nth_unstable_by`, `core::slice::select_nth_unstable_by_key`,
`core::slice::sort_unstable`, `core::slice::sort_unstable_by`,
`core::slice::sort_unstable_by_key`, `core::slice::split`, `core::slice::splitn`,
`core::slice::split_inclusive`, `core::slice::subslice_range`,
`alloc::vec::Drain::as_slice`,
`alloc::vec::IntoIter::as_mut_slice`, `alloc::vec::IntoIter::as_slice`,
`alloc::vec::Vec::as_mut_ptr`, `alloc::vec::Vec::as_ptr`,
`alloc::vec::Vec::extend_from_within`, `alloc::vec::Vec::extract_if`,
`alloc::vec::Vec::from_raw_parts`,
`alloc::vec::Vec::into_boxed_slice`,
`alloc::vec::Vec::into_flattened`,
`alloc::vec::Vec::into_raw_parts`, `alloc::vec::Vec::leak`,
`alloc::vec::Vec::pop_if`, `alloc::vec::Vec::resize_with`,
`alloc::vec::Vec::retain`, `alloc::vec::Vec::retain_mut`, `alloc::vec::Vec::dedup_by`,
`alloc::vec::Vec::dedup`, `alloc::vec::Vec::dedup_by_key`,
`alloc::vec::Vec::drain`, `alloc::vec::Vec::set_len`,
`alloc::vec::Vec::insert_mut`, `alloc::vec::Vec::push_mut`, and
`alloc::vec::Vec::spare_capacity_mut`.
Their harnesses keep the target bodies but depend on explicit private
representation, helper, pointer/provenance, source-backed iterator-view,
valid-index split, private ASCII-helper/iterator-adaptor, source-backed
array-helper/unsize, source-backed SliceIndex trait-method, source-backed
SliceContains trait/specialization, source-backed slice PartialEq prefix/suffix
comparison/range view, source-backed SlicePattern::as_slice plus split_at/range
view facts, reviewed `binary_search_by` plus source-backed Ord cmp/key/predicate
observations and result bridges for the Ord, by-key, and partition-point wrappers, including the
target-local Verus closure-lowering boundary for `|k| f(k).cmp(b)`, active
x86_64+sse2 private ASCII helper, primitive byte-helper, reverse immutable
constructor iterator-view, mutable reverse array-chunk view/final-frame,
source-backed CloneFromSpec specialization, source-shaped SpecFill default Clone
loop with lower clone/specialization boundaries, source-backed raw-parts UB/precondition,
reviewed `split_at_unchecked` plus `as_chunks_unchecked` boundaries for the
immutable chunks-and-remainder partition, source-backed
exact_div/UB-precondition/raw-pointer cast/from_raw_parts provenance,
MaybeUninit raw-pointer/Destruct/drop, raw-cast, immutable pointer-range raw add,
MaybeUninit clone/write guard-loop, copy same-layout transmute/copy_from_slice,
plus reviewed `assume_init_mut` raw cast,
source-backed element-offset ZST panic plus `ptr::from_ref`/`addr`/
wrapping-offset/alignment/division pointer-domain bridge,
source-backed `subslice_range` ZST panic plus dual `as_ptr().addr()`,
wrapping-sub/alignment/division/wrapping-add range-domain bridge,
unchecked-disjoint raw-pointer/MaybeUninit/index-clone, source-backed iterator/FnMut
key-observation, source-backed RSplit/Split and RSplitN/SplitN/GenericSplitN
constructor iterator-view with FnMut predicate-observation, source-backed selection partition with FnMut
key-closure observation, source-backed unstable-sort plus Ord::lt observation,
source-backed unstable-sort with FnMut comparator closure observation,
last-chunk suffix array-reference raw-pointer, RawVec allocator/raw-pointer,
RawVec-to-boxed-slice/MaybeUninit, flattened raw-parts/intrinsic/panic,
ManuallyDrop raw-parts pointer/provenance, leaked mutable-slice
raw-parts-view, source-backed Vec last-element/pop plus FnOnce predicate
observation, source-backed Vec resize_with len/truncate/extend_trusted/
repeat_with/take plus zero-arg FnMut callback-output, source-backed Vec
retain_mut raw-pointer/copy/drop/set_len/mem::forget plus FnMut mutable-callback,
source-backed Vec set_len allocator/capacity/raw-length/unsafe-precondition,
reviewed `Vec::as_mut_slice` plus source-backed raw mutable-slice pointer
coercion and `drop_in_place` for `Vec::clear`,
source-backed slice iterator view plus private `SpecExtend` clone forwarding for
`Vec::extend_from_slice`,
source-backed Vec insert_mut panic/bounds, allocator grow_one, raw-pointer
add/copy/write/return-reference, reviewed `as_mut_ptr`/`set_len` boundaries,
source-backed Vec push_mut allocator grow_one, raw-pointer add/write, direct
len update, return-reference reconstruction boundaries, reviewed `retain_mut`
plus FnMut read-only callback closure-lowering/result bridge,
source-backed slice reverse raw-half/revswap-loop/final-frame bridges,
source-backed mutable `align_to_mut` split/raw-parts/provenance/final-frame
boundaries, source-backed `split_at_mut_unchecked` unsafe-precondition,
unchecked-subtraction, raw-parts/provenance, and final-frame boundaries, or
source-backed `split_at_unchecked` immutable start-pointer,
unsafe-precondition, unchecked-subtraction, and raw-parts split boundaries,
or reviewed `strip_prefix`/`strip_suffix` dependencies plus source-backed
SlicePattern/PartialEq boundaries for `strip_circumfix`, recorded in the
dependency manifests.
The `core::slice::strip_circumfix` harness preserves the Rust 1.96 target flow
`self.strip_prefix(prefix)?.strip_suffix(suffix)` as an executable,
non-`external_body` public function with Verus explicit early-return lowering.
The actual Verus proof records a B disposition modulo the reviewed
`strip_prefix` and `strip_suffix` dependencies, their source-backed
`SlicePattern::as_slice`, prefix/suffix `PartialEq`, and split_at/range-view
boundaries, plus the generated circumfix subrange-composition vocabulary; it
does not assume the target postcondition.
The `alloc::vec::Vec::pop_if` harness preserves the Rust 1.96 target flow
`let last = self.last_mut()?; if predicate(last) { self.pop() } else { None }`
as an executable, non-`external_body` public method, adapted only to an explicit
match and a named FnOnce observation boundary. The saved actual Verus proof now
records a B disposition modulo the lower reviewed `Vec::as_mut_slice` /
`core::slice::last_mut` analogue boundaries, the executable pop helper's raw
pointer/read boundaries plus invariant-derived capacity proof, and callback observation; it does not mark
the raw mutable-slice construction or callback semantics boundary-free. The separate
`proof_harnesses/167_alloc_vec_Vec_pop/harness.rs` proof now discharges the
public `Vec::pop` target.
The `alloc::vec::Vec::resize_with` harness preserves the Rust 1.96 target flow
`let len = self.len(); if new_len > len { self.extend_trusted(iter::repeat_with(f).take(new_len - len)); } else { self.truncate(new_len); }`
as an executable, non-`external_body` public method. The actual Verus proof
records a B disposition modulo source-backed `len`, `truncate`,
`extend_trusted`, `repeat_with(...).take(...)`, and zero-argument FnMut
callback-output observation boundaries; it preserves the generated
`vec_resize_with_result` grow relation and truncate-prefix branch without
marking those helpers or iterator adapters complete.
The `alloc::vec::Vec::retain_mut` harness preserves the Rust 1.96 target flow with
`original_len`, empty return, first-kept prefix scan, PanicGuard read/write state,
raw-pointer drop/copy/set_len critical section, and final `mem::forget(g)` commit
as an executable, non-`external_body` public method. The active
`vec_panic_guard_cleanup_boundary_reduction_20260815T0202Z` evidence also removes
the wrapper-level `PanicGuard::cleanup_on_panic` `external_body`: the cleanup body
now verifies as executable copy-tail/set_len arithmetic. The actual Verus proof
records a B disposition modulo lower source-backed Vec storage/raw-pointer/
provenance, raw drop/copy, unchecked mutable access, allocator, `mem::forget`,
`FnMut(&mut T)->bool` callback-observation, and `vec_retain_mut_result`
effect-summary boundaries; it does not mark `get_unchecked_mut`, pointer
operations, allocator/provenance, or callback effects complete.
The `alloc::vec::Vec::retain` harness preserves the Rust 1.96 wrapper semantics
`self.retain_mut(|elem| f(elem))` through a named Verus closure-lowering delegate
because this Verus build rejects the direct mutable `FnMut` capture. The public
target remains executable and non-`external_body`; the actual Verus proof records
a B disposition modulo the reviewed `retain_mut` dependency boundary plus a
read-only-to-mutable callback/result bridge from `vec_retain_mut_result` to
`vec_retain_result`, without assuming the public target postcondition.
The `alloc::vec::Vec::spare_capacity_mut` harness preserves the Rust 1.96 unsafe
spare-storage construction as an executable, non-`external_body` public method:
`self.as_mut_ptr().add(self.len)`, `self.buf.capacity() - self.len`, and
`slice::from_raw_parts_mut` over `MaybeUninit<T>`. The 20260815T1316Z
MaybeUninit cast-wrapper reduction removes the target-local
`MutPtr<T>::cast_maybe_uninit` `external_body`; the wrapper now verifies as the
existing executable raw-pointer cast/token constructor body. The actual Verus
proof records a B disposition modulo the reviewed `Vec::as_mut_ptr` dependency,
source-backed RawVec capacity/len-domain, lower raw-pointer add/cast provenance,
and MaybeUninit mutable raw-parts boundaries; it proves the returned length,
`vec_spare_capacity_relation`, and `final(vec)@ == old(vec)@` frame clauses
without assuming the target postcondition. At that admission point, the
aggregate surface was 121 harnesses / 290 occurrences, split Slice 79/179 and
Vec 42/111; the later pointer-accessor aggregate admission surface was 111/260
before the remaining-consumer reduction moved the surface to 110/249, the
later raw Slice root, pointer-range, fixed-prefix, and tail-consumer reductions
moved the then-current surface to 108/224, and the later Slice pointer-accessor
reduction moved the current surface to 108/219.
The focused 20260816T0831Z raw-parts split probe for
`rust_1_96_spare_capacity_raw_parts_boundary` makes no production change: the
probe keeps the same Rust 1.96 flow and attempts to prove only the
`spare_len + source.len == capacity` arithmetic outside a lower
raw-spare-slice relation helper, but actual Verus fails on the `usize`/`nat`/`int`
cast-subtraction bridge while the unchanged production harness still passes both
required Verus modes. Evidence is preserved at
`proof_inventory/vec_spare_capacity_raw_parts_boundary_reduction_20260816T0831Z/summary.json`.
The `alloc::vec::Vec::dedup_by` harness preserves the Rust 1.96 target flow with
`len`, early return, `first_duplicate_idx` scan using reversed `FnMut(&mut T, &mut T)`
callback arguments, FillGapOnDrop read/write cleanup intent, first duplicate drop,
gap raw-pointer drop/copy loop, final `set_len(gap.write)`, and `mem::forget(gap)`
commit as an executable, non-`external_body` public method. The same active
cleanup-wrapper reduction removes the wrapper-level
`FillGapOnDrop::cleanup_on_panic` `external_body`: the cleanup body now verifies
as executable copy-tail/set_len arithmetic. The actual Verus proof records a B
disposition modulo lower source-backed Vec storage/raw-pointer/provenance, raw
drop/copy, allocator, `mem::forget`, reversed callback-observation, and
`vec_dedup_by_result` effect-summary boundaries; it does not mark `as_mut_ptr`,
pointer operations, allocator/provenance, or callback effects complete.
The `alloc::vec::Vec::dedup` harness preserves the Rust 1.96 wrapper semantics by
calling `dedup_by` with the PartialEq equality callback `a == b` as an executable,
non-`external_body` public method. Its target-local `dedup_by` callee is now a
source-shaped skeleton adapted from the reviewed harness 127 flow: length and
early-return handling, duplicate scan, FillGapOnDrop gap state, raw drop/copy
loop, final `set_len(gap.write)`, and `mem::forget`. The actual Verus proof
records a B disposition modulo lower raw-pointer/drop/copy/provenance, reversed
FnMut callback observation, `vec_dedup_by_result` effect-summary, and PartialEq
observation/bridge boundaries; it preserves `vec_dedup_partial_eq_result`
without assuming the public target postcondition or keeping the whole-method
`dedup_by` dependency boundary.
The `alloc::vec::Vec::dedup_by_key` harness preserves the Rust 1.96 wrapper
semantics by expanding `self.dedup_by(|a, b| key(a) == key(b))` into a local
source-shaped dedup loop adapted from the reviewed `dedup_by` harness. It keeps
the reversed dedup argument order by calling `key(current)` before
`key(previous)`, then comparing the key results with `PartialEq`. The actual
Verus proof records a B disposition modulo lower raw-pointer/drop/copy/provenance,
ordered FnMut key callback observation, PartialEq result observation, and
`vec_dedup_by_key_result` effect-summary boundaries; it no
longer keeps the whole `dedup_by` dependency boundary or assumes the public
target postcondition.
The `alloc::vec::Vec::set_len` harness preserves the Rust 1.96 target flow
`capacity = self.capacity(); check new_len <= capacity; self.len = new_len` as an
executable, non-`external_body` public unsafe method with no
`assume_specification`. The actual Verus proof records a B disposition modulo
source-backed allocator/capacity observation, the unsafe-precondition check, and
raw Vec length/view modeling; it preserves `vec_set_len_domain` and
`vec_set_len_result` without marking allocator/provenance or arbitrary initialized
storage complete.
The `alloc::vec::Vec::insert_mut` harness preserves the Rust 1.96 target flow
an executable `len`, `index > len` panic/bounds branch, `grow_one` when `len == capacity`,
`as_mut_ptr().add(index)`, conditional `ptr::copy` shift, `ptr::write(element)`,
`set_len(len + 1)`, and returning the mutable reference represented by `&mut *p`
as an executable, non-`external_body` public method. The actual Verus proof
records a B disposition modulo the reviewed `Vec::as_mut_ptr` and `Vec::set_len`
dependencies plus executable source-shaped capacity/overflow arithmetic over the
separated source-backed Vec len/capacity invariant and `grow_one`, allocator
growth, raw-pointer add/copy/write/
return-reference provenance, and panic/bounds boundaries; it preserves the
generated insertion postcondition without marking allocator/provenance or raw
storage complete.
The exact-vstd `alloc::vec::Vec::insert` wrapper now embeds that same
source-shaped `insert_mut` skeleton locally instead of trusting the whole
`insert_mut` body, while preserving the public Rust 1.96 wrapper flow
`let _ = self.insert_mut(i, element);`.
The `alloc::vec::Vec::push_mut` harness preserves the Rust 1.96 target flow
`len`, `grow_one` when `len == capacity`, `as_mut_ptr().add(len)`,
`ptr::write(end, value)`, direct `self.len = len + 1`, and returning the
mutable reference represented by `&mut *end` as an executable, non-`external_body`
public method. The actual Verus proof records a B disposition modulo reviewed
`Vec::as_mut_ptr` plus source-backed allocator growth, raw-pointer add/write/
return-reference provenance, and len-increment overflow/unsafe-domain
boundaries; it preserves the generated push postcondition without marking
allocator/provenance or raw storage complete.
The 2026-08-15 follow-up repaired the prior `push_mut` no-boundary attempt by
adding the separated source-backed Vec `len <= capacity` invariant at the direct
`self.len` call site and replaying the verified `insert_mut` len/capacity/grow
arithmetic. The target-local capacity/overflow helper is gone; allocator growth,
raw pointer add/write/provenance, overflow/unsafe domain, and returned-reference
reconstruction remain lower boundaries.
The 2026-08-17 `rawvec_grow_one_overflow_reduction_20260817T0750Z` production
round replaces the four retained `RawVec::grow_one` external bodies in harnesses
133, 139, 163, and 168 with executable bodies that save the old capacity, take
the normal `cap < usize::MAX` branch by assigning `self.cap = cap + 1`, and route
the overflow edge through the retained source-shaped `capacity_overflow(cap, 1)`
abort helper with `ensures false`. The public contracts and source-shaped
`insert_mut`/`push_mut`/wrapper flows are unchanged; actual Verus verifies all
four harnesses and the aggregate gate remains B=180, pending=0, exact-vstd=36
with the then-current external-body surface 111/260 before the
remaining-consumer reduction moved the surface to 110/249, the later raw
Slice root, pointer-range, fixed-prefix, and tail-consumer reductions moved the
then-current surface to 108/224, and the later Slice pointer-accessor reduction
moved the current surface to 108/219.
The 2026-08-16 bounded return-reference adjudication directly probed removing
the retained `insert_mut_return_ref_from_ptr` and sibling
`push_mut_return_ref_from_ptr` external-body annotations in harnesses 133/163 and
139/168. All four source-shaped probes fail during
`--crate-type=lib --no-verify` on the raw-pointer dereference used to reconstruct
`&mut T` (`&mut *p.raw` / `&mut *end.raw`), while the unchanged production
harnesses pass both no-verify and actual Verus; the retained boundary remains the
narrow source-backed Rust 1.96 raw-pointer/reference reconstruction boundary.
Evidence is under
`proof_inventory/vec_return_ref_reconstruction_boundary_20260816T1020Z/summary.json`.
The `core::slice::split_at_mut_unchecked` harness preserves the Rust 1.96 target
flow as an executable, non-`external_body` public unsafe function: `len`,
`as_mut_ptr`, the `assert_unsafe_precondition` check for `mid <= len`, and the
unsafe tuple using `from_raw_parts_mut(ptr, mid)` plus
`from_raw_parts_mut(ptr.add(mid), unchecked_sub(len, mid))`. Its actual Verus
proof records a B disposition modulo the reviewed mutable start-pointer
boundary, source-backed unsafe-precondition/`unchecked_sub`, and a named
raw-parts/provenance/final-frame boundary; it does not mark arbitrary
`from_raw_parts_mut`, raw-pointer addition, or unchecked arithmetic complete.
The `core::slice::split_at_unchecked` harness preserves the Rust 1.96 target
flow as an executable, non-`external_body` public unsafe function: `len`,
`as_ptr`, the `assert_unsafe_precondition` check for `mid <= len`, and the
unsafe tuple using `from_raw_parts(ptr, mid)` plus
`from_raw_parts(ptr.add(mid), unchecked_sub(len, mid))`. Its actual Verus proof
records a B disposition modulo the reviewed immutable start-pointer boundary,
source-backed unsafe-precondition/`unchecked_sub`, and a named immutable
raw-parts/provenance split boundary; it does not mark arbitrary
`from_raw_parts`, raw-pointer addition, or unchecked arithmetic complete.
The 20260816T1712Z no-external probe shows that removing only the named
immutable split raw-parts helper boundary from the four current consumers is not
yet typecheckable in this Verus build because the inlined source-shaped
`ptr.add(mid)` expression is unsupported.
The `core::slice::split_at_checked` harness preserves the Rust 1.96 checked
wrapper flow as an executable, non-`external_body` public function: compute
`len`, branch on `mid <= len`, return
`Some(unsafe { split_at_unchecked(slice, mid) })` in range, and return `None`
out of range. Its actual Verus proof records a B disposition modulo the
source-shaped target-local `split_at_unchecked` helper, whose lower immutable
start-pointer and raw-parts/provenance split boundaries remain retained; the
guard discharges the unchecked split precondition and the target postcondition
is not assumed.
The `core::slice::split_first_chunk` harness preserves the Rust 1.96 flow as an
executable, non-`external_body` public function: call `split_at_checked(N)`,
return `None` when the checked split is out of range, and on `Some((first,
tail))` return `Some((unsafe { &*(first.as_ptr().cast_array()) }, tail))`.
Its target-local `split_at_checked` helper is also executable: it computes
`len`, branches on `mid <= len`, calls the source-shaped target-local
`split_at_unchecked` helper only under that guard, and returns `None` otherwise.
Its actual Verus proof records a B disposition modulo the retained lower
unchecked-split raw-parts boundary plus source-backed raw-pointer
`as_ptr`/`cast_array` and unsafe array-reference boundaries; it does not assume
the target postcondition or recursively prove general raw-pointer provenance.
The `core::slice::split_first_chunk_mut` harness preserves the Rust 1.96 flow as
an executable, non-`external_body` public function: call
`split_at_mut_checked(N)`, return `None` when the checked split is out of range,
and on `Some((first, tail))` return
`Some((unsafe { &mut *(first.as_mut_ptr().cast_array()) }, tail))`. Its
target-local `split_at_mut_checked` helper is executable in the same shape:
compute `len`, branch on `mid <= len`, call the reviewed
source-shaped `split_at_mut_unchecked` helper only under that guard, and return
`None` otherwise. Its actual Verus proof records a B disposition modulo the
retained lower mutable unchecked-split raw-parts/final-frame boundary plus
source-backed mutable raw-pointer `as_mut_ptr`/`cast_array` and unsafe mutable
array-reference final-frame boundaries; it does not assume the target
postcondition or recursively prove general raw-pointer provenance.
The `core::slice::as_chunks` harness preserves the Rust 1.96 target flow as an
executable, non-`external_body` public function: `assert!(N != 0)`,
`len_rounded_down = slice.len() / N * N`, unsafe
`split_at_unchecked(len_rounded_down)`, unsafe `as_chunks_unchecked()` on the
multiple-of-N prefix, and return `(array_slice, remainder)`. Its actual Verus
proof records a B disposition modulo the now source-shaped target-local
`split_at_unchecked` helper's retained raw-parts boundary and the reviewed
immutable `as_chunks_unchecked` array-chunk relation.
The `core::slice::as_chunks_mut` harness preserves the Rust 1.96 target flow as
an executable, non-`external_body` public function: `assert!(N != 0)`,
`len_rounded_down = slice.len() / N * N`, unsafe
`split_at_mut_unchecked(len_rounded_down)`, unsafe
`as_chunks_unchecked_mut()` on the multiple-of-N prefix, and return
`(array_slice, remainder)`. Its actual Verus proof records a B disposition
modulo the now source-shaped target-local `split_at_mut_unchecked` helper's
retained raw-parts/final-frame boundary and the reviewed mutable
`as_chunks_unchecked_mut` array-chunk/final-frame relation; it does not mark
those unsafe dependencies recursively complete in this target.
The `core::slice::from_mut` and
`core::slice::from_ref` harnesses
preserve the Rust target bodies as the single `array::from_mut(s)` and
`array::from_ref(s)` delegations and record the public `core::array` helpers plus
implicit array-to-slice coercions as narrow boundaries, not as unconditional
proofs of those helpers' raw-pointer casts. The `core::slice::get_mut` harness
preserves the Rust target body as the single `index.get_mut(slice)` delegation
and records `core::slice::SliceIndex<[T]>::get_mut` as a source-backed
trait-method boundary until concrete `SliceIndex` implementations are
recursively proved. The `core::slice::contains` harness preserves the Rust target
body as the exact `cmp::SliceContains::slice_contains(x, slice)` delegation,
proves the generic default PartialEq implementation as an executable scan
corresponding to `x.iter().any(|y| *y == *self)`, and retains only the lower
`PartialEq::eq` observation bridge plus primitive memchr/SIMD specializations in
`core/src/slice/cmp.rs:411-455` as residual source-backed boundaries. The public
target is executable, not `external_body`, and contains no `assume_specification`.
The `core::slice::ends_with` harness preserves the Rust
1.96 length extraction and short-circuit shape
`let (m, n) = (slice.len(), needle.len()); m >= n && ...`; it records only the
second-conjunct `needle == &slice[m - n..]` slice PartialEq/suffix range-view
semantics as the narrow source-backed boundary from
`core/src/slice/mod.rs:2654-2655` and `core/src/slice/cmp.rs:15-141`. The
public target is executable, not `external_body`, and contains no
`assume_specification`. The `core::slice::starts_with` harness preserves the
Rust 1.96 target body shape `let n = needle.len(); slice.len() >= n && ...`; it
records only the second-conjunct `needle == &slice[..n]` slice PartialEq/prefix
range-view semantics as the narrow source-backed boundary from
`core/src/slice/mod.rs:2624` and `core/src/slice/cmp.rs:15-141`. The public
target is executable, not `external_body`, and contains no `assume_specification`.
The `core::slice::strip_prefix` harness preserves the Rust 1.96 body shape:
lower `SlicePattern::as_slice`, compute `n`, guard on `n <= slice.len()`, split
with `split_at(n)`, compare `head == prefix`, and return `Some(tail)` or
`None`. It records `SlicePattern::as_slice`, the guarded head/prefix slice
PartialEq comparison, and split_at/range-view facts as source-backed boundaries;
the public target is executable, not `external_body`, and contains no
`assume_specification`.
The `core::slice::strip_suffix` harness preserves the Rust 1.96 body shape:
lower `SlicePattern::as_slice`, compute `(len, n)`, guard on `n <= len`, split
with `split_at(len - n)`, compare `tail == suffix`, and return `Some(head)` or
`None`. It records `SlicePattern::as_slice`, the guarded tail/suffix slice
PartialEq comparison, and split_at/range-view facts as source-backed boundaries;
the public target is executable, not `external_body`, and contains no
`assume_specification`.
The `core::slice::subslice_range` harness preserves the Rust 1.96 body shape:
ZST panic precondition, `self.as_ptr().addr()`,
`subslice.as_ptr().addr()`, `wrapping_sub`, `is_multiple_of(size_of::<T>())`,
division by `size_of::<T>()`, `wrapping_add(subslice.len())`, and
length-guarded `Some(Range { start, end })`/`None` branches. Its actual Verus
proof records a B disposition modulo the reviewed `as_ptr` pointer-start
boundary plus target-local source-backed pointer-address, alignment arithmetic,
ZST panic, and range-domain result bridges; the public target is executable,
not `external_body`, and contains no `assume_specification`.
The `core::slice::swap` harness preserves the Rust 1.96 raw-pointer flow as
two target-body pointer values for `self[a]` and `self[b]` followed by the unsafe
`ptr::swap(pa, pb)`. Because this Verus build rejects raw-borrow syntax in
non-external target bodies, the exact indexed raw-borrow expression and the
unsafe raw-pointer swap are isolated in target-local source-backed boundaries;
the public target is executable, not `external_body`, and contains no
`assume_specification`. The focused
`swap_raw_pointer_boundary_adjudication_20260816T0400Z` no-production-change
probes confirmed both retained boundaries are minimal for this Verus build:
the no-external raw-borrow probe fails `--no-verify` on unsupported raw borrows,
and the no-external `ptr::swap` probe fails `--no-verify` unless an
`assume_specification` is added. The unchanged production harness still verifies
with `verification results:: 1 verified, 0 errors`.
The `core::slice::swap_with_slice` harness preserves the Rust 1.96 body shape:
the equal-length assertion, both `as_mut_ptr` calls, `self.len()` as the
`ptr::swap_nonoverlapping` count, and the final two-slice frame swap relation.
Its actual Verus proof records a B disposition modulo the reviewed `as_mut_ptr`
mutable start-pointer boundary plus target-local source-backed
`swap_nonoverlapping` and two-slice final-frame bridges; the public target is
executable, not `external_body`, and contains no `assume_specification`.
The later
`swap_with_slice_raw_swap_boundary_reduction_20260814T2150Z` no-production-change
adjudication removed each target-local raw-swap bridge in focused probes:
removing `rust_1_96_ptr_swap_nonoverlapping` exposes unsupported
`core::ptr::swap_nonoverlapping` during `--crate-type=lib --no-verify`, while
removing `rust_1_96_swap_with_slice_final_frame_bridge` leaves both generated
two-slice final-frame postconditions unproved in actual Verus. The production
harness therefore retains the narrow source-backed raw swap and final-frame
boundaries and still passes both production Verus checks plus the aggregate gate.
The `core::slice::is_ascii` harness preserves the Rust target
wrapper body as the single private-helper delegation and records the active
x86_64+sse2 private helper, including its SSE2 dispatch and small-slice loop, as
a source-backed boundary rather than a recursively verified helper proof. The
`core::slice::is_sorted_by_key` harness preserves the Rust 1.96
`self.iter().is_sorted_by_key(f)` shape via an explicit receiver wrapper and
target-local iterator method, keeps the generated
`slice_sorted_by_partial_key_result` postcondition, and records only the
iterator traversal, `FnMut` key-observation trace, and `PartialOrd` comparison
semantics as a source-backed boundary; the public target is executable, not
`external_body`, and contains no `assume_specification`.
The `core::slice::is_sorted` harness preserves the Rust 1.96
`CHUNK_SIZE = 33` flow with the short `windows(2).all` branch, the overlapping
chunk loop, the chunk `windows(2).fold(true, |acc, w| acc & (w[0] <= w[1]))`
false return, `i += CHUNK_SIZE - 1`, and the final suffix `windows(2).all`.
Its actual Verus proof records a B disposition modulo only the narrow
source-backed `PartialOrd` comparison observation bridge. `Windows::all` and
`Windows::fold` now execute adjacent-window traversal loops, the range and
suffix helpers execute source-shaped slice indexing while proving their sequence
views, and the chunk/suffix overlap composition is proved in target-local
lemmas. The public target is executable, not `external_body`, and contains no
`assume_specification`.
The `core::slice::last_chunk` harness preserves the Rust 1.96
`checked_sub(N)` early `None`, `split_at(index)`, and final unsafe
`last.as_ptr().cast_array()` suffix conversion shape. The saved actual Verus
proof records a B disposition modulo the reviewed vstd `split_at` suffix-view
facts plus the target-local source-backed raw-pointer/array-reference boundary
`rust_1_96_last_chunk_array_ref`; the public target function is executable, not
`external_body`, and contains no `assume_specification`.
The `core::slice::as_array` harness preserves the Rust 1.96 `len() == N`
success branch, `as_ptr` acquisition, `ptr.cast_array()`, unsafe `&*ptr`
array-reference cast, `Some(me)`, and `None` else flow. The saved actual Verus
proof records a B disposition modulo the reviewed `as_ptr` pointer-start
dependency plus target-local source-backed raw-pointer/array-reference
boundaries `rust_1_96_ptr_cast_array` and `rust_1_96_as_array_ref`; the public
target function is executable, not `external_body`, and contains no
`assume_specification`.
The `core::slice::first_chunk` harness preserves the Rust 1.96
`if self.len() < N { None } else { Some(unsafe { &*(self.as_ptr().cast_array()) }) }`
control flow, reuses the reviewed `as_ptr` pointer-start dependency and
`ptr.cast_array()` pattern from `as_array`, and records the success relation with
the generated `array_ref_view` plus `slice_fixed_prefix` contract. The saved
actual Verus proof records a B disposition modulo the target-local
source-backed raw-pointer/array-reference boundaries
`rust_1_96_ptr_cast_array` and `rust_1_96_first_chunk_array_ref`; the public
target function is executable, not `external_body`, and contains no
`assume_specification`.
The `core::slice::first_chunk_mut` harness preserves the Rust 1.96
`if self.len() < N { None } else { Some(unsafe { &mut *(self.as_mut_ptr().cast_array()) }) }`
control flow, reuses the reviewed `as_mut_ptr` mutable pointer-start/final-frame
dependency and `ptr.cast_array()` pattern from `as_mut_array`, and records the
generated mutable prefix plus suffix final-frame contract. The saved actual Verus
proof records a B disposition modulo the target-local source-backed mutable
raw-pointer/array-reference boundaries `rust_1_96_mut_ptr_cast_array` and
`rust_1_96_first_chunk_mut_array_ref`; the public target function is executable,
not `external_body`, and contains no `assume_specification`.
The `core::slice::get_disjoint_mut` harness preserves the Rust 1.96
`get_disjoint_check_valid(&indices, self.len())?` gate, Err early return, and
`unsafe { Ok(self.get_disjoint_unchecked_mut(indices)) }` success flow. The saved
actual Verus proof records a B disposition modulo the source-backed
`get_disjoint_check_valid` Ok/Err disjoint-validity helper boundary plus the
reviewed `get_disjoint_unchecked_mut` raw-pointer/MaybeUninit/indexing boundary;
the public target function is executable, not `external_body`, and contains no
`assume_specification`.
The `core::slice::as_mut_array` harness mirrors that proof for the mutable Rust
1.96 body: it preserves the `len() == N` success branch, `as_mut_ptr`
acquisition, `ptr.cast_array()`, unsafe `&mut *ptr` array-reference cast,
`Some(me)`, and `None` else flow. The saved actual Verus proof records a B
disposition modulo the reviewed `as_mut_ptr` mutable pointer-start/final-frame
dependency plus target-local source-backed mutable raw-pointer `cast_array` and
mutable array-reference final-frame boundaries; the public target function is
executable, not `external_body`, and contains no `assume_specification`.
The `core::slice::as_chunks_unchecked` harness preserves the Rust 1.96 unsafe
body as the UB precondition `N != 0` plus `len.is_multiple_of(N)`,
`exact_div(self.len(), N)`, `self.as_ptr().cast()`, and
`from_raw_parts(..., new_len)`. The saved actual Verus proof records a B
disposition modulo reviewed as_ptr/from_raw_parts patterns plus target-local
source-backed exact-div, UB-precondition, raw-pointer cast, and raw-parts
provenance boundaries; the public target function is executable, not
`external_body`, and contains no `assume_specification`.
The `core::slice::as_chunks_unchecked_mut` harness mirrors that proof for the
mutable Rust 1.96 unsafe body: it preserves the UB precondition `N != 0` plus
`len.is_multiple_of(N)`, `exact_div(self.len(), N)`,
`self.as_mut_ptr().cast()`, and `from_raw_parts_mut(..., new_len)`. The saved
actual Verus proof records a B disposition modulo reviewed
as_mut_ptr/from_raw_parts_mut patterns plus target-local source-backed exact-div,
UB-precondition, mutable raw-pointer cast/provenance, and mutable
raw-parts/final-frame boundaries; the public target function is executable, not
`external_body`, and contains no `assume_specification`.
The `core::slice::as_flattened` harness preserves the Rust 1.96 body as the
ZST `checked_mul().expect("slice len overflow")` path, the non-ZST unsafe
`unchecked_mul` path, `self.as_ptr().cast()`, and the final unsafe
`from_raw_parts(..., len)`. The 20260815T1950Z reduction executes the local
array-to-element raw pointer cast wrapper directly and retains only a proof-only
cast relation/domain bridge; directly exposing `core::slice::from_raw_parts`
still fails `--crate-type=lib --no-verify` as unsupported. The saved actual
Verus proof records `verification results:: 5 verified, 0 errors` and a B
disposition modulo reviewed as_ptr/from_raw_parts patterns plus target-local
source-backed layout-query, overflow-panic arithmetic, unchecked arithmetic,
cast relation/domain, and immutable raw-parts boundaries; the public target
function is executable, not `external_body`, and contains no
`assume_specification`.
The `core::slice::as_flattened_mut` harness mirrors that proof for the mutable
Rust 1.96 body: it preserves the ZST `checked_mul().expect("slice len overflow")`
path, the non-ZST unsafe `unchecked_mul` path, `self.as_mut_ptr().cast()`, and
the final unsafe `from_raw_parts_mut(..., len)`. The 20260815T1950Z reduction
executes the local mutable array-to-element raw pointer cast wrapper directly
(`ptr as *mut T`, because direct `ptr.cast()` is unsupported here) and retains
only a proof-only mutable cast relation/domain/final-frame bridge; directly
exposing `core::slice::from_raw_parts_mut` still fails `--crate-type=lib
--no-verify` as unsupported. The saved actual Verus proof records
`verification results:: 5 verified, 0 errors` and a B disposition modulo
reviewed as_mut_ptr/from_raw_parts_mut patterns plus target-local source-backed
layout-query, overflow-panic arithmetic, unchecked arithmetic, mutable cast
relation/domain/final-frame, and mutable raw-parts/final-frame boundaries; the
public target function is executable, not `external_body`, and contains no
`assume_specification`.
The flattened slice/Vec multiply helpers are currently adjudicated necessary
boundaries. Focused removal probes on the immutable slice flattening harness show
that an executable `checked_mul().expect` helper must prove both the exact
product postcondition and the `expect` panic precondition despite the preserved
ZST overflow path, while executable `usize::unchecked_mul` is rejected by this
Verus std surface as unsupported without an assume specification. The same
helper pair is used by `core::slice::as_flattened_mut` and
`alloc::vec::Vec::into_flattened`, so all six helper external bodies remain
narrow source-backed intrinsic/panic/arithmetic boundaries.
The `core::slice::last_chunk_mut` harness mirrors that suffix proof for the
mutable Rust 1.96 body: it preserves `checked_sub(N)` early `None`,
`split_at_mut(index)`, and the final unsafe
`last.as_mut_ptr().cast_array()` conversion. The saved actual Verus proof
records a B disposition modulo reviewed vstd `split_at_mut` suffix-view and
final-frame facts plus the target-local source-backed mutable raw-pointer/array
reference boundary `rust_1_96_last_chunk_mut_array_ref`; the public target
function is executable, not `external_body`, and contains no
`assume_specification`.
The `core::slice::split_last_chunk` harness preserves the Rust 1.96
`checked_sub(N)` early `None`, `split_at(index)`, and returned `(init, unsafe
suffix array reference)` pair. The saved actual Verus proof records a B
disposition modulo reviewed vstd `split_at` prefix/suffix-view facts plus the
target-local source-backed raw-pointer/array-reference boundary
`rust_1_96_split_last_chunk_array_ref`; the public target function is
executable, not `external_body`, and contains no `assume_specification`.
The `core::slice::split_last_chunk_mut` harness mirrors that proof for the
mutable Rust 1.96 body: it preserves `checked_sub(N)` early `None`,
`split_at_mut(index)`, and returns `(init, unsafe mutable suffix array
reference)` through `last.as_mut_ptr().cast_array()`. The saved actual Verus
proof records a B disposition modulo reviewed vstd `split_at_mut` prefix/suffix
view and final-frame facts plus the target-local source-backed mutable
raw-pointer/array-reference boundary `rust_1_96_split_last_chunk_mut_array_ref`;
the public target function is executable, not `external_body`, and contains no
`assume_specification`.
The `core::slice::rsplit` harness preserves the Rust 1.96 public delegation
`RSplit::new(slice, pred)` and the private constructor chain
`RSplit::new(slice, pred) -> Self { inner: Split::new(slice, pred) }` with
`Split::new(slice, pred) -> Self { v: slice, pred, finished: false }`. The
saved actual Verus proof records a B disposition modulo only the source-backed
reverse predicate split iterator-view vocabulary and uninterpreted FnMut
predicate-observation relation; the public target function is executable, not
`external_body`, and contains no `assume_specification`.
The `core::slice::rsplitn` harness preserves the Rust 1.96 public delegation
`RSplitN::new(self.rsplit(pred), n)`, adapted only to explicit receiver form
`RSplitN::new(rsplit(slice, pred), n)`. It reuses the reviewed immutable
`rsplit` constructor/view vocabulary and verifies the source-backed
`RSplitN::new(s, n) -> Self { inner: GenericSplitN { iter: s, count: n } }`
constructor flow, preserving the generated
`slice_predicate_split_view(iter, slice@, pred, false, true, n as int)`
contract through the stored count. The saved actual Verus proof records a B
disposition modulo the source-backed RSplitN/GenericSplitN iterator-view and
uninterpreted FnMut predicate-observation boundaries; the public target
function is executable, not `external_body`, and contains no
`assume_specification`.
The `core::slice::split` harness preserves the Rust 1.96 public delegation
`Split::new(slice, pred)` and verifies the private constructor data flow
`Split::new(slice, pred) -> Self { v: slice, pred, finished: false }`. The saved
actual Verus proof records a B disposition modulo only the source-backed forward
predicate split iterator-view vocabulary and uninterpreted FnMut
predicate-observation relation; the public target function is executable, not
`external_body`, and contains no `assume_specification`.
The `core::slice::splitn` harness preserves the Rust 1.96 public delegation
`SplitN::new(self.split(pred), n)`, adapted only to explicit receiver form
`SplitN::new(split(slice, pred), n)`. It reuses the reviewed immutable `split`
constructor/view vocabulary and verifies the source-backed
`SplitN::new(s, n) -> Self { inner: GenericSplitN { iter: s, count: n } }`
constructor flow, preserving the generated
`slice_predicate_split_view(iter, slice@, pred, false, false, n as int)`
contract through the stored count. The saved actual Verus proof records a B
disposition modulo the source-backed SplitN/GenericSplitN iterator-view and
uninterpreted FnMut predicate-observation boundaries; the public target function
is executable, not `external_body`, and contains no `assume_specification`.
The `core::slice::split_inclusive` harness preserves the Rust 1.96 public
delegation `SplitInclusive::new(slice, pred)` and verifies the private
constructor data flow
`let finished = slice.is_empty(); Self { v: slice, pred, finished }`. The saved
actual Verus proof records a B disposition modulo only the source-backed forward
inclusive predicate split iterator-view vocabulary and uninterpreted FnMut
predicate-observation relation; the public target function is executable, not
`external_body`, and contains no `assume_specification`.
The repaired mutable split-iterator rows `core::slice::split_inclusive_mut`,
`core::slice::rsplit_mut`, `core::slice::rsplitn_mut`,
`core::slice::split_mut`, and `core::slice::splitn_mut` preserve their Rust 1.96
public delegation and private constructor flows plus the source-backed
iterator-view and FnMut predicate-observation vocabulary. Their generated
contracts now remove only the unsound `final(slice)@ == old(slice)@`
postcondition that treated the borrowed mutable iterator as leaving the source
slice unowned. Actual Verus verifies the refreshed target harnesses as B rows
modulo the source-backed iterator-view boundary; the target bodies are
executable, not `external_body`, and contain no `assume_specification`.
The `core::slice::select_nth_unstable` harness preserves the Rust 1.96 public
delegation `sort::select::partition_at_index(slice, index, T::lt)`, adapted only
from the inherent receiver to an explicit Verus parameter. The saved actual Verus
proof records a B disposition modulo the source-backed private
`sort::select::partition_at_index` selection algorithm boundary from
`core/src/slice/sort/select.rs:17-59` plus the `T::lt` Ord comparison-observation
boundary; the public target function is executable, not `external_body`, and
contains no `assume_specification`.
The `core::slice::select_nth_unstable_by` harness preserves the Rust 1.96
comparator-selection intent
`sort::select::partition_at_index(self, index, |a: &T, b: &T| compare(a, b) == Less)`,
adapted to an explicit receiver and a named Verus-only comparator-closure lowering
boundary because this Verus build rejects closures that capture a mutable FnMut
comparator. The saved actual Verus proof records a B disposition modulo that
FnMut comparator observation boundary plus the source-backed private
`sort::select::partition_at_index` selection algorithm boundary; the public target
function is executable, not `external_body`, and contains no
`assume_specification`.
The `core::slice::select_nth_unstable_by_key` harness preserves the Rust 1.96
key-selection intent
`sort::select::partition_at_index(self, index, |a: &T, b: &T| f(a).lt(&f(b)))`,
adapted to an explicit receiver and a named Verus-only key-closure lowering
boundary because this Verus build rejects closures that capture a mutable FnMut
key extractor. The saved actual Verus proof records a B disposition modulo that
FnMut key/Ord observation boundary plus the source-backed private
`sort::select::partition_at_index` selection algorithm boundary; the public target
function is executable, not `external_body`, and contains no
`assume_specification`.
The `core::slice::sort_unstable` harness preserves the Rust 1.96 unstable-sort
delegation `sort::unstable::sort(self, &mut T::lt)`, adapted only from the
receiver to an explicit Verus `slice` parameter. The saved actual Verus proof
records a B disposition modulo the source-backed private
`sort::unstable::sort` algorithm boundary from
`core/src/slice/sort/unstable/mod.rs:22-58` plus the `T::lt` Ord comparison
observation boundary; the generated contract remains permutation plus
sorted-by-Ord only, with no stability or unique-output obligation.
The `core::slice::sort_unstable_by` harness preserves the Rust 1.96
unstable-sort comparator intent
`sort::unstable::sort(self, &mut |a, b| compare(a, b) == Ordering::Less)`,
adapted to an explicit receiver and a named Verus-only comparator-closure
lowering boundary because this Verus build rejects closures that capture a
mutable FnMut comparator. The saved actual Verus proof records a B disposition
modulo that FnMut comparator observation boundary plus the same source-backed
private `sort::unstable::sort` algorithm boundary; the generated contract
remains permutation plus comparator-observation sortedness only, with no
stability or unique-output obligation.
The `core::slice::sort_unstable_by_key` harness preserves the Rust 1.96
unstable-sort key intent
`sort::unstable::sort(self, &mut |a, b| f(a).lt(&f(b)))`, adapted to an
explicit receiver plus a named Verus-only key/Ord closure-observation boundary
because this Verus build rejects closures that capture a mutable FnMut key
function and compare extracted keys. The saved actual Verus proof records a B
disposition modulo that FnMut key/Ord observation boundary plus the same
source-backed private `sort::unstable::sort` algorithm boundary; the generated
contract remains permutation plus key-sortedness only, with no stability or
unique-output obligation.
The
`core::slice::iter_mut` harness preserves the Rust target body as the single
`IterMut::new(slice)` delegation. Its private constructor is now executable in
the harness through a Ghost constructor-to-view model that initializes the
iterator view from `old(slice)@` and proves `final(slice)@ == old(slice)@`; the
raw `NonNull`/`end_or_len` representation remains only a reviewed model limit.
The `core::slice::IterMut::into_slice`
harness preserves the Rust 1.96 body as
`unsafe { from_raw_parts_mut(self.ptr.as_ptr(), len!(self)) }`. The saved actual
Verus proof records a B disposition modulo the source-backed
raw-parts/provenance/unsafe and `len!` macro boundary; the target method is not
`external_body` and does not assume the generated postcondition directly. The
`alloc::vec::Vec::as_mut_ptr` harness preserves the Rust 1.96 public body as
`self.buf.ptr()`, with target-local `Vec { buf, len }` and RawVec context.
`RawVec::ptr` is now executable as `self.inner.ptr::<T>()`, with closed
RawVec-to-RawVecInner spec links for initialized sequence and capacity; the
retained boundary is the lower `RawVecInner::ptr`
allocator/raw-pointer/provenance relation for `vec_start_mut_ptr`. The public
target method is executable, not `external_body`, and contains no
`assume_specification`. The `alloc::vec::Vec::as_ptr` harness mirrors that
pattern for the immutable pointer contract: the public target keeps the Rust
1.96 body `self.buf.ptr()` under
`vec_start_ptr(vec@, vec.spec_capacity(), ptr)`, while `RawVec::ptr` is
executable and only the private `RawVecInner::ptr` allocator/raw-pointer/
provenance and immutable pointer exposure semantics are boundary-modeled. Both
RawVec pointer target harnesses pass actual Verus with `verification results::
2 verified, 0 errors`; their public target methods are executable, not
`external_body`, and contain no `assume_specification`. The
`alloc::vec::Vec::extend_from_within` harness
preserves the Rust 1.96 body shape as
`let range = slice::range(src, ..self.len()); self.reserve(range.len()); unsafe { self.spec_extend_from_within(range); }`
under the generated `vec_range_bounds_valid(old(vec)@, src)` precondition and
`vec_extend_from_within_result(old(vec)@, src, final(vec)@)` postcondition. The
saved actual Verus proof records a B disposition modulo the source-backed
`slice::range`/`RangeBounds` resolution and `Vec::len` view bridge,
`Vec::reserve` allocator/capacity behavior, and lower spare-storage/provenance,
unchecked-source `Clone`/write, and initialized-prefix bridges; the private
extension helper now executes a source-shaped clone/write loop rather than a
whole-helper boundary. The public target method is executable, not
`external_body`, and contains no `assume_specification`. The
`alloc::vec::Vec::extract_if` harness preserves the
Rust 1.96 public body as the single delegation
`ExtractIf::new(self, filter, range)` under the generated
`vec_range_bounds_valid(old(vec)@, range)` precondition and
`vec_extract_if_created(old(vec)@, range, filter, iter, final(vec)@)`
postcondition. The saved actual Verus proof records a B disposition modulo the
source-shaped private `ExtractIf::new` constructor lowering, with retained trust
limited to `slice::range`/`RangeBounds` resolution and the lower
`vec_extract_if_created` bridge over stored `FnMut`, mutable-borrow lifetime,
future iterator/removal trace, and Drop hole-filling state. The constructor
executes the leak-amplification `set_len(0)` and field initialization; the
public target method is executable, not `external_body`, and contains no
`assume_specification`. The `alloc::vec::Vec::drain` harness
preserves the Rust 1.96 public body flow as `len`, `slice::range(range, ..len)`,
unsafe `set_len(start)`, raw immutable slice construction from
`self.as_ptr().add(start)` and `end - start`, `range_slice.iter()`, and
`Drain { tail_start, tail_len, iter, vec: NonNull::from(self) }`. The saved
actual Verus proof now reports `verification results:: 7 verified, 0 errors`.
The harness executes `len`, `as_ptr`, `set_len(start)`, `NonNull::from`, and the
`ConstPtr::add` pointer-token wrapper directly, retaining only source-backed
RangeBounds normalization, raw-parts provenance, and opaque Drain
iterator/lifetime/drop-state semantics; the public target method is executable,
not `external_body`, and contains no
`assume_specification`. The `alloc::vec::Vec::from_raw_parts`
harness preserves the Rust 1.96 public body as
`unsafe { Self::from_raw_parts_in(ptr, length, capacity, Global) }` under the
generated `vec_raw_parts_domain::<T>(ptr, length, capacity)` precondition and
the initialized-sequence/capacity postconditions. The private allocator-aware
`Vec::from_raw_parts_in` wrapper is now executable too: it performs the
source-shaped `RawVec::from_raw_parts_in(ptr, capacity, alloc)` call and
returns `Vec { buf, len: length }`. The saved actual Verus proof records a B
disposition modulo the lower `RawVec::from_raw_parts_in` allocator/raw-pointer
provenance, capacity, and initialized-prefix model; the public target and
private Vec wrapper are executable, not `external_body`, and contain no
`assume_specification`. The `alloc::vec::Vec::into_boxed_slice` harness
preserves the Rust 1.96 flow
`self.shrink_to_fit(); let me = ManuallyDrop::new(self); let buf = ptr::read(&me.buf); let len = me.len(); buf.into_box(len).assume_init()`,
with only the Verus syntax adaptation from `mut self` to an owned `self` plus a
local mutable binding. The saved actual Verus proof records a B disposition
modulo source-backed `shrink_to_fit`, executable `ManuallyDrop` field projection,
executable modeled `ptr::read`, and retained `RawVec::into_box` /
`Box<[MaybeUninit<T>]>::assume_init` boundaries, while preserving the generated
`boxed_slice_view` and
`boxed_slice_capacity` postconditions; the public target method is executable,
not `external_body`, and contains no `assume_specification`. The
`alloc::vec::Vec::into_flattened` harness preserves the Rust 1.96 flow
`into_raw_parts_with_alloc(); if T::IS_ZST { checked_mul().expect(...) } else { unchecked_mul(...) }; Vec::<T, A>::from_raw_parts_in(ptr.cast(), new_len, new_cap, alloc)`.
The saved actual Verus proof records a B disposition modulo source-backed
`into_raw_parts_with_alloc`, `T::IS_ZST`/layout query,
`checked_mul().expect` panic edge, unchecked length/capacity multiplication,
array-to-element raw-pointer cast, and `Vec::from_raw_parts_in` allocator/raw
reconstruction boundaries, while preserving the generated
`ret@ == flatten_array_vec::<T, N>(vec@)` and
`ret@.len() == vec@.len() * N` postconditions; the public target method is
executable, not `external_body`, and contains no `assume_specification`. The
20260815T2003Z raw-parts no-external probe for this target passed
`--crate-type=lib --no-verify` but actual Verus failed exactly the unmodeled
array-cast relation, direct `from_raw_parts_in` view/length reconstruction,
`into_raw_parts_with_alloc` length/capacity/flattened-storage facts, and the
downstream unchecked-multiplication preconditions. Production was therefore left
unchanged and the retained raw-parts/provenance boundaries remain source-backed,
not an unexamined blocker. The
`alloc::vec::Vec::into_raw_parts` harness preserves the Rust 1.96 body as
`let mut me = ManuallyDrop::new(self); (me.as_mut_ptr(), me.len(), me.capacity())`.
The saved actual Verus proof records a B disposition modulo only the
source-backed raw-pointer/provenance and generated raw-parts vocabulary
boundaries; `ManuallyDrop::new`, `len`, and `capacity` are executable over the
length-indexed initialized-sequence model. The public target method is
executable, not `external_body`, and contains no `assume_specification`. The
`alloc::vec::Vec::leak` harness preserves the Rust
1.96 body as
`let mut me = ManuallyDrop::new(self); unsafe { slice::from_raw_parts_mut(me.as_mut_ptr(), me.len) }`.
The saved actual Verus proof records a B disposition modulo only the reviewed
no-drop wrapper context, Vec/RawVec raw-pointer provenance, and unsafe
mutable-slice-view boundaries; `ManuallyDrop::new` now verifies as an executable
field move over the length-indexed initialized-sequence model while preserving
`ret@ == vec@` and `final(ret)@.len() == vec@.len()`. The public target method is
executable, not `external_body`, and contains no `assume_specification`. The
`core::slice::as_mut_ptr` harness records a B disposition modulo a target-local
source-backed raw-pointer/provenance boundary for Rust's
`self as *mut [T] as *mut T` expression, because this Verus build rejects that
raw slice-to-element pointer cast when it is placed directly in the
non-`external_body` target body; the exact cast is kept inside the named
external boundary, and the public target function is not `external_body` and
contains no `assume_specification`. The `core::slice::as_mut_ptr_range`
harness preserves the Rust 1.96 body as `let start = self.as_mut_ptr(); let end
= unsafe { start.add(self.len()) }; start..end`, reuses the reviewed mutable
start-pointer/final-frame boundary from `as_mut_ptr`, and isolates only the
source-backed raw-pointer/provenance `add` range-end operation; the public
target function is executable, not `external_body`, and proves
`slice_mut_ptr_range_starts_at_slice(old(slice)@, range)` plus
`final(slice)@ == old(slice)@`. A focused no-external-body attempt for the
range-end `*mut T::add` bridge is rejected by this Verus build at typecheck
without a std pointer-add assume-specification, so the named range-end bridge is
retained. The `core::slice::as_ptr` harness mirrors that
source-backed boundary for Rust's `self as *const [T] as *const T` expression:
the public target function is executable and not `external_body`, while the
exact immutable raw slice-to-element pointer cast is isolated in the
target-local `rust_1_96_slice_as_ptr_cast` boundary carrying the generated
`slice_start_ptr` postcondition; its corresponding `*const T::add` range-end
bridge is retained for the same Verus pointer-add typecheck limitation. The
`core::slice::align_to` harness preserves
the Rust 1.96 body as the ZST early return, `self.as_ptr()`,
`ptr::align_offset`, offset fallback, `self.split_at(offset)`,
`rest.align_to_offsets::<U>()`, and final unsafe `from_raw_parts` tuple. The
saved actual Verus proof records a B disposition modulo named source-backed
layout/ZST, align-offset intrinsic, narrowed offsets multiplication-fit/view
bridge, split/result bridge, and raw-parts pointer/provenance boundaries; it does not mark
`split_at`, `from_raw_parts`, alignment intrinsics, or raw pointer provenance
complete for other targets. The `core::slice::align_to_mut` harness preserves
the Rust 1.96 branch structure as the ZST early return, `self.as_ptr()`,
`ptr::align_offset`, offset fallback, and aligned mutable raw-parts branch. The
saved actual Verus proof records a B disposition modulo named source-backed
layout/ZST, align-offset intrinsic, narrowed offsets multiplication-fit,
`split_at_mut`, mutable `from_raw_parts_mut` raw-pointer/provenance/aliasing, and final-frame
result-bridge boundaries; it does not mark `split_at_mut`,
`from_raw_parts_mut`, alignment intrinsics, or mutable raw-pointer provenance
complete for other targets. The `core::slice::as_rchunks` harness preserves the
Rust 1.96 body as the
nonzero const-generic assertion, `len = slice.len() / N`, split at
`slice.len() - len * N`, unsafe `multiple_of_n.as_chunks_unchecked()`, and
`(remainder, array_slice)` return. The saved actual Verus proof records a B
disposition modulo the reviewed vstd `split_at` view facts plus the
source-backed unsafe array/chunk-view boundary
`rust_1_96_as_chunks_unchecked_view`; the public target function is executable,
not `external_body`, and contains no `assume_specification`. The
`core::slice::as_rchunks_mut` harness preserves the Rust 1.96 body as the
nonzero const-generic assertion, `len = slice.len() / N`, mutable split at
`slice.len() - len * N`, unsafe `multiple_of_n.as_chunks_unchecked_mut()`, and
`(remainder, array_slice)` return. The saved actual Verus proof records a B
disposition modulo the reviewed vstd `split_at_mut` view/final-frame facts plus
the source-backed unsafe mutable array/chunk-view boundary
`rust_1_96_as_chunks_unchecked_mut_view`; the public target function is
executable, not `external_body`, and contains no `assume_specification`. The
`core::slice::assume_init_drop` harness preserves the Rust 1.96 nonempty check
and the unsafe `ptr::drop_in_place(self as *mut [MaybeUninit<T>] as *mut [T])`
operation through a single target-local source-backed boundary
`rust_1_96_assume_init_drop_in_place`. The saved actual Verus proof records a B
disposition modulo that MaybeUninit raw-storage, raw-pointer/provenance,
`Destruct`, and destructor-effect boundary; the public target function is
executable, not `external_body`, and contains no `assume_specification`. The
`core::slice::assume_init_mut` harness preserves the Rust 1.96 body shape as
the unsafe mutable slice cast
`unsafe { &mut *(self as *mut Self as *mut [T]) }`, adapted only to the explicit
`slice` receiver, through the target-local source-backed boundary
`rust_1_96_assume_init_mut_raw_cast`. The saved actual Verus proof records a B
disposition modulo MaybeUninit initialized raw-storage layout and mutable
raw-pointer/provenance semantics; the public target function is executable, not
`external_body`, and contains no `assume_specification`. The
20260815T1700Z raw-cast adjudication attempted exact no-external-body probes for
`core::slice::assume_init_mut`, `write_clone_of_slice`, and
`write_copy_of_slice` by preserving the Rust 1.96
`unsafe { &mut *(slice as *mut [MaybeUninit<T>] as *mut [T]) }` cast body while
removing only `#[verifier::external_body]`; all three probes fail during
`--crate-type=lib --no-verify` with Verus' unsupported implicit pointer
dereference diagnostic, while the unchanged production harnesses pass actual
Verus with 1/6/4 verified and 0 errors respectively. Therefore the production
raw-cast boundary is retained as the minimal source-backed boundary rather than
promoted to executable code. The
`core::slice::assume_init_ref` harness preserves the Rust 1.96 body shape as
the unsafe immutable slice cast
`unsafe { &*(self as *const Self as *const [T]) }`, adapted only to the explicit
`slice` receiver, through the target-local source-backed boundary
`rust_1_96_assume_init_ref_raw_cast`. The saved actual Verus proof records a B
disposition modulo MaybeUninit initialized raw-storage layout and immutable
raw-pointer/provenance semantics; the public target function is executable, not
`external_body`, and contains no `assume_specification`. The 20260815T1710Z
assume-init ref/drop adjudication attempted exact no-external-body probes for
`core::slice::assume_init_drop` and `core::slice::assume_init_ref` by preserving
the Rust 1.96 `ptr::drop_in_place(self as *mut [MaybeUninit<T>] as *mut [T])`
and `unsafe { &*(self as *const Self as *const [T]) }` bodies while removing
only the target-local `#[verifier::external_body]`; both probes fail during
`--crate-type=lib --no-verify` with Verus' unsupported implicit pointer
dereference diagnostic, while the unchanged production harnesses pass actual
Verus with 1 verified and 0 errors each. Therefore both production boundaries
are retained as minimal source-backed boundaries rather than promoted to
executable code. The
`core::slice::write_clone_of_slice` harness preserves the Rust 1.96 flow through
the length assertion, equal-length `&src[..len]` source prefix, Guard
initialized counter, indexed clone/write loop, `forget(guard)`, and final
`assume_init_mut` dependency. The equal-length source-prefix helper now verifies
as executable full-prefix `split_at(len)` code under `len == src@.len()`, so it
is no longer a target-local `external_body`; the per-iteration wrapper also now
verifies the source-side index bound and executes `src[i].clone()` before
crossing only the lower destination `slice[i].write(value)` MaybeUninit
slot-write/indexing/provenance boundary. The former whole-loop written-from
bridge is narrowed to a per-iteration prefix bridge carried by the loop invariant.
The saved actual Verus proof records a B disposition modulo source-backed
MaybeUninit relation vocabulary, that lower destination write boundary, the
per-iteration guard/write bridge, and the reviewed
`assume_init_mut` raw-cast boundary. The follow-up no-external probe for only the
per-iteration bridge typechecks but fails actual Verus on the one-step
initialized/value prefix postcondition, so that bridge is retained as the minimal
relational effect rather than removed; the public target function itself remains
executable, not `external_body`, and contains no
`assume_specification`. The `core::slice::write_copy_of_slice` harness preserves
the Rust 1.96 flow through the unsafe same-layout `&[T]` to
`&[MaybeUninit<T>]` transmute, `copy_from_slice` into the destination, and final
`assume_init_mut` dependency. The saved actual Verus proof records a B
disposition modulo source-backed MaybeUninit relation vocabulary, same-layout
transmute, copy_from_slice storage effect, and the reviewed `assume_init_mut`
raw-cast boundary; the public target function is executable, not
`external_body`, and contains no `assume_specification`. The
`core::slice::make_ascii_lowercase`
harness preserves the Rust loop over `self.len()`, mutable byte borrow,
per-byte lower-case call, and index increment; its primitive `u8` helper chain
now uses a verified numeric `matches!(byte, 0x41u8..=0x5au8)` range pattern for
the Rust `b'A'..=b'Z'` source range and records no trusted implementation
boundary. The `core::slice::make_ascii_uppercase` harness preserves the same
real slice loop shape for upper-case conversion; its primitive helper similarly
uses `matches!(byte, 0x61u8..=0x7au8)` for the Rust `b'a'..=b'z'` source range
and records no trusted implementation boundary. The `core::slice::rchunks`
harness preserves the Rust target body as the nonzero chunk-size assertion
followed by `RChunks::new(slice, chunk_size)`, verifies the extracted
`RChunks::new` constructor body in the same harness, and records only the
source-backed `RChunks { v, chunk_size }` iterator-view representation as a
boundary. The `core::slice::rchunks_exact` harness preserves the Rust target
body as the nonzero chunk-size assertion followed by
`RChunksExact::new(slice, chunk_size)`, verifies the extracted constructor body
through `rem = slice.len() % chunk_size`, split, and
`RChunksExact { v: snd, rem: fst, chunk_size }` construction, and records only a
source-backed iterator-view representation plus the valid-index split boundary.
The `core::slice::split_first` harness preserves the first/tail control-flow and
data-flow shape of Rust's slice pattern by mechanically lowering the unsupported
`[first, tail @ ..]` pattern to the nonempty branch, `split_at(1)`, and
`&head[0]`; it records the vstd `split_at` and index view facts as the narrow
boundary. The `core::slice::split_first_mut` harness applies the same mechanical
lowering to the mutable Rust body using `slice.len() != 0`,
`slice.split_at_mut(1)`, and `&mut head[0]`, with proof-only view assertions
before taking the mutable element borrow; it records the vstd mutable split/index
and final-reconstruction facts as the narrow boundary. The
`core::slice::split_last` harness preserves the Rust init/last control-flow and
data-flow shape by mechanically lowering the unsupported `[init @ .., last]`
pattern to the nonempty branch, `split_at(len - 1)`, and `&tail[0]`; it records
the vstd `split_at` and index view facts as the narrow boundary.
The `core::slice::split_last_mut` harness preserves the mutable init/last
control-flow and data-flow shape by mechanically lowering the unsupported
`[init @ .., last]` pattern to the nonempty branch,
`split_at_mut(slice.len() - 1)`, and `&mut tail[0]`, with proof-only view
assertions before taking the mutable last-element borrow; it records the vstd
mutable split/index and final-reconstruction facts as the narrow boundary.
The `core::slice::split_off` harness preserves the Rust 1.96 flow through
`split_point_of(range)`, the bounds check, `split_at(split_index)`, and the
`Direction::{Front,Back}` reassignment/return branches. It records a B proof
modulo the source-backed one-sided range-bound model plus the vstd immutable
`split_at` view facts needed to prove the generated prefix/suffix
`slice_split_off_partition` relation; the target body is executable and is not
externalized.
The `core::slice::split_off_first` harness preserves the Rust 1.96 flow by
calling the reviewed immutable `split_first` helper, returning `None` for the
empty branch, and in the nonempty branch executing `*self = rem` before
returning `Some(first)`. The saved actual Verus proof records a B disposition
modulo the reviewed `split_first` helper's vstd `split_at`/index
slice-pattern desugaring boundary plus the audited
`slice_split_off_first_result` vocabulary; the target body is executable and is
not externalized.
The `core::slice::split_off_last` harness preserves the Rust 1.96 flow by
calling the reviewed immutable `split_last` helper, returning `None` for the
empty branch, and in the nonempty branch executing `*self = rem` before
returning `Some(last)`. The saved actual Verus proof records a B disposition
modulo the reviewed `split_last` helper's vstd `split_at(len - 1)`/index
slice-pattern desugaring boundary plus the audited
`slice_split_off_last_result` vocabulary; the target body is executable and is
not externalized.
The `core::slice::split_off_first_mut` harness preserves the Rust 1.96 flow
through the `mem::replace(self, &mut [])` step by a lifetime-preserving
swap-with-empty lowering because this Verus build rejects `core::mem::replace`
without an assumption; it then mechanically lowers `split_first_mut` to
`split_at_mut(1)`, `&mut head[0]`, `*self = rem`, and `Some(first)`. The saved
actual Verus proof records a B disposition modulo the vstd `core::mem::swap`
replacement fact, mutable split/index facts, and the audited
`slice_split_off_first_result` vocabulary; the target body is executable and is
not externalized.
The `core::slice::split_off_last_mut` harness preserves the Rust 1.96 flow
through the `mem::replace(self, &mut [])` step by the same lifetime-preserving
swap-with-empty lowering; it then mechanically lowers `split_last_mut` to
`split_at_mut(len - 1)`, `&mut tail[0]`, `*self = rem`, and `Some(last)`.
The saved actual Verus proof records a B disposition modulo the vstd
`core::mem::swap` replacement fact, mutable split/index facts, and the audited
`slice_split_off_last_result` vocabulary; the target body is executable and is
not externalized.
The `core::slice::trim_ascii_end` harness preserves the Rust 1.96 flow through
`let mut bytes = self`, repeated trailing-byte inspection, shortening to the
prefix while `u8::is_ascii_whitespace` holds, breaking on the first
non-whitespace byte, and returning `bytes`. The unsupported `[rest @ .., last]`
pattern is mechanically lowered to `bytes.len()`, `bytes.split_at(len - 1)`,
and `&tail[0]`; the saved actual Verus proof records a B disposition modulo the
source-backed primitive byte whitespace helper, audited `ascii_trim_end_*`
vocabulary, and Verus slice-pattern desugaring boundary.
The `core::slice::trim_ascii_start` harness preserves the Rust 1.96 flow through
`let mut bytes = self`, repeated leading-byte inspection, shortening to the
rest while `u8::is_ascii_whitespace` holds, breaking on the first
non-whitespace byte, and returning `bytes`. The unsupported
`[first, rest @ ..]` pattern is mechanically lowered to `bytes.len()`,
`bytes.split_at(1)`, and `&head[0]`; the saved actual Verus proof records a B
disposition modulo the source-backed primitive byte whitespace helper, audited
`ascii_trim_start_*` vocabulary, and Verus slice-pattern desugaring boundary.
The `core::slice::trim_ascii` harness preserves the Rust 1.96 body
`self.trim_ascii_start().trim_ascii_end()` as an executable public target through
the already reviewed `trim_ascii_start` and `trim_ascii_end` dependencies. The
saved actual Verus proof records `8 verified, 0 errors` for the project-local
generated contract `ascii_trim_source_body_result(slice@, ret)`, whose end index
is computed on the suffix produced by `ascii_trim_start_index`. This converts
the row to **B** while preserving the source-body composition semantics for
nonempty all-whitespace inputs.
The `core::slice::utf8_chunks` harness preserves the Rust 1.96 body as the
single `Utf8Chunks { source: self }` construction, adapted only to an explicit
Verus receiver parameter. The saved actual Verus proof records a B disposition
modulo the source-backed `Utf8Chunks` source-field iterator-view boundary and
the audited `utf8_chunk_partition` vocabulary; it does not model UTF-8 decoding
iteration beyond the initial source-backed iterator state needed by the
contract.
The `core::slice::windows` harness preserves the Rust 1.96 body as
`let size = NonZero::new(size).expect("window size must be non-zero");`
followed by `Windows::new(slice, size)`, adapted only to an explicit Verus
receiver parameter. The saved actual Verus proof records a B disposition modulo
the source-backed local NonZero success/panic model, the extracted
`Windows { v, size }` private representation, the verified `Windows::new`
constructor body, and the audited `slice_iterator_view` vocabulary boundary.
The `alloc::vec::Drain::as_slice` harness preserves the Rust 1.96 body as the
single `self.iter.as_slice()` delegation. It extracts the source-backed
`Drain { tail_start, tail_len, iter: slice::Iter<'a, T>, vec }` representation,
instantiates `vec_drain_remaining` through the delegated slice iterator-view
relation over `Drain.iter`, and records a B disposition modulo that
source-backed iterator-view boundary rather than assuming the target
postcondition directly.
The `alloc::vec::IntoIter::as_slice` harness preserves the Rust 1.96 body as
`unsafe { slice::from_raw_parts(self.ptr.as_ptr(), self.len()) }`, adapted only
to a named Verus raw-parts boundary after evaluating the source operands. It
extracts `IntoIter { buf, phantom, cap, alloc, ptr, end }`, keeps `NonNull` and
allocator storage opaque, models `self.len()` as the source-backed remaining
view length, and records a B disposition modulo the immutable raw-parts
pointer/provenance and iterator-length boundaries. The public target is not
`external_body` and contains no `assume_specification`.
The `core::slice::chunk_by` harness preserves the Rust 1.96 body as the single
`ChunkBy::new(slice, pred)` delegation, adapted only from the inherent receiver
to an explicit Verus parameter. It extracts `ChunkBy { slice, predicate }`,
verifies the private constructor body `ChunkBy { slice, predicate }` in the same
harness, preserves the `F: FnMut(&T, &T) -> bool` callback bound without invoking
the callback, and records a B disposition modulo the source-backed
`slice_iterator_view` / `slice_adjacent_chunk_view` vocabulary boundary rather
than assuming the target postcondition.
The `core::slice::clone_from_slice` harness still preserves the Rust 1.96 public
body as the single private-helper delegation `self.spec_clone_from(src)`, adapted
only to an explicit `dst: &mut [T]` receiver. The private helper is no longer a
whole `external_body` boundary: `spec_clone_from` now executes the source-shaped
default path with an equal-length source prefix, an `idx < self.len()` loop, and
prefix proof invariants. Retained trust is limited to the lower per-element
`Clone::clone_from` effect plus the source-backed TrivialClone copy
specialization through `copy_from_slice_impl`. The target passes both
`--crate-type=lib --no-verify` and actual Verus (`verification results:: 6
verified, 0 errors`); aggregate admission remains B=180, pending=0, exact-vstd=36
with direct external-body surface 121/315.
The `core::slice::copy_from_slice` harness preserves the Rust 1.96 public wrapper
as `unsafe { copy_from_slice_impl(dst, src) }`, carries the exact-vstd equal-length
domain and `final(dst)@ == src@` postcondition, keeps the private helper's
length-mismatch branch shape by proving it unreachable from the domain, and reaches
`ptr::copy_nonoverlapping(src.as_ptr(), dest.as_mut_ptr(), dest.len())`. Its B
disposition is modulo named source-backed boundaries for slice pointer exposure
and the raw copy destination-write effect; the removed target-local
`len_mismatch_fail` helper is no longer a retained boundary, and the public target
is not `external_body` and contains no `assume_specification`. The follow-up
`copy_from_slice_raw_copy_boundary_adjudication_20260816T0538Z` keeps production
unchanged after a probe removed only the
`rust_1_96_copy_nonoverlapping_establishes_dst` `external_body`: the probe passes
`--crate-type=lib --no-verify`, then actual Verus fails the raw-copy effect
postcondition `final(dest)@ == source` (`verification results:: 2 verified, 1
errors`), while the unchanged production harness still passes
`--crate-type=lib --no-verify` and actual Verus (`verification results:: 2
verified, 0 errors`) and the aggregate gate then remained B=180, pending=0,
exact-vstd=36 with then-recorded direct external-body surface 121/290.
The `core::slice::copy_within` harness preserves the Rust 1.96 flow through
`slice::range`, `count = src_end - src_start`, the destination bounds assert, a
single same-loan `as_mut_ptr`, source and destination `ptr.add`, and overlapping
`ptr::copy`. It carries the exact-vstd valid-range/destination-fit domain and
proves `final(slice)@ == copy_within_result(old(slice)@, src_start, src_end,
dest)` modulo named source-backed boundaries for RangeBounds normalization,
pointer provenance, and the raw overlapping-copy effect. The destination assert
branch is proved unreachable from `copy_within_domain` plus the existing bounds
facts, so `rust_1_96_copy_within_dest_assert_failed` is no longer a retained
boundary; the public
target is not `external_body` and contains no `assume_specification`.
The `core::slice::first` harness preserves the Rust 1.96 body
`if let [first, ..] = self { Some(first) } else { None }` via the already-reviewed
immutable `split_first` slice-pattern desugaring boundary: nonempty slices use
`split_at(1)` and `&head[0]`, while empty slices return `None`. It proves the
exact-vstd contract that empty slices return `None` and nonempty slices return
`Some(slice[0])`; the public target is not `external_body` and contains no
`assume_specification`.
The `core::slice::first_mut` harness preserves the Rust 1.96 body
`if let [first, ..] = self { Some(first) } else { None }` via the
already-reviewed mutable `split_first_mut` slice-pattern desugaring boundary:
nonempty slices use `split_at_mut(1)` and `&mut head[0]`, while empty slices
return `None`. It proves the exact-vstd contract that empty mutable slices are
unchanged and nonempty results alias index 0 with
`final(slice)@ == old(slice)@.update(0, *final(ret.unwrap()))`; the public
target is not `external_body` and contains no `assume_specification`.
The `core::slice::get` harness preserves the Rust 1.96 body `index.get(self)`,
adapted only to the explicit receiver `slice`. It proves the exact-vstd
`ret == spec_slice_get(slice, index)` contract while retaining
`axiom_slice_get_usize`; the local `SliceIndex` contract uses a separate
trait-associated `spec_get` view to avoid a Verus cyclic self-reference between
the associated-output trait contract and `spec_slice_get`. The saved actual Verus
proof records a B disposition modulo the source-backed `SliceIndex::get`
trait-method boundary; the public target is not `external_body` and contains no
`assume_specification`.
The `core::slice::fill` harness preserves the Rust 1.96 public body as the
single `specialize::SpecFill::spec_fill(self, value)` delegation, adapted only
to an explicit `slice: &mut [T]` receiver, but no longer keeps the whole concrete
`[T]` `SpecFill::spec_fill` method as an external boundary. The default Clone
implementation is source-shaped in the harness: for a non-empty slice it
clone_froms the shared value into every element before the final slot and then
moves the original value into the final slot, represented as an index loop for
Verus prefix invariants. The retained trust is the lower per-element
`Clone::clone_from` effect plus the TrivialClone and primitive write-bytes/int
specialization alternatives; the public target and default helper are not
`external_body` and contain no `assume_specification`.
The `core::slice::fill_with` harness preserves the Rust 1.96 element-by-element
callback/write semantics of `for el in self { *el = f(); }`, represented as a
Verus index loop only to expose mutable-slice prefix/suffix invariants. It uses
the audited `zero_arg_fnmut_outputs` vocabulary and verifies the public target
modulo a narrowly named source-backed callback observation boundary whose body is
exactly `f()`; the public target is not `external_body` and contains no
`assume_specification`.
The `core::slice::from_raw_parts` harness replaces the seed recorder with an
executable public unsafe target carrying the generated raw-domain
requires/ensures. It instantiates the audited `SliceRawDomain` /
`slice_from_raw_parts_result` vocabulary locally and isolates only the Rust 1.96
UB-precondition/raw-pointer/provenance operation in
`rust_1_96_from_raw_parts_ub_checked_raw_slice`, whose body is the source-backed
`unsafe { &*core::ptr::slice_from_raw_parts(data, len) }`; the public target is
not `external_body` and contains no `assume_specification`.
The `core::slice::from_raw_parts_mut` harness now follows the same accepted
shape for the mutable raw-parts API. It instantiates the audited
`SliceRawDomain` / `slice_raw_mut_domain` /
`slice_from_raw_parts_mut_result` vocabulary locally, exposes an executable
public unsafe target with the generated mutable raw-domain requires/ensures, and
isolates only the Rust 1.96 UB-precondition/raw-pointer/provenance operation in
`rust_1_96_from_raw_parts_mut_ub_checked_raw_slice`, whose body is the
source-backed
`unsafe { &mut *core::ptr::slice_from_raw_parts_mut(data, len) }`; the public
target is not `external_body` and contains no `assume_specification`.
The `core::slice::get_unchecked` harness replaces the seed recorder with an
executable public unsafe target carrying the generated
`slice_index_in_range(slice@, index)` requires and
`slice_index_result(slice@, index, ret)` postcondition. It preserves the Rust
1.96 `unsafe { &*index.get_unchecked(self) }` data flow through one target-local
source-backed boundary for the `SliceIndex::get_unchecked` raw pointer result and
immediate dereference, citing the frozen trait safety contract in
`core/src/slice/index.rs:145-186`. The saved actual Verus proof records a B
disposition modulo that boundary; the public target is not `external_body` and
contains no `assume_specification`.
The `core::slice::get_unchecked_mut` harness now mirrors that unchecked-index
pattern for the mutable contract. It replaces the seed recorder with an
executable public unsafe target carrying the generated
`slice_index_in_range(old(slice)@, index)` requires and
`slice_index_mut_frame(old(slice)@, index, final(slice)@)` postcondition, and
preserves the Rust 1.96
`unsafe { &mut *index.get_unchecked_mut(self) }` data flow through one
target-local source-backed boundary for the `SliceIndex::get_unchecked_mut` raw
mutable pointer result and immediate dereference. The saved actual Verus proof
records a B disposition modulo that boundary; the public target is not
`external_body` and contains no `assume_specification`.
The `core::slice::get_disjoint_unchecked_mut` harness replaces the seed recorder
with an executable public unsafe target carrying the generated
`slice_disjoint_indices_valid(old(slice)@, indices)` requires and final length
postcondition. It preserves the Rust 1.96 raw-slice-pointer setup,
`MaybeUninit<[&mut I::Output; N]>` array setup, and unsafe fill/`assume_init`
shape through target-local source-backed boundaries for raw pointer/provenance,
MaybeUninit mutable-reference-array storage, `GetDisjointMutIndex: Clone`,
unchecked `indices.get_unchecked(i).clone()`, `SliceIndex::get_unchecked_mut`,
raw `cast/add/write`, and final `arr.assume_init()`. The saved actual Verus
proof records a B disposition modulo those boundaries; the public target is not
`external_body` and contains no `assume_specification`.
The `core::slice::chunk_by_mut` row is now a **B** disposition: the harness
preserves the Rust 1.96 body as the single `ChunkByMut::new(slice, pred)`
delegation, extracts the private `ChunkByMut { slice, predicate }` constructor,
preserves `F: FnMut(&T, &T) -> bool`, and contains no `assume_specification` or
target-body `external_body`. The generated contract removes only the unsound
`final(slice)@ == old(slice)@` frame postcondition; actual Verus verifies the
refreshed harness modulo the source-backed iterator-view boundary.
The `core::slice::split_off_mut` row is now a **B** disposition: the executable
harness preserves the Rust 1.96 flow through `split_point_of(range)?`, the bounds
check, a lifetime-preserving swap-with-empty lowering for the `mem::take(self)`
ownership transfer, `split_at_mut(split_index)`, and the `Direction::{Front,Back}`
reassignment/return branches. The active contract removes only the unsound
`final(ret.unwrap())@` partition while preserving the None frame and initial
returned-region partition. Actual Verus reports `verification results:: 3
verified, 0 errors`, recorded as
`actual_verus_verified_modulo_source_backed_one_sided_range_mem_take_swap_lowering_and_vstd_split_at_mut_boundary`.

The ten repaired mutable iterator rows `core::slice::chunk_by_mut`,
`core::slice::chunks_exact_mut`, `core::slice::chunks_mut`,
`core::slice::rchunks_exact_mut`, `core::slice::rchunks_mut`,
`core::slice::rsplit_mut`, `core::slice::rsplitn_mut`,
`core::slice::split_inclusive_mut`, `core::slice::split_mut`, and
`core::slice::splitn_mut` are all **B** dispositions after removing only the
unsound generated `final(slice)@ == old(slice)@` frame clause. The JSON-backed
live aggregate and CSV/JSON inventory mirrors are synchronized at B=180 and
pending=0; no Rust-body implementation proof remains pending in the 180-target
live scope.


The `alloc::vec::Vec::remove` exact-vstd row first removed the target-local `rust_1_96_remove_assert_failed` helper under `proof_inventory/vec_remove_unreachable_assert_reduction_20260815T1326Z/`: the `None` arm proves contradiction from `i < old(vec).len()` and the try_remove branch facts, then diverges with `loop {}` only to inhabit the unreachable branch. The follow-up `vec_remove_try_remove_boundary_reduction_20260815T2340Z` now also removes the whole unstable `Vec::try_remove` external-body dependency. The public wrapper body `match self.try_remove(i) { Some(elem) => elem, None => assert_failed(...) }` is preserved modulo the exact-vstd parameter name `i`, while local `try_remove` executes len observation, out-of-range `None`, `ptr::read`, overlapping tail `ptr::copy`, `set_len(len - 1)`, and `Some(ret)`. Retained trust is limited to lower raw-pointer/read/copy/set_len effect boundaries; actual Verus reports `verification results:: 12 verified, 0 errors`.
Historical then-recorded direct external-body surface was 121/315 (Slice 79/181, Vec 42/134).
