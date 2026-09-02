# Rust 1.96 `alloc::collections::btree_set` specifications

This is the mandatory module-wide specification interface. The live
Rustdoc/source derivation contains **92** stable executable,
BTreeSet-owned rows: **11** exact vstd references and
**81** generated contracts, with zero impossible and zero
pending rows.

- `generated_btree_set_specs.rs` has 81 direct
  `assume_specification` declarations, including separate source-owned
  `Extend::extend` bindings for owned and copied-reference inputs.
- `btree_set_shared_vocabulary.rs` defines the ordered-set, representative,
  range, iterator, set-operation, callback, formatter/hasher, and delegation
  vocabulary. Range predicates consume concrete `RangeBoundsSpec` endpoints;
  callback traces use `FnMut::requires`/`ensures` and explicit post-state
  steps; one adapter source state drives construction, `next`, size hints, and
  nested debug fields; and `ExtractIf` unwind/drop transitions retain the
  current set. Uninterpreted primitives expose only one-step effects or raw
  hidden state, and the audit rejects every unused, legacy-free-observation,
  or whole-operation primitive.
- `all_btree_set_specs.json` reconciles every stable row and records exact
  source, signature, contract, equivalence, and vstd bindings.
- `existing_vstd/references.json` records exact declarations without
  redeclaration.
- `verification/spec_determinism_harnesses/` contains one clause-derived
  determinism proof for every generated contract; generic-checker
  UNKNOWN/unsupported rows require current actual-Verus evidence here.
