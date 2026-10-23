---
name: "Verus Direct API Postconditions"
description: "Generate effective Rust API contracts with the actual guarantees written directly in ensures, not a single forwarding *_post predicate. Reuse semantic views/protocols, retain all guards, and distinguish helper models from bound API specifications."
---

# Verus Direct API Postconditions

[Chinese reference](references/verus-inline-api-postconditions.zh-CN.md)

For Rust std specification generation, write the guarantees directly in the
actual API's `ensures` clause. Do not make the public contract just a call to
one spec function that hides the entire postcondition.

Avoid:

```rust
ensures
    current::as_slice_post(drain, returned@),
```

Write the actual relation:

```rust
ensures
    returned@ == IteratorSpec::remaining(drain),
```

This is a semantic rule, not a physical line-count rule. A single line such as
`result@ == input@` can be a complete, explicit content postcondition.
Conversely, wrapping `whole_post(...)` over several lines is still forwarding
the whole contract and does not satisfy this rule.

## Inline guarantees, not every semantic abstraction

Keep independently meaningful views, sequence operations, `eq_spec`,
`IteratorSpec::remaining`, and proved shared lemmas where appropriate.
Do not duplicate or invent a parallel model merely to avoid a spec-function
name. Expand whole-contract predicates, including aliases that hide the same
delegation, into the return/content/writeback/branch relations the API promises.

Keep the exact original input domain and API identity. When TB-PARTIAL-EQ is
needed, inline **all** guarantees inside the exact conformance implication.
Do not move clauses outside the guard, introduce `requires B`, or combine an
independent container condition C into the outer guard. Proof-only exposed
fields remain forbidden in the exported contract; follow the
[field-visibility Skill](verus-proof-only-field-visibility.md).
Pointer and ownership properties are not additional spec/completeness
requirements for this work.

## The contract must belong to the real API

A `spec fn next_contract(...) -> bool` is a model, not a contract for
`Iterator::next`. An external type registration is not a method specification.
An analysis-only function with `Ghost<Seq<T>>` outputs is not an API binding.

Provide an effective specification for the exact Rust API, or integrate the
concrete type with the existing specification protocol and its constructor
relations so that the applicable inherited method contracts are usable.
Demonstrate the connection with a real call against the unchanged public
library. Do not assume a missing conformance condition solely to make the
client pass. Shared helper proofs and projection determinism cannot replace
this connection or either required API proof track.

Keep separate coverage fields for helper/candidate existence, effective API
binding, source correctness, completeness scope and independent review.
If binding is missing, say **API specification generation incomplete** rather
than "spec generated, only proof remains". A diagnosed local limitation may
be reported, but must not be counted as an API spec or hidden by a successful
aggregate/helper build.

When expanding an existing post predicate, keep the source-proof contract and
completeness contract equivalent to the actual API contract. Preserve the old
inputs/results, check the changed binding and affected clients/proofs, and do
not claim old snapshot bytes match edited inputs. Unchanged APIs need not be
rerun. Do not mark a whole remaining-spec queue complete just because helper
models and a limitation report were produced.
