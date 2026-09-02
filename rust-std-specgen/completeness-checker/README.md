# Completeness and determinism checker

Argus does not call a private completeness-checking service. Its Engineer role
has ordinary filesystem and shell access inside the campaign workdir.

The Rust std flow is:

1. The module prompt and process document identify the campaign manifest,
   selected contracts, vstd checkout, Verus binary, Z3 binary, and output path.
2. The Engineer runs `run_rust_std_spec_feedback.py`.
3. The adapter imports the local `spec-determinism/spec_determinism` package.
4. `spec-determinism` extracts contracts, builds guarded determinism checks,
   searches supported schemas, and invokes Verus/Z3.
5. The adapter writes per-target and aggregate evidence into the campaign.
6. Campaign-local checkers and an independent Reviewer consume that evidence.

The adapter defaults assume a complete campaign workspace adjacent to the
script. For another layout, pass explicit paths:

```bash
python rust-std-specgen/completeness-checker/run_rust_std_spec_feedback.py \
  --manifest /path/to/campaign/specgen/pilot-manifest.json \
  --contracts /path/to/campaign/results/vstd_contracts.json \
  --vstd-root /path/to/verus/source/vstd \
  --verus-bin /path/to/verus \
  --z3-path /path/to/z3 \
  --out /path/to/campaign/verification/evidence/feedback-round
```

Only source, scripts, configs, and documentation are included here. Historical
result corpora, solver logs, binaries, and generated experiment directories are
excluded.

