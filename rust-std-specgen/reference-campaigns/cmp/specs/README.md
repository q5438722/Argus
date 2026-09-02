# Rust 1.96 `core::cmp` specifications

This is the mandatory module-level browsing package. Its counts are regenerated
from `inventory/core_cmp_exec_fn_inventory.json`, never used as acceptance
constants.

- `generated_cmp_specs.rs` contains one source-backed declaration for each of
  the 196 inventory identities not exactly bound by vstd and not
  blocked by the loaded float model.
- `all_cmp_specs.json` accounts for all 334 stable executable
  identities and binds every row to source and exact outcome equivalence.
- `cmp_shared_vocabulary.rs` contains only shared observations and narrow
  dependency models; target return branches remain in direct `ensures`.
- `existing_vstd/bindings.json` retains the 124 exact bindings:
  116 tracked-clean upstream bindings and
  8 frozen current-checkout
  bindings that are explicitly noncanonical.
- `../specification/float_model_boundary_audit.json` records the
  14 `f32`/`f64` comparison identities that cannot receive a
  sound target-bound contract while vstd's unconstrained bindings are loaded.
  They receive no strict coverage credit and require independent row approval
  as `genuinely_impossible`.

Proof harness generation remains unauthorized until the independent
specification review is accepted.
