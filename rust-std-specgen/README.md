# Rust std specgen with Argus

This directory packages the reviewed Rust 1.96 standard-library
specification/proof-generation workflow used for the Result, Cmp, BTreeMap,
and BTreeSet campaigns. It is carried on top of the Argus repository.

## Contents

- `process/`: reviewed module-first specification, implementation-proof,
  completeness, mutation, trust-accounting, and Reviewer-gate process.
- `prompts/`: the four module campaign prompts used with Argus v0.1.1.
- `completeness-checker/`: the tracked `spec-determinism` source subset and
  the Rust std feedback adapter used by the campaigns.
- `knowledge/`: exported Rust std specgen wiki findings, research documents,
  final campaign checkpoints, and canonical final Reviewer decisions.
- `reference-campaigns/`: campaign-local generators, checkers, tests, generated
  module specifications, and delivery documentation. Large Verus evidence,
  handoffs, logs, and runtime databases are intentionally excluded.
- `examples/result/`: one complete per-target Result proof-harness example.

## Important distinction

Argus orchestrates Planner, Engineer, and Reviewer roles. The Rust-specific
inventory, specification, proof, mutation, and audit logic currently lives in
the reference campaign tools; it is not an Argus built-in command.

Argus reaches completeness/determinism checking through normal filesystem and
shell access. The campaign prompt gives the Engineer the checker and workspace
paths; the Engineer invokes `run_rust_std_spec_feedback.py`, which imports the
packaged `spec_determinism` Python package and runs Verus/Z3. Results are written
back into the campaign output tree for later Reviewer gates.

The reference tools retain module-specific paths and assumptions from their
original campaigns. Treat them as reviewed implementation references when
starting a new module, not as a path-independent one-command generator.

## Required external dependencies

- Rust 1.96 source and toolchain
- The matching Verus and Z3 builds
- A vstd checkout
- Python supported by the packaged Argus release

Do not commit Argus runtime state, credentials, copied Rust/vstd repositories,
or full proof evidence into this repository.

## Starting a new campaign

1. Install Argus from this repository root using the top-level README.
2. Copy the closest module under `reference-campaigns/` into a new isolated
   campaign directory.
3. Replace module-specific inventory, source, contract, and model adapters.
4. Adapt one of the prompts in `prompts/`.
5. Follow `process/rust-std-lib-specgen-process.md`.
6. Require canonical specification, proof/completeness, and final aggregate
   Reviewer handoffs before declaring completion.
