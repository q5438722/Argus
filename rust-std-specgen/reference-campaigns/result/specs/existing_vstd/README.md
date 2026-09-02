# Exact loaded vstd references

`exact_result_references.json` is generated from
`inventory/exact_vstd_audit.json`. It references only the 10 declarations that
match a stable Rust 1.96 `core::result` row across target, receiver, parameters,
return type, generics, bounds, lifetimes, mutability, and safety.

The referenced source is frozen under
`provenance/vstd-dependency-closure/source/vstd/std_specs/result.rs`; exact rows
are not redeclared in `generated_result_specs.rs`.
