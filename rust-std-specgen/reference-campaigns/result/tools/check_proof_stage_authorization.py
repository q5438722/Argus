#!/usr/bin/env python3
"""Validate the separate proof-stage authorization and frozen inputs."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AUTHORIZATION_PATH = ROOT / "proof_stage" / "authorization.json"
OUTPUT_PATH = ROOT / "verification" / "proof_stage_authorization.json"
REVIEWER_HANDOFF_PATH = Path(
    "/home/chentianyu/.argus-skill-v011-slice-conditional/projects/"
    "s-17ed5943/handoffs/b8c2aecd4131/round-0007.json"
)

EXPECTED_COUNTS = {
    "exact_vstd": 10,
    "generated": 54,
    "pending": 0,
    "specified": 64,
    "stable_inventory_total": 64,
}
EXPECTED_INPUTS = {
    "canonical_reviewer_handoff": (
        str(REVIEWER_HANDOFF_PATH),
        "d6c15c71b50b11c2ca6e96c463e46b63a3de79ad2a6979716a252ec70a55d46f",
    ),
    "accepted_specification_manifest": (
        "specs/specification_package_manifest.json",
        "79c836667fc88dfa334eb876d1cd74e5971e6ffa941e15cc9c698daec2cbdcbe",
    ),
    "accepted_specification_catalog": (
        "specs/all_result_specs.json",
        "eaa95817923b0de1f3f7823a8a0bafb76c40f2ca8a36482a026ffba5e6b21b78",
    ),
    "implementation_conformance_workflow": (
        "provenance/methodology/rust-std-lib-specgen-process.md",
        "b718e235187616459cd5e99eabc70cad9117f7ad6fbf03a2de5271c2baeccf0c",
    ),
    "trust_boundary_precedent": (
        "provenance/methodology/TRUST_BOUNDARY_AUDIT.md",
        "55f7aba92e27893c4b92ffff86d645addc58849156e2a0ad388e213503e4b5d0",
    ),
    "inventory_boundary_wiki": (
        ".autors/nanvix-rust-std-result-regeneration-20260901-v011-8798/"
        "wiki/pages/core-result-live-inventory.md",
        "4ff861288216428b11fa9dafa00c18e4788538a60bbee711a108edde32ea6cdc",
    ),
    "specification_boundary_wiki": (
        ".autors/nanvix-rust-std-result-regeneration-20260901-v011-8798/"
        "wiki/pages/core-result-specification-boundaries.md",
        "d35ae44adfa7230bd4bd885460eeb9c8f5d8026cbe07e1627ac8704d72f9aed5",
    ),
}
EXPECTED_GATES = [
    "proof_inventory_binding",
    "source_and_dependency_freeze",
    "per_target_no_verify",
    "per_target_actual_verus",
    "implementation_mutation",
    "completeness_mutation",
    "source_and_hash_fidelity",
    "literal_trust_boundary_audit",
    "semantic_trust_boundary_audit",
    "independent_reviewer",
    "final_aggregate_certification",
]
EXPECTED_TARGET_FILES = [
    "implementation_proof.rs",
    "completeness_proof.rs",
]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        value, ensure_ascii=True, indent=2, sort_keys=True
    ) + "\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(encoded, encoding="utf-8")
    os.replace(temporary, path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_error(
    errors: list[dict[str, Any]], code: str, **details: Any
) -> None:
    errors.append({"code": code, **details})


def resolve_input_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def audit_authorization(
    authorization: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = (
        load_json(AUTHORIZATION_PATH)
        if authorization is None
        else authorization
    )
    errors: list[dict[str, Any]] = []

    expected_header = {
        "freeze_scope": "accepted_specification_and_proof_workflow_inputs",
        "module": "core::result",
        "schema_version": 1,
        "stage": "implementation_conformance",
        "status": "authorized",
    }
    for field, expected in expected_header.items():
        if payload.get(field) != expected:
            add_error(
                errors,
                "authorization_field_mismatch",
                actual=payload.get(field),
                expected=expected,
                field=field,
            )

    authority = payload.get("authority", {})
    expected_authority = {
        "canonical_reviewer_handoff": str(REVIEWER_HANDOFF_PATH),
        "kind": (
            "operator_directive_after_independent_specification_acceptance"
        ),
        "reviewer_acceptance_scope": (
            "bounded_inventory_and_specification_gate"
        ),
    }
    for field, expected in expected_authority.items():
        if authority.get(field) != expected:
            add_error(
                errors,
                "authority_field_mismatch",
                actual=authority.get(field),
                expected=expected,
                field=field,
            )
    if not authority.get("operator_directive_received_at_utc"):
        add_error(errors, "operator_directive_timestamp_missing")

    frozen_rows = payload.get("frozen_inputs")
    if not isinstance(frozen_rows, list):
        add_error(errors, "frozen_inputs_missing")
        frozen_rows = []
    rows_by_role: dict[str, dict[str, Any]] = {}
    for row in frozen_rows:
        if not isinstance(row, dict):
            add_error(errors, "frozen_input_not_object")
            continue
        role = row.get("role")
        if not isinstance(role, str):
            add_error(errors, "frozen_input_role_missing")
            continue
        if role in rows_by_role:
            add_error(errors, "duplicate_frozen_input_role", role=role)
            continue
        rows_by_role[role] = row
    if set(rows_by_role) != set(EXPECTED_INPUTS):
        add_error(
            errors,
            "frozen_input_role_set_mismatch",
            actual=sorted(rows_by_role),
            expected=sorted(EXPECTED_INPUTS),
        )

    for role, (expected_path, expected_hash) in EXPECTED_INPUTS.items():
        row = rows_by_role.get(role)
        if row is None:
            continue
        path_text = row.get("path")
        stored_hash = row.get("sha256")
        if path_text != expected_path:
            add_error(
                errors,
                "frozen_input_path_mismatch",
                actual=path_text,
                expected=expected_path,
                role=role,
            )
            continue
        if stored_hash != expected_hash:
            add_error(
                errors,
                "frozen_input_expected_hash_mismatch",
                actual=stored_hash,
                expected=expected_hash,
                role=role,
            )
        path = resolve_input_path(path_text)
        if not path.is_file():
            add_error(
                errors,
                "frozen_input_missing",
                path=path_text,
                role=role,
            )
        elif sha256(path) != stored_hash:
            add_error(
                errors,
                "frozen_input_content_hash_mismatch",
                path=path_text,
                role=role,
            )

    handoff = load_json(REVIEWER_HANDOFF_PATH)
    if handoff.get("producer_role") != "reviewer":
        add_error(errors, "canonical_handoff_not_from_reviewer")
    if handoff.get("round") != 7:
        add_error(errors, "canonical_handoff_round_mismatch")
    review = handoff.get("review", {})
    if review.get("status") != "done":
        add_error(errors, "canonical_review_not_done")
    reason = review.get("reason", "")
    if (
        "bounded inventory/specification gate" not in reason
        or "not final campaign acceptance" not in reason
    ):
        add_error(errors, "canonical_review_scope_not_explicit")

    manifest_path = ROOT / "specs" / "specification_package_manifest.json"
    manifest = load_json(manifest_path)
    if manifest.get("proof_harnesses_authorized") is not False:
        add_error(errors, "accepted_manifest_transition_state_changed")
    if manifest.get("counts") != {
        "exact_vstd": 10,
        "generated": 54,
        "specified": 64,
    }:
        add_error(errors, "accepted_manifest_counts_mismatch")
    artifact_rows = manifest.get("artifacts")
    if not isinstance(artifact_rows, list):
        add_error(errors, "accepted_manifest_artifacts_missing")
        artifact_rows = []
    artifact_paths: set[str] = set()
    for row in artifact_rows:
        if not isinstance(row, dict):
            add_error(errors, "accepted_manifest_artifact_not_object")
            continue
        path_text = row.get("path")
        expected_hash = row.get("sha256")
        if not isinstance(path_text, str) or not isinstance(
            expected_hash, str
        ):
            add_error(errors, "accepted_manifest_artifact_fields_invalid")
            continue
        if path_text in artifact_paths:
            add_error(
                errors,
                "accepted_manifest_duplicate_artifact",
                path=path_text,
            )
            continue
        artifact_paths.add(path_text)
        artifact_path = ROOT / path_text
        if not artifact_path.is_file():
            add_error(
                errors,
                "accepted_specification_artifact_missing",
                path=path_text,
            )
        elif sha256(artifact_path) != expected_hash:
            add_error(
                errors,
                "accepted_specification_artifact_hash_mismatch",
                path=path_text,
            )

    catalog = load_json(ROOT / "specs" / "all_result_specs.json")
    rows = catalog.get("rows")
    if not isinstance(rows, list):
        add_error(errors, "accepted_catalog_rows_missing")
        rows = []
    item_ids = [
        int(row["rustdoc_item_id"])
        for row in rows
        if isinstance(row, dict) and "rustdoc_item_id" in row
    ]
    if len(item_ids) != len(rows):
        add_error(errors, "accepted_catalog_row_invalid")
    if len(item_ids) != len(set(item_ids)):
        add_error(errors, "accepted_catalog_duplicate_target")
    dispositions = Counter(
        row.get("disposition")
        for row in rows
        if isinstance(row, dict)
    )
    observed_counts = {
        "exact_vstd": dispositions["exact_vstd"],
        "generated": dispositions["generated"],
        "pending": dispositions["pending"],
        "specified": (
            dispositions["exact_vstd"] + dispositions["generated"]
        ),
        "stable_inventory_total": len(rows),
    }
    if observed_counts != EXPECTED_COUNTS:
        add_error(
            errors,
            "accepted_catalog_counts_mismatch",
            actual=observed_counts,
            expected=EXPECTED_COUNTS,
        )
    accepted = payload.get("accepted_specification", {})
    if accepted.get("counts") != EXPECTED_COUNTS:
        add_error(errors, "authorization_counts_mismatch")
    expected_accepted_fields = {
        "catalog_path": "specs/all_result_specs.json",
        "catalog_sha256": EXPECTED_INPUTS[
            "accepted_specification_catalog"
        ][1],
        "manifest_path": "specs/specification_package_manifest.json",
        "manifest_sha256": EXPECTED_INPUTS[
            "accepted_specification_manifest"
        ][1],
        "preservation": "byte_for_byte",
    }
    for field, expected in expected_accepted_fields.items():
        if accepted.get(field) != expected:
            add_error(
                errors,
                "accepted_specification_binding_mismatch",
                field=field,
            )

    if payload.get("required_gates") != EXPECTED_GATES:
        add_error(errors, "required_gate_set_or_order_mismatch")
    transition = payload.get("transition", {})
    expected_transition = {
        "accepted_specification_package_mutation": "forbidden",
        "completeness_contract_binding": (
            "accepted_contract_and_exact_outcome_equivalence"
        ),
        "exact_vstd_contract_mode": "reference_only",
        "generated_contract_mode": "frozen_declaration",
        "proof_evidence_modes": ["no_verify", "actual_verus"],
        "proof_harnesses_creation": "authorized",
        "required_files_per_target": EXPECTED_TARGET_FILES,
        "target_directory_count": 64,
    }
    for field, expected in expected_transition.items():
        if transition.get(field) != expected:
            add_error(
                errors,
                "proof_transition_field_mismatch",
                actual=transition.get(field),
                expected=expected,
                field=field,
            )

    return {
        "audit": "proof_stage_authorization",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "checked_frozen_inputs": len(rows_by_role),
        "checked_specification_artifacts": len(artifact_paths),
        "counts": observed_counts,
        "error_details": errors,
        "errors": sorted({row["code"] for row in errors}),
        "inputs": {
            "authorization_path": str(
                AUTHORIZATION_PATH.relative_to(ROOT)
            ),
            "authorization_sha256": sha256(AUTHORIZATION_PATH),
            "reviewer_handoff_sha256": sha256(REVIEWER_HANDOFF_PATH),
            "specification_catalog_sha256": sha256(
                ROOT / "specs" / "all_result_specs.json"
            ),
            "specification_manifest_sha256": sha256(manifest_path),
        },
        "schema_version": 1,
        "status": "passed" if not errors else "failed",
    }


def main() -> int:
    report = audit_authorization()
    write_json(OUTPUT_PATH, report)
    print(
        f"proof-stage authorization: {report['status']} "
        f"({report['checked_frozen_inputs']} frozen inputs, "
        f"{report['checked_specification_artifacts']} accepted artifacts)"
    )
    for row in report["error_details"]:
        print(json.dumps(row, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
