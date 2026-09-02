# Rust 1.96 `core::cmp` regeneration

This isolated campaign inventories every stable executable identity publicly
reachable through `core::cmp`, references exact vstd coverage, generates the
remaining source-backed contracts, and retains implementation and completeness
proofs for every selected exact-vstd or generated row. Rows independently
accepted as `genuinely_impossible` remain visible in the module catalog and
receive no specification, proof, or mutation coverage credit.

The mandatory browsing interfaces are:

- `specs/` for the accepted module-wide contract catalog and exact-vstd
  references.
- `proof_harnesses/` for exactly one directly discoverable child per selected
  specified identity, including both proof sources, source/contract bindings,
  transformations, dependencies, trust records, mutations, and evidence.
- `specification/float_model_boundary_audit.json` for the target-specific
  `f32`/`f64` rows blocked by the loaded vstd float model.

The inventory-derived gate order is:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q tools tests
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q tests
python3 tools/build_inventory.py check
python3 tools/run_float_model_boundary_probes.py --run-id cmp-float-model
python3 tools/build_specification.py
python3 tools/check_specification.py
python3 tools/build_implementation_proofs.py
python3 tools/run_implementation_proofs.py \
  --run-id cmp-final \
  --run-dir verification/evidence/cmp-final \
  --phase all --timeout 120
python3 tools/run_mutation_probes.py --run-id cmp-mutations-final
python3 tools/check_implementation_proofs.py \
  --require-results --require-mutations --require-review
python3 tools/check_aggregate.py --require-final-review
```

The long runners use immutable run-local input snapshots, durable command
records, run-scoped `STOP` files, and separate `--no-verify` and actual-Verus
executions. Canonical acceptance requires exact `producer_role=reviewer` and
`review.status=done` records bound to the current request hashes.
