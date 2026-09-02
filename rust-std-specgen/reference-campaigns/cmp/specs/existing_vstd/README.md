# Existing vstd references

`bindings.json` records all 124 exact identity/signature bindings and
their frozen source hashes. The files below are relative symbolic references to
the campaign's immutable vstd snapshots.

The 8 `Ordering` convenience
bindings from `std_specs/ordering.rs` have
`canonical_upstream_binding: false`; they depend on the frozen untracked module
and dirty loader edits and must not be described as canonical upstream vstd.
