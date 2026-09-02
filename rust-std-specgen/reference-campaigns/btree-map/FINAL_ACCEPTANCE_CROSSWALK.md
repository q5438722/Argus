# Final acceptance crosswalk

The Rust 1.96 inventory reconciles **151 = 13 exact-vstd + 137 generated +
1 Reviewer-approved impossible + 0 pending**. The **150 selected APIs** each
have source/hash binding, executable implementation lowering, relational
completeness proof, a nonempty set of target-specific source-shaped
postcondition mutants, separate no-verify and actual-Verus evidence,
dependency/trust accounting, and artifact hashes. The matrix rejects all
**271** target-bound mutant functions
across **270** byte-distinct
verification artifacts (the `BTreeMap::new` and `Default::default` bodies are
intentionally identical).

The mutation gate covers every accepted public target postcondition on an
independent copy of the source-shaped implementation body. Operation-local
`external_body` contracts remain explicit trust-accounting surfaces and are
not mislabeled as executable implementation mutants.

Inventory/specification review is `reviews/inventory_specification.json`;
proof-artifact review is `reviews/proof_completeness.json`; final dynamic review
is `reviews/final_aggregate.json`.
