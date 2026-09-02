# `core::result` specification view

This directory is the complete Rust 1.96 module-level specification package.

- `generated_result_specs.rs` contains one direct, source-backed
  `assume_specification` binding for each of the 54 inventory rows not already
  covered exactly by loaded vstd.
- `result_shared_vocabulary.rs` contains only shared mathematical views,
  private iterator-state projections, a source-item consumption trace, and
  narrow generic dependency laws.
- `all_result_specs.json` is the inventory-ordered 64-row catalog.
  Every row carries its complete versioned `outcome_equivalence` binding.
- `result_helper_usage.json` classifies every shared helper and binds it to
  the generated contracts that use it.
- `result_outcome_equivalence.json` records a target-specific version,
  positive and negative observation witnesses, and exact equality for every
  row. For private iterator/formatter/hasher state and returned references,
  equality is exact componentwise equality over a named, source-backed
  semantic observation schema; unmodeled representation is outside the
  theorem domain rather than treated as a non-exact equivalent output.
- `../specgen/result_feedback_relation_capability.json` records that the
  canonical feedback runner has no selected-relation input. Canonical
  SAT/UNSAT/UNKNOWN results are therefore diagnostic only; every feedback
  surface explicitly classifies selected-relation evaluation as unsupported.
  Each `round_*` directory has a hash-bound
  `selected_relation_diagnostic_binding.json` that labels all canonical
  checker artifacts in that round as diagnostic-only.
- `specification_package_manifest.json` hashes the complete specification
  package and its reproducibility tooling.
- `existing_vstd/exact_result_references.json` references the 10 exact-vstd
  declarations by Rustdoc row, declaration ID, source span, and hash.

`Sum<Result<...>>`, `Product<Result<...>>`, and
`FromIterator<Result<...>>` bind the consumed source-item trace to the exact
input prefix ending at the first `Err`; consuming a later item violates the
contract. The per-target feedback manifest, seed, raw candidate, final
candidate, run manifest, and run binding all carry the applicable equivalence
version and the selected-relation capability classification.

The aggregate Verus run and per-target feedback are specification checks.
They are not implementation proofs, completeness proofs, or Reviewer
acceptance. `proof_harnesses/` remains absent until the canonical
inventory/specification Reviewer gate passes.
