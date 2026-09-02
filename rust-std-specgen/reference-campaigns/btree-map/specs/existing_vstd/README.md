# Existing vstd references

`references.json` pins the unchanged vstd files relevant to this campaign.
These files are references, not copied or locally redeclared specifications.

The completed eight-dimension audit accepts exactly 13 BTreeMap declarations
as `exact_vstd`. The BTreeSet declarations colocated in `btree.rs` are
excluded. The cmp files define only the narrow `OrdSpec`/`obeys_cmp`
dependency; they do not make the concurrent Cmp campaign an accepted
dependency.
