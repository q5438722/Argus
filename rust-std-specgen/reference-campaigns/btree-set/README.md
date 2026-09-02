# Rust 1.96 BTreeSet regeneration campaign

This isolated campaign covers exactly `alloc::collections::btree_set`. Browse contracts in
`specs/`, all 92 selected source-shaped proof harnesses in
`proof_harnesses/`, inventory and exact-vstd reconciliation in `inventory/`,
and the inventory-derived aggregate in `proof_inventory/`.

The reproducible fail-closed command is:

```bash
python3 tools/check_campaign.py
```

Generation is phase ordered:

```bash
python3 tools/generate_campaign.py --stage specification
# canonical inventory/specification Reviewer acceptance is mandatory here
python3 tools/generate_campaign.py --stage proofs
```

The proof stage rejects a missing or stale accepted specification artifact
index and regenerates every harness against that exact contract set.
