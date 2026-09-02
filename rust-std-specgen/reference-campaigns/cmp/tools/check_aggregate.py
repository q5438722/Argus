#!/usr/bin/env python3
"""Prepare and validate the final inventory-derived core::cmp aggregate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_specification as specification
from tools import build_inventory
from tools import check_implementation_proofs as proofs
from tools import check_specification
from tools.review_schema import artifact_binding_map, question_verdict_map
from tools import provenance
from tools import run_implementation_proofs as runner


ACTIVE = ROOT / "proof_inventory" / "active_aggregate_certification.json"
FINAL_REQUEST = ROOT / "reviews" / "final_aggregate_review_request.json"
FINAL_REVIEW = ROOT / "reviews" / "final_aggregate_review.json"
FINAL_REVIEW_HANDOFF = (
    ROOT / "reviews" / "canonical_final_aggregate_handoff.json"
)
FINAL_DELIVERY = ROOT / "proof_inventory" / "final_delivery.json"
CHECK_REPORT = ROOT / "proof_inventory" / "aggregate_check.json"
REQUIRED_SPEC_FILES = (
    "README.md",
    "generated_cmp_specs.rs",
    "all_cmp_specs.json",
    "cmp_shared_vocabulary.rs",
    "existing_vstd",
)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def compact_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
    ).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(json_bytes(value))
    temporary.replace(path)


def binding(path: Path) -> dict[str, str]:
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256(path),
    }


def add(errors: list[dict[str, Any]], code: str, **details: Any) -> None:
    errors.append({"code": code, **details})


def layout_errors() -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    if not (ROOT / "README.md").is_file():
        add(errors, "campaign_readme_missing")
    specs = ROOT / "specs"
    for name in REQUIRED_SPEC_FILES:
        if not (specs / name).exists():
            add(errors, "mandatory_spec_interface_missing", name=name)
    if not proofs.TARGETS.is_file():
        add(errors, "mandatory_proof_inventory_missing")
        return errors
    rows = load(proofs.TARGETS).get("rows", [])
    proof_root = ROOT / "proof_harnesses"
    if not proof_root.is_dir():
        add(errors, "mandatory_proof_harness_interface_missing")
        return errors
    expected = {proofs.target_dir(row).resolve() for row in rows}
    actual = {
        path.resolve()
        for path in proof_root.iterdir()
        if path.is_dir() or path.is_symlink()
    }
    if expected != actual:
        add(
            errors,
            "proof_harness_interface_identity_mismatch",
            expected=len(expected),
            actual=len(actual),
        )
    prohibited = ("btreemap", "btreeset", "core_result", "result_module")
    for path in ROOT.rglob("*"):
        relative = str(path.relative_to(ROOT)).lower()
        if any(term in relative for term in prohibited):
            add(
                errors,
                "out_of_scope_campaign_artifact",
                path=str(path.relative_to(ROOT)),
            )
    return errors


def active_payload() -> dict[str, Any]:
    inventory = load(specification.INVENTORY)
    aggregate = load(proofs.AGGREGATE_JSON)
    trust = load(proofs.TRUST_AUDIT)
    latest = load(runner.EVIDENCE_ROOT / "latest.json")
    evidence_result = ROOT / latest["run_dir"] / "result.json"
    proof_review = load(proofs.REVIEW)
    rows = inventory["rows"]
    proof_rows = load(proofs.TARGETS)["rows"]
    selected_ids = {row["row_id"] for row in proof_rows}
    catalog_counts = load(specification.CATALOG)["counts"]
    return {
        "schema_version": 1,
        "module": "core::cmp",
        "scope": (
            "exactly the stable executable Rust 1.96 APIs publicly reachable "
            "through core::cmp"
        ),
        "status": "ready_for_final_independent_review",
        "inventory_derived": True,
        "counts": {
            "stable_inventory_total": len(rows),
            "selected": len(proof_rows),
            "generated_contract": sum(
                row["disposition"] == "pending"
                and row["row_id"] in selected_ids
                for row in rows
            ),
            "exact_vstd_contract": sum(
                row["disposition"] == "exact_vstd"
                and row["row_id"] in selected_ids
                for row in rows
            ),
            "genuinely_impossible": catalog_counts[
                "genuinely_impossible"
            ],
            "strict_specification_coverage": catalog_counts[
                "strict_specification_coverage"
            ],
            "implementation_actual_verus_verified": aggregate["counts"][
                "actual_verus_verified"
            ],
            "completeness_actual_verus_verified": aggregate["counts"][
                "actual_verus_verified"
            ],
            "failed": aggregate["counts"]["failed"],
            "pending": aggregate["counts"]["pending"],
            "target_level_external_body": trust["counts"][
                "target_level_external_body"
            ],
            "completeness_level_external_body": trust["counts"][
                "completeness_level_external_body"
            ],
            "implementation_harness_literal_external_body": trust["counts"][
                "implementation_harness_literal_external_body"
            ],
            "completeness_harness_literal_external_body": trust["counts"][
                "completeness_harness_literal_external_body"
            ],
            "helper_dependency_function_external_body": trust["counts"][
                "helper_dependency_function_external_body"
            ],
            "model_or_type_external_body": trust["counts"][
                "model_or_type_external_body"
            ],
            "harness_wide_literal_external_body": trust["counts"][
                "harness_wide_literal_external_body"
            ],
            "no_additional_implementation_dependency_boundary": trust[
                "counts"
            ]["no_additional_implementation_dependency_boundary"],
            "foundational_end_to_end_trust_free": 0,
        },
        "identity_set_sha256": compact_hash(
            sorted(row["row_id"] for row in proof_rows)
        ),
        "stable_inventory_identity_set_sha256": compact_hash(
            sorted(row["row_id"] for row in rows)
        ),
        "artifact_bindings": [
            binding(ROOT / "README.md"),
            binding(provenance.CAMPAIGN_MANIFEST),
            binding(provenance.PRESERVATION_MANIFEST),
            binding(provenance.VALIDATION_RESULT),
            binding(build_inventory.RECONCILIATION_JSON),
            binding(specification.INVENTORY),
            binding(specification.CATALOG),
            binding(specification.FLOAT_MODEL_BOUNDARY),
            binding(check_specification.INDEPENDENT_REVIEW),
            binding(proofs.TARGETS),
            binding(proofs.AGGREGATE_JSON),
            binding(proofs.TRUST_AUDIT),
            binding(proofs.TRUST_MD),
            binding(proofs.MUTATION_SUMMARY),
            binding(runner.EVIDENCE_ROOT / "latest.json"),
            binding(evidence_result),
            binding(proofs.CHECK_REPORT),
            binding(proofs.REVIEW),
        ],
        "review_bindings": {
            "specification": {
                "producer_role": load(
                    check_specification.INDEPENDENT_REVIEW
                )["producer_role"],
                "status": load(check_specification.INDEPENDENT_REVIEW)[
                    "review"
                ]["status"],
            },
            "implementation_and_completeness": {
                "producer_role": proof_review["producer_role"],
                "status": proof_review["review"]["status"],
            },
        },
        "trust_language": trust["language"],
    }


def final_request_payload(active: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "module": "core::cmp",
        "review_type": "final_aggregate",
        "required_verdict": {
            "producer_role": "reviewer",
            "review_status": "done",
            "independent": True,
            "canonical_handoff_required": True,
            "approved_genuinely_impossible_count": active["counts"][
                "genuinely_impossible"
            ],
        },
        "counts": active["counts"],
        "artifacts": [
            binding(ACTIVE),
            binding(proofs.REVIEW),
            binding(check_specification.INDEPENDENT_REVIEW),
            binding(proofs.CHECK_REPORT),
            binding(proofs.AGGREGATE_JSON),
            binding(proofs.TRUST_AUDIT),
            binding(proofs.MUTATION_SUMMARY),
            binding(runner.EVIDENCE_ROOT / "latest.json"),
        ],
        "review_questions": [
            (
                f"Does the selected {active['counts']['selected']}-row identity "
                f"set exactly match the {active['counts']['selected']} "
                "top-level harness children?"
            ),
            (
                f"Are the {active['counts']['genuinely_impossible']} "
                "independently approved float exceptions reported without "
                "proof or mutation coverage credit?"
            ),
            "Are implementation and completeness actual-Verus results fresh and complete for every identity?",
            "Are pending, failed, target external_body, and completeness external_body all zero?",
            "Do mutation evidence and trust accounting match the retained artifacts?",
            "Are generated and exact-vstd counts inventory-derived and canonical/noncanonical vstd provenance preserved?",
            "Are no-additional-boundary claims kept distinct from foundational end-to-end trust-free claims?",
        ],
    }


def final_review_errors() -> list[dict[str, Any]]:
    if not FINAL_REVIEW.is_file():
        return [{"code": "final_aggregate_review_missing"}]
    review = load(FINAL_REVIEW)
    errors: list[dict[str, Any]] = []
    request = load(FINAL_REQUEST)
    if review.get("schema_version") != 1:
        add(errors, "final_review_schema_invalid")
    if review.get("module") != "core::cmp":
        add(errors, "final_review_module_invalid")
    if review.get("review_type") != "final_aggregate":
        add(errors, "final_review_type_invalid")
    if review.get("producer_role") != "reviewer":
        add(errors, "final_reviewer_role_invalid")
    independence = review.get("independence", {})
    if (
        independence.get("independent") is not True
        or independence.get("artifacts_modified_by_reviewer") != []
    ):
        add(errors, "final_review_not_independent")
    decision = review.get("review", {})
    if decision.get("status") != "done":
        add(errors, "final_review_status_not_done")
    if decision.get("unresolved_findings") != []:
        add(errors, "final_review_has_findings")
    if decision.get("final_aggregate_accepted") is not True:
        add(errors, "final_aggregate_not_accepted")
    if decision.get("rejected") not in (None, False):
        add(errors, "final_review_contradictory_rejection")
    questions = request.get("review_questions")
    if not isinstance(questions, list) or not all(
        isinstance(question, str) for question in questions
    ):
        add(errors, "final_review_request_questions_invalid")
        questions = []
    verdicts = decision.get("question_verdicts", [])
    verdict_by_question = question_verdict_map(verdicts)
    if (
        verdict_by_question is None
        or set(verdict_by_question) != set(questions)
        or any(
            verdict_by_question[question] != "satisfied"
            for question in questions
        )
    ):
        add(errors, "final_review_question_set_invalid")
    request_binding = review.get("review_request", {})
    if request_binding != {
        "path": str(FINAL_REQUEST.relative_to(ROOT)),
        "sha256": sha256(FINAL_REQUEST),
    }:
        add(errors, "final_review_request_stale")
    expected = {
        item["path"]: item["sha256"] for item in request["artifacts"]
    }
    actual = artifact_binding_map(review.get("artifact_bindings"))
    if actual is None:
        add(errors, "final_review_artifact_bindings_schema_invalid")
    elif actual != expected:
        add(errors, "final_review_artifacts_stale")
    counts = request["counts"]
    impossible_count = counts.get("genuinely_impossible")
    if not isinstance(impossible_count, int):
        add(errors, "final_review_impossible_count_invalid")
        impossible_count = -1
    if decision.get("accepted_target_count") != counts["selected"]:
        add(errors, "final_review_target_count_mismatch")
    if decision.get("actual_verus_verified") != counts["selected"]:
        add(errors, "final_review_verified_count_mismatch")
    if decision.get("pending") != 0 or decision.get("failed") != 0:
        add(errors, "final_review_nonzero_incomplete_count")
    if (
        decision.get("approved_genuinely_impossible_count")
        != impossible_count
    ):
        add(errors, "final_review_impossible_count_mismatch")
    canonical = review.get("canonical_handoff", {})
    if canonical.get("path") != str(FINAL_REVIEW_HANDOFF.relative_to(ROOT)):
        add(errors, "canonical_final_handoff_path_invalid")
    elif not FINAL_REVIEW_HANDOFF.is_file():
        add(errors, "canonical_final_handoff_missing")
    elif canonical.get("sha256") != sha256(FINAL_REVIEW_HANDOFF):
        add(errors, "canonical_final_handoff_stale")
    else:
        handoff = load(FINAL_REVIEW_HANDOFF)
        handoff_review = handoff.get("review", {})
        mission = handoff.get("mission", {})
        mission_path = Path(str(mission.get("path", "")))
        if (
            handoff.get("producer_role") != "reviewer"
            or handoff_review.get("status") != "done"
            or handoff_review.get("next_action") != ""
            or handoff_review.get("final_aggregate_accepted") is not True
            or handoff_review.get(
                "approved_genuinely_impossible_count"
            )
            != impossible_count
            or handoff_review.get("unresolved_findings") != []
        ):
            add(errors, "canonical_final_handoff_verdict_invalid")
        if handoff.get("review_request") != {
            "path": str(FINAL_REQUEST.relative_to(ROOT)),
            "sha256": sha256(FINAL_REQUEST),
        }:
            add(errors, "canonical_final_handoff_request_stale")
        if handoff.get("artifact_bindings") != request["artifacts"]:
            add(errors, "canonical_final_handoff_artifacts_stale")
        if (
            mission_path != check_specification.MISSION_PATH
            or not mission_path.is_file()
            or mission.get("sha256") != sha256(mission_path)
        ):
            add(errors, "canonical_final_handoff_mission_stale")
    return errors


def validate(*, require_final_review: bool) -> list[dict[str, Any]]:
    if FINAL_DELIVERY.exists():
        FINAL_DELIVERY.unlink()
    errors: list[dict[str, Any]] = []
    try:
        provenance.check_provenance()
        build_inventory.check()
    except (
        provenance.ProvenanceError,
        build_inventory.InventoryError,
        OSError,
    ) as error:
        add(errors, "provenance_or_inventory_gate_failed", detail=str(error))
    errors.extend(layout_errors())
    proof_errors = proofs.validate(
        require_results=True,
        require_mutations=True,
        require_review=True,
    )
    proofs.atomic_json(
        proofs.CHECK_REPORT,
        {
            "schema_version": 1,
            "module": "core::cmp",
            "status": "passed" if not proof_errors else "failed",
            "errors": proof_errors,
            "requirements": {
                "results": True,
                "mutations": True,
                "review": True,
            },
        },
    )
    errors.extend(
        {"code": "implementation_gate_failed", "detail": error}
        for error in proof_errors
    )
    if errors:
        return errors
    active = active_payload()
    counts = active["counts"]
    selected = counts["selected"]
    for key in (
        "implementation_actual_verus_verified",
        "completeness_actual_verus_verified",
    ):
        if counts[key] != selected:
            add(errors, "aggregate_verified_count_mismatch", field=key)
    for key in (
        "failed",
        "pending",
        "target_level_external_body",
        "completeness_level_external_body",
        "foundational_end_to_end_trust_free",
    ):
        if counts[key] != 0:
            add(errors, "aggregate_required_zero_nonzero", field=key)
    if errors:
        return errors
    atomic_json(ACTIVE, active)
    atomic_json(FINAL_REQUEST, final_request_payload(active))
    if require_final_review:
        errors.extend(final_review_errors())
    if errors:
        return errors
    if require_final_review:
        final = {
            **active,
            "status": "accepted",
            "final_review": binding(FINAL_REVIEW),
        }
        certification_id = compact_hash(final)[:16]
        final_path = (
            ROOT
            / "proof_inventory"
            / f"final_aggregate_certification_{certification_id}.json"
        )
        atomic_json(final_path, final)
        delivery = {
            "schema_version": 1,
            "module": "core::cmp",
            "status": "accepted",
            "certification_id": certification_id,
            "final_certification": binding(final_path),
            "final_review": binding(FINAL_REVIEW),
            "selected": selected,
            "stable_inventory_total": counts["stable_inventory_total"],
            "genuinely_impossible": counts["genuinely_impossible"],
            "actual_verus_verified": selected,
            "failed": 0,
            "pending": 0,
        }
        atomic_json(FINAL_DELIVERY, delivery)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-final-review", action="store_true")
    args = parser.parse_args()
    errors = validate(require_final_review=args.require_final_review)
    report = {
        "schema_version": 1,
        "module": "core::cmp",
        "status": "passed" if not errors else "failed",
        "final_review_required": args.require_final_review,
        "errors": errors,
    }
    atomic_json(CHECK_REPORT, report)
    print(json.dumps(report, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
