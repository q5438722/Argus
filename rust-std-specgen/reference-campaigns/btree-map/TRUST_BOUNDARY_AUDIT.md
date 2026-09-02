# BTreeMap trust-boundary audit

All 150 selected target bodies are executable and none is marked
`external_body`. The whole-harness scan contains **6522**
literal markers: **2286**
in implementation files, **1950**
in completeness files, and **2286**
in mutation files. The implementation helper/model surface accounts for
**2286** markers; the shared vocabulary
itself contains **13** markers. Every target relies on
the accepted public contract, executable source-shaped lowering,
operation-local private semantics, and the narrow comparator/generic
dependency. The target-local scan reports
**0/150** harnesses with a
non-leaf boundary covering the complete target contract, alongside
**336** source-span-bound operation boundaries
and **12** documented private-field leaf
exceptions.

The actual whole-harness semantic marker scan is
`{'assume_specification': 0, 'broadcast_axiom': 7650, 'external_body': 6522, 'external_type_specification': 5850, 'uninterpreted_spec': 14402}`.
Target-specific ownership, borrowing, ordering, iterator, allocator, callback,
panic, drop, unwind, formatter, and hasher categories are counted in
`proof_inventory/aggregate_coverage.json`.

Accordingly, **0/150** targets have no
additional implementation/dependency boundary and **0/150** are
foundationally end-to-end trust-free. Zero literal markers is not a zero-TCB
claim.
