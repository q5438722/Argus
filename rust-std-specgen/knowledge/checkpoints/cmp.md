# Goal

Regenerate source-backed Rust 1.96 specifications, implementation proofs, and
completeness proofs for exactly the stable executable APIs publicly reachable
through `core::cmp`, with inventory-derived accounting and canonical Reviewer
acceptance.

# Current State

The campaign is complete. The live inventory contains 334 unique identities:
124 exact-vstd bindings, 196 generated contracts, and 14 independently
approved `genuinely_impossible` float-model exceptions. The selected proof
closure contains the remaining 320 identities, with exactly 320 top-level
proof harnesses and 320 proof manifests.

The independent specification, implementation/completeness, and final
aggregate reviews all have `producer_role=reviewer` and `review.status=done`.
The final-review-required aggregate gate passed and materialized
`proof_inventory/final_delivery.json` with `status=accepted`, 320 selected and
actual-Verus-verified targets, and zero failed or pending targets.

# Current Evidence

- This L2 review ran
  `python3 tools/check_aggregate.py --require-final-review`. It completed with
  exit code zero, reported the 334-row inventory reconciliation as passing,
  and returned `status=passed`, `final_review_required=true`, and `errors=[]`.
- This L2 review ran
  `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q tools tests` followed by
  `PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q tests`.
  Compilation passed and pytest reported
  `206 passed, 13760 subtests passed in 323.22s`.
- The retained complete Verus run covers 320 targets and all 1,280 required
  implementation/completeness actual/no-verify commands; all passed, with zero
  failed or cancelled commands.
- The retained mutation run contains 740 syntax-valid probes across all nine
  required semantic categories; actual Verus rejected all 740 mutations.
- Direct closure checks found 320 unique inventory rows, 320 unique target
  directories, 320 top-level `proof_harnesses/` children, 320
  `proof_manifests/` children, and 320 evidence target children. Every harness
  colocates both proof sources and all required source, contract,
  transformation, dependency, trust, mutation, and evidence records.
- The final trust accounting reports zero target-level or
  completeness-level `external_body` boundaries and makes zero foundational
  end-to-end trust-free claims.
- The canonical Rust 1.96 checkout remains clean. The Verus checkout's current
  dirty path set matches the campaign's recorded pre-existing baseline.
- `specs/all_cmp_specs.json` and the specification review request retain the
  producer-stage `review_adjusted_accounting_complete=false` value from before
  independent approval. The canonical specification review separately
  approves every one of the 14 exception rows, and final accepted accounting
  gives those rows no strict specification, proof, or mutation credit.

# Acceptance Gap

None.

# Blockers

None.

# Retry Conditions

No retry is pending. Any intentional change to inventory, specifications,
proofs, trust records, mutations, evidence, or review artifacts invalidates
the accepted closure and requires rerunning the affected native and aggregate
gates.

# Open Questions

None.
