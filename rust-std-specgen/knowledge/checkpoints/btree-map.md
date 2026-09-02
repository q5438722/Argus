# Goal

Regenerate Rust 1.96 Verus/vstd specifications, source-shaped implementation
proofs, and relational completeness proofs for exactly
`alloc::collections::btree_map`, with inventory-derived accounting and no
BTreeSet or unrelated-module artifacts.

# Current State

The campaign is complete and its active aggregate certification is
`accepted`. The independent inventory/specification, proof/completeness, and
final-aggregate records all have `producer_role=reviewer`,
`independent=true`, and `review.status=done`.

The inventory remains 151 stable rows: 13 exact-vstd, 137 generated, one
independently accepted impossible reference-`Extend` target, and zero pending.
All 150 selected targets have exactly one directly discoverable proof-harness
directory. Each directory contains the mandatory ten colocated source,
implementation, completeness, mutation, contract/equivalence,
transformation, dependency, and trust files plus separate evidence files.

# Established Evidence

- Reviewer-round build:
  `../verus/source/target-verus/release/verus --crate-type=lib
  --triggers-mode silent --no-verify specs/generated_btree_map_specs.rs`
  exited 0 with no diagnostics.
- Reviewer-round tests:
  `PYTHONPATH=. ../.venv/bin/python -m pytest -q tests` reported
  `36 passed in 1.93s`.
- Reviewer-round aggregate verification:
  `PYTHONPATH=. ../.venv/bin/python scripts/verify_campaign.py` exited 0 and
  reported 151 stable rows, 150 selected proofs, 13 exact-vstd, 137 generated,
  one reviewed impossible target, and zero pending.
- The current post-authorization matrix contains 751 completed trials and zero
  failed records: one generated-spec no-verify trial plus, for each of 150
  targets, implementation no-verify, implementation actual-Verus,
  completeness no-verify, completeness actual-Verus, and mutation
  actual-Verus.
- Matrix results report 150 verified implementation proofs, 150 verified
  completeness proofs, and 271 rejected mutant functions.
- Feedback preserves the raw `not_run=7`, `unknown=73`, `unsat=57` taxonomy;
  the reconciliation resolves all 80 checker-limitation rows through
  actual-Verus completeness evidence, with zero unresolved rows.
- Trust accounting reports zero target-level `external_body` boundaries, 336
  operation-local boundaries, 12 documented leaf representation exceptions,
  6,522 literal whole-harness markers, and explicit non-zero-TCB
  qualification.
- Scoped status checks are clean for the canonical Rust collections sources
  and the referenced vstd BTree/comparison files.

# Superseded Evidence

- r15 proof evidence is pre-authorization diagnostic evidence.
- r16 used stale generic mutation artifacts.
- r17 and r18 are superseded intermediate mutation runs.
- The pre-r19 `reviews/final_aggregate.json` claiming 450 mutants has been
  replaced by the current r19-bound independent review.
- Any proof/completeness review, final-aggregate review, certification, or
  rendered aggregate predating the current r19 bindings is stale.

# Blockers and Open Questions

- No acceptance blocker or unresolved evidence row remains.
- The entire campaign directory is currently untracked by the parent Git
  repository (`tracked_files=0`, with the directory reported as untracked).
  This does not invalidate direct content or test evidence, but the worktree is
  worth preserving as a private local restore point.
- Per-target evidence sidecars do not carry the matrix run identifier. Current
  linkage is provided by the matrix result set, timestamps, source paths, and
  phase-order record rather than a direct sidecar field.
- Non-blocking presentation issue: `aggregate_coverage.json` retains the raw
  pre-reconciliation feedback resolution count, while the authoritative
  reconciliation and feedback-determinism audit record all 80 resolved rows.

# Relevant Files

- Campaign:
  `/home/chentianyu/nanvix-rust-std-spec-survey/nanvix-rust-std-btree-map-regeneration-20260901-v011-8798`
- Inventory: `inventory/btree_map_exec_fn_inventory.json`
- Generated specifications: `specs/generated_btree_map_specs.rs`
- Proof harnesses: `proof_harnesses/`
- Matrix results:
  `verification/evidence/verus_matrix/source-shaped-r19-public-mutations-post-review/`
- Feedback reconciliation:
  `verification/evidence/btree_map_feedback_determinism/source-shaped-r15/reconciliation.json`
- Phase-order archive: `verification/premature_phase_ordering.json`
- Inventory review: `reviews/inventory_specification.json`
- Proof/completeness review: `reviews/proof_completeness.json`
- Final aggregate review: `reviews/final_aggregate.json`
- Active certification:
  `proof_inventory/active_aggregate_certification.json`
- Artifact integrity audit:
  `verification/audits/artifact_integrity_audit.json`
- Static verifier: `scripts/verify_campaign.py`
- Finalizer: `scripts/finalize_campaign.py`
- Regression tests: `tests/test_campaign.py`
- Trust audit: `TRUST_BOUNDARY_AUDIT.md`

# Next Action

No further campaign action is required. Rerun the affected gates if campaign
content changes.
