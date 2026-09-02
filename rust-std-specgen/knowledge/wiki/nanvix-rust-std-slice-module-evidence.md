---
title: Nanvix Rust Std Slice Module Evidence
description: Measured catalog and verification evidence for the isolated core::slice module experiment.
---

# Nanvix Rust Std Slice Module Evidence

The isolated experiment root
`/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-slice-specgen-2026-08-11` contains the
current `core::slice` module artifact set. This is an isolated experiment, not
an upstream or canonical-results modification.

The catalog currently accounts for 132 stable unique executable `core::slice`
APIs: 12 exact existing-vstd contracts and 120 non-vstd generated rows. The
executable generated conversion now covers all 120 non-vstd APIs. Earlier
batches covered observation/search/mutation plus iterator/splitting/chunking
and fixed array views; the remaining-family batch covers the final 44 rows:
ASCII byte operations, fixed-array flattening, raw pointer/provenance APIs,
generic `SliceIndex` and disjoint mutable accessors, `MaybeUninit` storage
transitions, `strip_*`/`subslice_range`, `is_sorted*`, and unstable sort/select
APIs.

The integrity evidence under `verification/` records per-target contract
coverage, typecheck/static contract-shape result, determinism, target binding,
signature shape, generic bounds, anti-vacuity, and source fidelity. The
task-native checks report:

- inventory: 132 stable unique `core::slice` exec APIs, 12 existing-vstd, 120
  pending before generation;
- catalog: 132 rows, 12 existing-vstd, 120 generated/justified;
- provenance: 23 copied Rust slice files, 2 copied vstd baseline files, and 25
  manifest rows;
- contracts: 132 marked spec blocks, 12 exact vstd contracts, 120 generated
  relation/spec rows, 120 executable generated `assume_specification`
  declarations in `specs/generated_slice_specs.rs`, and 133 actual
  `pub assume_specification` declarations in the merged
  `specs/all_slice_specs.rs`;
- bootstrap Verus typecheck: `/home/chentianyu/nanvix-rust-std-spec-survey/verus/source/target-verus/release/verus verification/harnesses/slice_observation_bootstrap.rs --no-verify`
  returned rc=0 with empty stdout/stderr, recorded under
  `verification/evidence/slice_observation_bootstrap.verus.*`;
- feedback-pipeline determinism: the generated assume-specification contracts
  are converted through
  `/home/chentianyu/nanvix-rust-std-spec-survey/run_rust_std_spec_feedback.py`
  into synthetic `__rust_std_candidate` exec specifications before
  spec-determinism is invoked;
- mutation batch Verus typecheck:
  `/home/chentianyu/nanvix-rust-std-spec-survey/verus/source/target-verus/release/verus verification/harnesses/slice_observation_mutation_batch.rs --no-verify`
  returned rc=0 with empty stdout/stderr, recorded under
  `verification/evidence/slice_observation_mutation_batch.verus.*`;
- mutation/search rows now use the same feedback-pipeline determinism evidence
  as the rest of the generated catalog instead of the old direct
  assume-specification harness result;
- splitting/iterator batch Verus typecheck:
  `/home/chentianyu/nanvix-rust-std-spec-survey/verus/source/target-verus/release/verus verification/harnesses/slice_splitting_iterator_batch.rs --no-verify`
  returned rc=0 with empty stdout/stderr, recorded under
  `verification/evidence/slice_splitting_iterator_batch.verus.*`;
- splitting/chunk/iterator rows now use the same feedback-pipeline determinism
  evidence as the rest of the generated catalog instead of the old direct
  assume-specification harness result;
- remaining-family batch Verus typecheck:
  `/home/chentianyu/nanvix-rust-std-spec-survey/verus/source/target-verus/release/verus verification/harnesses/slice_remaining_families_batch.rs --no-verify`
  returned rc=0 with empty stdout/stderr, recorded under
  `verification/evidence/slice_remaining_families_batch.verus.*`;
- remaining-family rows now use the same feedback-pipeline determinism evidence
  as the rest of the generated catalog instead of the old direct
  assume-specification harness result;
- artifact integrity: 132 targets, 12 existing-vstd, and 120
  generated/justified rows with evidence recorded in
  `verification/artifact_integrity_evidence.*`.

`verification/check_contracts.py` currently strips Rust comments, checks the
provided `--specs` file for non-comment shared vocabulary and observation,
find-like search, mutation, plus splitting/chunk/iterator
`assume_specification` snippets, and requires the latest feedback-pipeline
determinism manifest for the 120 generated targets. The adjacent catalog
checker accepts the converted rows' real `verus-typecheck: pass` evidence and
rejects stale direct-harness no-target determinism rows. No
non-vstd generated rows remain in the old static-only pending state. Final
slice-module acceptance remains an operator review decision.

The current determinism evidence no longer uses the legacy direct
assume-specification harness result. The generated assume-specification blocks
are converted to synthetic executable `__rust_std_candidate` functions before
spec-determinism runs, so the catalog records real feedback-pipeline outcomes
per generated target. The executable `contains`, `starts_with`, and `ends_with`
contracts use the shared `partial_eq_observed` bridge rather than mathematical
sequence equality for arbitrary Rust `PartialEq` implementations.

The ASCII escape vocabulary now includes a source-backed `ascii_escape_seq`
definition for Rust 1.96 `escape_default` byte cases and slice
`escape_ascii` flat-map behavior: tab, carriage return, line feed, single quote,
double quote, and backslash use two-byte escapes; printable ASCII
`0x20..=0x7e` is emitted verbatim except those escaped cases; all other bytes are
lowercase `\xNN`. A focused no-update feedback smoke under
`verification/evidence/slice_feedback_determinism/ascii-escape-source-backed-smoke-20260811T1235Z`
ran `core::slice::escape_ascii` and reached `status=ok` with `r0_z3=unsat`.

`verification/check_contracts.py` now enforces an audit of the 41 shared
vocabulary helpers that were originally uninterpreted. The audit rejects
unaudited `pub uninterp spec fn` additions and classifies the current helper set
as 10 source-backed replacements, 7 law-constrained observation/state
abstractions, and 24 irreducible boundary abstractions. The source-backed
replacements are `slice_multiplicity`, `array_ref_view`, `array_mut_ref_view`,
`array_value_view`, `flatten_array_chunks`, `ascii_lower_byte`,
`ascii_upper_byte`, `ascii_trim_start_index`, `ascii_trim_end_index`, and
`ascii_escape_seq`; multiplicity is tied to `Seq::to_multiset().count`,
fixed-array/chunk flattening is tied to Verus array views, ASCII case/trim
helpers are tied to the byte ranges and leading/trailing whitespace searches in
`core/src/slice/ascii.rs`; the trim whitespace classifier matches Rust
`u8::is_ascii_whitespace` for `0x09`, `0x0a`, `0x0c`, `0x0d`, and `0x20`
only, explicitly excluding vertical tab `0x0b`; and `ascii_escape_seq` is tied to
`core/src/escape.rs` lowercase byte escape rules plus slice `escape_ascii`
flat-map source behavior. The law-constrained helpers are `partial_eq_observed`,
`zero_arg_fnmut_outputs`, `ord_cmp_observed`, `partial_ord_leq_observed`,
`comparator_ordering_observed`, `comparator_observation`, and
`slice_iterator_view`; their constraints are supplied by concrete broadcast
axiom laws and shared open predicates for PartialEq/Ord/comparator observed
`core::cmp::Ordering` results and iterator/chunk structure. The additional boundary helpers
`fnmut_adjacent_bool_outputs` and `fnmut_adjacent_key_outputs` model source-order
stateful `FnMut` traces for `is_sorted_by` and `is_sorted_by_key` instead of
all-pairs/extensional callback or key behavior.

The standalone review summary at `catalog/SLICE_SPEC_REVIEW.md` audits the
current all-target feedback evidence set:
`verification/evidence/slice_feedback_determinism/all-20260815T0127Z-ascii-whitespace-vtab-repair`.
That set has 132 catalog rows, 12 existing-vstd rows, 120 generated contract
attempts, 120 generated Verus typecheck passes, 0 generated typecheck failures,
58 `R0=UNSAT`, 0 `R0=SAT`, 62 `R0=UNKNOWN`, 0 feedback-pipeline unsupported
outcomes, 0 feedback-pipeline Verus errors, 0 runner crashes, and 0 remaining
unconverted non-vstd rows.

Before that active all-target run, a focused no-update exact-empty smoke
`verification/evidence/slice_feedback_determinism/focused-exact-empty-20260814T0021Z`
covered `core::slice::{split,chunk_by,utf8_chunks,chunks_mut,chunks_exact_mut}`.
It produced complete candidate, synthetic-exec, determinism spec/harness,
Verus stdout/stderr, SMT/schema-search, and result artifacts with no legacy
no-target marker. The focused results were real `status=ok`:
`split`, `chunk_by`, and `utf8_chunks` reached `r0_z3=unsat`, while
`chunks_mut` and `chunks_exact_mut` honestly remained `r0_z3=unknown` under the
iterator/subslice-state boundary. The
`all-20260814T0030Z-exact-empty-artifact-refresh` full 120-target refresh
promoted those results into the catalog before the later
`all-20260814T0126Z-array-chunk-length-refresh` run superseded it as the active
all-target manifest; that run was later superseded by
`all-20260814T0147Z-array-chunk-elementwise-refresh` and then by
`all-20260814T0235Z-post-sync-exec-decl-refresh`, then by
`all-20260814T0343Z-mut-array-final-subranges-refresh`, and now by
`all-20260815T0127Z-ascii-whitespace-vtab-repair`.

The active `core::slice::as_flattened_mut` contract no longer depends on the
reverse opaque `unflatten_array_chunks` helper: its final-frame relation is
`flatten_array_chunks::<T, N>(final(slice)@) == final(ret)@`. The focused
source-backed feedback smoke under
`verification/evidence/slice_feedback_determinism/flattened-mut-source-backed-smoke-20260811T0958Z`
reached `status=ok` with `r0_z3=unknown`. The subsequent all-target refresh
`verification/evidence/slice_feedback_determinism/all-20260811T1008Z-flattened-mut-source-backed`
completed all 120 generated targets with `status=ok`. Later all-target refreshes
for adjacent-`FnMut` sortedness, iterator/chunk state, and the MaybeUninit helper
prune also completed all 120 generated targets; the later source-backed ASCII
escape, raw-pointer/provenance, align-to split-shape, MaybeUninit storage-shape,
select-nth result-shape, mutable-iterator final-frame repair, iterator-empty-state,
reverse-chunk empty-state, and exact-empty artifact refreshes supersede that
split, and the generated catalog rows and spec markers now reference
`verification/evidence/slice_feedback_determinism/all-20260815T0127Z-ascii-whitespace-vtab-repair`.

The iterator/adaptor equality adapter is covered by the representative feedback
smoke under
`verification/evidence/slice_feedback_determinism/iterator-view-smoke-20260811T0924Z`
and by the all-target run above. In the all-target evidence, 25 determinism specs
record equal-policy source `nanvix_slice_iterator_view_fields`; their generated
det harnesses contain no stale opaque `(r1 == r2)` return equality and compare
the modeled `slice_iterator_view` fields fixed by the contract. The named
representatives `chunks`, `array_windows`, `iter_mut`, `split`, `chunk_by`,
`escape_ascii`, and `utf8_chunks` all reached `status=ok` in the all-target run,
with 4 `R0=UNSAT` and 3 `R0=UNKNOWN`.

The iterator/chunk shared vocabulary now records source-derived constructor state
instead of only shape facts for the affected chunk/window/split families. Exact
chunk partitions distinguish forward suffix remainders from reverse prefix
remainders; non-exact chunk/window constructors fix source, remaining,
empty yielded-prefix and empty remainder state; predicate split/rsplit/splitn and
`chunk_by` helpers fix source/remaining partition state plus the relevant
predicate-observation bridge. Focused no-update feedback smoke
`verification/evidence/slice_feedback_determinism/iterator-chunk-state-smoke-20260811T1047Z/run_manifest.json`
covered `chunks`, `chunks_exact`, `rchunks_exact`, `windows`, `array_windows`,
`split`, `split_inclusive`, `splitn`, `rsplitn`, and `chunk_by`; all 10 reached
`status=ok` with real `r0_z3=unknown`. The subsequent all-target refresh
`verification/evidence/slice_feedback_determinism/all-20260811T1100Z-iterator-chunk-state-refresh`
completed all 120 generated targets with `status=ok`; the later
MaybeUninit-helper-prune refresh
`verification/evidence/slice_feedback_determinism/all-20260811T1115Z-prune-unused-maybeuninit-helpers`
preserved the same `r0_z3` split of 45 `unsat` and 75 `unknown`; the later
source-backed ASCII escape refresh supersedes that evidence for current catalog
determinism rows.

The target-to-helper audit is now recorded in
`verification/shared_helper_target_usage_audit.{json,csv}` and enforced by
`verification/check_contracts.py`. The validator computes direct shared-helper
calls from every generated `assume_specification` contract, closes them through
shared-vocabulary helper definitions, and rejects target-local
`pub uninterp spec fn` declarations in generated specs. The current audit covers
120 generated targets: 111 have direct shared-helper calls, 96 reach at least
one of the 41 audited helpers, and 0 declare target-local uninterpreted helpers.
By class, generated targets reach source-backed helpers in 31 targets,
law-constrained helpers in 49 targets, and irreducible boundary helpers in 42 targets; target-helper
reference counts are 45 source-backed, 51 law-constrained, and 51 boundary. No
audited helper is currently unused by the generated contracts.

`verification/run_slice_assume_spec_feedback_determinism.py` now defaults to all
120 generated targets. It constructs project-local Rust std feedback candidates
from the real generated `assume_specification` blocks, inlines the shared
vocabulary body without a nested `verus!`, carries the slice feature
gates/imports, converts through `active_contract_code` and
`assume_to_synthetic` to `__rust_std_candidate`, installs a narrow source-backed
mutable-reference-return adapter for the 11 affected slice targets, and calls the
survey `run_determinism` path. The active all-target round
`verification/evidence/slice_feedback_determinism/all-20260815T0127Z-ascii-whitespace-vtab-repair`
contains per-target `synthetic_spec.rs`, `det_spec.json`, `det_harness.rs`,
Verus stdout/stderr aliases, SMT files and schema-search evidence when `r0_z3`
is produced, candidate JSON, and full `result.json`. The latest manifest has
120 result JSONs with status counts `ok=120`; `r0_z3` counts are `unsat=58`
and `unknown=62`.

The former `unsupported_mut_ref_return` targets now all produce
feedback-pipeline `status=ok` with real `r0_z3` values. The three iterator
remainder/view targets `ChunksExactMut::into_remainder`,
`IterMut::into_slice`, and `RChunksExactMut::into_remainder` are `unsat`; the
remaining source-backed mutable-reference-return targets
`as_chunks_unchecked_mut`, `as_flattened_mut`, `assume_init_mut`, `from_mut`,
`from_raw_parts_mut`, `get_unchecked_mut`, `write_clone_of_slice`, and
`write_copy_of_slice` are `unknown`.

The Option-wrapped mutable fixed-array return targets
`as_mut_array`, `first_chunk_mut`, `last_chunk_mut`,
`split_first_chunk_mut`, and `split_last_chunk_mut` use narrow
feedback-determinism equality policies for source-backed array/tuple Seq views
instead of mutable-reference identity. A focused no-update smoke under
`verification/evidence/slice_feedback_determinism/reviewer-option-mut-array-smoke-20260813T151120Z`
covered all five targets, with complete candidate/synthetic/determinism
harness/SMT/schema-search/result artifacts, `status=ok`, `r0_z3=unknown`, and
no legacy no-target marker. The UNKNOWN outcome is preserved
because the contracts fix the modeled Seq views and old/final slice frame but
do not uniquely determine mutable-reference identity or alias/lifetime state.

The chunk/window/subview no-change smoke
`verification/evidence/slice_feedback_determinism/chunk-window-subview-nochange-20260813T1532Z/run_manifest.json`
covered `as_chunks`, `as_chunks_mut`, `as_chunks_unchecked`,
`as_chunks_unchecked_mut`, `as_rchunks`, `as_rchunks_mut`, `chunk_by_mut`,
`chunks_mut`, `chunks_exact_mut`, `rchunks`, `rchunks_mut`,
`rchunks_exact_mut`, and `utf8_chunks`. All 13 targets reached real
feedback-pipeline `status=ok` with `r0_z3=unknown`, complete
candidate/synthetic/determinism harness/SMT/schema-search/result artifacts,
and no legacy no-target marker. No production catalog or
contract refresh was made for this focused pass; the UNKNOWN classification is
preserved because the current source-backed contracts fix chunk partitions or
iterator public view fields, but not the opaque reference/iterator runtime
identity needed for a uniqueness result.

The fixed-array chunk contracts make the source quotient/remainder length facts
explicit in `slice_array_chunks_partition`, `slice_array_rchunks_partition`,
`as_chunks`, `as_rchunks`, `as_chunks_unchecked`, and the semantics-safe mutable
counterparts. A focused no-update feedback smoke under
`verification/evidence/slice_feedback_determinism/focused-array-chunk-length-20260814T0126Z`
covered `as_chunks`, `as_rchunks`, `as_chunks_unchecked`, `as_chunks_mut`,
`as_rchunks_mut`, and `as_chunks_unchecked_mut`; all six reached real
feedback-pipeline `status=ok`, `r0_z3=unknown`, with complete
candidate/synthetic/determinism harness/SMT/schema-search/result artifacts.
The UNKNOWN classification is preserved rather than strengthened away because
the returned slice/reference runtime identity remains outside the pure
quotient/remainder Seq facts.

The subsequent all-target refresh
`verification/evidence/slice_feedback_determinism/all-20260814T0126Z-array-chunk-length-refresh`
promoted those strengthened fixed-array chunk contracts into the catalog. A
later source-backed immutable elementwise/subrange refresh
`verification/evidence/slice_feedback_determinism/all-20260814T0147Z-array-chunk-elementwise-refresh`
first added explicit immutable per-chunk source subrange facts for `as_chunks`,
`as_rchunks`, and `as_chunks_unchecked`. The later
`verification/evidence/slice_feedback_determinism/all-20260814T0343Z-mut-array-final-subranges-refresh`
kept those immutable facts in the production executable declarations and added
the analogous mutable initial/final chunk plus remainder subrange facts for
`as_chunks_mut`, `as_rchunks_mut`, and `as_chunks_unchecked_mut`, without adding
mutable-reference identity assumptions. The current active refresh
`verification/evidence/slice_feedback_determinism/all-20260815T0127Z-ascii-whitespace-vtab-repair`
preserves those facts, repairs `core::slice::is_sorted` adjacent-pair semantics,
and is now the active catalog/spec/review/`latest_manifest.json` round. It
completed all 120 generated targets with `status=ok`; `r0_z3` counts remain
`unsat=58` and `unknown=62`.

The merged production `specs/all_slice_specs.rs` executable declarations for
`as_chunks`, `as_rchunks`, `as_chunks_unchecked`, `as_chunks_mut`,
`as_rchunks_mut`, and `as_chunks_unchecked_mut` now carry the same
`array_value_view` source/final subrange clauses as `specs/generated_slice_specs.rs`
and the catalog `contract_text` rows.
`verification/check_contracts.py` now guards this synchronization by comparing
generated executable declarations in merged specs against generated specs and
by checking both marker-block `contract_text` copies against the catalog. A
focused exec-sync feedback smoke at
`verification/evidence/slice_feedback_determinism/focused-array-chunk-exec-sync-20260814T0223Z`
covered the three immutable fixed-array chunk targets with real
`status=ok`/`r0_z3=unknown` results and complete synthetic/determinism
artifacts; the active all-120 artifact-updating determinism refresh is
`all-20260815T0127Z-ascii-whitespace-vtab-repair`.

The immutable iterator/window/split no-change smoke
`verification/evidence/slice_feedback_determinism/immutable-iterator-window-nochange-20260813T1644Z/run_manifest.json`
covered `array_windows`, `chunk_by`, `chunks`, `chunks_exact`,
`rchunks_exact`, `rsplitn`, `split`, `split_inclusive`, `splitn`, and
`windows`. All 10 targets reached real feedback-pipeline `status=ok` with
`r0_z3=unknown`, complete candidate/synthetic/determinism
harness/SMT/schema-search/result artifacts, and no legacy no-target marker. No
production catalog or contract refresh was
made for this focused pass; the UNKNOWN classification is preserved because the
source-backed contracts fix public iterator view fields, chunk partitions, or
predicate split state, but not opaque iterator runtime/lifetime identity.

A later focused iterator-empty-state repair strengthens the constructor
contracts for `chunks`, `chunks_exact`, `windows`, and `array_windows` from
empty-state length constraints to direct `Seq::empty()` equalities on the
modeled iterator `yielded_prefix`/`remainder` fields. The no-update smoke
`verification/evidence/slice_feedback_determinism/iterator-empty-state-smoke-20260813T2315Z/run_manifest.json`
records all four targets at real feedback-pipeline `status=ok` and
`r0_z3=unsat`, with complete candidate, synthetic spec, determinism spec/harness,
Verus stdout/stderr, SMT/schema-search, and result artifacts and no legacy
no-target marker. The subsequent all-target refresh
`verification/evidence/slice_feedback_determinism/all-20260813T2324Z-iterator-empty-state-refresh`
promotes this repair into the active manifest, catalog determinism rows, review
summary, artifact-integrity baseline, and downstream Slice/Vec incompleteness
surfaces.

A subsequent reverse-chunk exact-empty repair applies the same direct
`Seq::empty()` empty-state strengthening to `rchunks`, `rchunks_exact`, and the
source-equivalent mutable mirrors where valid. Focused feedback runs record
`rchunks` and `rchunks_exact` at real `status=ok` / `r0_z3=unsat`, while
`rchunks_mut` and `rchunks_exact_mut` remain honest real
`status=ok` / `r0_z3=unknown` with
`unknown_reason_class=iterator-or-subslice-state-boundary`. The all-target refresh
`verification/evidence/slice_feedback_determinism/all-20260813T2355Z-reverse-chunk-empty-state-refresh`
first promoted this result into the active manifest, catalog determinism rows,
review summary, artifact-integrity baseline, and downstream Slice/Vec
incompleteness surfaces. The later exact-empty artifact refresh
`verification/evidence/slice_feedback_determinism/all-20260814T0030Z-exact-empty-artifact-refresh`
superseded it, and the later fixed-array chunk length refresh
`verification/evidence/slice_feedback_determinism/all-20260814T0126Z-array-chunk-length-refresh`
was later superseded by
`verification/evidence/slice_feedback_determinism/all-20260814T0147Z-array-chunk-elementwise-refresh`,
which was later superseded by
`verification/evidence/slice_feedback_determinism/all-20260814T0343Z-mut-array-final-subranges-refresh`
and then by the active
`verification/evidence/slice_feedback_determinism/all-20260815T0127Z-ascii-whitespace-vtab-repair`
all-target run; the intervening
`verification/evidence/slice_feedback_determinism/all-20260814T0235Z-post-sync-exec-decl-refresh`
run is historical.

The search/sort no-change smoke
`verification/evidence/slice_feedback_determinism/search-sort-nochange-20260813T1550Z/run_manifest.json`
covered `binary_search`, `binary_search_by`, `binary_search_by_key`,
`partition_point`, `select_nth_unstable`, `select_nth_unstable_by`,
`select_nth_unstable_by_key`, `sort_unstable`, `sort_unstable_by`, and
`sort_unstable_by_key`. All 10 targets reached real feedback-pipeline
`status=ok` with `r0_z3=unknown`, complete
candidate/synthetic/determinism harness/SMT/schema-search/result artifacts,
and no legacy no-target marker. No production catalog or
contract refresh was made for this focused pass; the UNKNOWN classification is
preserved because Rust documents arbitrary duplicate binary-search matches,
`partition_point` is callback-trace based, and unstable sort/select APIs do not
fix a unique equal-key or pivot-equivalent permutation.

The comparator-ordering vocabulary now derives comparator `<=` from the observed
`core::cmp::Ordering` value recorded by `comparator_ordering_observed`, rather
than treating `comparator_leq_observed` as an independent opaque total preorder.
Focused no-update feedback smoke
`verification/evidence/slice_feedback_determinism/comparator-ordering-smoke-20260811T1134Z/run_manifest.json`
covered `binary_search`, `binary_search_by`, `binary_search_by_key`,
`partition_point`, `is_sorted`, `is_sorted_by`, `is_sorted_by_key`,
`select_nth_unstable*`, and `sort_unstable*`; all 13 reached `status=ok`, with
3 `r0_z3=unsat` sortedness results and 10 `r0_z3=unknown` relational or
source-nondeterministic results. The post-comparator all-target refresh
`verification/evidence/slice_feedback_determinism/all-20260811T1142Z-comparator-ordering-refresh`
completed all 120 generated targets with `status=ok`, `r0_z3` split
`unsat=45` and `unknown=75`, and no `unsupported` or direct-harness no-target
result. `latest_manifest.json`, generated/all spec
determinism markers, catalog determinism rows, and
`verification/check_artifact_integrity.py` later moved to the post-migration active
refresh below, preserving the same 120 `ok`, 45 `unsat`, and 75 `unknown`
feedback split.

The prior source-backed ASCII escape refresh
`verification/evidence/slice_feedback_determinism/all-20260811T1246Z-ascii-escape-source-backed`
completed from the migrated slice root with 120 `status=ok` results and the same
45 `unsat` / 75 `unknown` `r0_z3` split. It was superseded by the
raw-pointer/provenance refresh
`verification/evidence/slice_feedback_determinism/all-20260811T1317Z-raw-provenance-source-backed`,
then by the align-to split-shape refresh
`verification/evidence/slice_feedback_determinism/all-20260811T133754Z-align-to-split-shape`,
then by the MaybeUninit storage-shape refresh
`verification/evidence/slice_feedback_determinism/all-20260811T1358Z-maybeuninit-storage-shape`,
then by the select-nth result-shape refresh
`verification/evidence/slice_feedback_determinism/all-20260811T1415Z-select-nth-result-shape`,
then by the mutable-iterator final-frame repair refresh
`verification/evidence/slice_feedback_determinism/all-20260813T1204Z-final-frame-repair`,
then by the iterator-empty-state refresh
`verification/evidence/slice_feedback_determinism/all-20260813T2324Z-iterator-empty-state-refresh`,
then by the reverse-chunk empty-state refresh
`verification/evidence/slice_feedback_determinism/all-20260813T2355Z-reverse-chunk-empty-state-refresh`,
then by the exact-empty artifact refresh
`verification/evidence/slice_feedback_determinism/all-20260814T0030Z-exact-empty-artifact-refresh`,
then by the fixed-array chunk length refresh
`verification/evidence/slice_feedback_determinism/all-20260814T0126Z-array-chunk-length-refresh`,
then by the immutable chunk elementwise/subrange refresh
`verification/evidence/slice_feedback_determinism/all-20260814T0147Z-array-chunk-elementwise-refresh`,
then by the post-sync executable-declaration refresh
`verification/evidence/slice_feedback_determinism/all-20260814T0235Z-post-sync-exec-decl-refresh`,
then by the mutable fixed-array final-subrange refresh
`verification/evidence/slice_feedback_determinism/all-20260814T0343Z-mut-array-final-subranges-refresh`,
and now by the post-`is_sorted` adjacent-pair refresh
`verification/evidence/slice_feedback_determinism/all-20260815T0127Z-ascii-whitespace-vtab-repair`,
which `latest_manifest.json`, generated/all spec determinism markers, catalog
determinism rows, the review summary, and `verification/check_artifact_integrity.py`
now reference. The old standalone slice root is absent on disk, and the active
feedback evidence tree contains no active selector references to that retired
standalone root string; older historical evidence remains historical.

The active manifest, per-target `result.json` files, catalog/spec determinism
markers, review summary, and artifact-integrity evidence now classify every one
of the 62 `R0=UNKNOWN` generated rows with a non-empty `unknown_reason_class`.
The current taxonomy split is: 2 clone/callback-effect boundary, 2 disjoint
mutable-alias boundary, 4 duplicate-or-callback search boundary, 24
iterator-or-subslice state boundary, 4 MaybeUninit storage boundary, 7 mutable
reference-view boundary, 13 raw-pointer/provenance boundary, and 6 unstable
sort-or-selection boundary. These are review reasons for inconclusive real
`r0_z3=unknown` outcomes, not contract strengthening or result rewriting.

The raw-pointer/provenance slice vocabulary now has source-expressible open
wrappers for raw-domain length/mutability, pointer-range start pointers,
`element_offset` in-domain/in-bounds results, and `subslice_range` modeled range
plus source-observable length bounds. A focused no-update smoke run under
`verification/evidence/slice_feedback_determinism/raw-provenance-source-backed-smoke-20260811T1305Z`
covered `as_ptr`, `as_mut_ptr`, `as_ptr_range`, `as_mut_ptr_range`,
`from_raw_parts`, `from_raw_parts_mut`, `element_offset`, and `subslice_range`;
all 8 reached `status=ok` with `r0_z3=unknown` and
`unknown_reason_class=raw-pointer-provenance-boundary`, with synthetic
`__rust_std_candidate`, det-harness, SMT/schema-search, candidate, and result
artifacts present. The subsequent all-target refresh
`verification/evidence/slice_feedback_determinism/all-20260811T1317Z-raw-provenance-source-backed`
completed all 120 generated targets with `status=ok`, `R0=UNSAT` for 45 targets,
`R0=UNKNOWN` for 75 targets, and no `SAT`, unsupported, Verus-error, runner-crash,
or legacy direct assume-specification no-target outcomes. It was superseded by
the align-to split-shape refresh below.

A later bounded raw/provenance no-change review smoke under
`verification/evidence/slice_feedback_determinism/raw-provenance-nochange-smoke-20260813T1415Z`
covered `align_to`, `as_ptr_range`, `from_raw_parts_mut`,
`get_unchecked_mut`, and `subslice_range`; all five reached `status=ok` with
real `r0_z3=unknown`, complete synthetic/determinism/Verus/SMT/schema-search
artifacts, no legacy no-target marker, and
`unknown_reason_class=raw-pointer-provenance-boundary`. The same bounded
increment repaired the harness-only `core::slice::get_unchecked_mut` equality
policy: `det_spec.json` records source
`nanvix_slice_index_mut_final_frame`, and the generated equal function compares
the modeled final slice frame instead of dereferencing the possibly-unsized
`SliceIndex::Output` return.

The active `align_to` / `align_to_mut` vocabulary now states source-visible split
shape without collapsing the middle reinterpretation: the immutable result
requires exact source prefix/suffix subranges and
`prefix.len() + suffix.len() <= source.len()`, while the mutable result also
frames `final(slice)@` with matching final prefix/suffix subranges and disjoint
bounds. The focused no-update smoke
`verification/evidence/slice_feedback_determinism/align-to-split-shape-smoke-20260811T133731Z`
covered `core::slice::align_to` and `core::slice::align_to_mut`; both reached
`status=ok`, `r0_z3=unknown`, and
`unknown_reason_class=raw-pointer-provenance-boundary`. The subsequent all-target
refresh
`verification/evidence/slice_feedback_determinism/all-20260811T133754Z-align-to-split-shape`
completed all 120 generated targets with `status=ok`, `R0=UNSAT` for 45 targets,
`R0=UNKNOWN` for 75 targets, and no `SAT`, unsupported, Verus-error, runner-crash,
or legacy direct assume-specification no-target outcomes. It was superseded by
the MaybeUninit storage-shape refresh below.

The active MaybeUninit slice-storage contracts keep `maybe_uninit_seq_relation`
as the raw storage/layout boundary, but now add source-visible relation
well-formedness and length preservation for `assume_init_drop`,
`assume_init_mut`, `assume_init_ref`, `write_clone_of_slice`, and
`write_copy_of_slice`. The write contracts and `assume_init_mut` also record
all-initialized final storage facts; `assume_init_drop` instead records
post-drop uninitialized storage while preserving storage length. The focused
no-update smoke
`verification/evidence/slice_feedback_determinism/maybeuninit-storage-shape-smoke-20260811T1354Z`
covered all five MaybeUninit storage targets and reached 5 `status=ok` results:
`assume_init_ref` was `r0_z3=unsat`, while the four storage-boundary targets
remained honest `r0_z3=unknown`. The subsequent all-target refresh
`verification/evidence/slice_feedback_determinism/all-20260811T1358Z-maybeuninit-storage-shape`
completed all 120 generated targets with `status=ok`, `R0=UNSAT` for 45 targets,
`R0=UNKNOWN` for 75 targets, and no `SAT`, unsupported, Verus-error,
runner-crash, or legacy direct assume-specification no-target outcomes. It was
superseded by the select-nth result-shape refresh below.

A later focused MaybeUninit/raw-storage no-change audit under
`verification/evidence/slice_feedback_determinism/maybeuninit-storage-nochange-20260813T1605Z/run_manifest.json`
covered `assume_init_drop`, `assume_init_mut`, `write_clone_of_slice`, and
`write_copy_of_slice`. All four reached real feedback-pipeline `status=ok` with
`r0_z3=unknown`, complete candidate/synthetic/determinism/Verus/SMT
schema-search/result artifacts, no legacy no-target marker, and
`unknown_reason_class=maybeuninit-storage-boundary`. No production catalog or
contract refresh was made for this focused pass because no source-backed UNSAT
strengthening was sound without collapsing MaybeUninit raw-storage and
initialization-state semantics.

The active `select_nth_unstable`, `select_nth_unstable_by`, and
`select_nth_unstable_by_key` contracts explicitly tie the returned pivot to the
post-state slice position and the right returned subslice length:
`*final(ret.1) == final(slice)@[index as int]` and
`final(ret.2)@.len() == old(slice)@.len() - (index as int) - 1`, while preserving
permutation and unstable partition semantics rather than imposing a unique output
ordering. The focused no-update smoke
`verification/evidence/slice_feedback_determinism/select-nth-result-shape-smoke-20260811T1415Z`
covered the three select-nth targets and reached 3 `status=ok` results with
`r0_z3=unknown` and
`unknown_reason_class=unstable-sort-or-selection-boundary`. The subsequent
all-target refresh
`verification/evidence/slice_feedback_determinism/all-20260815T0127Z-ascii-whitespace-vtab-repair`
completed all 120 generated targets with `status=ok`, `R0=UNSAT` for 58 targets,
`R0=UNKNOWN` for 62 targets, and no `SAT`, unsupported, Verus-error,
runner-crash, or legacy direct assume-specification no-target outcomes. It is
the active run referenced by `latest_manifest.json`, catalog/spec determinism
markers, review summary, and artifact-integrity evidence.
