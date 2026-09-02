---
title: Nanvix Rust Std Slice/Vec Incompleteness Baseline
description: Measured post-proof generated-contract analysis inventory, active 20260817T1200Z implproof certification provenance through reviewed post-1550 retained-boundary/current-consumer evidence, rchunks unchecked source-fidelity repair, the 20260817T0103Z Vec len/capacity production reduction, the 20260817T0240Z RawVec reserve/grow capacity post-type-invariant reduction, the 20260817T0340Z RawVec reserve-family initialized-prefix/type-invariant reduction, the 20260817T0410Z RawVec shrink initialized-prefix/type-invariant reduction, the 20260817T0455Z Vec reserve-caller initialized-prefix reduction, the 20260817T0613Z RangeBounds normalization retry, Vec pop/pop_if capacity-boundary reduction, Vec tail raw-slice constructor reduction, Vec dedup mutable pointer-add token reduction, the 20260817T1012Z Vec capacity-overflow eight-helper source-panic adjudication, active flattened checked-mul provenance through 20260817T1133Z, package-facing flattened unchecked-mul and len-overflow panic retained-boundary provenance through 20260817T1220Z and 20260817T1241Z, RawVec start-pointer Vec::{as_slice,as_mut_slice,as_mut_ptr,as_ptr} and remaining-consumer production seeds, the raw Slice root, pointer-range, fixed-prefix, tail-consumer, get-disjoint, PartialEq observation, pointer-accessor, fixed-array cast/reference, and unchecked chunk-array evidence through 20260818T1105Z, two-layer checker-vs-semantic classification, UNKNOWN evidence matrix, current live implproof 108/219 direct external-body surface, and delivery package validation state for the isolated Slice/Vec implementation-proof campaign.
---

# Nanvix Rust Std Slice/Vec Incompleteness Baseline

The post-proof incompleteness workspace is
`/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-slice-vec-incompleteness-2026-08-12`.
It is derived from the certified implementation-proof workspace
`/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-slice-vec-implproof-2026-08-12`
and covers only generated contracts, not exact existing-vstd rows.
Its delivery package is `delivery_package/`, with
`delivery_package/package_manifest.json`,
`delivery_package/CROSSWALK.md`, and
`delivery_package/validate_delivery_package.py` preserving the active
inventory/classification/UNKNOWN-matrix artifacts, validator scripts, validation
reports, and active certification provenance.
The active `20260817T1200Z` certification now explicitly binds
`proof_inventory/vec_capacity_overflow_eight_helper_adjudication_20260817T1012Z/summary.json`
as current no-production-change evidence for the retained Vec
capacity-overflow abort helpers and
`proof_inventory/vec_dedup_ptr_add_token_reduction_20260817T1104Z/summary.json`
as the current Vec dedup mutable ptr-add token reduction, plus
`proof_inventory/flattened_checked_mul_expect_reduction_20260817T1133Z/summary.json`
for the flattened checked-multiply normal-return reduction without changing the
generated contracts, checker split, UNKNOWN matrix, or semantic classifications.
Package-facing provenance also binds
`proof_inventory/flattened_unchecked_mul_reduction_20260817T1220Z/summary.json`
and
`proof_inventory/flattened_len_overflow_panic_adjudication_20260817T1241Z/summary.json`
as reviewed no-production-change retained-boundary evidence for the same
flattened Slice/Vec targets. They preserve generated contracts, checker counts,
UNKNOWN rows, and semantic classifications; the later RawVec start-pointer
`Vec::{as_slice,as_mut_slice,as_mut_ptr,as_ptr}` and remaining-consumer
production seeds, raw Slice root/pointer-range/fixed-prefix/tail reductions,
get-disjoint current-consumer refresh, PartialEq observation refresh, and Slice
pointer-accessor reduction leave the live implproof surface at 108/219 without
changing generated incompleteness rows or the 63 UNSAT / 81 UNKNOWN split. The
refreshed package also explicitly requires and finds
`proof_inventory/raw_parts_helper_current_consumer_refresh_20260818T0847Z/summary.json`
and
`proof_inventory/vec_raw_read_current_consumer_refresh_20260818T0900Z/summary.json`,
plus
`proof_inventory/slice_partialeq_observed_current_refresh_20260818T0934Z/summary.json`,
`proof_inventory/get_disjoint_current_consumer_refresh_20260818T0957Z/summary.json`,
`proof_inventory/slice_pointer_accessor_current_reduction_20260818T1005Z/summary.json`,
`proof_inventory/fixed_array_cast_reference_probe_20260818T1048Z/summary.json`, and
`proof_inventory/unchecked_chunk_array_current_reduction_20260818T1105Z/summary.json`
as package-facing current-boundary/reduction provenance; these packets preserve
generated contracts, checker counts, UNKNOWN rows, semantic classifications, and
the current 108/219 direct external-body surface.
The current semantic/report validators report 144 analysis rows, 144
classification rows, 81 UNKNOWN-matrix rows, no stale active-certification
surface references across package files and validator scripts, and no
unsupported, no-target, or semantic-mismatch rows. The package-local saved
validation capture is also current: `validation.stdout` records
`20260817T1200Z`, `validation.stderr` is empty, and `validation.exit_code` is
`0`. After the
`copy_within_bounds_bridge_reduction_20260815T1814Z`,
`vec_resize_extend_with_loop_reduction_20260815T1719Z`,
`vec_from_raw_parts_private_constructor_boundary_reduction_20260815T2011Z`,
`vec_extract_if_constructor_boundary_reduction_20260816T0059Z`,
`sort_select_private_boundary_adjudication_20260815T2100Z`,
`write_copy_maybeuninit_raw_ptr_adjudication_20260816T0324Z`, the
`vec_resize_truncate_shrink_reduction_20260816T0606Z` evidence, the
no-production-change
`align_to_offsets_view_bridge_adjudication_20260816T0717Z` evidence, and
`vec_dedup_partial_eq_bridge_adjudication_20260816T0743Z`, plus the reviewed
active-certification evidence from `vec_append_initialized_prefix_bridge_adjudication_20260816T0811Z`,
`vec_push_mut_len_capacity_invariant_adjudication_20260816T0822Z`,
`vec_spare_capacity_raw_parts_boundary_reduction_20260816T0831Z`,
`split_off_raw_copy_effect_adjudication_20260816T0843Z`,
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
`vec_remove_raw_copy_storage_model_reduction_20260816T1533Z`,
`slice_partialeq_observed_bridge_adjudication_20260816T1550Z`, and the
post-1550 retained-boundary/current-consumer evidence through
`rchunks_unchecked_source_fidelity_20260816T2306Z` and the
`rangebounds_normalization_retry_20260817T0613Z` packet were incorporated
into the active certification artifact, the generated
incompleteness rows and delivery package were regenerated from the active pointer.
The later reviewed
`immutable_split_raw_parts_helper_adjudication_20260816T1712Z`,
`mutable_split_raw_parts_helper_adjudication_20260816T1728Z`,
`vec_raw_read_storage_model_boundary_adjudication_20260816T1823Z`, and
`raw_parts_constructor_boundary_refresh_20260816T1841Z`, and
`vec_reserve_capacity_current_consumers_20260816T1936Z`,
`raw_copy_current_consumers_20260816T1957Z`,
`fixed_array_current_consumers_20260816T2008Z`, and
`iterator_subslice_unknown_current_consumers_20260816T2037Z`, and
`raw_pointer_provenance_unknown_current_consumers_20260816T2053Z`, and
`mutable_reference_view_unknown_current_consumers_20260816T2112Z`,
`callback_trace_unknown_current_consumers_20260816T2123Z`, and
`unstable_sort_selection_unknown_current_consumers_20260816T2133Z`, and
`maybeuninit_storage_current_consumers_20260816T2246Z`, and
`rchunks_unchecked_source_fidelity_20260816T2306Z` results are
accounted for as no-production-change retained-boundary evidence for
`core::slice::{as_chunks,split_at_checked,split_at_unchecked,split_first_chunk}`
and
`core::slice::{as_chunks_mut,split_at_mut_checked,split_at_mut_unchecked,split_first_chunk_mut}`:
plus `alloc::vec::Vec::{pop_if,pop,remove,swap_remove}` raw-read storage-model
bridges, plus `core::slice::{from_raw_parts,from_raw_parts_mut}` raw-parts
constructor boundaries, plus
`alloc::vec::Vec::{extend_from_within,append,extend_from_slice,reserve}`
reserve/capacity current-consumer boundaries, plus
`core::slice::{write_copy_of_slice,copy_from_slice}` and
`alloc::vec::Vec::append` raw-copy current-consumer boundaries, plus 18 Slice
fixed-array prefix/suffix, unchecked chunk-array, and flattened array-cast
current-consumer targets, plus the 24 Slice iterator/subslice UNKNOWN rows now
bound to current array-chunk, mutable iterator, predicate split, and mutable
split/subslice proof consumers, plus the 17 raw-pointer/provenance UNKNOWN rows
bound to current Slice/Vec raw pointer, raw-parts, unchecked-index,
alignment/domain, allocator/start-pointer, and raw-length proof consumers, plus
the 9 mutable-reference-view UNKNOWN rows bound to current Slice mutable
array/chunk, SliceIndex mutable-reference, and Vec mutable-return-reference
proof consumers, plus the 8 Vec callback-trace UNKNOWN rows bound to current
compaction, clone, predicate, and zero-arg callback proof consumers, plus the 6
Slice unstable sort/selection UNKNOWN rows bound to current source-backed
select/sort and Ord/FnMut callback/closure-lowering proof consumers, plus the 5
MaybeUninit storage UNKNOWN rows bound to current source-backed raw-storage,
drop/destructor, raw-cast, initialized-prefix, and raw-parts proof consumers for
`core::slice::{assume_init_drop,assume_init_mut,write_clone_of_slice,write_copy_of_slice}`
and `alloc::vec::Vec::spare_capacity_mut`, plus the rchunks unchecked
source-fidelity repair for `core::slice::{as_rchunks,as_rchunks_mut}`. No
generated contract, checker-count, UNKNOWN-matrix, or catalog-semantics change is
required, so the refreshed package remains anchored to the active `20260817T1200Z`
certification while explicitly recording the RangeBounds normalization retry, split raw-parts, raw-read,
constructor, Vec reserve/capacity and reserve-caller initialized-prefix,
raw-copy, fixed-array, iterator/subslice, raw-pointer, mutable-reference,
callback-trace, and unstable sort/selection retained-boundary states, the 2246Z
MaybeUninit current-consumer state, the 2306Z rchunks source-fidelity repair, and
the 1220Z/1241Z flattened unchecked-mul / len-overflow panic retained-boundary
adjudications.
The active selector is current, the superseded active-certification
marker is absent from current generated/package surfaces, and the
native analysis/classification/UNKNOWN validators are clean: they report 144
analysis rows, 144 classification rows, 81 UNKNOWN-matrix rows, no missing
artifacts, no unsupported/no-target rows, and no semantic spec-mismatch rows.
The delivery-package preserved-artifact manifest has been refreshed after native
regeneration: package validation reports 144 analysis rows, 144 classification
rows, 81 UNKNOWN-matrix rows, 11 preserved artifacts, 7 validator scripts, no
stale active-certification surface references, and no failures. Package
validation also compares embedded active-certification and active-pointer
provenance in the preserved generated/package surfaces against the current
selector and certification artifact.
The package-facing `DELIVERY_INDEX.md`, `delivery_package/CROSSWALK.md`, and
`delivery_package/package_manifest.json` now explicitly name the
`rawvec_shrink_initialized_prefix_reduction_20260817T0410Z` packet, the
`vec_reserve_callers_initialized_prefix_reduction_20260817T0455Z` packet, the
`rangebounds_normalization_retry_20260817T0613Z` packet, the
`rawvec_start_pointer_as_slice_production_seed_20260817T1316Z` packet,
`rawvec_start_pointer_as_mut_slice_production_seed_20260818T0400Z`,
`rawvec_start_pointer_vec_pointer_accessors_20260818T0430Z`,
`rawvec_start_pointer_remaining_consumers_20260818T0512Z`, the raw Slice root,
pointer-range, fixed-prefix, and tail-consumer start-pointer packets, the
`get_disjoint_current_consumer_refresh_20260818T0957Z` packet, and the
`slice_pointer_accessor_current_reduction_20260818T1005Z` packet with the
current 108/219 direct external-body surface. This preserves the 144-row
analysis set, the 63 UNSAT / 81 UNKNOWN checker split, and the empty
unsupported/no-target/semantic-mismatch surfaces. `baseline_report.md` and
`semantic_omissions_report.md` include the full
`proof_inventory/rawvec_reserve_exact_try_reserve_invariant_reduction_20260817T0340Z/summary.json`
relpath.
The package-facing provenance now also names
`proof_inventory/vec_capacity_overflow_eight_helper_adjudication_20260817T1012Z/summary.json`
and
`proof_inventory/vec_dedup_ptr_add_token_reduction_20260817T1104Z/summary.json`,
`proof_inventory/flattened_checked_mul_expect_reduction_20260817T1133Z/summary.json`,
`proof_inventory/flattened_unchecked_mul_reduction_20260817T1220Z/summary.json`,
and
`proof_inventory/flattened_len_overflow_panic_adjudication_20260817T1241Z/summary.json`
plus the current-boundary
`proof_inventory/slice_partialeq_observed_current_refresh_20260818T0934Z/summary.json`,
`proof_inventory/get_disjoint_current_consumer_refresh_20260818T0957Z/summary.json`,
`proof_inventory/slice_pointer_accessor_current_reduction_20260818T1005Z/summary.json`,
`proof_inventory/fixed_array_cast_reference_probe_20260818T1048Z/summary.json`, and
`proof_inventory/unchecked_chunk_array_current_reduction_20260818T1105Z/summary.json`
without changing generated contracts, checker classifications, or UNKNOWN
evidence rows.
The live native rerun and package validator captures are the current
package-admission evidence. The root-level `delivery_package_validation.latest.*`
and package-local `delivery_package/validation.*` captures record the active
certification id, active pointer relpath, 144 analysis/classification rows, 81
UNKNOWN rows, the required 0934 PartialEq, 0957 get-disjoint, 1005
pointer-accessor, 1048 fixed-array cast/reference, and 1105 unchecked
chunk-array evidence refs, no stale surface
references, no failures, empty stderr, and exit code `0`.

The superseded `20260817T0016Z`, `20260817T0512Z`, and `20260817T0613Z`
incompleteness provenance is preserved as historical evidence; the active
`20260817T1200Z` refresh points generated analysis/classification/UNKNOWN/package
surfaces at the post-0613 aggregate certification while preserving the 144-row /
81-UNKNOWN baseline and empty failure surfaces.

The generated-contract analysis inventory is `analysis_inventory.{csv,json}`.
It contains 144 rows: 120 `core::slice` generated contracts and 24
`alloc::vec` generated contracts. The row set is selected from
`proof_inventory/targets_180.csv` by
`catalog_status == generated-new-real-relation-spec`; the legacy
`targets_144.*` filenames in the implementation-proof workspace mirror the full
180-row live scope and are not the generated-row authority.

The current proof-disposition split for generated rows is B=144 with no C rows.
The prior ten mutable-iterator spec-mismatch rows were repaired by removing only
the unsound `final(slice)@ == old(slice)@` frame clause from their generated
contracts and target-local proof harness obligations.

The determinism baseline preserves checker-inconclusive UNKNOWN outcomes without
classifying them as semantic incompleteness. The checked generated
incompleteness artifacts consume the
`all-20260815T0127Z-ascii-whitespace-vtab-repair` Slice feedback run and record
120 `ok` determinism rows, with 58 `r0_z3=unsat` and 62 `r0_z3=unknown`. The
Slice inventory rows use the current production executable contract text, so
`as_chunks`, `as_rchunks`, `as_chunks_unchecked`, `as_chunks_mut`,
`as_rchunks_mut`, and `as_chunks_unchecked_mut` carry the explicit
`array_value_view` source/final per-chunk and remainder subrange facts from that
refresh.
The Vec checker layer consumes the active
`all-20260813T1305Z-as-mut-slice-parser` feedback manifest and records 24 `ok`
rows, with 5 `r0_z3=unsat` and 19 `r0_z3=unknown`. The earlier Slice
select-nth-result-shape inventory pointer and the earlier 19-ok / 5-unsupported
and 23-ok / 1-unsupported Vec splits are historical only and have been replaced
in the generated analysis artifacts.
The generated-row analysis inventory, classification, and UNKNOWN matrix also
consume the active implementation-proof row-level 0202 Vec panic-cleanup evidence
for `alloc::vec::Vec::{dedup_by,retain_mut}`:
`proof_inventory/vec_panic_guard_cleanup_boundary_reduction_20260815T0202Z/`.
Those two rows now take their proof status and Verus stdout paths from the
current dependency manifests instead of the older
`vec_scalar_length_helper_reduction_20260814T0847Z` fallback evidence.

The two-layer classification artifacts are
`incompleteness_classification.{csv,json}`, `semantic_omissions_report.md`, and
`classification_validation_report.json`. The checker-layer split is `unsat=63`,
`unknown=81`, and `unsupported_mut_ref_return=0`. All 81 UNKNOWN rows carry a
non-empty `unknown_reason_class`. The semantic-gap split is
`no_row_specific_semantic_omission=144`, with an empty semantic mismatch target
set. There are no checker-unsupported mutable-reference-return rows in the active
baseline.

The current generated-row baseline is selected by the active implementation
proof pointer `proof_inventory/active_aggregate_certification.json`, which
selects `proof_inventory/final_aggregate_certification_20260817T1200Z.json`.
That active artifact now includes
`copy_within_bounds_bridge_reduction_20260815T1814Z`,
`vec_resize_extend_with_loop_reduction_20260815T1719Z`,
`vec_from_raw_parts_private_constructor_boundary_reduction_20260815T2011Z`,
and `vec_extract_if_constructor_boundary_reduction_20260816T0059Z`,
plus `sort_select_private_boundary_adjudication_20260815T2100Z` and
`write_copy_maybeuninit_raw_ptr_adjudication_20260816T0324Z`, plus
`vec_resize_truncate_shrink_reduction_20260816T0606Z`,
`align_to_offsets_view_bridge_adjudication_20260816T0717Z`, and
`vec_dedup_partial_eq_bridge_adjudication_20260816T0743Z`, followed by
`vec_append_initialized_prefix_bridge_adjudication_20260816T0811Z`,
`vec_push_mut_len_capacity_invariant_adjudication_20260816T0822Z`,
`vec_spare_capacity_raw_parts_boundary_reduction_20260816T0831Z`,
`split_off_raw_copy_effect_adjudication_20260816T0843Z`,
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
`vec_remove_raw_copy_storage_model_reduction_20260816T1533Z`,
`slice_partialeq_observed_bridge_adjudication_20260816T1550Z`,
post-1550 retained-boundary/current-consumer evidence through
`rchunks_unchecked_source_fidelity_20260816T2306Z`,
the RawVec reserve/shrink and Vec reserve-caller initialized-prefix reductions
through `vec_reserve_callers_initialized_prefix_reduction_20260817T0455Z`, and
`rangebounds_normalization_retry_20260817T0613Z`.
The analysis inventory, classification, semantic report, UNKNOWN evidence
matrix, and their validation reports record this active certification
provenance rather than the superseded 20260815T0824Z, 20260815T0501Z, 20260815T0320Z, 20260815T0127Z,
20260814T2238Z, 20260814T2114Z, 20260814T2043Z, 20260814T1548Z,
20260814T1517Z, and 20260814T1436Z
certifications. The active
certification preserves the 144 generated rows after the reviewed PartialEq
bridge adjudication, Vec length-observation reduction, raw slice start-pointer
cast adjudication,
`rotate_ptr_rotate_final_frame_adjudication_20260814T0750Z`,
`rangebounds_resolution_boundary_reduction_20260814T0903Z`, immutable/mutable
exact-chunk remainder reviews, `trim_ascii` choose-index uniqueness,
`is_sorted` adjacent-pair proof lemmas, `core::slice::reverse`
split-reborrow verification, and `core::slice::binary_search_by`
loop-result reduction, the `Vec::truncate` length/drop proof-helper
reduction, `vec_len_capacity_invariant_reduction_20260814T1334Z`,
`slice_len_ptr_metadata_boundary_reduction_20260814T1345Z`, and
`eq_ignore_ascii_case_helper_boundary_reduction_20260814T1406Z`,
`eq_ignore_ascii_case_chunk_helper_reduction_20260814T1517Z`, the ASCII u8
range-pattern reduction, and
`vec_len_intrinsics_assume_boundary_reduction_20260814T1548Z`,
`vec_set_len_helper_reduction_20260814T1619Z`,
`pointer_add_helper_reduction_20260814T1659Z`,
`get_disjoint_maybeuninit_scaffold_reduction_20260814T1734Z`,
`pointer_address_helper_boundary_reduction_20260814T1749Z`,
`source_pure_constructor_boundary_reduction_20260814T1826Z`,
`raw_copy_helper_boundary_reduction_20260814T1844Z`,
`slice_iterator_constructor_boundary_reduction_20260814T1906Z`, and
`is_sorted_slice_range_suffix_reduction_20260814T1925Z`, plus
`unchecked_sub_boundary_reduction_20260814T2016Z`, the reviewed
no-production-change `singleton_array_boundary_reduction_20260814T2032Z`, and
`unreachable_panic_boundary_reduction_20260814T2043Z`, the
`slicecontains_default_partialeq_reduction_20260814T2114Z`, and
`rawvec_ptr_boundary_reduction_20260814T2238Z`, plus
`reverse_revswap_loop_result_reduction_20260814T2302Z`,
`prefix_suffix_scan_reduction_20260814T2334Z`,
`split_unchecked_helper_reduction_20260815T0026Z`, and
`vec_panic_guard_cleanup_boundary_reduction_20260815T0202Z`, plus the reviewed
`split_off_allocator_constructor_boundary_reduction_20260815T0426Z`,
`core::slice::is_sorted` Windows traversal reduction, and
`partition_point_result_bridge_reduction_20260815T0501Z`, plus the reviewed
post-0501 `copy_from_slice_len_mismatch_reduction_20260815T0730Z`,
`copy_within_dest_assert_reduction_20260815T0800Z`,
`swap_remove_unreachable_assert_reduction_20260815T0812Z`, and
`vec_from_raw_parts_private_constructor_boundary_reduction_20260815T2011Z`,
while selecting the
post-`is_sorted` adjacent-pair Slice feedback refresh and keeping the active
aggregate at `B=180`, `pending=0`, and `exact-vstd=36`.

The reviewed `split_unchecked_helper_reduction_20260815T0026Z` evidence is now
part of the active certification snapshot, so the generated-row incompleteness
baseline consumes the promoted split-helper proof state directly.
The reviewed `split_off_allocator_constructor_boundary_reduction_20260815T0426Z`
evidence is also part of the active certification snapshot; it removes the
target-local `Vec::allocator` and `Vec::with_capacity_in` external-body helpers
from `alloc::vec::Vec::split_off` while retaining the generic `Clone`,
len-capacity, raw-pointer/provenance, and tail-copy boundaries.

The reviewed `partition_point_result_bridge_reduction_20260815T0501Z` evidence
is also part of the active certification snapshot; it removes the proof-only
`rust_1_96_partition_point_result_bridge` external body from
`core::slice::partition_point` by proving the Ok/Err bridge over the existing
partition-point result predicates while retaining the reviewed binary-search
dependency and FnMut predicate observation boundaries.

The iterator/subslice state representative no-change evidence covers
`core::slice::{as_chunks,as_chunks_mut,as_chunks_unchecked,as_chunks_unchecked_mut,as_rchunks,as_rchunks_mut,chunk_by_mut,chunks_mut,chunks_exact_mut,rchunks,rchunks_mut,rchunks_exact_mut,utf8_chunks}`.
The focused Slice run
`verification/evidence/slice_feedback_determinism/chunk-window-subview-nochange-20260813T1532Z`
records 13/13 `status=ok` and 13/13 `r0_z3=unknown` with
`unknown_reason_class=iterator-or-subslice-state-boundary`; this is reviewed
no-change evidence for that representative family, not an UNKNOWN-to-UNSAT
improvement.

The immutable iterator/window/split representatives
`core::slice::{array_windows,chunk_by,chunks,chunks_exact,rchunks_exact,rsplitn,split,split_inclusive,splitn,windows}`
also remain checker-layer `unknown` with
`unknown_reason_class=iterator-or-subslice-state-boundary`. The focused Slice run
`verification/evidence/slice_feedback_determinism/immutable-iterator-window-nochange-20260813T1644Z`
records all 10 rows at real `status=ok` / `r0_z3=unknown`, with complete
candidate, synthetic-exec, determinism harness, Verus stdout/stderr,
SMT/schema-search, and result artifacts and no legacy no-target marker; this is
no-change evidence for the iterator/subslice boundary, not an UNKNOWN-to-UNSAT
improvement.

After that baseline, a focused iterator-empty-state repair smoke
`verification/evidence/slice_feedback_determinism/iterator-empty-state-smoke-20260813T2315Z`
showed `core::slice::{array_windows,chunks,chunks_exact,windows}` at real
`status=ok` / `r0_z3=unsat` with complete feedback-pipeline artifacts. The
subsequent all-target refresh
`verification/evidence/slice_feedback_determinism/all-20260813T2324Z-iterator-empty-state-refresh`
first promoted this result into the active incompleteness baseline and UNKNOWN
matrix. A later reverse-chunk exact-empty repair
`verification/evidence/slice_feedback_determinism/all-20260813T2355Z-reverse-chunk-empty-state-refresh`
promotes `core::slice::{rchunks,rchunks_exact}` to real `status=ok` /
`r0_z3=unsat`, while preserving `core::slice::{rchunks_mut,rchunks_exact_mut}`
as real `status=ok` / `r0_z3=unknown` iterator/subslice-state boundaries.
After that active baseline, a focused no-update exact-empty smoke
`verification/evidence/slice_feedback_determinism/focused-exact-empty-20260814T0021Z`
showed `core::slice::{split,chunk_by,utf8_chunks}` at real `status=ok` /
`r0_z3=unsat` and `core::slice::{chunks_mut,chunks_exact_mut}` at real
`status=ok` / `r0_z3=unknown` with complete feedback-pipeline artifacts and no
legacy no-target marker. The later full 120-target artifact-updating Slice
refresh
`verification/evidence/slice_feedback_determinism/all-20260814T0030Z-exact-empty-artifact-refresh`
promotes those focused results into the active incompleteness checker counts.
The subsequent fixed-array chunk length refresh
`verification/evidence/slice_feedback_determinism/all-20260814T0126Z-array-chunk-length-refresh`
updated Slice specgen artifacts with explicit quotient/remainder length facts
for the `as_chunks`/`as_rchunks` family. The later elementwise refresh
`verification/evidence/slice_feedback_determinism/all-20260814T0147Z-array-chunk-elementwise-refresh`
first added explicit immutable per-chunk source subrange facts for `as_chunks`,
`as_rchunks`, and `as_chunks_unchecked`. The later
`verification/evidence/slice_feedback_determinism/all-20260814T0235Z-post-sync-exec-decl-refresh`
run preserves those facts in the production executable declarations, preserves
the mutable counterpart UNKNOWN rows, and keeps the same 120 `ok`, 58 `unsat`,
and 62 `unknown` determinism counts. The later
`verification/evidence/slice_feedback_determinism/all-20260814T0343Z-mut-array-final-subranges-refresh`
run adds the analogous mutable initial/final chunk and remainder subrange facts
for `as_chunks_mut`, `as_rchunks_mut`, and `as_chunks_unchecked_mut` while
preserving those rows as real `status=ok` / `r0_z3=unknown`. The current
`verification/evidence/slice_feedback_determinism/all-20260815T0127Z-ascii-whitespace-vtab-repair`
run preserves those facts, repairs `core::slice::is_sorted` to adjacent-pair
PartialOrd semantics, and is the recorded Slice input for the generated
incompleteness inventory, classification, and UNKNOWN evidence matrix.

The mutable split/split-off iterator representatives
`core::slice::{rsplit,rsplit_mut,rsplitn_mut,split_at_mut_checked,split_at_mut_unchecked,split_first_mut,split_inclusive_mut,split_last_mut,split_mut,split_off,split_off_first_mut,split_off_last_mut,split_off_mut,splitn_mut}`
also remain checker-layer `unknown` with
`unknown_reason_class=iterator-or-subslice-state-boundary`. Fresh focused
feedback artifacts under
`verification/evidence/slice_feedback_determinism/mut-split-off-iterator-nochange-20260813T1635Z`
show all 14 rows reached real `status=ok` / `r0_z3=unknown` with complete
candidate, synthetic-exec, determinism harness, Verus stdout/stderr,
SMT/schema-search, and result artifacts and no legacy no-target marker; this is
no-change evidence for the iterator/subslice boundary, not an
UNKNOWN-to-UNSAT improvement.

The MaybeUninit/raw-storage no-change representatives
`core::slice::{assume_init_drop,assume_init_mut,write_clone_of_slice,write_copy_of_slice}`
and `alloc::vec::Vec::spare_capacity_mut` remain checker-layer `unknown` with
non-empty `unknown_reason_class=maybeuninit-storage-boundary` and
`semantic_gap_outcome=no_row_specific_semantic_omission`. Fresh focused feedback
artifacts under the Slice
`verification/evidence/slice_feedback_determinism/maybeuninit-storage-nochange-20260813T1605Z`
and Vec
`verification/evidence/vec_feedback_determinism/maybeuninit-storage-nochange-20260813T1605Z`
runs show all five rows reached real `status=ok` / `r0_z3=unknown` with complete
synthetic-exec determinism artifacts and no legacy no-target marker; the active
Slice and Vec baseline counts are now 58 UNSAT / 62 UNKNOWN
and 5 UNSAT / 19 UNKNOWN, respectively.

The Slice mutable-reference/disjoint-aliasing/Clone-effect representatives
`core::slice::{as_flattened_mut,get_mut,get_disjoint_mut,get_disjoint_unchecked_mut,clone_from_slice,fill}`
remain checker-layer `unknown` with non-empty reason classes split across
`mutable-reference-view-boundary`, `disjoint-mutable-alias-boundary`, and
`clone-or-callback-effect-boundary`. Fresh focused feedback artifacts under
`verification/evidence/slice_feedback_determinism/mut-disjoint-clone-nochange-20260813T1615Z`
show all six rows reached real `status=ok` / `r0_z3=unknown` with complete
synthetic-exec determinism artifacts and no legacy no-target marker; this is
reviewed focused no-change evidence, not an
UNKNOWN-to-UNSAT improvement. The active Slice baseline counts are now 58 UNSAT /
62 UNKNOWN.

The Option-wrapped mutable fixed-array return representatives
`core::slice::{as_mut_array,first_chunk_mut,last_chunk_mut,split_first_chunk_mut,split_last_chunk_mut}`
also remain checker-layer `unknown` with complete focused feedback evidence under
`verification/evidence/slice_feedback_determinism/reviewer-option-mut-array-smoke-20260813T151120Z`.
All five rows reached real `status=ok` / `r0_z3=unknown` with complete
candidate/synthetic/determinism/Verus/SMT/schema-search/result artifacts and no
legacy no-target marker; UNKNOWN is preserved because the
contracts fix modeled Seq views and old/final slice frame, but not runtime
mutable-reference identity or alias/lifetime state.

The Vec mutable-return representatives
`alloc::vec::Vec::{insert_mut,push_mut}` remain checker-layer `unknown` with
`unknown_reason_class=mutable-reference-view-boundary` and
`semantic_gap_outcome=no_row_specific_semantic_omission`. The active Vec
feedback refresh
`verification/evidence/vec_feedback_determinism/all-20260813T1305Z-as-mut-slice-parser`
records both rows at real `status=ok` / `r0_z3=unknown`, with complete
candidate, synthetic-exec, determinism harness, Verus stdout/stderr,
SMT/schema-search, and result artifacts; `push_mut` also has reviewer smoke
evidence under `reviewer-push-mut-smoke-20260813T124132Z`.

The raw-pointer/provenance no-change review representatives
`core::slice::{align_to,as_ptr_range,from_raw_parts_mut,get_unchecked_mut,subslice_range}`
and `alloc::vec::Vec::{as_ptr,as_mut_ptr,from_raw_parts,set_len}` remain
checker-layer `unknown` with non-empty
`unknown_reason_class=raw-pointer-provenance-boundary` and
`semantic_gap_outcome=no_row_specific_semantic_omission`. Fresh representative
feedback artifacts under the Slice `raw-provenance-nochange-smoke-20260813T1415Z`
and Vec `raw-provenance-nochange-smoke-20260813T1405Z` runs support this as a
reviewed no-change classification, not an UNKNOWN-to-UNSAT improvement.
The remaining Slice raw-pointer/provenance representatives
`core::slice::{align_to_mut,as_mut_ptr,as_mut_ptr_range,as_ptr,element_offset,from_mut,from_raw_parts,get_unchecked}`
are covered by the focused Slice run
`verification/evidence/slice_feedback_determinism/raw-provenance-remaining-nochange-20260813T1654Z`.
It records all eight rows at real `status=ok` / `r0_z3=unknown`, with complete
candidate, synthetic-exec, determinism harness, Verus stdout/stderr,
SMT/schema-search, and result artifacts, no legacy no-target marker, and the same
`raw-pointer-provenance-boundary` reason class.

The Slice search/sort representatives
`core::slice::{binary_search,binary_search_by,binary_search_by_key,partition_point,select_nth_unstable,select_nth_unstable_by,select_nth_unstable_by_key,sort_unstable,sort_unstable_by,sort_unstable_by_key}`
remain checker-layer `unknown` with non-empty
`unknown_reason_class` values split as
`duplicate-or-callback-search-boundary=4` and
`unstable-sort-or-selection-boundary=6`. Fresh focused feedback artifacts under
`verification/evidence/slice_feedback_determinism/search-sort-nochange-20260813T1550Z`
show all 10 rows reached real `status=ok` / `r0_z3=unknown` with complete
synthetic-exec determinism artifacts and no legacy no-target marker; the active
Slice baseline counts are now 58 UNSAT / 62 UNKNOWN.

`core::slice::is_sorted` is repaired as a source-fidelity issue, not an
UNKNOWN/no-target issue. The active `slice_sorted_by_partial_ord` helper now
quantifies only adjacent pairs (`i` and `i + 1`) and is vacuous for empty and
singleton slices, matching the frozen Rust 1.96 source's `windows(2).all(...)`,
chunk `windows(2).fold(...)`, overlapping chunk boundary, and final suffix
`windows(2).all(...)` flow. The focused feedback-pipeline result for
`core::slice::is_sorted` records real `status=ok` / `r0_z3=unsat`, the active
Slice refresh `all-20260815T0127Z-ascii-whitespace-vtab-repair` keeps all 120
generated Slice targets at `status=ok` with 58 UNSAT and 62 UNKNOWN rows, and
the incompleteness row is checker-layer UNSAT with
`semantic_gap_outcome=no_row_specific_semantic_omission`.

The Vec dedup callback representatives
`alloc::vec::Vec::{dedup,dedup_by,dedup_by_key}` likewise remain checker-layer
`unknown` with non-empty `unknown_reason_class=callback-trace-boundary` and no
row-specific semantic omission. Fresh focused feedback artifacts under
`verification/evidence/vec_feedback_determinism/dedup-callback-nochange-20260813T1519Z`
show all three rows reached real `status=ok` / `r0_z3=unknown` with complete
synthetic-exec determinism artifacts and no legacy no-target marker; the active
24-row Vec baseline counts remain 5 UNSAT / 19 UNKNOWN. The
`alloc::vec::Vec::dedup_by` generated-row proof provenance now points at the
0202 cleanup-wrapper Verus evidence and the dependency-manifest proof status.

The remaining Vec callback/Clone representatives
`alloc::vec::Vec::{extend_from_within,pop_if,resize_with}` also remain
checker-layer `unknown` with non-empty
`unknown_reason_class=callback-trace-boundary` and no row-specific semantic
omission. Fresh focused feedback artifacts under
`verification/evidence/vec_feedback_determinism/remaining-callback-clone-nochange-20260813T1540Z`
show all three rows reached real `status=ok` / `r0_z3=unknown` with complete
synthetic-exec determinism artifacts and no legacy no-target marker; the active
24-row Vec baseline counts remain 5 UNSAT / 19 UNKNOWN.

The remaining Vec retain callback representatives
`alloc::vec::Vec::{retain,retain_mut}` also remain checker-layer `unknown` with
non-empty `unknown_reason_class=callback-trace-boundary` and no row-specific
semantic omission. Fresh focused feedback artifacts under the reviewed
retain/retain_mut no-change round show both rows reached real `status=ok` /
`r0_z3=unknown` with complete synthetic-exec determinism artifacts and no legacy
no-target marker. The `alloc::vec::Vec::retain_mut` generated-row proof
provenance now points at the 0202 cleanup-wrapper Verus evidence and the
dependency-manifest proof status.

The Vec iterator-adaptor and boxed-conversion representatives
`alloc::vec::IntoIter::as_mut_slice` and
`alloc::vec::Vec::{drain,extract_if,into_boxed_slice}` remain checker-layer
`unknown` with non-empty reason classes split across
`iterator-adaptor-state-boundary` and `conversion-allocation-boundary`, with no
row-specific semantic omission. The earlier active Vec determinism refresh
`all-20260813T1305Z-as-mut-slice-parser` gives `IntoIter::as_mut_slice` a real
feedback-pipeline result instead of an unsupported mutable-reference-return row.
Fresh focused feedback artifacts under
`verification/evidence/vec_feedback_determinism/adaptor-boxed-nochange-20260813T1624Z`
show all three rows reached real `status=ok` / `r0_z3=unknown` with complete
synthetic-exec determinism artifacts and no legacy no-target marker; the active
24-row Vec baseline counts remain 5 UNSAT / 19 UNKNOWN.

The task-native tooling is:

```sh
python3 -m py_compile tools/build_analysis_inventory.py tools/validate_analysis_inventory.py tools/classify_incompleteness.py tools/validate_incompleteness_classification.py tools/build_unknown_evidence_matrix.py tools/validate_unknown_evidence_matrix.py
python3 tools/build_analysis_inventory.py
python3 tools/validate_analysis_inventory.py
python3 tools/classify_incompleteness.py
python3 tools/validate_incompleteness_classification.py
python3 tools/build_unknown_evidence_matrix.py
python3 tools/validate_unknown_evidence_matrix.py
```

The validator reports missing artifact entries explicitly. In the current
baseline, every row links to existing implementation-proof evidence, proof
harness, proof manifest, source-body manifest, determinism result, synthetic
specification, and determinism harness paths; missing artifact count is zero.
The row-level UNKNOWN evidence matrix artifacts are
`unknown_evidence_matrix.{csv,json}` and
`unknown_evidence_matrix_validation_report.json`. The active matrix contains all
81 checker-layer UNKNOWN rows (`slice=62`, `vec=19`), links each row to
candidate, synthetic spec, determinism spec/harness, Verus stdout/stderr, SMT
and schema-search evidence, result JSON, proof evidence, and semantic
no-omission classification, and rejects missing artifacts, legacy no-target
markers, unsupported rows, semantic mismatches, and non-`add_spec` /
non-`assume_specification` candidates.

The refreshed incompleteness baseline now consumes active certification
`20260817T1200Z` at
`proof_inventory/final_aggregate_certification_20260817T1200Z.json`; it
preserves 144 analysis/classification rows, 81 UNKNOWN rows, no
unsupported/no-target/semantic-mismatch rows, and live package validation
`failures=[]` while incorporating the post-1059 evidence through
`vec_compaction_storage_drop_bridge_probe_20260816T1426Z`,
`vec_push_insert_raw_write_token_reduction_20260816T1506Z`,
`vec_remove_raw_copy_storage_model_reduction_20260816T1533Z`,
`slice_partialeq_observed_bridge_adjudication_20260816T1550Z`, the post-1550
retained-boundary/current-consumer evidence,
`rchunks_unchecked_source_fidelity_20260816T2306Z`,
`vec_len_capacity_type_invariant_production_20260817T0103Z`,
`rawvec_reserve_grow_capacity_post_type_invariant_20260817T0240Z`,
`rawvec_reserve_exact_try_reserve_invariant_reduction_20260817T0340Z`,
`rawvec_shrink_initialized_prefix_reduction_20260817T0410Z`, and
`vec_reserve_callers_initialized_prefix_reduction_20260817T0455Z`, plus
`rangebounds_normalization_retry_20260817T0613Z`, while the active certification
also binds
`proof_inventory/flattened_checked_mul_expect_reduction_20260817T1133Z/summary.json`
without changing generated contracts or catalog semantics.

The active `20260817T1200Z` certification binds the post-1059 retained-boundary
evidence through `vec_compaction_storage_drop_bridge_probe_20260816T1426Z`, the
Vec push/insert raw-write token reduction, the Vec remove raw-copy storage-model
reduction, the Slice PartialEq observed-bridge adjudication, the post-1550
retained-boundary/current-consumer evidence, the rchunks unchecked
source-fidelity repair, the 20260817T0103Z Vec len/capacity production
reduction, the 20260817T0240Z RawVec reserve/grow capacity post-type-invariant
reduction,
`proof_inventory/rawvec_reserve_exact_try_reserve_invariant_reduction_20260817T0340Z/summary.json`,
`proof_inventory/rawvec_shrink_initialized_prefix_reduction_20260817T0410Z/summary.json`,
and
`proof_inventory/vec_reserve_callers_initialized_prefix_reduction_20260817T0455Z/summary.json`,
`proof_inventory/rangebounds_normalization_retry_20260817T0613Z/summary.json`, and
`proof_inventory/vec_pop_capacity_invariant_reduction_20260817T0823Z/summary.json`
while preserving B=180, pending=0, exact-vstd=36, generated rows=144, checker
split 63 UNSAT / 81 UNKNOWN, and the then-current direct external-body surface
110/249 before the later raw Slice root, pointer-range, fixed-prefix, and
tail-consumer reductions moved the then-current surface to 108/224 and the later
Slice pointer-accessor reduction moved the live implproof surface to 108/219.
The active certification also binds
`proof_inventory/flattened_checked_mul_expect_reduction_20260817T1133Z/summary.json`
as provenance for the flattened checked-mul normal-return reduction.
