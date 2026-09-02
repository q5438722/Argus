# Rust 1.96 std library module-first specgen process

This document defines the revised module-first specification-generation process for Rust 1.96 standard-library APIs and the post-specification implementation-conformance workflow. It replaces broad `justified-no-spec` completeness with specification completeness: every stable executable API in each selected module must have either an exact existing-vstd specification or a meaningful generated specification, except for target-specific rows that are independently reviewed and accepted as genuinely impossible to specify with the current model.

This is a process and review artifact. It is not authorization to edit canonical Rust or vstd checkouts, create implementation proofs, commit, publish, rewrite prior first-pass workspaces, or start a module campaign before the Phase 0 Reviewer gate accepts this process revision.

## Evidence base and negative lesson

| Evidence | Path / observed fact |
| --- | --- |
| Survey root | `/home/chentianyu/nanvix-rust-std-spec-survey` |
| Canonical Rust 1.96 source checkout | `/home/chentianyu/nanvix-rust-std-spec-survey/rust-1.96` |
| Canonical Verus/vstd checkout | `/home/chentianyu/nanvix-rust-std-spec-survey/verus/source/vstd` |
| Live survey tables used by module campaigns | `results/modules.csv`, `results/coverage.csv`, `results/uncovered_production_stable_apis.csv`, `results/vstd_contracts.csv` |
| Feedback determinism runner | `/home/chentianyu/nanvix-rust-std-spec-survey/run_rust_std_spec_feedback.py` |
| Prior reusable module templates | `nanvix-rust-std-slice-specgen-2026-08-11`, `nanvix-rust-std-vec-specgen-2026-08-11`, `nanvix-rust-std-str-specgen-2026-08-12` |
| Implementation-proof precedent | `/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-slice-vec-implproof-2026-08-12` |
| First-pass Array/Option/String campaigns, retained as negative lessons only | `nanvix-rust-std-array-specgen-2026-08-20`, `nanvix-rust-std-option-specgen-2026-08-20`, `nanvix-rust-std-string-specgen-2026-08-20` |
| Wiki pages used | `nanvix-rust-std-slice-module-evidence.md`, `nanvix-rust-std-vec-module-evidence.md`, `nanvix-rust-std-str-module-evidence.md`, `nanvix-rust-std-specgen-current-progress.md`, `nanvix-rust-std-specgen-module-priorities.md` |

The project wiki records the pre-module-first canonical tree as 2,121 target rows, 128 accepted semantic-gated candidates, 1,993 skip rows, zero missing/extra/duplicate rows, and zero empty skip rationales. That canonical rerun remains evidence and a seed source, but module acceptance must be made from isolated live inventory, exact-vstd subtraction, generated-spec evidence, target-specific impossibility review, typecheck, determinism, audits, and inventory-derived checker totals.

The first-pass Array/Option/String campaigns are explicitly not acceptance precedents. They showed that a campaign can appear complete while leaving many stable APIs in broad no-spec buckets:

| Module | First-pass workspace | Historical stable rows | Historical exact vstd | Historical generated | Historical no-spec | Negative lesson |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `core::array` | `/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-array-specgen-2026-08-20` | 12 | 1 | 5 | 6 | Revisit every no-spec row; add IntoIter state, ordered callbacks, and Clone-output relations where sound. |
| `core::option` | `/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-option-specgen-2026-08-20` | 85 | 24 | 5 | 56 | Revisit every no-spec row; shared Option branch, payload, iterator, callback, projection, trait-law, formatter/hasher, unsafe-domain, and conversion/Try vocabulary is required before claiming completion. |
| `alloc::string` | `/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-string-specgen-2026-08-20` | 47 | 14 | 5 | 28 | Revisit every no-spec row; byte-view, UTF validity/decoding/lossy, mutation, iterator/drain, raw-parts, allocator, ownership, and provenance models are required before claiming completion. |

These counts are historical baselines to correct, not hard-coded second-pass expectations. Every second-pass total must be rebuilt from live Rust 1.96 inventory and exact-vstd audit.

## Phase 0 Reviewer gate

No second-pass workspace creation, inventory generation, or candidate generation may start until an independent Reviewer accepts this document's completeness criteria and the exceptional last-resort treatment of impossible rows. After second-pass specification campaigns complete, no implementation-proof workspace creation, proof inventory, harness extraction, or module proof run may start until an independent Reviewer accepts this document's implementation-conformance section, artifact layout, audit rules, and module gate. If the Reviewer rejects or conditions either process, update this document first and resubmit before Phase 1.

## Acceptance model

The unit of accounting is a stable executable API row in the selected Rust 1.96 module. The row set includes inherent functions and methods, trait impl methods, public iterator/helper APIs surfaced in the inventory, and stable unsafe APIs. Stability must be derived from the main Rust `Stability` attribute; unstable const-stability alone must not exclude an otherwise stable API.

Each inventory row has exactly one final disposition:

| Disposition | Meaning | Counts as specification coverage? | Acceptance rule |
| --- | --- | --- | --- |
| `exact_vstd` | The row is already covered by an exact vstd declaration with matching target binding, receiver/reference shape, parameter shape, return shape, lifetimes, generics, bounds, and mutability. | Yes | Retain in the inventory and catalog, but do not redeclare locally. |
| `generated` | The campaign generated a meaningful `assume_specification` contract for the row, and the contract passed the required typecheck and audits. | Yes | Must be source-backed, non-vacuous, typechecked with Verus `--no-verify`, cataloged, and accompanied by per-target feedback evidence. |
| `genuinely_impossible` | The row cannot be meaningfully specified with the current project model after concrete target-specific attempts. | No | Exceptional last resort. Requires attempt evidence, named missing model/tool boundary, source rationale, alternatives tried, and independent Reviewer approval for that exact row. |
| `pending` | The row is uncovered, unattempted, failed, blocked, unsupported-as-no-spec, missing evidence, or still waiting for reviewer acceptance. | No | Any pending row fails module completion. |

Use these metrics in every checker and final report:

- `stable_inventory_total = exact_vstd + generated + genuinely_impossible + pending`.
- `specified_total = exact_vstd + generated`.
- `strict_specification_coverage = specified_total / stable_inventory_total`.
- `review_adjusted_accounting_complete = pending == 0` and every `genuinely_impossible` row has independent row-level approval.

The target outcome is 100% strict specification coverage. A module with approved `genuinely_impossible` rows may be review-accounted but must report less than 100% strict specification coverage and list the evidence path for each exception. Broad `justified-no-spec`, skipped-by-default, unsupported-without-attempt, and "future work" rows are pending, not complete.

## Non-vacuous generated specifications

A generated specification is meaningful only when it constrains source-observable behavior. It must have source-bound `requires` and/or `ensures` clauses that rule out trivial satisfaction and connect inputs, receiver state, outputs, mutation, callbacks, ownership, or errors as appropriate for the API.

Reject or demote to `pending` any generated row that:

1. Uses only `ensures true`, `requires false`, unconstrained `arbitrary()`, or an output relation that does not mention the source-observable result or state.
2. Hides the target semantics in a one-off uninterpreted helper without reviewed laws or source-backed definition.
3. Ignores required generic, lifetime, trait-bound, receiver, mutability, unsafe-domain, or ownership shape.
4. Skips an unsafe API solely because it is unsafe. Unsafe APIs require source-justified safety preconditions and ownership/provenance relations, or a reviewed `genuinely_impossible` exception after concrete attempts.
5. Strengthens or weakens a contract only to force a preferred determinism result rather than matching source semantics.

## Reviewed target-specific outcome equivalence

Completeness is relative to a reviewed target-specific outcome-equivalence function, not necessarily structural equality of every returned bit and final-state field. For target `T`, the checker obligation is:

```text
Spec_T(input, pre, output1, post1)
and Spec_T(input, pre, output2, post2)
implies Equivalent_T(input, pre, output1, post1, output2, post2)
```

The default `Equivalent_T` is exact equality over every principal source/doc-observable return and final-state component. It may be weakened only when Rust source and public documentation intentionally permit multiple outcomes, such as unstable ordering among comparator-equal elements or any matching index for a duplicate-key binary search.

Every non-exact equivalence function must:

1. Cite the exact implementation and documentation evidence that makes the distinction intentionally unspecified.
2. Preserve all documented distinctions outside that freedom, including result branch, error payload, panic/safety domain, mutation, ownership, callback obligations, and ordering that the API does guarantee.
3. Be target-specific and input-relative where necessary, and be reviewed as an equivalence relation rather than an ad hoc predicate that merely accepts the current counterexample.
4. Have positive and negative witnesses showing which distinct outcomes are equivalent and which are not.
5. Be versioned, independently reviewed, and recorded in the target catalog and feedback evidence.

Never place the selected output, final state, algorithm trace, or another equivalent encoding of the answer into `Equivalent_T` or a trust boundary merely to force uniqueness. Equivalence cannot rescue a vacuous or under-specified contract: relation-only placeholders, opaque output predicates, and omitted principal behavior require a source/doc-backed specification rewrite and semantic re-review.

For every SAT, UNKNOWN, or suspected nondeterministic target, triage in this order:

1. **Review the specification semantics.** Confirm that the contract is source-backed, non-vacuous, and covers the principal observable behavior.
2. **Review outcome equivalence.** If the distinct witnesses are both intentionally permitted by the implementation/docs, update `Equivalent_T` and rerun completeness without strengthening the contract to choose an implementation-specific outcome.
3. **Rewrite defective specifications.** If the witnesses are not equivalent, or the contract is opaque or omits principal behavior, regenerate the spec from implementation plus docs and repeat semantic review.
4. **Assess model/checker boundaries last.** Only after the spec and equivalence function pass review may the row be classified as missing a source-backed model, checker-unsupported, or solver-limited. A boundary schema alone is not transition semantics.

Reports must distinguish `exact-output deterministic` from `complete modulo reviewed equivalence`. For example, `sort_unstable` and duplicate-key `binary_search` may be complete under documented target-specific equivalence while remaining intentionally non-deterministic under exact output equality.

## Checker capability versus specification validity

Feedback determinism is evidence about the generated contract and the current checker, not a replacement for source review.

| Feedback taxonomy | Meaning | Catalog treatment |
| --- | --- | --- |
| `unsat` | The generated candidate reached UNSAT under the recorded target equivalence. | Count as generated only when typecheck, source-fidelity, anti-vacuity, helper, provenance, and equivalence audits also pass; separately record whether equality was exact or reviewed non-exact equivalence. |
| `unknown` | SMT/checker returned UNKNOWN after a real run. | First audit specification semantics and target equivalence. Preserve as UNKNOWN with per-target evidence only after those gates pass; do not weaken the spec solely to force UNSAT. |
| `unsupported/no-SMT` | The current determinism checker cannot encode the generated contract form. | Preserve as checker-capability evidence for a typechecked generated row. It is not proof that the spec is invalid. It cannot justify a no-spec row by itself. |
| `verus_error` | Verus failed while typechecking the generated candidate or feedback harness. | The row is pending until repaired or independently accepted as genuinely impossible. |
| `runner_crash` | The pipeline failed before producing target evidence. | Repair the runner/manifest and rerun; do not classify as target semantics. |
| `sat` | The checker found two outcomes not related by the currently selected equivalence. | Review whether the difference is documented nondeterminism requiring a corrected `Equivalent_T`; otherwise rewrite and re-review the spec. Only after both reviews may the row be sent for Reviewer-approved impossibility. |

Every generated row needs per-target feedback evidence even when the determinism status is UNKNOWN or unsupported. Unsupported checker capability must be reported separately from semantic validity and from anti-vacuity.

## Module-first workflow

Every module campaign must run in strict order and stop before moving to the next module unless the current module passes the revised specification-completeness checker and independent review. For the second pass, the order is `core::array`, then `core::option`, then `alloc::string`.

1. **Create an isolated second-pass workspace after Phase 0 review.** Use a clearly named directory under `/home/chentianyu/nanvix-rust-std-spec-survey`, such as `nanvix-rust-std-array-specgen-full-2026-08-21`, `nanvix-rust-std-option-specgen-full-2026-08-21`, and `nanvix-rust-std-string-specgen-full-2026-08-21`. Do not modify `/rust-1.96`, `/verus/source/vstd`, canonical rerun trees, or previous first-pass workspaces.
2. **Freeze provenance.** Copy only the module source files, directly required adjacent source files, relevant vstd baseline files, and current result CSVs into the workspace. Write `provenance/source_manifest.{csv,json}` with source path, copied path, role, timestamp, size, hash when available, and row-count facts needed to detect drift.
3. **Build a live stable executable inventory.** Prefer `results/modules.csv` and `results/coverage.csv` when the module is present. If absent, derive the inventory from Rust 1.96 rustdoc/source and record the derivation rule. Include trait impl methods and public iterator/helper APIs. Record excluded unstable or non-executable items separately.
4. **Subtract exact vstd coverage.** Match live rows against `results/vstd_contracts.csv` and copied vstd declarations. Exact-vstd rows remain inventory rows and count as specified, but are not regenerated.
5. **Produce an API/spec dependency graph and advisory generation order.** Group rows by shared views, helper vocabulary, callers/callees, trait laws, iterator state, callback traces, mutation/final-state relations, ownership/provenance, and checker-support needs. Use the graph to generate reusable vocabulary before target contracts.
6. **Build semantic views and shared vocabulary first.** Reuse audited Slice, Vec, Str, Option, Array, and vstd vocabulary when semantically identical. New helpers must be source-backed definitions, law-constrained abstractions, or explicit boundary abstractions reviewed before they support target specs.
7. **Attempt meaningful specs for every non-vstd stable target.** The attempt set is the live inventory minus exact-vstd rows, not a hand-picked subset. Include trait impl methods, iterator/helper public APIs, callbacks, unsafe APIs, format/hash effects, projections, conversions, and mutation APIs present in the inventory.
8. **Define and review target-specific outcome equivalence.** Start from exact equality. For documented nondeterminism, add only the smallest source/doc-backed equivalence relation needed to quotient the intentionally unspecified choice, with positive/negative witnesses and Reviewer evidence.
9. **Handle impossible rows only as exceptions.** Before marking a row `genuinely_impossible`, record target-specific generated-spec attempts, equivalence review, failed checker/typecheck/source-fidelity results, source rationale, missing model/tool boundary, and why weaker or relational specs would be dishonest. The row remains pending until independent Reviewer approval.
10. **Generate specs and harnesses.** Emit module generated specs, merged all-spec references, and a standalone Verus `--no-verify` harness for generated declarations. Binary-shaped standalone harnesses need `fn main() {}`. Harnesses that import `alloc::...` items need `extern crate alloc;`. Do not add duplicate `#![feature(rustc_attrs)]`.
11. **Typecheck before feedback acceptance.** A generated contract that does not pass Verus `--no-verify` is not accepted, regardless of how correct it reads.
12. **Run feedback determinism through the feedback pipeline.** Use `run_rust_std_spec_feedback.py`; do not pass raw `assume_specification` blocks directly to the determinism engine. Bind each run to the exact equivalence-function version used.
13. **Run required audits.** Source-binding, signature/generic-shape, source-fidelity, anti-vacuity, helper-usage, outcome-equivalence, provenance, artifact-integrity, and feedback-determinism audits must pass or produce explicit pending/impossible rows. Keep honest relational semantics for callbacks, nondeterministic observations, hidden state, mutation, and unsafe APIs.
14. **Run an inventory-derived completeness checker.** The checker must derive totals from the live inventory and fail on missing, extra, duplicate, unsupported-as-no-spec, unattempted uncovered, unapproved impossible, typecheck-failed generated, audit-failed generated, unreviewed equivalence, or pending rows. Hard-coded expected row totals are allowed only as historical annotations, never as pass criteria.
15. **Get independent review before advancing.** The module review must report exact-vstd, generated, genuinely impossible, pending, strict specification coverage percentage, exact-output versus equivalence-relative completeness, determinism taxonomy, and trust/model boundaries. Do not start the next module until the Reviewer accepts the current module.
16. **Capture validation once after final changes.** Compile task-owned Python, run Verus `--no-verify`, run the module checker, and capture each result-bearing shell command byte-faithfully in a sidecar log. Judge inner command return codes, not an outer pipeline or `tee` status.

## Post-specification implementation conformance workflow

Implementation conformance starts only after the relevant specification-completeness campaigns are accepted. Verus `--no-verify`, completeness checking, and feedback determinism checking are necessary specification gates, but they do not prove that the Rust implementation satisfies the selected contract. `--no-verify` only checks that declarations and harnesses typecheck without proof obligations; completeness checking only proves inventory/accounting coverage; determinism checking only evaluates the generated contract against the feedback harness and current solver support. None of those checks is an implementation proof.

An implementation proof means a fresh actual-Verus run over a source-shaped harness whose public target body is executable and bound to exactly one accepted contract and exact Rust 1.96 source item. The Slice/Vec campaign at `/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-slice-vec-implproof-2026-08-12` is the process precedent: it freezes inputs, binds inventory rows to contracts and source bodies, records source-to-Verus transformations and dependency boundaries per target, runs both `--no-verify` and actual Verus, and reports aggregate proof and trust-boundary metrics. Historical Slice/Vec details are precedent and evidence shape, not proof of any later module.

Use this module-neutral workflow after a module's selected contract set is accepted:

1. **Freeze proof inputs.** Create a new isolated implementation-proof workspace and preserve all first-pass, full second-pass, Rust, and vstd workspaces unchanged. Freeze the selected contract set, stable target inventory, exact Rust 1.96 source bodies for every target, adjacent private dependencies needed by those bodies, vstd version and copied/exact declarations, Verus/rustc/Z3 versions, command lines, timestamps, sizes, and SHA256 provenance. A frozen manifest must cover every selected target source reference and every source-adjacent dependency used by the harness; do not infer coverage from file counts alone.
2. **Build a proof inventory.** Bind every selected stable target to exactly one accepted contract row and exactly one exact Rust source item/span/hash. Distinguish `generated` provenance from `exact_vstd` provenance. Exact-vstd rows remain implementation-proof obligations and source-audit rows, but their contracts should be referenced through the loaded vstd instead of redeclared when duplicate specification loading would occur.
3. **Build the API/private-helper dependency graph.** Include public target calls, private helper calls, shared semantic views, type invariants, trait laws, iterator private state, callback traces, formatter/hasher effects, UTF/byte relations, ownership/raw-parts relations, allocator/provenance models, and unsafe-domain predicates. Use the graph for advisory proof order: semantic views and type invariants first, leaf callees before callers, foundational unsafe/representation helpers before wrappers, and strongly connected groups when cycles make a strict order unsound.
4. **Create one source-shaped harness per target.** The harness must keep the target body executable and preserve Rust control flow, normal-return behavior, mutation and final-frame behavior, callback ordering, panic and unsafe preconditions, ownership movement, drop order, and relevant private-helper calls. A whole target body marked `#[verifier::external_body]`, an assumed target implementation, or a body that simply restates the postcondition is not an implementation proof. If Verus cannot directly express a source feature, first attempt a source-shaped lowering; retain only the narrow lower-level boundary that remains necessary, and record failed attempts before keeping the boundary.
5. **Record every source-to-Verus adaptation.** For each target, keep a source review and transformation manifest that names all line/span changes, syntactic lowerings, ghost state, helper extractions, lifetime/ownership encodings, panic/unsafe-domain encodings, and dropped or reordered Rust constructs. The manifest must explain why each adaptation preserves source-observable behavior under the selected contract.
6. **Model or prove the private dependency closure.** For every target, either prove private dependencies in executable Verus or name and justify lower-level trust boundaries in the dependency-assumption manifest. Record per-target `external_body` functions, axioms, external type specs, uninterpreted models, trait/callback laws, allocator and raw-pointer/provenance assumptions, formatter/hasher effects, iterator private state, UTF validity, `MaybeUninit`, `Pin`/projection, unsafe-domain assumptions, and any other semantic boundary. The target-level proof result must distinguish a public target with no `external_body` from lower helper/model boundaries inside the harness.
7. **Run both Verus modes with durable evidence.** For every harness, run Verus `--no-verify` and a fresh actual Verus verification using the same frozen inputs. Retain command, stdout, stderr, exit code, Verus/rustc/Z3 version output, timing, and parsed verification-result evidence. A contract declaration that only typechecks, or a harness that passes only `--no-verify`, remains pending until actual Verus succeeds or an explicit unresolved proof failure is recorded.
8. **Audit proof soundness and artifact integrity.** Required audits cover exact contract binding, source hash, target signature and generic shape, source-body fidelity, dependency closure, anti-vacuity, proof evidence, artifact integrity, and trust boundaries. Any correction to accepted generated contract text requires separate source-backed specification review and regeneration evidence before implementation proof continues for affected targets.
9. **Aggregate module and combined proof metrics.** Report selected targets, generated-contract targets, exact-vstd targets, actual-Verus verified targets, failed targets, pending targets, target-level `external_body` count, harness-wide literal `external_body` surface, targets with no additional implementation/dependency boundary, and semantic trust-boundary categories. Keep module totals separate from combined totals.
10. **Use precise trust-boundary language.** "No additional implementation/dependency boundary" means the campaign did not add a target-local implementation or dependency boundary beyond the accepted contract, source adaptation, Verus/rustc/Z3, vstd, and reviewed models. It is not the same as foundational end-to-end trust-free. Never claim zero TCB merely because a harness contains no literal `external_body`.
11. **Gate every module and final delivery through independent review.** Do not advance from one implementation-proof module to the next until every selected target in the current module has a source/contract binding, an executable target-body harness, fresh actual-Verus success or an explicit unresolved proof failure, module aggregate/checker output, and independent Reviewer acceptance. Final delivery must also have independent Reviewer acceptance.
12. **Feed back actual proof lessons.** After implementation proofs complete or stop on reviewed unresolved failures, update this general process document with measured lessons, proof counts, trust-surface metrics, and any reusable workflow corrections while preserving the document's module-neutral purpose.

For the currently authorized Array/Option/String implementation-proof campaign, use a new isolated combined workspace such as `/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-array-option-string-implproof-2026-08-21`, treat the accepted full second-pass catalogs/specs as frozen contract inputs, and prove modules in this strict order:

| Module | Selected targets | Generated contracts | Exact-vstd contracts |
| --- | ---: | ---: | ---: |
| `core::array` | 12 | 11 | 1 |
| `core::option` | 85 | 59 | 26 |
| `alloc::string` | 47 | 33 | 14 |
| **Combined** | **144** | **103** | **41** |

The desired final state is 144/144 fresh actual-Verus verified targets with pending equal to zero. If any target remains failed or pending, report it plainly and do not claim implementation-proof completion for the campaign. Do not create a submission subset unless a separate operator request authorizes one.

Expected implementation-proof artifact layout:

```text
specs/
  README.md
  generated_<module>_specs.rs
  all_<module>_specs.json
  existing_vstd/
    <referenced vstd source files>
frozen_inputs/
  file_manifest.{csv,json}
  selected_contracts/
  rust_1_96_source/
  adjacent_private_dependencies/
  vstd/
proof_inventory/
  targets.{csv,json}
  dependency_graph.{dot,json}
  aggregate_coverage.{json,md}
  active_aggregate_certification.json
  final_aggregate_certification_<id>.json
proof_manifests/<target>/
  source_body.json
  transformation_manifest.json
  dependency_assumption_manifest.json
proof_harnesses/<target>/
  implementation_proof.rs
  completeness_proof.rs
  source_excerpt.rs
  contract_equivalence.json
  transformation_manifest.json
  dependency_assumptions.json
  trust_boundaries.json
  evidence/
    no_verify.{command,stdout,stderr,rc,json}
    actual_verus.{command,stdout,stderr,rc,json}
    versions.json
TRUST_BOUNDARY_AUDIT.md
```

The top-level `specs/` and `proof_harnesses/` directories are mandatory delivery
interfaces, not optional aliases hidden under verification or implementation
subtrees:

1. `specs/` must provide a module-wide browsing surface. It must identify the
   generated contract source, the exact-vstd source files, and a machine-readable
   all-target catalog that reconciles every stable API disposition. A reader must
   not need to search `verification/`, `specification/`, or provenance directories
   to find the accepted module contracts.
2. `proof_harnesses/` must contain exactly one directly discoverable child per
   selected API. Each child must colocate `implementation_proof.rs` and
   `completeness_proof.rs` with its source, contract, transformation, dependency,
   trust, and evidence records.
3. Existing validated storage may be exposed through stable read-only symbolic
   links when moving it would invalidate hashes. The standardized top-level paths
   must resolve correctly, must not create duplicate target accounting, and must
   be checked as part of final artifact-integrity validation.
4. A campaign is not deliverable merely because equivalent files exist elsewhere.
   Missing or broken `specs/` or `proof_harnesses/` interfaces block final
   acceptance.

The aggregate checker and certification must validate that this artifact layout is
complete, both mandatory top-level interfaces resolve, hashes match current files,
every selected target appears exactly once, no unapproved target-body assumption is
present, exact-vstd rows are referenced rather than duplicated when required,
evidence files correspond to the commands actually run, and trust-boundary counts
match the harness scan.

## Advisory dependency-aware generation order

Within a module, prefer this order unless the dependency graph shows a stronger reason to reorder:

1. Exact-vstd audit and inventory reconciliation.
2. Shared semantic views and vocabulary, including reused Slice, Vec, Str, Option, Array, and vstd models.
3. Pure observers and constructors whose specs establish reusable output/state relations.
4. Iterator remaining-state and helper public APIs.
5. Callback APIs with ordered stateful traces.
6. Mutation/final-state APIs and projections.
7. Trait impl methods, trait-law rows, formatting/hash effects, and conversions.
8. Unsafe, raw-parts, allocator, ownership, and provenance-sensitive APIs after their safety domain vocabulary exists.
9. Genuinely-impossible review packets only after all concrete target attempts and model alternatives are exhausted.

This order is advisory for generation efficiency, not an excuse to leave late groups uncovered.

## Required second-pass module adaptations

| Module | Required second-pass focus |
| --- | --- |
| `core::array` | Revisit all six first-pass no-spec rows. Build an `IntoIter` remaining-sequence/alive-range view, ordered stateful callback traces for `from_fn` and `map`, and an explicit Clone output relation for `repeat` if source-sound. |
| `core::option` | Revisit all 56 first-pass no-spec rows. Build shared Option payload/branch, iterator remaining-state, callback trace, trait-law, projection, formatter/hasher state-effect, and unsafe-domain vocabulary for iterator adapters, trait impl methods, formatting/hash effects, deref/pin projections, copied/cloned, callback combinators, `iter`/`iter_mut`, `zip`, `unzip`, `transpose`, unsafe methods, and conversion/Try rows. |
| `alloc::string` | Revisit all 28 first-pass no-spec rows. Add a byte-length/String byte-view model for `len`; UTF-8/UTF-16 validity, decoding, error, and lossy-replacement relations; mutation/final-state contracts for push/pop/insert/remove/truncate/split/range APIs; iterator/drain state; ownership/raw-parts/allocator/provenance contracts with safety and ownership relations. Reuse audited `core::str`, Slice, Vec, Option, and Array vocabulary when semantically identical. |

## Required artifact set

Each module workspace must have at least:

| Area | Required artifacts |
| --- | --- |
| Provenance | `provenance/source_manifest.{csv,json}` and canonical/prior-workspace preservation evidence |
| Inventory | `inventory/<module>_exec_fn_inventory.{csv,json}`, unstable/non-executable exclusions, exact-vstd audit, and inventory-derived totals |
| Dependency planning | API/spec dependency graph and advisory generation order |
| Specs | generated spec file, merged all-spec file, shared vocabulary, and exact-vstd reference map |
| Outcome equivalence | Per-target `Equivalent_T` definition/version, source/doc justification, exact-versus-non-exact classification, positive/negative witnesses, and independent review evidence |
| Harnesses | Verus generated-contract batch harness and any target-specific feedback harness artifacts |
| Feedback | `verification/evidence/<module>_feedback_determinism/latest_manifest.json`; active run `<run-id>/batch_summary.json` and `<run-id>/SUMMARY.md`; per-target `round_00/{round_result.json,candidate.json}`; add-spec `round_00/{synthetic_spec.rs,contract_harness.rs,typecheck_stdout.txt,typecheck_stderr.txt}`; supported determinism artifacts `round_00/{det_harness.rs,det_spec.json,det_stdout.txt,det_stderr.txt,verus_log/*}` |
| Audits | source-binding, signature/generic-shape, source-fidelity, anti-vacuity, helper-usage, outcome-equivalence, provenance, artifact-integrity, and feedback-determinism audits |
| Catalog | `<module>_spec_catalog.{csv,json}`, generated/exact/impossible/pending accounting, and module review markdown |
| Validation | Sidecar command captures for bootstrap, feedback, finalization, Verus `--no-verify`, and checker gates |

The reusable feedback layout uses `round_00/round_result.json` as the per-target source of truth and `batch_summary.json` plus `SUMMARY.md` for run-level aggregation. Do not require a per-target `summary.json` when this layout is used.

## Trust and model boundaries

The default for a hard target is not no-spec; it is to build or reuse a reviewed abstraction and attempt a meaningful relational spec. Common boundaries that need explicit model treatment are:

1. **Exact vstd ownership.** Existing vstd contracts are trusted inventory rows. Do not redeclare them locally or treat them as newly generated recoveries.
2. **Pointer/provenance and representation.** Raw pointer identity, metadata, layout, aliasing, allocation liveness, and provenance need reviewed representation and ownership models.
3. **Mutable reference returns.** Compare source-backed pre-return/current observable views where possible; do not make determinism equality depend on caller-controlled final returned-reference state.
4. **Iterator and adapter state.** Remaining-sequence, alive-range, drain, and private-state abstractions must exist before specifying adapter progress precisely.
5. **Closure/callback observations.** `FnMut`, comparators, key extraction, and stateful callbacks require ordered observation traces and relational effects.
6. **Clone/payload laws.** Generic clone or payload-view preservation is a law-constrained assumption, not an automatic Rust guarantee.
7. **Pattern/Searcher and parsing.** Pattern-dependent string behavior, repeated matching, parsing, and UTF-8 chunk state need explicit relations or reviewed impossibility evidence.
8. **Runtime/hidden state.** Filesystem, process, clock, networking, synchronization, and panic-info state need coherent module-wide state/effect models rather than per-method result functions.
9. **Unsafe APIs.** Unsafe-domain preconditions must be source-justified. Unsafe alone is not a reason to skip.
10. **Boundary/equivalence separation.** Trust boundaries describe external or hidden observations; outcome equivalence describes which API-permitted outcomes count as the same completeness result. Neither may encode the selected answer, and neither substitutes for a source-backed target transition relation.

## Operator/reviewer approval checklist

Before specification-generation Phase 1 starts:

1. The Reviewer accepts this document's specification-completeness definitions, inventory-derived checker requirements, non-vacuity rules, target-specific outcome-equivalence rules, and exceptional last-resort impossibility policy.
2. The Reviewer confirms that first-pass no-spec counts are negative lessons and not accepted completion criteria.

Before implementation-proof Phase 1 starts after accepted specification-completeness campaigns:

1. The Reviewer accepts this document's implementation-conformance workflow, including the rule that Verus `--no-verify`, completeness checking, and feedback determinism checking are not implementation proofs.
2. The Reviewer accepts the proof-input freeze, proof inventory, source-shaped harness, dependency-assumption, evidence-retention, audit, trust-boundary, aggregate-metric, and reusable artifact-layout requirements.
3. The Reviewer confirms that no implementation-proof workspace, inventory, harness, proof run, or module advancement has started before this document revision was accepted.

Before a specification-generation module is called complete:

1. The workspace is isolated and canonical Rust/vstd checkouts plus prior first-pass workspaces are unchanged.
2. The live stable executable inventory is complete for the selected module, including trait impl methods and public iterator/helper APIs.
3. Inventory rows reconcile as `stable_inventory_total = exact_vstd + generated + genuinely_impossible + pending`.
4. `specified_total`, `strict_specification_coverage`, `genuinely_impossible`, and `pending` are reported from inventory-derived totals.
5. Pending is zero; unsupported-as-no-spec and unattempted uncovered rows are checker failures.
6. Every generated contract is non-vacuous, source-backed, and passes Verus `--no-verify`.
7. Every target has a reviewed outcome-equivalence function, exact by default; every non-exact relation has source/doc evidence, positive/negative witnesses, a version, and independent acceptance.
8. Feedback determinism ran through `run_rust_std_spec_feedback.py`, is bound to the recorded equivalence version, and preserves SAT, UNSAT, UNKNOWN, unsupported/no-SMT, Verus error, and runner-crash taxonomy.
9. The report separates exact-output determinism from completeness modulo reviewed equivalence.
10. Checker capability limitations are reported separately from spec validity, source-fidelity, anti-vacuity, and equivalence review.
11. Exact-vstd rows are retained but not redeclared.
12. Every genuinely impossible row has target-specific attempt evidence and independent Reviewer approval.
13. Shared helper/vocabulary usage is audited and categorized.
14. Source-binding, signature/generic-shape, source-fidelity, anti-vacuity, helper-usage, outcome-equivalence, provenance, artifact-integrity, and feedback-determinism audits pass or leave explicit pending rows.
15. Result-bearing commands are captured in sidecars and the final report cites the captures actually used.
16. No implementation proofs, commits, pushes, publishing, Live View, canonical checkout edits, first-pass workspace edits, or unrelated maintenance occurred.

Before an implementation-proof module can advance:

1. The module was processed in strict campaign order, and the previous implementation-proof module, if any, has independent Reviewer acceptance.
2. Every selected target is bound to exactly one selected contract and one exact Rust 1.96 source item/span/hash, with generated and exact-vstd provenance distinguished.
3. Every selected target has a source-shaped executable harness, source excerpt, source-body manifest, transformation manifest, and dependency-assumption manifest.
4. No selected target is counted complete through a whole-target `external_body`, assumed target implementation, or postcondition-restatement harness.
5. Both Verus `--no-verify` and fresh actual Verus evidence exist for every harness, with command, stdout, stderr, exit code, version, timing, and parsed verification result retained.
6. Any unresolved proof failure is explicit, target-specific, source-backed, and accompanied by concrete failed lowering/proof attempts; such a target remains failed or pending for final completion accounting.
7. Exact contract binding, source hash, target signature/generic shape, source-body fidelity, dependency closure, anti-vacuity, proof evidence, artifact integrity, and trust-boundary audits pass or leave explicit failed/pending rows.
8. Module aggregate/checker output reports selected, generated, exact-vstd, actual-Verus verified, failed, pending, target-level `external_body`, harness-wide literal `external_body`, no-additional-boundary targets, and semantic trust categories.
9. The independent Reviewer accepts the module before any next module starts.

Before final implementation-proof delivery:

1. Array, Option, String, and combined actual-Verus proof counts are reported separately.
2. Failed and pending targets are reported plainly; completion is not claimed unless pending is zero and every selected target is freshly actual-Verus verified.
3. Direct and harness-wide `external_body` surface plus semantic trust-boundary categories are reported, with campaign-level no-additional-boundary separated from foundational end-to-end trust-free.
4. The general process document is updated with actual implementation-proof lessons and final metrics.
5. Independent Reviewer acceptance is obtained, no submission subset is created without separate operator authorization, and canonical Rust/vstd checkouts plus prior workspaces remain unchanged.

After all accepted second-pass campaigns and after each implementation-proof campaign finish, update this document again with actual lessons and final metrics while preserving its module-neutral process purpose.
