# BTreeSet trust-boundary audit

The campaign binds 92 selected Rust 1.96 source APIs
(11 exact-vstd and 81 generated).
No public target implementation or completeness theorem is marked
`external_body`. The implementation harnesses contain exactly
299 literal `external_body` markers:
110 operation-specific lower
dependencies and 189 source discriminants,
private map/cursor observation bridges, callback-step boundaries, or
lower-to-public representation projectors required by those targets. Every
marker is recorded in the colocated trust
manifest. No lower function has the public target return shape, and no lower
function is permitted to restate the whole public contract.
The harnesses also contain
3
local `assume_specification` bindings for `Option::and`/`Option::or`, owned by
targets 082 and 090 and hash-bound to
`provenance/frozen/rust-1.96/library/core/src/option.rs`. Each narrowly states
the frozen combinator result; its required
`allow(undeclared_external_trait)` annotation is recorded in the same trust
manifest.
Additional semantic boundaries cover the selected
external contract, source-to-Verus ordered-set lowering, `Ord`/borrowed-order
laws, core `Option` combinator semantics, private iterator/node state,
allocation/provenance, and drop.

Each compiled harness also includes
10 shared external
type-model declarations. These are reported separately from the
299 target-local markers. Public targets
and completeness theorems each contain zero literal markers.

The exact signatures of
3 `IntoIterator::Item`
targets trigger a frozen Verus ill-typed-AIR internal error even for an empty
body. Their exact sources remain mandatory `--no-verify` inputs. Actual
verification additionally uses the identical executable proof and mutation
with only that equality precondition erased; this strengthens the proof domain,
and both the raw checker error and stronger-domain results are retained. Those
six auxiliary sources contain 32 literal
`external_body` occurrences, accounted separately from canonical harnesses.

Consequently **0/92** targets claim no additional
implementation/dependency boundary and **0/92** claim foundational
end-to-end trust-freedom. The external type declarations in shared
specification vocabulary are separately accounted model boundaries and are
not confused with target-body proof markers.
