#!/usr/bin/env python3
"""Prepare a hash-bound request for the independent specification Reviewer."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_specification
import check_specification_gate
import run_spec_negative_mutations
import run_verus_typecheck
import specification_support as support


OUTPUT_PATH = (
    support.ROOT / "review" / "specification_reviewer_request.json"
)
MISSION_ID = "b8c2aecd4131"


def evidence(path: Path, status: str) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(support.ROOT)),
        "sha256": support.sha256(path),
        "status": status,
    }


def main() -> int:
    gate = support.load_json(check_specification_gate.OUTPUT_PATH)
    if gate.get("status") != "passed":
        raise SystemExit("specification gate is not passed")
    evidence_rows = [
        evidence(support.CATALOG_PATH, "complete"),
        evidence(support.EXACT_REFERENCES_PATH, "complete"),
        evidence(support.HELPER_USAGE_PATH, "passed"),
        evidence(support.OUTCOME_EQUIVALENCE_PATH, "passed"),
        evidence(
            support.FEEDBACK_RELATION_CAPABILITY_PATH,
            "unsupported_capability_recorded",
        ),
        evidence(support.PACKAGE_MANIFEST_PATH, "passed"),
        evidence(support.FEEDBACK_SUMMARY_PATH, "completed"),
        evidence(support.FEEDBACK_RUN_BINDING_PATH, "completed"),
        evidence(support.FROM_ITER_PROBE_REPORT_PATH, "passed"),
        evidence(support.FROM_ITER_ADJUDICATION_PATH, "passed"),
        evidence(run_verus_typecheck.OUTPUT_PATH, "passed"),
        evidence(audit_specification.SUMMARY_PATH, "passed"),
        evidence(run_spec_negative_mutations.OUTPUT_PATH, "passed"),
        evidence(check_specification_gate.OUTPUT_PATH, "passed"),
    ]
    payload = {
        "acceptance_claim": False,
        "counts": gate["counts"],
        "evidence": evidence_rows,
        "mission_id": MISSION_ID,
        "producer_role": "engineer",
        "requested_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_gate": "inventory_and_specification",
        "review_questions": [
            "Do the 10 exact-vstd references satisfy full-signature subtraction?",
            "Do all 54 generated contracts state principal Result branch, payload, callback, mutation, panic/unsafe, iterator, and short-circuit behavior directly?",
            "Are the shared helpers limited to mathematical views, private-state projections, and narrow dependency laws?",
            "Do Sum, Product, and FromIterator constrain their consumed source-item trace to end exactly at the first Err, with eager traversal rejected by mutation?",
            "Does every catalog row carry its target-specific versioned exact-equality binding, including exact componentwise equality over named source-backed observation schemas where private representation is outside the theorem domain?",
            "Do all negative mutations fail a named semantic obligation rather than only a stored digest comparison?",
            "Do all feedback surfaces accurately classify selected-relation evaluation as unsupported because the canonical runner accepts no relation input, while retaining canonical checker results only as diagnostics?",
            "Are the Verus typecheck and nine static audit records current and sufficient to authorize implementation/completeness work?",
        ],
        "schema_version": 1,
        "status": "ready_for_independent_reviewer",
    }
    support.write_json(OUTPUT_PATH, payload)
    print(
        {
            "evidence": len(evidence_rows),
            "status": payload["status"],
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
