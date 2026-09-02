---
title: Nanvix Rust Std Vec Module Evidence
description: Measured evidence for the isolated Rust 1.96 alloc::vec module experiment, including source provenance, frozen inventory counts, exact vstd subtraction, generated/no-spec coverage, helper audit, and feedback-determinism outcomes.
---

# Nanvix Rust Std Vec Module Evidence

The isolated `alloc::vec` module-first workspace is
`/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-vec-specgen-2026-08-11`.
It is separate from the canonical Rust 1.96 checkout, the Verus/vstd checkout,
the canonical 2,121-target tree, and the completed slice workspace.

The frozen source/provenance set is recorded in
`provenance/source_manifest.{csv,json}`. It contains 24 copied input files: the
complete 16-file Rust 1.96 `library/alloc/src/vec/**` copy, directly required
adjacent alloc sources for `RawVec`, allocator traits/global allocation,
`TryReserveError`, and boxed-slice conversions, the vstd
`std_specs/{vec,capacity}.rs` baselines, and local frozen copies of
`results/{modules,coverage}.csv`.

The source-wide executable API inventory is frozen in
`inventory/vec_exec_fn_inventory.{csv,json}`. The local `results/modules.csv`
authority reports 49 stable unique `alloc::vec` executable APIs, 24 covered
stable unique APIs, 25 uncovered stable unique APIs, and 28 unstable
declarations excluded by the stable-counting rule. The exact existing-vstd
subtraction in `inventory/vec_existing_vstd_exact_match_audit.{csv,json}`
matches each of the 24 coverage-covered stable rows to a copied vstd
`assume_specification` target binding in
`vstd-baseline/std_specs/{vec,capacity}.rs`, including receiver/reference
mutability, parameter, return, and generic-bound shape checks.

The final `catalog/vec_spec_catalog.{csv,json}` disposition accounts for all 49
stable rows: 24 exact existing-vstd rows, 24 generated executable
`pub assume_specification` rows in `specs/generated_vec_specs.rs`, and one
target-specific justified-no-spec row for `alloc::vec::Vec::splice` in
`catalog/vec_justified_no_spec_records.{csv,json}`. `Vec::splice` remains a
no-spec record because the exact stable signature returns
`Splice<'_, I::IntoIter, A>` for `I: IntoIterator<Item = T>`, and the local
Verus model cannot typecheck that associated-type return without narrowing the
source API.

The shared Vec vocabulary lives in `specs/vec_shared_vocabulary.rs`. Its target
coverage spans logical sequence, length/capacity, allocation and allocator
state, ownership/mutation frames, raw-parts and pointer/provenance boundaries,
spare `MaybeUninit` storage, Drain/Splice/IntoIter/ExtractIf state,
callback-trace mutation, and slice/boxed-slice conversions.
`verification/shared_helper_target_usage_audit.{csv,json}` records 49
target-usage rows and classifies reachable helpers as source-backed,
law-constrained, or irreducible-boundary abstractions. The transitive helper
audit is closed: `array_value_view` is classified and attributed through
`flatten_array_vec` for `Vec::into_flattened`; `vec_range_start` and
`vec_range_end` are attributed through `vec_range_bounds_valid` for range-using
targets including `drain`, `extend_from_within`, `extract_if`, and the
`splice` no-spec row; and the harness-only raw-parts feedback helper
`vec_raw_parts_storage_ptr` is classified as an irreducible-boundary abstraction
and recorded in `Vec::from_raw_parts` reachable/audited usage.

The generated declaration harness is
`verification/harnesses/vec_all_contracts_batch.rs`; exact-vstd rows are not
redeclared in that harness because vstd already provides them. The Verus
no-verify command
`/usr/bin/timeout 110s /home/chentianyu/nanvix-rust-std-spec-survey/verus/source/target-verus/release/verus verification/harnesses/vec_all_contracts_batch.rs --no-verify`
typechecks the 24 generated declarations.

The active feedback-determinism evidence is
`verification/evidence/vec_feedback_determinism/latest_manifest.json`, currently
pointing at
`verification/evidence/vec_feedback_determinism/all-20260813T1305Z-as-mut-slice-parser/run_manifest.json`.
It contains 24 generated targets with 24 `ok` outcomes. The recorded `r0_z3`
split is 5 UNSAT and 19 UNKNOWN; `alloc::vec::IntoIter::as_mut_slice` now has a
real feedback-pipeline result with `r0_z3=unknown` rather than an unsupported
mutable-reference-return row. The mutable-reference-return adapter now produces
real feedback-pipeline determinism results for `alloc::vec::IntoIter::as_mut_slice`,
`alloc::vec::Vec::push_mut`,
`alloc::vec::Vec::insert_mut`, `alloc::vec::Vec::leak`, and
`alloc::vec::Vec::spare_capacity_mut`; UNKNOWN outcomes are explicitly
classified as callback-trace, conversion/allocation, iterator/adaptor-state,
mutable-reference-view, MaybeUninit-storage, or raw-pointer/provenance
boundaries rather than strengthened away.

A bounded raw/provenance no-change review smoke under
`verification/evidence/vec_feedback_determinism/raw-provenance-nochange-smoke-20260813T1405Z`
covered `Vec::as_ptr`, `Vec::as_mut_ptr`, `Vec::from_raw_parts`, and
`Vec::set_len`; all four reached `status=ok` with real `r0_z3=unknown`,
complete synthetic/determinism/Verus/SMT/schema-search artifacts, no legacy
`0 exec ensures targets` marker, and
`unknown_reason_class=raw-pointer-provenance-boundary`.

A bounded MaybeUninit spare-storage no-change round under
`verification/evidence/vec_feedback_determinism/maybeuninit-storage-nochange-20260813T1605Z`
covered `Vec::spare_capacity_mut`; it reached `status=ok` with real
`r0_z3=unknown`, complete candidate/synthetic/determinism/Verus/SMT
schema-search artifacts, no legacy `0 exec ensures targets` marker, and
`unknown_reason_class=maybeuninit-storage-boundary`. The production 24-row
feedback manifest was not refreshed because no source-backed UNSAT strengthening
was sound without erasing spare `MaybeUninit` storage semantics.

A bounded callback-trace no-change round under
`verification/evidence/vec_feedback_determinism/retain-callback-nochange-20260813T1453Z`
covered `Vec::retain` and `Vec::retain_mut`; both reached `status=ok` with
real `r0_z3=unknown`, complete candidate/synthetic/determinism/Verus/SMT
schema-search artifacts, no legacy `0 exec ensures targets` marker, and
`unknown_reason_class=callback-trace-boundary`. This preserves the generated
FnMut trace relations instead of strengthening either contract to a unique
output sequence.

A later bounded callback-trace no-change round under
`verification/evidence/vec_feedback_determinism/dedup-callback-nochange-20260813T1519Z`
covered `Vec::dedup`, `Vec::dedup_by`, and `Vec::dedup_by_key`; all three
reached `status=ok` with real `r0_z3=unknown`, complete
candidate/synthetic/determinism/Verus/SMT schema-search artifacts, no legacy
`0 exec ensures targets` marker, and
`unknown_reason_class=callback-trace-boundary`. The production 24-row feedback
manifest was not refreshed because no source-backed UNSAT strengthening was
sound without erasing PartialEq/FnMut ordered callback-trace semantics.

A further bounded callback/Clone no-change round under
`verification/evidence/vec_feedback_determinism/remaining-callback-clone-nochange-20260813T1540Z`
covered `Vec::extend_from_within`, `Vec::pop_if`, and `Vec::resize_with`; all
three reached `status=ok` with real `r0_z3=unknown`, complete
candidate/synthetic/determinism/Verus/SMT schema-search artifacts, no legacy
`0 exec ensures targets` marker, and
`unknown_reason_class=callback-trace-boundary`. The production 24-row feedback
manifest was not refreshed because no source-backed UNSAT strengthening was
sound without erasing Clone/FnOnce/FnMut trace semantics.

A bounded iterator-adaptor/boxed-conversion no-change round under
`verification/evidence/vec_feedback_determinism/adaptor-boxed-nochange-20260813T1624Z`
covered `Vec::drain`, `Vec::extract_if`, and `Vec::into_boxed_slice`; all three
reached `status=ok` with real `r0_z3=unknown`, complete
candidate/synthetic/determinism/Verus/SMT schema-search artifacts, no legacy
`0 exec ensures targets` marker, and reason classes split as
`iterator-adaptor-state-boundary=2` and `conversion-allocation-boundary=1`.
The production 24-row feedback manifest was not refreshed because no
source-backed UNSAT strengthening was sound without erasing Drain/ExtractIf
iterator/drop state or boxed-slice allocation identity/lifetime state.

The old canonical alloc::vec subset comparison is kept separate in
`catalog/vec_old_30_subset_comparison.{csv,json}`. It maps the old 30-target
subset as 3 previously strict-accepted rows, 5 duplicate-vstd rows, and 22 old
gaps against the full 49-row module inventory.

The task-native gates are:

```sh
python3 -m py_compile verification/generate_vec_artifacts.py verification/run_supervised_vec_feedback.py verification/run_vec_assume_spec_feedback_determinism.py verification/check_inventory.py verification/check_provenance.py verification/check_catalog.py verification/check_contracts.py verification/check_artifact_integrity.py
python3 verification/check_inventory.py --modules-csv results/modules.csv --inventory inventory/vec_exec_fn_inventory.csv --expect-total 49 --expect-existing-vstd 24 --expect-unstable 28
python3 verification/check_provenance.py
python3 verification/check_catalog.py
python3 verification/check_contracts.py
python3 verification/check_artifact_integrity.py
```

Independent L2 delivery review reran the Verus no-verify build and the Python
compile, inventory, provenance, catalog, contracts, and artifact-integrity gates
from the isolated Vec workspace. Later bounded mutable-reference-return repairs
reran focused feedback smokes, the full 24-target feedback refresh, Vec
artifact-integrity, post-proof incompleteness, and Slice/Vec aggregate gates; the
active Vec feedback manifest has 24 `ok` rows, no missing required feedback
artifacts, and honest catalog/spec review markers for the five
mutable-reference-return targets.
