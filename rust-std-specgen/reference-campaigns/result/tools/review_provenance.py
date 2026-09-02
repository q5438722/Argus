"""Readable provenance for independent core::result review requests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


READABLE_ARTIFACTS = (
    "specs/all_result_specs.json",
    "proof_inventory/targets.json",
    "proof_inventory/generation_summary.json",
    "proof_inventory/dependency_graph.json",
    "proof_inventory/verification_run.json",
    "audits/trust_boundary_audit.json",
    "audits/semantic_trust_boundary_audit.json",
    "audits/mutation_audit.json",
    "proof_harnesses/*/source_excerpt.rs",
    "proof_harnesses/*/accepted_contract.rs",
    "proof_harnesses/*/implementation_proof.rs",
    "proof_harnesses/*/completeness_proof.rs",
    "proof_harnesses/*/trust_boundaries.json",
    "proof_harnesses/*/mutations/*.rs",
)


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def implementation_review_basis(root: Path) -> dict[str, Any]:
    generation = _load_object(root / "proof_inventory/generation_summary.json")
    verification = _load_object(root / "proof_inventory/verification_run.json")
    return {
        "readable_artifacts": list(READABLE_ARTIFACTS),
        "fresh_execution": {
            "proof_generation_at_utc": generation.get("generated_at_utc"),
            "verification_bound_at_utc": verification.get("bound_at_utc"),
            "run_id": verification.get("run_id"),
            "run_dir": verification.get("run_dir"),
            "state": verification.get("state"),
            "commands_recorded": verification.get("commands_recorded"),
            "mutation_rejections": verification.get("mutation_rejections"),
        },
    }
