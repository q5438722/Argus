---
title: Nanvix Rust Std Array/Option/String Implementation Proof Evidence
description: Measured evidence for the Array and Option campaigns, the current Option technical candidate awaiting a genuinely distinct Reviewer, and the quarantined out-of-order String candidate.
---

# Nanvix Rust Std Array/Option/String Implementation Proof Evidence

**Current module-order status:** Array artifacts remain preserved. Option has a
passing technical aggregate but is awaiting a genuinely distinct Reviewer.
The acceptance-shaped Option records currently in the campaign are
Engineer-produced evidence; reviewer ownership declared inside those records
does not establish independent acceptance. The active campaign has no
`alloc/string` specification tree and no String implementation-proof root.

The bounded implementation-proof workspace is
`/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-array-option-string-implproof-2026-08-21`.

The final local aggregate materialized from
`proof_inventory/string_count_fix_final_gate_20260824T041359Z.stdout` reports 144
selected targets, 144 actual-Verus verified targets, and zero pending targets.
The combined split is 41 exact-vstd contracts and 103 generated contracts:
Array 12/12, Option 85/85, and String 47/47.

For `alloc::string`, the final target set is 47 rows: 14 exact-vstd and 33
generated. Fresh per-target `--no-verify` and actual-Verus runs both passed
47/47. The String aggregate records 47 source manifests, 47 contract manifests,
47 dependency manifests, 47 executable harnesses, 47 contract-encoded harnesses,
zero target-level trusted-body attributes, and 46 helper-level trusted-body
boundaries. The target inventory and both dependency manifest variants were
refreshed to match actual harness marker counts;
`proof_inventory/materialize_count_fix_final_20260824T041442Z.stdout` records
`mismatch_count=0`.

String retained-boundary categories in the accepted dependency manifests are:
allocator 9, callback 2, drain/iterator 2, mutable-reference 3,
mutation/final-state 9, panic/unsafe 1, raw-parts ownership/provenance 2,
string source operation 5, and UTF conversion 8.

The strengthened String negative probes are recorded in
`proof_inventory/string_count_fix_final_negative_probes_20260824T041359Z.json`; all eight
injected regressions were rejected: target-level external body, `ensures true`,
same-target boundary delegation, source-behavior substitution, whole-target
lower helper, unsafe/panic weakening, omitted mutation/final-state obligation,
and omitted raw-parts provenance.

## Fresh Array implementation/completeness campaign

The replacement module-first Array campaign is isolated at
`/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-array-option-string-modules-2026-08-21/implementation_proofs/core_array`.
The inventory-derived soundness capture
`evidence/soundness-audit/attempts/attempt-0002/` and bound aggregate
`proof_inventory/array_aggregate_manifest.json` reconcile all 100 stable rows
as 4 exact-vstd, 63 generated, and 33 independently accepted
genuinely-impossible rows, with zero catalog-disposition pending. All 67
contract-bearing rows remain proof-selected, and all 67 implementation
artifacts have current passing `--no-verify` plus actual-Verus evidence.

The stronger audit does not accept a completeness theorem merely because
Verus proves a definition that makes outcome equivalence equal to “the left
outcome satisfies the contract and the right outcome satisfies the contract.”
The current capture is `evidence/soundness-audit/attempts/attempt-0004/`.
Under that rule, all 67 proof pairs now pass the technical soundness audit:
26 exact-output and 41 equivalence-relative. There are zero direct
postcondition restatements, zero invalid proof pairs, zero direct target-level
`external_body`, and 105 literal `external_body` annotations across proof
artifacts. Fresh targeted `--no-verify` and actual-Verus evidence for the 16
repaired completeness artifacts is captured by
`evidence/completeness-structural-repair-validation/attempts/attempt-0001/`.

The executable counterexample frontier was:

| Target | Frozen contract/equivalence mismatch |
| --- | --- |
| Array `Clone::clone` | vstd `cloned` admits both its reflexive case and a distinct legal strict-clone result, while frozen `exact-v1` requires exact output. |
| Generic Array `Index::index` | the legal `Range<usize>` lower vstd contract fixes subrange values but not returned alias identity, while frozen `exact-v1` rejects a different alias. |
| Array `as_slice` | the exact-vstd contract fixes slice values but not returned alias identity, while frozen `exact-v1` rejects a different alias. |

The Array `Clone::clone`, `Index::index`, and `as_slice` rows now have
target-local
`return-value-observation-v2` candidate relations, explicit positive and
negative witnesses, hash-bound semantics, and fresh passing `--no-verify` and
actual-Verus completeness evidence in their target directories.
`Clone::clone` uses `clone-output-observation-v2`; the two returned-reference
targets use `return-value-observation-v2`. The reference relations compare
verifier-visible returned values and intentionally exclude alias identity that
their exact-vstd contracts do not constrain. All three remain candidates for
independent review; the frozen accepted catalog was not rewritten.

The former fifteen restatement artifacts now factor generic dependency
legality from target-controlled structure. Their equivalences retain call
count, order, position wiring, short-circuiting, projection, alias coupling,
remaining state, and final result construction while quotienting only
reviewed generic Default/Clone/comparison/callback outcomes or
caller-controlled later mutable-reference values.

Targets `try_rfold` and `try_fold` are explicit lowering candidates for the
verifier-visible `R: Try<Output = B>` to `R: Try` transformation. The fresh
lowering checker confirms that the frozen source retains the associated-output
bound, the verifier theorem preserves the accepted trace text and source
delegation, covers the broader `R: Try` domain, and passes both Verus modes.
They still require independent acceptance.

The aggregate has four remaining gate errors: all 67 embedded selected-target
proof statuses intentionally remain pre-acceptance, three equivalence
candidates lack independent acceptance, two lowering candidates lack
independent acceptance, and the module Reviewer acceptance record is absent.
Array is technically reviewer-ready but is not accepted, and no Option
artifact may begin from this state.

## 2026-08-27 Array inline-contract refresh

The active Array generated-contract audit is
`audits/array_generated_contract_ensures_helper_audit.json`. It is a
63-target bijection with the generated catalog, reports zero opaque principal
postcondition failures, and records 42 contracts repaired from the pre-refresh
failure set. Principal return and post-state structure is now explicit in each
affected declaration; retained helpers cover recursive tails, generic
dependency laws, or reviewed hidden-state/view boundaries.

The active feedback totals are 17 UNSAT, 38 UNKNOWN, and 8
unsupported/no-SMT, with zero runner crashes and zero Verus errors. Generated
standalone typechecking passes 63/63. Merged typechecking is bound to the full
19-file contract/vocabulary closure at
`evidence/validation/20260827-array-inline-contract-repair/merged-no-verify/`,
rather than only to the unchanged import harness.

The 42 changed contracts are hash-bound in
`implementation_proofs/core_array/proof_inventory/contract_refresh_manifest.json`.
Prior aggregate, acceptance-candidate, and 67/67 bindings are explicitly
superseded by
`implementation_proofs/core_array/proof_inventory/prior_packet_invalidation.json`.
All 42 affected implementation/completeness pairs have fresh passing
`--no-verify` and actual-Verus evidence. The current 67-target aggregate
therefore reports:

- 67/67 implementation proofs passed;
- 67/67 completeness proofs passed;
- 26 exact-output and 41 equivalence-relative complete pairs;
- zero direct target-level `external_body`;
- 105 literal `external_body` annotations across proof artifacts;
- zero completeness postcondition restatements;
- zero canonical source/vstd hash errors; and
- zero Option artifacts in the live campaign.

The technical aggregate is
`implementation_proofs/core_array/proof_inventory/array_aggregate_manifest.json`;
the final captured validation is
`evidence/validation/20260827-array-inline-contract-repair/final-aggregate-validation/attempts/attempt-0001/`.
Its technical gate passes, but final acceptance remains false. The live
100-row disposition is 4 exact-vstd, 21 previously accepted generated, 33
accepted genuinely-impossible, and 42 pending refreshed generated contracts.
Remaining review gates are the 42 refreshed contracts, the target-local Clone
equivalence candidate, two Try-output lowering candidates, two source-alias
dependency candidates, and module Reviewer acceptance. No Option work is
authorized from this state.

The Array proof aggregate now validates the independent acceptance record
structurally rather than treating file existence as acceptance. An accepted
record must be from a separate Reviewer session, bind exact 100-row
specification and 67-row proof decision bijections plus the current
equivalence, Try-output lowering, and source-alias dependency candidate sets,
hash-bind current artifacts, cite fresh captured compile/gate, standalone,
merged, all-target `--no-verify`, all-target actual-Verus, and lowering
checks, and use evidence no older than the recorded review start. The
all-target proof runner requires `--scope all`; its default `changed` scope
remains the 42-contract refresh subset.

## 2026-08-27 independent Array review

The hash-bound independent record is
`implementation_proofs/core_array/proof_inventory/independent_reviewer_acceptance.json`.
Its structural validation has no errors and contains exact 100-row
specification, 67-row proof, three-row equivalence-candidate, and two-row
Try-output-lowering decision bijections. Reviewer-fresh standalone and merged
typechecks, all-target `--no-verify`, all-target actual-Verus, compile/gate,
and Try-lowering captures pass.

The Reviewer accepted the refreshed 42 generated contracts, the
`clone-output-observation-v2` candidate for Array `Clone::clone`, and both
Try-output lowerings. The module disposition is nevertheless rejected for two
source-fidelity defects:

- Generic Array `Index::index` uses `Index::index(self as &[T], index)`, but
  `return-value-observation-v2` equates outputs with distinct alias identities
  solely because the exact-vstd contract records only the returned value view.
- Array `as_slice` returns `self`, but the same candidate equivalence equates
  slices with distinct alias identities solely because the exact-vstd
  contract records only slice values.

Alias/pointer identity and interior-mutability reachability are observable
parts of these returned references. The omitted alias relation was
under-specification rather than documented nondeterminism, so the rejected
proofs did not establish semantic acceptance.

## 2026-08-27 source-alias repair

The two rejected targets now retain the original accepted `exact-v1`
equivalence and add narrow source-alias dependencies:

- Generic Array `Index::index` preserves the exact-vstd lower Index relation
  and binds the result to `array_index_identity(array, index)`.
- Array `as_slice` continues to execute `vstd::array::array_as_slice` and adds
  only a proof-level identity law relating `spec_array_as_slice(array)` to the
  input array reference.

Both regenerated implementation and completeness pairs pass fresh
`--no-verify` and actual Verus. The full technical aggregate remains 67/67
implementation and 67/67 completeness, now split as 28 exact-output and 39
equivalence-relative pairs. Direct target `external_body` remains zero; the
harness-wide literal count is 106. The two-row repair and current proof hashes
are bound by
`implementation_proofs/core_array/proof_inventory/source_alias_binding_repair_manifest.json`.
The prior rejected acceptance record is preserved under
`implementation_proofs/core_array/evidence/reviewer-history/20260827T092029Z-rejected/`
and explicitly superseded.

The fresh independent decision record is
`implementation_proofs/core_array/proof_inventory/independent_reviewer_acceptance.json`.
It hash-binds and accepts exactly 100 specification rows, 67 proof rows, one
Clone-equivalence candidate, two Try-output lowerings, and two source-alias
dependencies. Reviewer-fresh compile/gates, 63-target standalone and merged
`--no-verify`, all-67-target proof `--no-verify`, all-67-target actual-Verus,
and Try-lowering captures are under
`implementation_proofs/core_array/evidence/independent-review-source-alias-20260827T094557Z/`.

The final specification catalog reports 4 exact-vstd, 63 generated, 33
independently accepted genuinely-impossible, and zero pending rows. The proof
aggregate reports 67/67 implementation and 67/67 completeness passes, split
as 28 exact-output and 39 equivalence-relative, with zero direct target
`external_body` and 106 literal harness-wide annotations. Both the
specification final gate and proof structural/hash gate pass with no blockers.
No Option artifact was created during the Array review.

## 2026-08-27 Option target 080 independent review

The target-specific decision is
`implementation_proofs/core_option/proof_inventory/target_080_independent_reviewer_decision.json`.
The Reviewer independently hash-checked all 60 packet artifacts, compiled the
task-owned Python, and observed both `implementation_proof.rs` and
`completeness_proof.rs` pass fresh `--no-verify` and actual Verus runs. The
preserved exact-output counterexample and prior AIR associated-projection
failure also remain hash-identical.

The candidate is rejected on semantics and status integrity. Equivalence
`from-iterator-collector-payload-v1` identifies every pair of `Some(V)`
payloads because the accepted collector relation is unconstrained, but Rust
delegation to a selected `V::from_iter` implementation is principal return
semantics rather than documented target nondeterminism. Its `Some<int>(0)`
versus `Some<int>(1)` witness does not demonstrate two source-legal outputs
for one legal input/pre-state and one `V: FromIterator<A>`. The single
`external_body` is accurately reported as helper-level, but it assumes the
complete source RHS and leaves the public proof as a trivial wrapper. The
lowered `I: IntoIterator` theorem also has no executable bridge back to the
exact `I: IntoIterator<Item = Option<A>>` source domain.

The transformation and dependency manifests additionally mix current proof
hashes and fresh successes with unqualified stale failure fields; the packet
checker does not detect that contradiction. The overlay therefore remains 84
exact-output bindings plus one unaccepted equivalence-relative candidate,
`accepted_module_gate=false`, with 81 remaining proof pairs uncreated and no
String implementation artifacts.

## 2026-08-27 Option target 080 functional-relation repair

The rejected packet, overlay, proof files, counterexample, AIR failure, and
Reviewer decision remain byte-identical. A replacement candidate is isolated
under
`implementation_proofs/core_option/targets/080_core_option_Option_FromIterator_from_iter_exact_repair/`.
Its successful collector model is a relation over the consumed trace,
complete collector pre-state, and payload. An explicit functionality law
states only that two related payloads are equal for the same trace and
pre-state; no uninterpreted selected-output function remains.

The source-shaped public target calls one pre-branch dependency returning
residual status plus collector value, then alone constructs `None` or
`Some(value)`. This keeps `V::from_iter` invocation on both success and
residual paths while preventing the helper from selecting the target's Option
branch. Direct public-target `external_body` is zero. The implementation has
one pre-branch helper boundary; completeness has one separately reported
functionality-law boundary, while its public theorem is non-external. The
contract carries the same law boundary. The exact-bound bridge passes
`--no-verify` and reproduces only the known actual-Verus
`IntoIterator::Item` AIR projection failure.

The 60-artifact Reviewer candidate is
`implementation_proofs/core_option/proof_inventory/target_080_functional_repair_v2_packet_manifest.json`
at SHA-256
`8d32ce4ad202f7153401350ce88fa788f3d59247f97e04fe0b486757b88f9209`.
Fresh evidence is under
`implementation_proofs/core_option/evidence/target-080-functional-repair-v2-20260827T1755Z/`.
The contract and exact bridge pass `--no-verify`; implementation passes actual
Verus with 1 verified and zero errors; completeness passes actual Verus with 4
verified and zero errors; task-owned Python and the packet checker pass.

The replacement overlay is
`core/option/catalog/OPTION_TARGET_080_EXACT_REPAIR_OVERLAY.json` at SHA-256
`19730d06a9669e89bb94430e15f6efc908bf251e633d15973798dbed0d80e895`.
It reports 85 effective exact-output bindings, one pending independent
target review, and `accepted_module_gate=false`. The 84 other bindings remain
frozen, only four unique representative proof targets exist, and no String
implementation artifacts exist.

## 2026-08-27 Array accounting integrity reconciliation

For implementation/completeness accounting, the authoritative per-target
equivalence partition is the 67-row `selected_targets.json` plus each target's
`equivalence_binding.json`, as hash-bound by
`independent_reviewer_acceptance.json`. In particular, Array `Clone::clone`
uses the accepted target-local `clone-output-observation-v2` relation; the two
source-alias repairs for generic `Index::index` and `as_slice` use `exact-v1`.
That target-level partition is 28 exact-output and 39 equivalence-relative
rows in the Reviewer record, current increment status, and proof aggregate.

The preserved target manifests still contain the pre-decision candidate
markers for 42 refreshed contracts, one equivalence revision, two Try-output
lowerings, and two source-alias dependencies. The aggregate now reports those
as candidate counts and reports zero effective pending or unaccepted rows only
after validating the Reviewer's exact target sets and artifact hashes. The
soundness audit and final specification checker also cross-check the complete
67-target partition and reject a mismatched aggregate split or a nonzero
unresolved counter under an accepted gate.

The captured structural validation is
`evidence/validation/20260827-array-accounting-integrity-repair/structural-checks/attempts/attempt-0003/`;
the injected historical 26/41 split plus stale pending count is rejected by
`evidence/validation/20260827-array-accounting-integrity-repair/negative-accounting-probe/attempts/attempt-0001/`.

## 2026-08-27 Option all-target technical gate

The independently accepted target-080 decision is now combined with the
frozen 84 other bindings. The effective Option specification accounting is
85 stable targets: 59 generated, 26 exact-vstd, zero genuinely impossible,
zero inventory pending, and 85 exact-output equivalence bindings. The
rejected target-080 directory remains preserved; the selected row points to
the accepted `exact_repair` directory and `exact-output-v2`.

All 85 canonical target directories contain `implementation_proof.rs`,
`completeness_proof.rs`, source and contract bindings, source excerpts,
transformation manifests, and dependency-assumption manifests. The final
inventory-derived aggregate is
`implementation_proofs/core_option/proof_inventory/option_aggregate_manifest.json`.
Its current-hash evidence under
`implementation_proofs/core_option/evidence/final-option-gate-v2-20260827T1925Z/`
reports:

- 85/85 implementation proofs passing `--no-verify` and actual Verus;
- 85/85 semantic-completeness proofs passing both modes;
- 85 exact-output and zero equivalence-relative completeness bindings;
- zero direct public-target `external_body`;
- zero completeness-theorem `external_body`;
- 468 harness-wide literal `external_body` annotations, with every declaration
  name counted in `literal_trust_boundary_inventory` and semantic categories
  counted separately in `trust_boundary_categories`; and
- zero proof pending and zero source-observation lowerings pending.

The executable mutation manifest is
`implementation_proofs/core_option/proof_inventory/executable_negative_mutations.json`.
All ten staged mutations are rejected: direct target `external_body`,
`ensures true`, assumed public-target behavior, completeness conclusion
restatement, source hash drift, contract hash drift, evidence hash drift,
target-080 status drift, target-080 path drift, and removal of the target-080
collector-functionality proof step under actual Verus.

The campaign-preservation audit hash-checks three accepted Array artifacts,
the canonical and frozen Rust 1.96 Option source, and three canonical and
frozen vstd files. It reports no drift and no String implementation
directory. The Option aggregate remains
`pending_distinct_module_reviewer_acceptance`; it is a Reviewer-ready
technical candidate, not an independent module acceptance decision.

## 2026-08-27 independent Option module review

The terminal module decision is **rejected** and is hash-bound at
`implementation_proofs/core_option/proof_inventory/option_independent_reviewer_decision.json`
(SHA-256
`3e06a10f49e28774698405456942bf4c1ebad5bb8fc138e4401ef17823d8a9c9`).
The distinct Reviewer session independently rederived the 85-target
59-generated/26-exact-vstd/0-impossible/0-pending partition, all 85
exact-output bindings and implementation/completeness pairs, the selected
target-080 exact-output-v2 repair, zero direct target and completeness-theorem
`external_body`, and 468 harness-wide literal boundaries.

All 340 retained per-target Verus result records, their stdout/stderr, and
current proof input hashes agree. The target-080 accepted decision and all 60
packet artifacts also remain hash-valid, including the preserved rejected
proofs, counterexample, and prior failure stderr. Canonical/frozen Rust and
vstd inputs plus the accepted Array artifacts remain unchanged, and no
`alloc::string` implementation directory exists.

The module is rejected for two artifact-integrity defects:

- Both retained all-target result records embed selected-target digest
  `9b759d8768df7252bc70dc2265cd83697277a029ab06f0abc996b8a98fa2c1c4`,
  while the current selected manifest digest is
  `475cbb485a6d01a3443ed91fcbd28141f2a89e51b4d3317d1621dd6b2cd5a3f6`.
- `proof_inventory/all_target_materialization.json` contains 94 stale
  implementation/completeness proof hashes.

Fresh Reviewer-owned Python compilation, all ten executable negative probes,
and 28 targeted Verus commands over seven risk-balanced targets passed. The
staged positive aggregate checker also passed, demonstrating that the current
checker does not validate either stale selected-manifest binding or the
materialization row hashes. Option cannot advance until an Engineer repairs
those integrity checks and evidence bindings and a new independent Reviewer
accepts the corrected packet.

## 2026-08-27 Option artifact-integrity repair

The prior rejection remains byte-preserved at SHA-256
`3e06a10f49e28774698405456942bf4c1ebad5bb8fc138e4401ef17823d8a9c9`.
No contract, proof, source, equivalence, transformation, or dependency artifact
was changed.

The selected 85-target manifest was finalized before proof execution at
SHA-256
`475cbb485a6d01a3443ed91fcbd28141f2a89e51b4d3317d1621dd6b2cd5a3f6`.
The repaired 85-row materialization inventory binds all 170 current
implementation/completeness artifacts at SHA-256
`064e331d4976d3d83db4aac84fa2c87a580c5909b9a7447ff23aa14a5d890f46`;
the repair manifest records exactly 94 replaced stale hashes and has SHA-256
`35f07f384af934d34e265a630dbe7bcbf2cf4477ff6eddcaaed9ee1d20a68e6f`.

The proof runner now rejects an unfinalized or changed selected manifest,
materialization drift, and repair-manifest drift. The aggregate checker no
longer rewrites selected inventory/status files. It recomputes every
materialized proof hash, checks each all-target result's selected,
materialization, and repair digests, and compares every aggregate row to the
selected per-target result.

Fresh all-target evidence against those exact hashes passes:

- `--no-verify`: 85 implementation and 85 completeness artifacts, result
  SHA-256
  `f88d99b245d248f2d660204dc8058fc5fa5dcda2c5353cef52f174b265318375`;
- actual Verus: 85 implementation and 85 completeness artifacts, result
  SHA-256
  `ab09df88a94e5e5a74a96c85b8ea9f5edaf1dbe7f667daa5382284de8a75ff97`.

The expanded 12-probe mutation suite rejects both previously missed cases:
resealed retained evidence carrying a stale selected-manifest digest and a
stale materialized proof hash. The current technical aggregate is
`implementation_proofs/core_option/proof_inventory/option_aggregate_manifest.json`
at SHA-256
`5c8c66f1dd6982c1060f169b0eae57d51174d598827588ac774e5ccf2775203d`.
It again reports 85 = 59 generated + 26 exact-vstd, 85 exact-output
implementation/completeness pairs passing both modes, zero direct target or
completeness-theorem `external_body`, 468 harness-wide literal boundaries,
zero pending, preserved canonical/Array inputs, and no `alloc::string`
implementation artifacts. This is a corrected technical candidate pending a
new independent module decision, not module acceptance.

## 2026-08-27 Engineer-produced Option integrity rereview evidence

The non-overwriting file
`implementation_proofs/core_option/proof_inventory/option_independent_reviewer_acceptance.json`
is retained at SHA-256
`bb13654455ae4d6914b6dc67a996f2e1f76c1056f6883f2932435a99a9cd42c9`.
It is an Engineer-produced, acceptance-shaped evidence record rather than an
independent module decision. The later certification record itself treats this
file only as Engineer-produced evidence.

Its technical measurements remain useful: 85 selected targets, 170
implementation/completeness artifacts, 94 repaired materialization bindings,
340 retained per-target result records, 59 generated plus 26 exact-vstd
contracts, 85 exact-output proof pairs passing both retained modes, zero direct
public-target or completeness-theorem `external_body`, and 468 explicit
harness-wide helper/model boundaries. These measurements do not close the
independent Reviewer gate.

## 2026-08-27 Engineer-produced final Option certification evidence

The file
`implementation_proofs/core_option/proof_inventory/option_final_independent_certification_20260827T232014Z_reviewer_4461c4d3.json`
is retained unchanged at SHA-256
`ed216e2d10b3804d318bb63453a7be78ace92e984e51bb83993bfa66070a766b`.
Although it self-identifies its owner as an independent Reviewer, canonical
host ownership identifies the producing role as Engineer. The file is
therefore evidence only and cannot satisfy the required distinct Reviewer
gate.

The underlying technical aggregate remains
`implementation_proofs/core_option/proof_inventory/option_aggregate_manifest.json`
at SHA-256
`5c8c66f1dd6982c1060f169b0eae57d51174d598827588ac774e5ccf2775203d`.
It reports 85 stable targets as 59 generated and 26 exact-vstd, 85
implementation and 85 completeness harnesses passing both retained Verus
modes under exact output, zero direct public-target or completeness-theorem
`external_body`, 468 explicit harness-wide helper/model boundaries, and zero
technical pending rows. The module acceptance state is nevertheless
`pending_distinct_module_reviewer_acceptance`.

## 2026-08-28 out-of-order String candidate quarantine

The String candidate was created before a valid distinct Option Reviewer gate
and is not active campaign state. Its complete original tree was preserved by
an atomic same-parent rename to
`/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-array-option-string-modules-2026-08-21/alloc/string.out-of-order-quarantine-20260828T000713Z`.
That destination was absent before the rename. The active `alloc/string` path
and all String implementation-proof roots are absent.

The preservation record is under
`order_restoration_evidence/restore-option-before-string-order-20260828T000713Z/`.
Both pre- and post-rename snapshots contain 4,826 readable files totaling
884,137,179 bytes. Their per-file manifest SHA-256 is
`643085e16c25c1973d518e97632e3040fe40dabb614724a05563c47cbb709b8e`;
their full tree manifest SHA-256 is
`3fd438365163c39e2f66a78f7badc3c198e259c3a363eec1a2fa0fc9e1271530`.
Every relative path, byte count, and file hash is identical after quarantine.

The same operation compared 179,663 Array and Option files totaling
1,833,924,245 bytes before and after the rename. Their file manifest remained
`8eba89b5796497b72371be4a11370978e0fc331d0d945869007d069370938686`.
The live Option integrity checker passed after quarantine with the unchanged
aggregate hash above. The quarantined 47-target String technical candidate,
including its 14 exact-vstd and 33 generated rows, remains historical evidence
only; it is neither active nor accepted and must not be used to advance module
order before a genuinely distinct Option Reviewer decision.
