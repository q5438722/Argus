#!/usr/bin/env python3
"""Check the complete Result specification package before Reviewer handoff."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_specification
import run_spec_negative_mutations
import run_verus_typecheck
import specification_support as support


OUTPUT_PATH = support.VERIFICATION_ROOT / "specification_gate.json"


def add_error(
    errors: list[dict[str, Any]], code: str, **details: Any
) -> None:
    errors.append({"code": code, **details})


def current_input_hashes() -> dict[str, str]:
    return {
        "catalog_sha256": support.sha256(support.CATALOG_PATH),
        "contracts_sha256": support.sha256(support.CONTRACT_PATH),
        "inventory_sha256": support.sha256(support.INVENTORY_PATH),
        "vocabulary_sha256": support.sha256(support.VOCABULARY_PATH),
    }


def current_evidence_hashes() -> dict[str, str]:
    return {
        "feedback_manifest_sha256": support.sha256(
            support.FEEDBACK_MANIFEST_PATH
        ),
        "feedback_diagnostic_bindings_sha256": (
            support.feedback_diagnostic_binding_set()["set_sha256"]
        ),
        "feedback_run_binding_sha256": support.sha256(
            support.FEEDBACK_RUN_BINDING_PATH
        ),
        "feedback_seed_sha256": support.sha256(
            support.FEEDBACK_SEED_PATH
        ),
        "feedback_summary_sha256": support.sha256(
            support.FEEDBACK_SUMMARY_PATH
        ),
        "from_iter_adjudication_sha256": support.sha256(
            support.FROM_ITER_ADJUDICATION_PATH
        ),
        "from_iter_projection_probe_sha256": support.sha256(
            support.FROM_ITER_PROBE_REPORT_PATH
        ),
        "helper_usage_sha256": support.sha256(
            support.HELPER_USAGE_PATH
        ),
        "outcome_equivalence_sha256": support.sha256(
            support.OUTCOME_EQUIVALENCE_PATH
        ),
        "package_manifest_sha256": support.sha256(
            support.PACKAGE_MANIFEST_PATH
        ),
        "relation_capability_sha256": support.sha256(
            support.FEEDBACK_RELATION_CAPABILITY_PATH
        ),
        "vstd_contracts_sha256": support.sha256(
            support.VSTD_CONTRACTS_PATH
        ),
    }


def main() -> int:
    errors: list[dict[str, Any]] = []
    support.validate_metadata_coverage()
    inventory = support.inventory_rows()
    catalog = support.load_json(support.CATALOG_PATH)
    catalog_rows = catalog.get("rows")
    if not isinstance(catalog_rows, list):
        raise ValueError("catalog rows are missing")
    counts = Counter(row["disposition"] for row in catalog_rows)
    inventory_ids = {int(row["rustdoc_item_id"]) for row in inventory}
    catalog_ids = {int(row["rustdoc_item_id"]) for row in catalog_rows}
    if catalog_ids != inventory_ids:
        add_error(errors, "catalog_inventory_row_set_mismatch")
    if counts["generated"] != len(support.generated_ids()):
        add_error(errors, "generated_count_mismatch")
    if counts["exact_vstd"] != len(support.exact_ids()):
        add_error(errors, "exact_count_mismatch")
    if counts["pending"] or counts["genuinely_impossible"]:
        add_error(errors, "unresolved_catalog_rows")
    if len(catalog_rows) != len(inventory):
        add_error(errors, "catalog_total_mismatch")

    typecheck = support.load_json(run_verus_typecheck.OUTPUT_PATH)
    if (
        typecheck.get("status") != "passed"
        or typecheck.get("exit_code") != 0
        or typecheck.get("timed_out") is not False
    ):
        add_error(errors, "verus_typecheck_not_passed")
    expected_current = current_input_hashes()
    for key, value in expected_current.items():
        if typecheck.get("inputs", {}).get(key) != value:
            add_error(
                errors,
                "verus_typecheck_input_stale",
                input=key,
            )
    if (
        typecheck.get("tools", {}).get("verus_binary_sha256")
        != support.sha256(run_verus_typecheck.VERUS_BIN)
    ):
        add_error(errors, "verus_binary_hash_stale")
    if (
        typecheck.get("tools", {}).get("z3_binary_sha256")
        != support.sha256(run_verus_typecheck.Z3_PATH)
    ):
        add_error(errors, "z3_binary_hash_stale")

    audit_summary = support.load_json(audit_specification.SUMMARY_PATH)
    if audit_summary.get("status") != "passed":
        add_error(errors, "static_audit_summary_not_passed")
    expected_audits = {name for name, _ in audit_specification.AUDITS}
    actual_audits = {
        row.get("audit") for row in audit_summary.get("audits", [])
    }
    if actual_audits != expected_audits:
        add_error(errors, "static_audit_set_mismatch")
    audit_evidence: list[dict[str, Any]] = []
    expected_audit_inputs = {
        **expected_current,
        **current_evidence_hashes(),
    }
    for name in sorted(expected_audits):
        path = support.AUDIT_ROOT / f"{name}.json"
        payload = support.load_json(path)
        if payload.get("status") != "passed":
            add_error(errors, "static_audit_not_passed", audit=name)
        for key, value in expected_audit_inputs.items():
            if payload.get("inputs", {}).get(key) != value:
                add_error(
                    errors,
                    "static_audit_input_stale",
                    audit=name,
                    input=key,
                )
        audit_evidence.append(
            {
                "audit": name,
                "path": str(path.relative_to(support.ROOT)),
                "sha256": support.sha256(path),
                "status": payload.get("status"),
            }
        )

    negative = support.load_json(
        run_spec_negative_mutations.OUTPUT_PATH
    )
    if negative.get("status") != "passed":
        add_error(errors, "negative_mutation_not_passed")
    if negative.get("mutation_count") != len(support.generated_ids()):
        add_error(errors, "negative_mutation_count_mismatch")
    for record in negative.get("records", []):
        if not record.get("semantic_rejection_codes"):
            add_error(
                errors,
                "negative_mutation_has_no_semantic_rejection",
                rustdoc_item_id=record.get("rustdoc_item_id"),
            )
        if int(record.get("rustdoc_item_id", -1)) in (
            support.SHORT_CIRCUIT_IDS
        ) and (
            record.get("mutation_kind")
            != "short_circuit_consumption_boundary"
            or record.get("obligation")
            != "stop_at_first_err_consumption_boundary"
            or "short_circuit_consumption_boundary_missing"
            not in record.get("semantic_rejection_codes", [])
        ):
            add_error(
                errors,
                "short_circuit_consumption_mutation_not_rejected",
                rustdoc_item_id=record.get("rustdoc_item_id"),
            )
    for key in ("catalog_sha256", "contracts_sha256"):
        if negative.get("inputs", {}).get(key) != expected_current[key]:
            add_error(
                errors,
                "negative_mutation_input_stale",
                input=key,
            )

    required_paths = (
        support.ROOT / "specs" / "README.md",
        support.CONTRACT_PATH,
        support.CATALOG_PATH,
        support.VOCABULARY_PATH,
        support.HELPER_USAGE_PATH,
        support.OUTCOME_EQUIVALENCE_PATH,
        support.PACKAGE_MANIFEST_PATH,
        support.EXACT_REFERENCES_PATH,
        support.ROOT / "specs" / "existing_vstd" / "README.md",
        support.FEEDBACK_MANIFEST_PATH,
        support.FEEDBACK_SEED_PATH,
        support.FEEDBACK_RELATION_CAPABILITY_PATH,
        support.FEEDBACK_SUMMARY_PATH,
        support.FEEDBACK_RUN_BINDING_PATH,
        support.FEEDBACK_ADAPTER_PATH,
        support.FROM_ITER_ADJUDICATION_PATH,
        support.FROM_ITER_PROBE_REPORT_PATH,
        support.FROM_ITER_PROBE_SOURCE_PATH,
        support.VSTD_CONTRACTS_PATH,
    )
    for path in required_paths:
        if not path.is_file():
            add_error(
                errors,
                "required_spec_artifact_missing",
                path=str(path.relative_to(support.ROOT)),
            )

    payload = {
        "acceptance_claim": False,
        "audits": [
            *audit_evidence,
            {
                "audit": "negative_mutation",
                "path": str(
                    run_spec_negative_mutations.OUTPUT_PATH.relative_to(
                        support.ROOT
                    )
                ),
                "sha256": support.sha256(
                    run_spec_negative_mutations.OUTPUT_PATH
                ),
                "status": negative.get("status"),
            },
        ],
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "exact_vstd": counts["exact_vstd"],
            "generated": counts["generated"],
            "genuinely_impossible": counts["genuinely_impossible"],
            "pending": counts["pending"],
            "specified": counts["exact_vstd"] + counts["generated"],
            "stable_inventory_total": len(inventory),
        },
        "error_details": errors,
        "errors": sorted({row["code"] for row in errors}),
        "inputs": {
            **expected_current,
            **current_evidence_hashes(),
            "checker_sha256": support.sha256(Path(__file__)),
            "exact_references_sha256": support.sha256(
                support.EXACT_REFERENCES_PATH
            ),
        },
        "reviewer_gate": {
            "canonical_reviewer_status": "not_yet_requested",
            "required": True,
        },
        "schema_version": 1,
        "status": "passed" if not errors else "failed",
        "typecheck": {
            "path": str(
                run_verus_typecheck.OUTPUT_PATH.relative_to(support.ROOT)
            ),
            "sha256": support.sha256(run_verus_typecheck.OUTPUT_PATH),
            "status": typecheck.get("status"),
        },
    }
    support.write_json(OUTPUT_PATH, payload)
    print(
        {
            "exact_vstd": counts["exact_vstd"],
            "generated": counts["generated"],
            "status": payload["status"],
            "total": len(inventory),
        }
    )
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
