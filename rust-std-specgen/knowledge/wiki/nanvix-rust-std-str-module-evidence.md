---
title: Nanvix Rust Std Str Module Evidence
description: Measured final evidence for the isolated Rust 1.96 core::str module experiment, including source provenance, frozen inventory, exact vstd subtraction, generated/no-spec coverage, helper audit, and feedback-determinism outcomes.
---

# Nanvix Rust Std Str Module Evidence

The isolated `core::str` module-first workspace is
`/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-str-specgen-2026-08-12`.
It is separate from the canonical Rust 1.96 checkout, the Verus/vstd checkout,
the canonical 2,121-target tree, and the completed slice and Vec workspaces.

The final provenance set is recorded in `provenance/source_manifest.{csv,json}`.
It contains 28 copied input files: 9 Rust 1.96 `library/core/src/str/**` files,
12 directly required adjacent core char/slice/error/unicode source files, 5 vstd
str/String/UTF-8 baseline files, and local frozen copies of
`results/{modules,coverage}.csv`.

The frozen executable inventory is recorded in
`inventory/str_exec_fn_inventory.{csv,json}` and summarized in
`inventory/STR_EXEC_FN_INVENTORY.md`. It is keyed by unique
`display_path`/`declaration_id` rows because the canonical constructor paths
for `from_utf8`, `from_utf8_mut`, `from_utf8_unchecked`, and
`from_utf8_unchecked_mut` intentionally alias inherent and free-function rows.
The current inventory contains 86 stable executable declaration/display rows,
20 unstable exclusions, 11 exact coverage-marked vstd rows, and 75 uncovered
stable rows. The exact-vstd subtraction audit is recorded in
`inventory/str_existing_vstd_exact_match_audit.{csv,json}` and checks target
binding, receiver/reference shape, parameters, return shape, lifetimes,
generic bounds, and mutability for the 11 coverage-marked rows. Those 11 rows
map to 10 copied vstd declarations because the inherent and free-function
`from_utf8_unchecked` rows intentionally share the copied vstd binding.

The final `catalog/str_spec_catalog.{csv,json}` disposition accounts for all 86
stable rows: 11 exact existing-vstd rows, 62 generated executable
`pub assume_specification` rows in `specs/generated_str_specs.rs`, and 13
target-specific justified-no-spec rows in
`catalog/str_justified_no_spec_records.{csv,json}`. The no-spec records cover
generic Pattern/Searcher iterator wrappers, `FromStr::from_str`, and
`substr_range`, each with attempted contract shape, Verus/model failure, source
backing, and the required future model boundary.

The shared string vocabulary lives in `specs/str_shared_vocabulary.rs`.
`verification/shared_helper_target_usage_audit.{csv,json}` records one row per
stable inventory target. Generated and existing-vstd rows have audited shared
helper usage; justified-no-spec rows are explicit records rather than local
uninterpreted helpers. The helper classes cover source-backed definitions,
law-constrained abstractions, and irreducible boundary abstractions for UTF-8
byte views, char-boundary slicing, Pattern/Searcher behavior, iterator state,
ASCII/Unicode trim and escape relations, parsing, mutable string-slice
operations, and raw pointer/provenance boundaries.

The generated declaration harness is
`verification/harnesses/str_generated_contracts_batch.rs`. The Verus no-verify
command
`/usr/bin/timeout 110s /home/chentianyu/nanvix-rust-std-spec-survey/verus/source/target-verus/release/verus verification/harnesses/str_generated_contracts_batch.rs --no-verify`
typechecks the 62 generated declarations.

The active feedback-determinism evidence is
`verification/evidence/str_feedback_determinism/str-feedback-20260812T022711Z/run_manifest.json`
and is mirrored by `verification/evidence/str_feedback_determinism/latest_manifest.json`.
The live status records 62 expected targets, 62 completed targets, and return
code 0. The final split is 57 `ok` and 5 `unsupported_mut_ref_return`; the R0
split is 2 UNSAT, 55 UNKNOWN, and 5 unsupported/no-SMT rows. All 55 UNKNOWN
outcomes have an explicit reason class, preserving Pattern-dependent,
iterator/private-state, UTF-8 boundary, ASCII/Unicode, pointer/provenance,
slice-index, parsing, and Utf8Chunk boundary outcomes rather than strengthening
them to force UNSAT.

The old canonical `core::str` subset comparison is kept separate in
`catalog/str_old_74_subset_comparison.{csv,json}`. It maps the old 74-target
subset as 17 previously strict-accepted rows, 2 duplicate-vstd rows, and 55 old
gaps against the full 86-row module inventory.

The task-native gates are:

```sh
python3 -m py_compile verification/generate_str_artifacts.py verification/check_inventory.py verification/check_provenance.py verification/check_catalog.py verification/check_contracts.py verification/check_artifact_integrity.py verification/run_str_assume_spec_feedback_determinism.py verification/run_supervised_str_feedback.py
python3 verification/check_provenance.py
python3 verification/check_inventory.py --modules-csv results/modules.csv --inventory inventory/str_exec_fn_inventory.csv --expect-stable 86 --expect-existing-vstd 11 --expect-unstable 20
python3 verification/check_catalog.py
python3 verification/check_contracts.py
python3 verification/check_artifact_integrity.py
```

Independent L2 delivery review reran the Verus no-verify build and the Python
compile, inventory, provenance, catalog, contracts, and artifact-integrity gates
from the isolated Str workspace. The review also parsed the inventory,
exact-vstd audit, catalog, justified-no-spec records, helper audit, old-subset
comparison, active feedback manifest, live run status, and per-target feedback
artifact paths directly; the `core::str` module-first delivery is accepted with
no remaining Str repair blocker.
