# Package manifest

## Argus baseline

- The package is added as `rust-std-specgen/` on top of the destination Argus
  repository's `main` branch.
- The campaigns were originally executed with Argus version 0.1.1 at commit
  `f6d89c8c49e13f09c2af1fed3f80968081d1642e`.
- Local uncommitted changes, Argus runtime state, and virtual environments are
  excluded.

## Included campaign material

For Result, Cmp, BTreeMap, and BTreeSet:

- generation/checking Python tools
- task-native tests
- top-level generated `specs/`
- delivery and trust-boundary documentation when present

The package also includes:

- the source-only `spec-determinism` engine subset used by Rust std feedback
- the Rust std feedback adapter with a repository-relative checker import
- 16 Rust std specgen wiki pages
- the two reviewed research/process documents
- final checkpoints and canonical final Reviewer handoffs for four modules

One Result target is included under `examples/result/` with:

- accepted contract
- Rust source excerpt
- implementation proof
- completeness proof
- transformation and dependency manifests
- trust accounting

## Explicitly excluded

- `~/.argus-skill*` runtime state
- project databases, events, journals, handoffs, and subagent logs
- Copilot session state
- credentials and tokens
- full Rust, Verus, Z3, and vstd checkouts
- full per-target proof trees
- large live-run and mutation evidence
- generated `spec-determinism` result corpora and binary artifacts
