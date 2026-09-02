# Rust 1.96 `core::array` specgen process/design document

This is a review document for a future `core::array` module-first specification-generation campaign. It does not start generation and does not authorize edits to generated specs, catalogs, proof harnesses, certification/delivery artifacts, canonical Rust/vstd checkouts, or any other module workspace.

## Grounding evidence

Use these as the live source of truth when the operator approves implementation:

| Evidence | Live path / fact |
| --- | --- |
| Survey root | `/home/chentianyu/nanvix-rust-std-spec-survey` |
| Rust 1.96 source | `/home/chentianyu/nanvix-rust-std-spec-survey/rust-1.96/library/core/src/array/{mod.rs,iter.rs,ascii.rs,equality.rs,drain.rs,iter/iter_inner.rs}` |
| Current coverage tables | `results/modules.csv`, `results/coverage.csv`, `results/uncovered_production_stable_apis.csv`, `results/vstd_contracts.csv` |
| Current first-run classification | `specgen/CLASSIFICATION.md` lists `core::array::{each_ref,from_ref,repeat}` in the 133 suitable-now first-run set |
| Canonical 2,121-target fresh rerun | `/home/chentianyu/nanvix-rust-std-specgen-rerun-2026-08-06/specgen/all-2121-gpt56sol-fresh-20260806-0453` |
| Feedback determinism implementation | `/home/chentianyu/nanvix-rust-std-spec-survey/run_rust_std_spec_feedback.py` |
| Existing vstd array vocabulary | `/home/chentianyu/nanvix-rust-std-spec-survey/verus/source/vstd/array.rs` |
| Module-first precedents | Slice: `/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-slice-specgen-2026-08-11`; Vec: `/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-vec-specgen-2026-08-11`; Str: `/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-str-specgen-2026-08-12` |
| Wiki pages used | `nanvix-rust-std-slice-module-evidence.md`, `nanvix-rust-std-vec-module-evidence.md`, `nanvix-rust-std-str-module-evidence.md`, `nanvix-rust-std-specgen-current-progress.md`, `nanvix-rust-std-specgen-accepted-candidates.md`, `nanvix-rust-std-specgen-remaining-recovery-surface.md`, `nanvix-rust-std-specgen-module-priorities.md` |

The current `results/modules.csv` row for `core::array` reports `used_in_production=True`, `production_evidence_count=6`, `source_file_count=3`, `production_source_file_count=3`, `exec_declarations=24`, `unique_api_paths=23`, `stable_unique_api_paths=12`, `stable_declarations=12`, `unstable_declarations=12`, `covered_unique_api_paths=1`, and `uncovered_stable_unique_api_paths=11` with stable unique path coverage `8.33%`.

`results/vstd_contracts.csv` has one high-confidence exact vstd contract for this module: `core::array::as_slice`, mechanism `assume_specification`, source `array.rs:143`, raw target `<[T; N]>::as_slice`. The vstd `array.rs` file also provides reusable vocabulary such as `array_view`, `ArrayAdditionalSpecFns`, `spec_array_as_slice`, `array_as_slice`, `spec_array_update`, and `group_array_axioms`; those are vocabulary assets, not automatic authorization to redeclare an already-covered target.

## Lessons to reuse from existing module-first artifacts

`core::slice` is the closest process template. Its isolated workspace accounts for 132 stable unique executable APIs, with 12 exact existing-vstd contracts and 120 generated non-vstd rows. The slice evidence explicitly records shared-helper auditing, Verus `--no-verify` typechecks, catalog/spec evidence, and feedback-pipeline determinism. Most importantly for this future array campaign, slice no longer treats the old direct assume-spec harness failure as contract unsupported: generated `assume_specification` blocks are converted through `run_rust_std_spec_feedback.py` into synthetic `__rust_std_candidate` exec specifications before spec-determinism runs.

`alloc::vec` is the template for array/slice/ownership boundaries. Its isolated workspace accounts for 49 stable rows: 24 exact existing-vstd rows, 24 generated `assume_specification` rows, and one justified no-spec row for `Vec::splice`. Its feedback determinism manifest records 24 generated targets with 24 `ok` outcomes and an `r0_z3` split of 5 UNSAT and 19 UNKNOWN; raw/provenance, callback-trace, mutable-reference-view, and MaybeUninit outcomes are preserved as UNKNOWN instead of being strengthened away.

`core::str` is the template for source-backed skip hygiene. Its isolated workspace accounts for 86 stable rows: 11 exact existing-vstd rows, 62 generated declarations, and 13 target-specific justified no-spec records. Its determinism split keeps 55 UNKNOWN outcomes and 5 unsupported/no-SMT rows distinct. Pattern/Searcher, iterator/private-state, UTF-8 boundary, pointer/provenance, slice-index, parsing, and Utf8Chunk boundaries are not treated as proof that a contract is wrong.

The future `core::array` workspace should copy these precedents: freeze source/provenance, subtract exact vstd rows, audit shared vocabulary once, generate complete single-target `assume_specification` blocks, run Verus typechecking, run feedback-pipeline determinism, and publish a catalog/review summary that distinguishes accepted specs from justified no-spec/unsupported records.

## Current `core::array` scope, exclusions, and candidate set

### Stable current scope

The current stable uncovered production API set in `results/uncovered_production_stable_apis.csv` has 11 rows:

| Target | Kind | Rust 1.96 source |
| --- | --- | --- |
| `core::array::IntoIter::as_mut_slice` | inherent method | `core/src/array/iter.rs:228` |
| `core::array::IntoIter::as_slice` | inherent method | `core/src/array/iter.rs:220` |
| `core::array::IntoIter::new` | inherent method | `core/src/array/iter.rs:85` |
| `core::array::as_mut_slice` | primitive method | `core/src/array/mod.rs:658` |
| `core::array::each_mut` | primitive method | `core/src/array/mod.rs:719` |
| `core::array::each_ref` | primitive method | `core/src/array/mod.rs:688` |
| `core::array::from_fn` | free function | `core/src/array/mod.rs:110` |
| `core::array::from_mut` | free function | `core/src/array/mod.rs:175` |
| `core::array::from_ref` | free function | `core/src/array/mod.rs:167` |
| `core::array::map` | primitive method | `core/src/array/mod.rs:592` |
| `core::array::repeat` | free function | `core/src/array/mod.rs:54` |

The stable covered row is `core::array::as_slice`, already owned by vstd. The module campaign should include it in the inventory and exact-vstd audit, not regenerate it.

### Unstable exclusions for the first campaign

Do not include unstable declarations in the first stable campaign unless the operator explicitly broadens scope. Current unstable `core::array` rows in `results/coverage.csv` include `as_ascii`, `as_ascii_unchecked`, `try_from_fn`, `try_map`, `split_array_ref`, `split_array_mut`, `rsplit_array_ref`, `rsplit_array_mut`, `transpose`, `IntoIter::empty`, and `IntoIter::new_unchecked`. They should be listed as unstable exclusions with source locations and feature names, not silently dropped.

### Canonical rerun evidence to use as starting proposals, not as final module proof

The canonical 2,121-target rerun already has five accepted `core::array` add-spec rows in `accepted_semantic_candidates.csv`:

| Accepted target | Existing evidence |
| --- | --- |
| `core::array::as_mut_slice` | Typechecked, `r0_z3=unsat`; source-backed whole-array mutable-slice view, no pointer/provenance claim. |
| `core::array::each_mut` | Typechecked, `r0_z3=unsat`; source-backed per-index mutable-reference array relation from `buf[i] = &raw mut self[i]` and `transmute_unchecked(buf)`. |
| `core::array::each_ref` | Typechecked, `r0_z3=unsat`; pointwise dereferenced reference values preserve array order without comparing reference identity. |
| `core::array::from_mut` | Typechecked, `r0_z3=unsat`; singleton mutable array view, final input state tied to returned mutable view, no provenance claim. |
| `core::array::from_ref` | Typechecked, `r0_z3=unsat`; singleton shared array view. |

The same canonical `final_candidates.csv` keeps six stable rows as skips with non-empty rationales:

| Skipped target | Current reason to preserve unless a new approved model exists |
| --- | --- |
| `core::array::IntoIter::as_slice` | `IntoIter<T, N>` lacks an external type specification / public remaining-sequence abstraction. |
| `core::array::IntoIter::as_mut_slice` | Depends on the same `IntoIter` abstraction plus mutable remaining-slice semantics. |
| `core::array::IntoIter::new` | Source establishes start-to-end iteration, but no public vstd abstraction exposes the remaining sequence of `IntoIter`. |
| `core::array::from_fn` | Needs sequential stateful `FnMut(usize) -> T` observation semantics. |
| `core::array::map` | Needs stateful `FnMut(T) -> U` observation semantics over consumed elements in source order. |
| `core::array::repeat` | Needs a Clone law or source-backed semantic view for arbitrary `T: Clone`; Rust does not guarantee Verus equality/view preservation for clones. |

These rows are evidence, not a final module disposition. A module-first campaign must rebuild an isolated `core::array` inventory from the live Rust 1.96 source and current `results/` tables, revalidate target binding/signature/generic shape, rerun Verus typechecks, rerun determinism, and then decide whether the six skipped rows remain justified no-spec records or receive new source-backed contracts after operator-approved vocabulary.

## Shared vocabulary and modeling decisions

Start with vocabulary already used by vstd and the Slice/Vec module work:

1. Array values use Verus sequence views (`ar@`, `array_view`, `ArrayAdditionalSpecFns`) and extensional per-index equality.
2. Array-to-slice coercions reuse `spec_array_as_slice`, `array_as_slice`, and slice `Seq` vocabulary. `core::array::as_slice` remains an exact-vstd row.
3. Mutable array/slice adapters use the direct mutable-return model from slice/vec: compare semantic old/current views and returned dereferenced values, not reference identity or pointer/provenance.
4. `each_ref` and `each_mut` compare per-index dereferenced values. The accepted rerun explicitly avoids reference identity for `each_ref` and pointer/provenance identity for `each_mut`.
5. Higher-order rows (`from_fn`, `map`) require a reviewed closure-observation trace vocabulary before acceptance. The trace must model ordered calls and stateful `FnMut` evolution, not independent calls on the original closure value.
6. `repeat` requires an approved Clone model. A generic law such as “clone preserves semantic view” is a trust boundary and must be named, justified, and audited before a generated contract can rely on it.
7. `IntoIter` rows require an approved external type specification or vstd abstraction for remaining sequence state, alive range, and mutable remaining slice views. The Rust source stores a `ManuallyDrop<PolymorphicIter<[MaybeUninit<T>; N]>>`; do not infer a public view without a reviewed abstraction.

The document should call these vocabulary classes source-backed, law-constrained, or irreducible-boundary abstractions, matching the Slice/Vec/Str helper-audit pattern.

## End-to-end workflow for the future campaign

1. **Prepare an isolated workspace.** Create a new `nanvix-rust-std-array-specgen-YYYY-MM-DD` directory under the survey root. Copy only the relevant Rust 1.96 array source files, adjacent source needed for signatures, current `results/{modules,coverage,coverage-before-abstractions,uncovered_production_stable_apis,vstd_contracts}.csv`, and vstd `array.rs`/slice vocabulary needed for exact-vstd matching. Do not edit `/rust-1.96` or `/verus/source/vstd`.
2. **Freeze provenance.** Write `provenance/source_manifest.{csv,json}` with every copied source/result/vstd input and the source path it came from. Include the current module row counts above so drift is visible.
3. **Build inventory.** Generate `inventory/array_exec_fn_inventory.{csv,json}` and a human-readable inventory markdown. Count stable and unstable rows separately. Expected first stable accounting from live results is 12 stable unique paths: one exact-vstd row and 11 uncovered stable production rows.
4. **Subtract exact vstd coverage.** Build `inventory/array_existing_vstd_exact_match_audit.{csv,json}`. The known current exact row is `core::array::as_slice` / `<[T; N]>::as_slice` from vstd `array.rs:143`. Verify receiver/reference shape, parameters, return type, const generic `N`, and bounds before subtracting.
5. **Define shared vocabulary.** Write `specs/array_shared_vocabulary.rs` only after deciding which of the modeling decisions above are in scope. Reuse vstd and Slice/Vec helpers; do not create one-off uninterpreted functions where a source-backed or law-constrained helper already exists.
6. **Construct candidates.** For each non-vstd target, create a candidate dict with at least `decision: add_spec`, `contract_form: assume_specification`, complete single-target `contract_code`, structured `requires` / `ensures`, `imports`, and `feature_gates`. The `contract_code` must typecheck as one target with all required helper/import/feature-gate context. If a target remains out of scope, create a target-specific justified no-spec record with source-backed rationale and empty contract text.
7. **Generate declarations.** Emit `specs/generated_array_specs.rs` for generated rows and `specs/all_array_specs.rs` that merges generated rows with shared vocabulary and exact-vstd references without redeclaring exact-vstd specs.
8. **Typecheck.** Build an array declaration harness and run Verus with `--no-verify` against generated declarations. A contract that does not typecheck is not an accepted candidate.
9. **Run feedback determinism.** Do not pass assume-spec files directly to `spec_determinism.corpus.verusage_run`. Use the feedback pipeline described below so each `assume_specification` becomes a normal synthetic exec spec named `__rust_std_candidate`.
10. **Run audits.** Check target binding, signature shape, generic/const-generic bounds, source-fidelity of `requires` and `ensures`, anti-vacuity, shared-helper usage, catalog consistency, artifact integrity, and preservation of exact-vstd rows.
11. **Publish catalog and review summary.** Write `catalog/array_spec_catalog.{csv,json}`, any `catalog/array_justified_no_spec_records.{csv,json}`, and `catalog/ARRAY_SPEC_REVIEW.md`. The review summary must report exact-vstd, generated accepted, justified no-spec, unsupported, Verus error, runner crash, SAT/UNKNOWN/UNSAT splits, and any trust-boundary assumptions separately.

## Feedback determinism path

The future array runner should reuse the Rust std feedback path in `run_rust_std_spec_feedback.py`, not the legacy direct assume-spec harness path.

For every generated candidate:

1. Call `active_contract_code(candidate)`. The implementation normalizes `candidate["contract_code"]`, respects `candidate["decision"]`, strips cfg/cfg_attr lines, and returns the active contract text.
2. Call `assume_to_synthetic(active_code)`. It splits the `assume_specification[...]` item, preserves local declarations, and creates `pub exec fn __rust_std_candidate... { loop { } }`.
3. Call `build_determinism_artifacts(candidate, ViewRegistry.from_project(vstd_root))` or directly call `run_determinism(...)` with the approved Verus/Z3 paths.
4. The artifact builder writes a synthetic source with imports/feature gates and `__rust_std_candidate`, calls `extract_spec(..., "__rust_std_candidate")`, runs `build_det_check_spec`, `enumerate_schemas`, and `build_det_harness`, and applies target-specific normalizers including the existing array `each_mut` harness normalizer.
5. `run_determinism(...)` writes `synthetic_spec.rs`, `det_harness.rs`, and `det_spec.json`; runs Verus with SMT logging; writes `det_stdout.txt` and `det_stderr.txt`; finds the largest generated `.smt2`; builds schema context; runs schema search; and records `status`, `r0_z3`, `classification`, `requires`, `ensures`, equal policy, schema count, Verus return code/timing, assumptions, and errors.

Use the fixed paths from the survey environment:

| Tool | Path |
| --- | --- |
| vstd root | `/home/chentianyu/nanvix-rust-std-spec-survey/verus/source/vstd` |
| Verus binary | `/home/chentianyu/nanvix-rust-std-spec-survey/verus/source/target-verus/release/verus` |
| Z3 | `/home/chentianyu/nanvix-rust-std-spec-survey/verus/source/z3` |
| spec-determinism | `/home/chentianyu/intent_formalization/spec-determinism` |

Each target needs an independent round/evidence directory containing at least `candidate.json`, `synthetic_spec.rs`, `det_spec.json`, `det_harness.rs`, Verus stdout/stderr, SMT/schema-search evidence, and full `result.json`. A `0 exec ensures targets` marker is evidence of the wrong entrypoint, not evidence that the contract form is unsupported.

## Determinism result taxonomy and UNKNOWN handling

Record statuses exactly:

| Category | Meaning / action |
| --- | --- |
| `ok` + `r0_z3=unsat` | Determinism checker found no two-output witness for the modeled output/equal policy. This supports acceptance only if typecheck, source-fidelity, anti-vacuity, and semantic gates also pass. |
| `ok` + `r0_z3=sat` | The checker found a witness to underdetermined or nondeterministic modeled output. Preserve it honestly; do not strengthen the contract just to force UNSAT. |
| `ok` + `r0_z3=unknown` | The checker could not decide. Preserve UNKNOWN with a reason class such as closure trace, iterator/private state, Clone law, mutable-reference view, MaybeUninit storage, pointer/provenance, or external type boundary. UNKNOWN is not unsupported and is not proof that the contract is wrong. |
| `unsupported_*` / `no_smt2` / `no_ensures` | The checker path or candidate shape lacks required support/evidence. Keep separate from SAT/UNKNOWN/UNSAT. |
| `verus_error` | The harness failed in a way that is not the expected determinism assertion/postcondition failure. This is not a determinism result. |
| `runner_crash` | Python/tooling crashed; preserve traceback and do not classify the target semantically. |

Relational or source-nondeterministic APIs must stay honest. Slice already keeps duplicate binary-search and unstable-sort semantics source-shaped; array should do the same for future `IntoIter`, closure, or Clone rows. If Rust source permits multiple valid observations or does not expose a state component, the catalog must say so instead of imposing uniqueness.

## Validation plan and artifacts

Use task-native gates analogous to Slice/Vec/Str after the workspace exists:

```sh
python3 -m py_compile verification/generate_array_artifacts.py verification/check_inventory.py verification/check_provenance.py verification/check_catalog.py verification/check_contracts.py verification/check_artifact_integrity.py verification/run_array_assume_spec_feedback_determinism.py
python3 verification/check_provenance.py
python3 verification/check_inventory.py --modules-csv results/modules.csv --inventory inventory/array_exec_fn_inventory.csv --expect-stable 12 --expect-existing-vstd 1
python3 verification/check_catalog.py
python3 verification/check_contracts.py
python3 verification/check_artifact_integrity.py
/home/chentianyu/nanvix-rust-std-spec-survey/verus/source/target-verus/release/verus verification/harnesses/array_generated_contracts_batch.rs --no-verify
```

The exact script names are proposed for the future workspace; they should be implemented by following the Slice/Vec/Str checker patterns and updated if the generated workspace chooses different names. The acceptance criteria should be stable: provenance matches copied inputs, inventory totals match current `results/` facts, exact-vstd subtraction is target/signature/generic-shape checked, generated contracts typecheck, determinism evidence is feedback-pipeline evidence with per-target artifacts, catalog rows cover every stable target exactly once, source-fidelity audits pass for accepted `requires`/`ensures`, and justified no-spec records have non-empty source-backed rationales.

Expected deliverables:

| Artifact family | Expected files |
| --- | --- |
| Provenance | `provenance/source_manifest.{csv,json}` |
| Inventory | `inventory/array_exec_fn_inventory.{csv,json}`, inventory markdown, exact-vstd audit |
| Specs | `specs/array_shared_vocabulary.rs`, `specs/generated_array_specs.rs`, `specs/all_array_specs.rs` |
| Harnesses | `verification/harnesses/array_generated_contracts_batch.rs` and any targeted typecheck harnesses |
| Feedback evidence | `verification/evidence/array_feedback_determinism/<round>/<target>/...`, `latest_manifest.json`, run manifest |
| Catalog/review | `catalog/array_spec_catalog.{csv,json}`, `catalog/array_justified_no_spec_records.{csv,json}` if needed, `catalog/ARRAY_SPEC_REVIEW.md` |
| Audits | helper usage, target binding, signature shape, generic/const-generic bounds, source fidelity, anti-vacuity, artifact integrity |

## Milestones

1. **Operator approval.** Confirm stable-only scope, whether the five canonical accepted candidates may seed module candidates, and whether any new vocabulary for `IntoIter`, `FnMut`, or Clone is in scope.
2. **Workspace/provenance freeze.** Create the isolated array workspace and freeze copied Rust/vstd/result inputs.
3. **Inventory and exact-vstd subtraction.** Produce the 12-stable-row inventory and subtract only the exact `as_slice` vstd row unless live coverage has changed.
4. **Vocabulary review.** Approve array/slice/mutable-reference vocabulary and explicitly reject or accept proposed `IntoIter`, closure-trace, and Clone assumptions.
5. **Candidate/typecheck bootstrap.** Port the five source-backed canonical accepted candidates first, then attempt any newly approved rows. Run Verus `--no-verify`.
6. **Feedback determinism bootstrap.** Run a small representative set such as `as_mut_slice`, `each_mut`, `each_ref`, `from_mut`, `from_ref`, and one skip-boundary probe if a new model is approved. Confirm real `status` and `r0_z3`, not `0 exec ensures targets`.
7. **Full stable run and review.** Run all generated rows, write catalog/review, and preserve justified no-spec records for unresolved `IntoIter`, closure, or Clone targets.

## Ranked next-module survey after `core::array`

The module-priority wiki ranks pure sequence/container semantics before memory, concurrency, and OS/runtime modules. If the operator chooses `core::array` now as a small closure point, the next review queue should be:

| Rank after array | Module | Evidence from wiki | Why next |
| ---: | --- | --- | --- |
| 1 | `alloc::string` | 44 canonical targets, 15 strict accepted, 11 already vstd, 18 remaining gap | Builds directly on accepted `core::str` UTF-8 and mutation views. |
| 2 | `core::option` | 27 canonical targets, 8 strict accepted, 0 already vstd, 19 gap | Fundamental proof glue; branch/value forwarding can use small shared enum vocabulary. |
| 3 | `core::result` | 26 canonical targets, 6 strict accepted, 0 already vstd, 20 gap | Fundamental error-flow semantics; useful for fallible array/string/collection APIs. |
| 4 | `alloc::collections::btree` | 56 canonical targets, 15 strict accepted, 0 already vstd, 41 gap | Ordered map/set semantics reuse key-order laws and semantic collection views. |
| 5 | `std::collections::hash` | 38 canonical targets, 7 strict accepted, 0 already vstd, 31 gap | High-value map/set operations after one reviewed hash/key model. |
| 6 | `alloc::collections::vec_deque` | 38 canonical targets, 1 strict accepted, 16 already vstd, 21 gap | Sequence-like but ring-buffer split state must be approved first. |

Defer `core::cell`, `core::mem`, `core::ptr`, `alloc::boxed`, `alloc::rc`, `alloc::sync`, atomics, synchronization, I/O, filesystem, process, environment, time, and networking until their hidden state, representation, ownership, provenance, concurrency, or OS-effect vocabulary is reviewed. Do not count weak one-off hidden-state assumptions as module verification.

## Trust boundaries

- Exact-vstd rows are trusted inventory coverage and must not be duplicated.
- Source-backed contracts may describe observable semantic values, lengths, order, branch shape, and final-state relations that Rust source/docs justify.
- Pointer identity, reference identity, provenance, allocation identity, `IntoIter` internal alive range, Clone semantic preservation, and closure/callback traces are trust boundaries unless a named shared abstraction is approved.
- `requires` clauses are allowed only when source safety docs, normal-return preconditions, trait bounds, or module laws justify them. Do not add a precondition merely to make typechecking or determinism pass.
- An accepted row requires the conjunction of typecheck pass, feedback determinism status that satisfies the chosen gate, source-fidelity, target binding, signature/generic shape, anti-vacuity, semantic review, and catalog/artifact integrity.
- `UNKNOWN` is a checker result, not an unsupported contract form and not proof of contract incorrectness.

## Operator approval / amendment checklist

Before implementation, the operator should approve or amend:

1. Stable-only scope: include exactly the 12 stable unique `core::array` paths from current `results/coverage.csv`, with `as_slice` as exact-vstd and the 11 uncovered rows as generated-or-justified targets.
2. Candidate seeding: allow the five canonical accepted rows (`as_mut_slice`, `each_mut`, `each_ref`, `from_mut`, `from_ref`) to seed the module-first campaign, subject to fresh isolated typecheck/determinism/audits.
3. Boundary policy: keep `IntoIter::{new,as_slice,as_mut_slice}`, `from_fn`, `map`, and `repeat` as justified no-spec records unless the operator explicitly approves new `IntoIter`, closure-trace, or Clone-law vocabulary.
4. Determinism path: require the feedback pipeline through `active_contract_code`, `assume_to_synthetic`, synthetic `__rust_std_candidate`, `build_determinism_artifacts`/`run_determinism`, Verus SMT, and schema search.
5. Artifact contract: require independent per-target evidence directories and final catalog/review artifacts analogous to Slice/Vec/Str.
6. Next-module order: after `core::array`, prioritize `alloc::string`, `core::option`, `core::result`, BTree collections, Hash collections, then `VecDeque`, unless project needs override.

Wait for explicit operator review and authorization before creating the `core::array` workspace, generating specs, modifying catalogs/harnesses/certification artifacts, or editing source/vstd checkouts.
