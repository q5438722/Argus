# Rust 1.96 `alloc::collections::btree_map` specifications

This directory is the mandatory module-wide specification interface. The live
Rustdoc/source inventory contains **151** stable executable, source-owned API
rows: **13** exact declarations in accepted vstd and
**137** generated
contracts. Reference-`Extend` is a Reviewer-gated genuinely-impossible
exception after exhaustive exact-target attempts exposed Verus implied-outlives
shape limitations. `Index<&Q>` uses a cmp.rs-style unused early lifetime and a
target-specific inherited-`IndexSpec` membership bridge. Exact-vstd rows are
referenced and never redeclared.

- `generated_btree_map_specs.rs` contains all 137 generated contracts as direct
  `assume_specification` declarations.
- `../impossibility/extend_ref_outlives.json` is the row-level Reviewer packet
  for the reference-`Extend` implied-outlives signature.
- `btree_map_shared_vocabulary.rs` defines reusable ordered-map, borrowed-key,
  range, entry, iterator, callback, formatter/hasher, allocator, and frame
  vocabulary.
- `all_btree_map_specs.json` reconciles every inventory row to one disposition.
- `existing_vstd/references.json` freezes exact and narrow dependency sources.

The public aliases `alloc::collections::BTreeMap` and
`std::collections::BTreeMap` are duplicate paths, not additional rows.
`alloc::collections::btree_set` is outside this campaign.
