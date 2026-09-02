#!/usr/bin/env python3
"""Run anti-vacuity, direct, source, signature, and provenance audits."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import sys
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import specification_support as support


SUMMARY_PATH = support.AUDIT_ROOT / "specification_audit_summary.json"


def error(errors: list[dict[str, Any]], code: str, **details: Any) -> None:
    errors.append({"code": code, **details})


def command_argument(command: Any, flag: str) -> str | None:
    if not isinstance(command, list):
        return None
    try:
        index = command.index(flag)
    except ValueError:
        return None
    if index + 1 >= len(command):
        return None
    return str(command[index + 1])


def base_inputs() -> dict[str, str]:
    return {
        "catalog_sha256": support.sha256(support.CATALOG_PATH),
        "checker_sha256": support.sha256(Path(__file__)),
        "contracts_sha256": support.sha256(support.CONTRACT_PATH),
        "derive_expansion_sha256": support.sha256(
            support.DERIVE_AUDIT_PATH
        ),
        "exact_references_sha256": support.sha256(
            support.EXACT_REFERENCES_PATH
        ),
        "exact_vstd_audit_sha256": support.sha256(
            support.EXACT_AUDIT_PATH
        ),
        "feedback_manifest_sha256": support.sha256(
            support.FEEDBACK_MANIFEST_PATH
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
        "feedback_diagnostic_bindings_sha256": (
            support.feedback_diagnostic_binding_set()["set_sha256"]
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
        "inventory_sha256": support.sha256(support.INVENTORY_PATH),
        "outcome_equivalence_sha256": support.sha256(
            support.OUTCOME_EQUIVALENCE_PATH
        ),
        "relation_capability_sha256": support.sha256(
            support.FEEDBACK_RELATION_CAPABILITY_PATH
        ),
        "package_manifest_sha256": support.sha256(
            support.PACKAGE_MANIFEST_PATH
        ),
        "vstd_contracts_sha256": support.sha256(
            support.VSTD_CONTRACTS_PATH
        ),
        "vocabulary_sha256": support.sha256(support.VOCABULARY_PATH),
    }


def report(
    name: str,
    errors: list[dict[str, Any]],
    checked_rows: int,
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "audit": name,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "checked_rows": checked_rows,
        "error_details": errors,
        "errors": sorted({item["code"] for item in errors}),
        "inputs": base_inputs(),
        "schema_version": 1,
        "status": "passed" if not errors else "failed",
        **details,
    }


def semantic_record(block: support.ContractBlock) -> dict[str, list[str]]:
    requires, ensures = support.structured_clauses(block.text)
    return {
        "ensures": [support.squash(clause) for clause in ensures],
        "requires": [support.squash(clause) for clause in requires],
    }


def anti_vacuity_audit() -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for item_id, block in sorted(support.contract_blocks().items()):
        try:
            semantic = semantic_record(block)
        except Exception as exception:
            error(
                errors,
                "contract_parse_error",
                rustdoc_item_id=item_id,
                message=str(exception),
            )
            continue
        requires = semantic["requires"]
        ensures = semantic["ensures"]
        row_errors: list[str] = []
        if not ensures:
            row_errors.append("missing_ensures")
        if any(clause in {"false", "(false)"} for clause in requires):
            row_errors.append("false_requires")
        if any(clause in {"true", "(true)"} for clause in ensures):
            row_errors.append("true_ensures")
        combined = " ".join(requires + ensures)
        if "arbitrary(" in combined:
            row_errors.append("arbitrary_output")
        if "result" not in combined and "final(" not in combined:
            row_errors.append("no_output_or_post_state_constraint")
        if len(ensures) == 1 and re.fullmatch(
            r"result_[A-Za-z0-9_]+\(.*result.*\)", ensures[0]
        ):
            row_errors.append("whole_target_relation_only")
        for code in row_errors:
            error(errors, code, rustdoc_item_id=item_id)
        records.append(
            {
                "ensures_count": len(ensures),
                "issues": row_errors,
                "requires_count": len(requires),
                "rustdoc_item_id": item_id,
                "status": "passed" if not row_errors else "failed",
            }
        )
    return report(
        "anti_vacuity",
        errors,
        len(records),
        {"records": records},
    )


def direct_errors(
    item_id: int,
    block_text: str,
    expected_semantic_sha256: str | None = None,
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    normalized = support.squash(block_text)
    for fragment in support.DIRECT_FRAGMENTS[item_id]:
        if support.squash(fragment) not in normalized:
            error(
                errors,
                "required_direct_fragment_missing",
                fragment=fragment,
                rustdoc_item_id=item_id,
            )
    forbidden = (
        "ensures true",
        "requires false",
        "result_target_semantics(",
        "result_contract_holds(",
        "result_whole_outcome(",
        "result_deref_mut_projection(",
        "result_delegate_trace(",
    )
    for fragment in forbidden:
        if fragment in normalized:
            error(
                errors,
                "forbidden_semantic_placeholder",
                fragment=fragment,
                rustdoc_item_id=item_id,
            )
    try:
        semantic = semantic_record(
            support.ContractBlock(item_id, block_text, 0, 0)
        )
    except Exception as exception:
        error(
            errors,
            "contract_parse_error",
            rustdoc_item_id=item_id,
            message=str(exception),
        )
        return errors
    if expected_semantic_sha256 is not None:
        actual_hash = support.object_sha256(semantic)
        if actual_hash != expected_semantic_sha256:
            error(
                errors,
                "semantic_clause_hash_mismatch",
                actual=actual_hash,
                expected=expected_semantic_sha256,
                rustdoc_item_id=item_id,
            )
    if item_id in support.CALLBACK_IDS:
        combined = " ".join(
            semantic["requires"] + semantic["ensures"]
        )
        if ".requires" not in combined or ".ensures" not in combined:
            error(
                errors,
                "callback_contract_incomplete",
                rustdoc_item_id=item_id,
            )
    if item_id in support.UNSAFE_IDS:
        expected = "input is Ok" if item_id == 29308 else "input is Err"
        if expected not in semantic["requires"]:
            error(
                errors,
                "unsafe_domain_missing",
                rustdoc_item_id=item_id,
            )
    if item_id in support.MUTABLE_PROJECTION_IDS:
        combined = " ".join(semantic["ensures"])
        if "final(" not in combined:
            error(
                errors,
                "mutable_post_state_missing",
                rustdoc_item_id=item_id,
            )
    if item_id in support.SHORT_CIRCUIT_IDS:
        combined = " ".join(semantic["ensures"])
        if "result_short_circuit_trace" not in combined:
            error(
                errors,
                "short_circuit_trace_missing",
                rustdoc_item_id=item_id,
            )
        if ").len() == stop + 1" not in combined:
            error(
                errors,
                "short_circuit_consumption_boundary_missing",
                rustdoc_item_id=item_id,
            )
    return errors


def direct_ensures_audit() -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    catalog = support.load_json(support.CATALOG_PATH)
    rows = {
        int(row["rustdoc_item_id"]): row
        for row in catalog["rows"]
        if row["disposition"] == "generated"
    }
    records: list[dict[str, Any]] = []
    for item_id, block in sorted(support.contract_blocks().items()):
        expected_hash = rows[item_id]["contract"][
            "semantic_clause_sha256"
        ]
        row_errors = direct_errors(item_id, block.text, expected_hash)
        errors.extend(row_errors)
        records.append(
            {
                "required_fragment_count": len(
                    support.DIRECT_FRAGMENTS[item_id]
                ),
                "rustdoc_item_id": item_id,
                "status": "passed" if not row_errors else "failed",
            }
        )
    return report(
        "direct_ensures",
        errors,
        len(records),
        {
            "forbidden_whole_target_helpers": [
                "result_target_semantics",
                "result_contract_holds",
                "result_whole_outcome",
                "result_deref_mut_projection",
                "result_delegate_trace",
            ],
            "records": records,
        },
    )


def source_fidelity_audit() -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    captures = support.derived_captures()
    expanded_data = support.DERIVE_SOURCE_PATH.read_bytes()
    records: list[dict[str, Any]] = []
    for row in support.inventory_rows():
        item_id = int(row["rustdoc_item_id"])
        frozen = support.frozen_source_for(row)
        row_errors: list[str] = []
        if support.sha256(frozen) != row["source_file_sha256"]:
            row_errors.append("source_file_hash_mismatch")
        excerpt = support.source_excerpt(frozen, row)
        if support.text_sha256(excerpt) != row["source_excerpt_sha256"]:
            row_errors.append("source_excerpt_hash_mismatch")
        if item_id in support.generated_ids():
            if item_id in support.DERIVED_IDS:
                capture = captures.get(item_id)
                if capture is None:
                    row_errors.append("derive_capture_missing")
                else:
                    span = capture["expanded_method"]
                    selected = expanded_data[
                        int(span["start_byte"]) : int(span["end_byte"])
                    ]
                    if (
                        hashlib.sha256(selected).hexdigest()
                        != span["sha256"]
                    ):
                        row_errors.append("derive_method_hash_mismatch")
                    expanded_text = selected.decode("utf-8")
                    for marker, required in capture[
                        "semantic_markers"
                    ].items():
                        if required and marker not in expanded_text:
                            row_errors.append(
                                f"derive_marker_missing:{marker}"
                            )
            else:
                normalized_source = support.squash(excerpt)
                for fragment in support.SOURCE_FRAGMENTS[item_id]:
                    if support.squash(fragment) not in normalized_source:
                        row_errors.append(
                            f"source_fragment_missing:{fragment}"
                        )
        for code in row_errors:
            error(errors, code, rustdoc_item_id=item_id)
        records.append(
            {
                "derive_backed": item_id in support.DERIVED_IDS,
                "rustdoc_item_id": item_id,
                "source_excerpt_sha256": row["source_excerpt_sha256"],
                "status": "passed" if not row_errors else "failed",
            }
        )
    return report(
        "source_fidelity",
        errors,
        len(records),
        {
            "derive_capture_count": len(captures),
            "records": records,
        },
    )


def signature_audit() -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    inventory = support.inventory_by_id()
    blocks = support.contract_blocks()
    catalog = support.load_json(support.CATALOG_PATH)
    catalog_rows = {
        int(row["rustdoc_item_id"]): row for row in catalog["rows"]
    }
    references = support.load_json(support.EXACT_REFERENCES_PATH)
    reference_rows = {
        int(row["rustdoc_item_id"]): row
        for row in references["references"]
    }
    if set(blocks) != support.generated_ids():
        error(
            errors,
            "generated_marker_set_mismatch",
            missing=sorted(support.generated_ids() - set(blocks)),
            extra=sorted(set(blocks) - support.generated_ids()),
        )
    if set(reference_rows) != support.exact_ids():
        error(
            errors,
            "exact_reference_set_mismatch",
            missing=sorted(support.exact_ids() - set(reference_rows)),
            extra=sorted(set(reference_rows) - support.exact_ids()),
        )
    if set(catalog_rows) != set(inventory):
        error(errors, "catalog_inventory_set_mismatch")
    records: list[dict[str, Any]] = []
    for item_id, inventory_row in sorted(inventory.items()):
        row_errors: list[str] = []
        catalog_row = catalog_rows.get(item_id)
        if catalog_row is None:
            row_errors.append("catalog_row_missing")
        else:
            for field in ("target", "signature", "signature_shape_sha256"):
                if catalog_row.get(field) != inventory_row.get(field):
                    row_errors.append(f"{field}_mismatch")
        if item_id in blocks:
            actual_binding = support.binding_text(blocks[item_id])
            expected_binding = support.squash(
                support.BINDING_FRAGMENTS[item_id]
            )
            if actual_binding != expected_binding:
                row_errors.append("target_binding_mismatch")
        for code in row_errors:
            error(errors, code, rustdoc_item_id=item_id)
        records.append(
            {
                "disposition": (
                    catalog_row["disposition"] if catalog_row else None
                ),
                "rustdoc_item_id": item_id,
                "signature_shape_sha256": inventory_row[
                    "signature_shape_sha256"
                ],
                "status": "passed" if not row_errors else "failed",
                "target": inventory_row["target"],
            }
        )
    return report(
        "signature",
        errors,
        len(records),
        {"records": records},
    )


def provenance_audit() -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    catalog = support.load_json(support.CATALOG_PATH)
    expected_inputs = {
        "derive_expansion_sha256": support.sha256(
            support.DERIVE_AUDIT_PATH
        ),
        "exact_vstd_audit_sha256": support.sha256(
            support.EXACT_AUDIT_PATH
        ),
        "generated_contracts_sha256": support.sha256(
            support.CONTRACT_PATH
        ),
        "helper_usage_sha256": support.sha256(
            support.HELPER_USAGE_PATH
        ),
        "inventory_sha256": support.sha256(support.INVENTORY_PATH),
        "outcome_equivalence_sha256": support.sha256(
            support.OUTCOME_EQUIVALENCE_PATH
        ),
        "relation_capability_sha256": support.sha256(
            support.FEEDBACK_RELATION_CAPABILITY_PATH
        ),
        "shared_vocabulary_sha256": support.sha256(
            support.VOCABULARY_PATH
        ),
    }
    if catalog.get("inputs") != expected_inputs:
        error(errors, "catalog_input_hash_mismatch")
    exact_audit = support.load_json(support.EXACT_AUDIT_PATH)
    declarations = {
        str(row["declaration_id"]): row
        for row in exact_audit["declarations"]
    }
    references = support.load_json(support.EXACT_REFERENCES_PATH)
    records: list[dict[str, Any]] = []
    for reference in references["references"]:
        declaration = declarations.get(reference["declaration_id"])
        row_errors: list[str] = []
        if declaration is None:
            row_errors.append("exact_declaration_missing")
        else:
            path = support.ROOT / declaration["source_path"]
            if support.sha256(path) != declaration["source_sha256"]:
                row_errors.append("exact_source_hash_mismatch")
            text = support.extract_lines(
                path,
                int(declaration["start_line"]),
                int(declaration["end_line"]),
            ).rstrip("\n")
            if support.text_sha256(text) != declaration[
                "declaration_sha256"
            ]:
                row_errors.append("exact_declaration_hash_mismatch")
        for code in row_errors:
            error(
                errors,
                code,
                rustdoc_item_id=reference["rustdoc_item_id"],
            )
        records.append(
            {
                "declaration_id": reference["declaration_id"],
                "rustdoc_item_id": reference["rustdoc_item_id"],
                "status": "passed" if not row_errors else "failed",
            }
        )
    return report(
        "provenance",
        errors,
        len(records),
        {
            "catalog_inputs": expected_inputs,
            "exact_reference_records": records,
        },
    )


def helper_usage_audit() -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    payload = support.load_json(support.HELPER_USAGE_PATH)
    raw_records = payload.get("records")
    if not isinstance(raw_records, list):
        error(errors, "helper_usage_records_malformed")
        raw_records = []
    records_by_name = {
        str(record.get("helper")): record
        for record in raw_records
        if isinstance(record, dict)
    }
    expected_helpers = support.helper_names()
    if set(records_by_name) != expected_helpers:
        error(
            errors,
            "helper_usage_set_mismatch",
            extra=sorted(set(records_by_name) - expected_helpers),
            missing=sorted(expected_helpers - set(records_by_name)),
        )
    inventory = support.inventory_by_id()
    blocks = support.contract_blocks()
    expected_users: dict[str, list[int]] = {
        helper: [] for helper in expected_helpers
    }
    for item_id, block in sorted(blocks.items()):
        for helper in support.used_helpers(block):
            expected_users[helper].append(item_id)
    linked_to = {
        "result_into_iter_value_values": "result_into_iter_values",
        "result_iter_mut_value_identities": "result_iter_mut_identities",
        "result_iter_mut_value_values": "result_iter_mut_values",
        "result_iter_value_identities": "result_iter_identities",
        "result_iter_value_values": "result_iter_values",
    }
    checked_records: list[dict[str, Any]] = []
    for helper in sorted(expected_helpers):
        record = records_by_name.get(helper)
        row_errors: list[str] = []
        if record is None:
            continue
        classification, boundary = support.helper_classification(helper)
        item_ids = expected_users[helper]
        expected = {
            "boundary": boundary,
            "classification": classification,
            "helper": helper,
            "linked_to": linked_to.get(helper),
            "rustdoc_item_ids": item_ids,
            "target_count": len(item_ids),
            "targets": [inventory[item_id]["target"] for item_id in item_ids],
        }
        if record != expected:
            row_errors.append("helper_usage_record_mismatch")
        if not item_ids:
            row_errors.append("shared_helper_unused")
        for code in row_errors:
            error(errors, code, helper=helper)
        checked_records.append(
            {
                "classification": classification,
                "helper": helper,
                "status": "passed" if not row_errors else "failed",
                "target_count": len(item_ids),
            }
        )

    vocabulary = support.VOCABULARY_PATH.read_text(encoding="utf-8")
    for helper, borrowed in linked_to.items():
        pattern = (
            rf"pub\s+open\s+spec\s+fn\s+{re.escape(helper)}\b"
            rf".*?\{{\s*{re.escape(borrowed)}\(&iter\)\s*\}}"
        )
        if re.search(pattern, vocabulary, re.DOTALL) is None:
            error(
                errors,
                "iterator_projection_link_missing",
                helper=helper,
                linked_to=borrowed,
            )
        if re.search(
            rf"pub\s+uninterp\s+spec\s+fn\s+{re.escape(helper)}\b",
            vocabulary,
        ):
            error(
                errors,
                "iterator_projection_link_uninterpreted",
                helper=helper,
            )

    forbidden = {
        "result_contract_holds",
        "result_delegate_trace",
        "result_deref_mut_projection",
        "result_target_semantics",
        "result_whole_outcome",
    }
    present_forbidden = sorted(forbidden & expected_helpers)
    if present_forbidden:
        error(
            errors,
            "whole_target_helpers_present",
            helpers=present_forbidden,
        )
    if payload.get("defined_helper_count") != len(expected_helpers):
        error(errors, "helper_usage_count_mismatch")
    if payload.get("generated_target_count") != len(blocks):
        error(errors, "helper_usage_target_count_mismatch")
    if payload.get("unused_helpers") != []:
        error(errors, "helper_usage_unused_not_empty")
    if payload.get("whole_target_helpers") != []:
        error(errors, "helper_usage_whole_target_not_empty")
    if payload.get("contracts_sha256") != support.sha256(
        support.CONTRACT_PATH
    ):
        error(errors, "helper_usage_contract_binding_stale")
    if payload.get("vocabulary_sha256") != support.sha256(
        support.VOCABULARY_PATH
    ):
        error(errors, "helper_usage_vocabulary_binding_stale")
    return report(
        "helper_usage",
        errors,
        len(checked_records),
        {
            "classification_counts": dict(
                sorted(
                    Counter(
                        record["classification"]
                        for record in checked_records
                    ).items()
                )
            ),
            "records": checked_records,
        },
    )


def outcome_equivalence_audit() -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    payload = support.load_json(support.OUTCOME_EQUIVALENCE_PATH)
    raw_records = payload.get("records")
    if not isinstance(raw_records, list):
        error(errors, "outcome_equivalence_records_malformed")
        raw_records = []
    records = {
        int(record["rustdoc_item_id"]): record
        for record in raw_records
        if isinstance(record, dict) and "rustdoc_item_id" in record
    }
    if len(records) != len(raw_records):
        error(errors, "outcome_equivalence_duplicate_or_malformed_records")
    inventory = support.inventory_by_id()
    catalog = support.load_json(support.CATALOG_PATH)
    catalog_rows = {
        int(row["rustdoc_item_id"]): row for row in catalog["rows"]
    }
    if set(records) != set(inventory):
        error(
            errors,
            "outcome_equivalence_target_set_mismatch",
            extra=sorted(set(records) - set(inventory)),
            missing=sorted(set(inventory) - set(records)),
        )
    checked_records: list[dict[str, Any]] = []
    for item_id, inventory_row in sorted(inventory.items()):
        record = records.get(item_id)
        row_errors: list[str] = []
        if record is None:
            continue
        expected = support.outcome_equivalence_record(inventory_row)
        if record != expected:
            row_errors.append("outcome_equivalence_record_mismatch")
        unhashed = {
            key: value
            for key, value in record.items()
            if key != "record_sha256"
        }
        if record.get("record_sha256") != support.object_sha256(unhashed):
            row_errors.append("outcome_equivalence_record_hash_stale")
        expected_kind = "exact_equality"
        if record.get("kind") != expected_kind:
            row_errors.append("outcome_equivalence_kind_mismatch")
        observation_schema = (
            support.PROJECTED_EXACT_OBSERVATION_SCHEMAS.get(item_id)
        )
        schema = record.get("proof_observation_schema")
        if observation_schema is None:
            if (
                record.get("non_exact_justification") is not None
                or record.get("equality_scope")
                != "complete_output_and_explicit_post_state"
                or record.get("observation_schema_id")
                != "complete-output-and-explicit-post-state-v1"
                or record.get("proof_observation_schema")
                != {"mode": "exact_result_and_explicit_post_state"}
            ):
                row_errors.append("exact_equivalence_record_malformed")
        else:
            component_bindings = record.get(
                "component_contract_bindings"
            )
            if (
                record.get("non_exact_justification") is not None
                or record.get("equality_scope")
                != "source_backed_observation_schema"
                or record.get("observation_schema_id")
                != (
                    f"core-result-rustdoc-{item_id}-"
                    f"{observation_schema}-"
                    "observations-v1"
                )
                or not isinstance(schema, dict)
                or schema.get("mode")
                != "exact_componentwise_source_observation_equality"
                or schema.get("components")
                != record.get("observable_components")
                or not schema.get("source_basis")
                or not schema.get("representation_boundary")
                or record.get("observable_components")
                != list(support.TARGET_OBSERVATION_COMPONENTS[item_id])
                or not isinstance(component_bindings, dict)
                or set(component_bindings)
                != set(record.get("observable_components", []))
            ):
                row_errors.append(
                    "projected_exact_equivalence_record_malformed"
                )
            else:
                contract = catalog_rows[item_id]["contract"]
                contract_text = " ".join(
                    [
                        *contract.get("requires", []),
                        *contract.get("direct_ensures", []),
                    ]
                )
                for component, anchors in component_bindings.items():
                    if (
                        not isinstance(anchors, list)
                        or not anchors
                        or any(
                            not isinstance(anchor, str)
                            or anchor not in contract_text
                            for anchor in anchors
                        )
                    ):
                        row_errors.append(
                            "projected_exact_component_binding_missing"
                        )
                        break
        identity = support.outcome_equivalence_identity(item_id)
        if any(record.get(key) != value for key, value in identity.items()):
            row_errors.append("outcome_equivalence_version_malformed")
        components = record.get("observable_components")
        if not isinstance(components, list) or not components:
            row_errors.append("outcome_equivalence_components_malformed")
            components = []
        equivalence_id = str(identity["equivalence_id"])
        for witness_name, expected_related in (
            ("positive_witness", True),
            ("negative_witness", False),
        ):
            witness = record.get(witness_name)
            if not isinstance(witness, dict):
                row_errors.append(
                    f"outcome_equivalence_{witness_name}_malformed"
                )
                continue
            left = witness.get("left_observations")
            right = witness.get("right_observations")
            if (
                not isinstance(left, dict)
                or not isinstance(right, dict)
                or set(left) != set(components)
                or set(right) != set(components)
            ):
                row_errors.append(
                    f"outcome_equivalence_{witness_name}_observations_malformed"
                )
                continue
            if observation_schema is not None and any(
                isinstance(value, str)
                and value.startswith(f"{equivalence_id}:observable-")
                for value in [*left.values(), *right.values()]
            ):
                row_errors.append(
                    "projected_exact_witness_uses_symbolic_placeholder"
                )
            actual_related = left == right
            if (
                witness.get("expected_equivalent") is not expected_related
                or actual_related is not expected_related
                or witness.get("left_candidate")
                == witness.get("right_candidate")
            ):
                row_errors.append(
                    f"outcome_equivalence_{witness_name}_verdict_mismatch"
                )
            if witness_name == "negative_witness":
                distinguishing = witness.get("distinguishing_component")
                differences = [
                    component
                    for component in components
                    if left[component] != right[component]
                ]
                if differences != [distinguishing]:
                    row_errors.append(
                        "outcome_equivalence_negative_witness_not_minimal"
                    )
        inequality_witnesses = record.get(
            "component_inequality_witnesses"
        )
        if (
            not isinstance(inequality_witnesses, list)
            or len(inequality_witnesses) != len(components)
            or (
                inequality_witnesses
                and record.get("negative_witness")
                != inequality_witnesses[0]
            )
        ):
            row_errors.append(
                "outcome_equivalence_component_witness_set_malformed"
            )
        else:
            for component, witness in zip(
                components, inequality_witnesses, strict=True
            ):
                if not isinstance(witness, dict):
                    row_errors.append(
                        "outcome_equivalence_component_witness_mismatch"
                    )
                    break
                left = witness.get("left_observations", {})
                right = witness.get("right_observations", {})
                differences = [
                    name
                    for name in components
                    if left.get(name) != right.get(name)
                ]
                if (
                    witness.get("distinguishing_component")
                    != component
                    or witness.get("expected_equivalent") is not False
                    or differences != [component]
                ):
                    row_errors.append(
                        "outcome_equivalence_component_witness_mismatch"
                    )
                    break
        catalog_equivalence = catalog_rows.get(item_id, {}).get(
            "outcome_equivalence", {}
        )
        if catalog_equivalence != support.outcome_equivalence_binding(
            record, payload
        ):
            row_errors.append("catalog_equivalence_binding_mismatch")
        for code in row_errors:
            error(errors, code, rustdoc_item_id=item_id)
        checked_records.append(
            {
                "equivalence_version_id": identity[
                    "equivalence_version_id"
                ],
                "kind": expected_kind,
                "rustdoc_item_id": item_id,
                "status": "passed" if not row_errors else "failed",
            }
        )
    kind_counts = Counter(
        record["kind"] for record in records.values()
    )
    if payload.get("kind_counts") != dict(sorted(kind_counts.items())):
        error(errors, "outcome_equivalence_counts_stale")
    if payload.get("exact_equality_count") != len(records):
        error(errors, "outcome_equivalence_exact_count_stale")
    if payload.get("exact_observation_schema_equality_count") != len(
        support.PROJECTED_EXACT_OBSERVATION_SCHEMAS
    ):
        error(
            errors,
            "outcome_equivalence_observation_schema_count_stale",
        )
    if payload.get("non_exact_equivalence_count") != 0:
        error(errors, "outcome_equivalence_non_exact_count_stale")
    if payload.get("inventory_sha256") != support.sha256(
        support.INVENTORY_PATH
    ):
        error(errors, "outcome_equivalence_inventory_binding_stale")
    if payload.get("schema_version") != 3:
        error(errors, "outcome_equivalence_schema_version_mismatch")
    if payload.get("version_set_sha256") != (
        support.outcome_equivalence_version_set_sha256(
            list(records.values())
        )
    ):
        error(errors, "outcome_equivalence_version_set_stale")
    return report(
        "outcome_equivalence",
        errors,
        len(checked_records),
        {
            "kind_counts": dict(sorted(kind_counts.items())),
            "records": checked_records,
        },
    )


def artifact_integrity_audit() -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    payload = support.load_json(support.PACKAGE_MANIFEST_PATH)
    raw_artifacts = payload.get("artifacts")
    if not isinstance(raw_artifacts, list):
        error(errors, "package_manifest_artifacts_malformed")
        raw_artifacts = []
    artifacts = {
        str(record.get("path")): record
        for record in raw_artifacts
        if isinstance(record, dict)
    }
    expected_paths = set(support.SPEC_PACKAGE_ARTIFACTS)
    if set(artifacts) != expected_paths:
        error(
            errors,
            "package_manifest_artifact_set_mismatch",
            extra=sorted(set(artifacts) - expected_paths),
            missing=sorted(expected_paths - set(artifacts)),
        )
    records: list[dict[str, Any]] = []
    for relative in support.SPEC_PACKAGE_ARTIFACTS:
        path = support.ROOT / relative
        row_errors: list[str] = []
        artifact = artifacts.get(relative)
        if not path.is_file():
            row_errors.append("package_artifact_missing")
        elif artifact is None or artifact.get("sha256") != support.sha256(path):
            row_errors.append("package_artifact_hash_stale")
        for code in row_errors:
            error(errors, code, path=relative)
        records.append(
            {
                "path": relative,
                "status": "passed" if not row_errors else "failed",
            }
        )
    catalog = support.load_json(support.CATALOG_PATH)
    counts = catalog["counts"]
    expected_counts = {
        "exact_vstd": counts["exact_vstd"],
        "generated": counts["generated"],
        "specified": counts["specified"],
    }
    if payload.get("counts") != expected_counts:
        error(errors, "package_manifest_counts_stale")
    if payload.get("module") != "core::result":
        error(errors, "package_manifest_module_mismatch")
    if payload.get("proof_harnesses_authorized") is not False:
        error(errors, "package_manifest_premature_proof_authorization")
    if (support.ROOT / "proof_harnesses").exists():
        error(errors, "proof_harnesses_created_before_reviewer_gate")
    return report(
        "artifact_integrity",
        errors,
        len(records),
        {"records": records},
    )


def feedback_determinism_audit() -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    summary = support.load_json(support.FEEDBACK_SUMMARY_PATH)
    binding = support.load_json(support.FEEDBACK_RUN_BINDING_PATH)
    manifest = support.load_json(support.FEEDBACK_MANIFEST_PATH)
    seeds = support.load_json(support.FEEDBACK_SEED_PATH)
    equivalence = support.load_json(support.OUTCOME_EQUIVALENCE_PATH)
    relation_capability = support.load_json(
        support.FEEDBACK_RELATION_CAPABILITY_PATH
    )
    expected_relation_capability = (
        support.feedback_relation_capability_payload(equivalence)
    )
    if relation_capability != expected_relation_capability:
        error(errors, "feedback_relation_capability_stale")
    equivalence_records = {
        str(record["target"]): record
        for record in equivalence["records"]
        if isinstance(record, dict)
    }
    common_equivalence_binding = (
        support.outcome_equivalence_artifact_binding(equivalence)
    )
    common_relation_capability = (
        support.feedback_relation_capability_binding(
            relation_capability
        )
    )
    diagnostic_bindings = support.feedback_diagnostic_binding_set()
    catalog = support.load_json(support.CATALOG_PATH)
    catalog_by_target = {
        str(row["target"]): row
        for row in catalog["rows"]
        if row["disposition"] == "generated"
    }
    expected_targets = set(catalog_by_target)
    raw_manifest_targets = manifest.get("targets")
    manifest_targets = {
        str(row.get("target")): row
        for row in raw_manifest_targets
        if isinstance(row, dict)
    } if isinstance(raw_manifest_targets, list) else {}
    raw_candidates = summary.get("final_candidates")
    if not isinstance(raw_candidates, list):
        error(errors, "feedback_candidates_malformed")
        raw_candidates = []
    candidates = {
        str(candidate.get("target")): candidate
        for candidate in raw_candidates
        if isinstance(candidate, dict)
    }
    if len(candidates) != len(raw_candidates):
        error(errors, "feedback_duplicate_or_malformed_candidates")
    if set(candidates) != expected_targets:
        error(
            errors,
            "feedback_target_set_mismatch",
            extra=sorted(set(candidates) - expected_targets),
            missing=sorted(expected_targets - set(candidates)),
        )
    taxonomy = Counter()
    canonical_taxonomy = Counter()
    records: list[dict[str, Any]] = []
    fatal_statuses = {"runner_crash", "verus_error"}
    projection_adjudication = support.load_json(
        support.FROM_ITER_ADJUDICATION_PATH
    )
    for target in sorted(expected_targets):
        item_id = int(catalog_by_target[target]["rustdoc_item_id"])
        candidate = candidates.get(target)
        row_errors: list[str] = []
        classification = "missing"
        canonical_classification = "missing"
        if candidate is None:
            row_errors.append("feedback_candidate_missing")
        else:
            if candidate.get("decision") != "add_spec":
                row_errors.append("feedback_non_add_spec")
            if candidate.get("typecheck_status") != "pass":
                row_errors.append("feedback_typecheck_failed")
            expected_requires = catalog_by_target[target]["contract"][
                "requires"
            ]
            expected_ensures = catalog_by_target[target]["contract"][
                "direct_ensures"
            ]
            actual_requires = [
                support.squash(str(clause))
                for clause in candidate.get("requires", [])
            ]
            actual_ensures = [
                support.squash(str(clause))
                for clause in candidate.get("ensures", [])
            ]
            if actual_requires != expected_requires:
                row_errors.append("feedback_requires_mismatch")
            if actual_ensures != expected_ensures:
                row_errors.append("feedback_ensures_mismatch")
            equivalence_record = equivalence_records.get(target)
            expected_equivalence = (
                support.outcome_equivalence_binding(
                    equivalence_record, equivalence
                )
                if equivalence_record is not None
                else None
            )
            if expected_equivalence is None:
                row_errors.append("feedback_equivalence_record_missing")
            else:
                expected_relation_evaluation = (
                    support.feedback_relation_target_classification(
                        expected_equivalence,
                        relation_capability,
                    )
                )
                if (
                    candidate.get("outcome_equivalence")
                    != expected_equivalence
                ):
                    row_errors.append(
                        "feedback_candidate_equivalence_binding_mismatch"
                    )
                if (
                    manifest_targets.get(target, {}).get(
                        "outcome_equivalence"
                    )
                    != expected_equivalence
                ):
                    row_errors.append(
                        "feedback_manifest_equivalence_binding_mismatch"
                    )
                if (
                    seeds.get(target, {}).get("outcome_equivalence")
                    != expected_equivalence
                ):
                    row_errors.append(
                        "feedback_seed_equivalence_binding_mismatch"
                    )
                if candidate.get(
                    "selected_relation_evaluation"
                ) != expected_relation_evaluation:
                    row_errors.append(
                        "feedback_candidate_relation_capability_mismatch"
                    )
                if manifest_targets.get(target, {}).get(
                    "selected_relation_evaluation"
                ) != expected_relation_evaluation:
                    row_errors.append(
                        "feedback_manifest_relation_capability_mismatch"
                    )
                if seeds.get(target, {}).get(
                    "selected_relation_evaluation"
                ) != expected_relation_evaluation:
                    row_errors.append(
                        "feedback_seed_relation_capability_mismatch"
                    )
                target_root = (
                    support.FEEDBACK_ROOT
                    / "targets"
                    / support.safe_name(target)
                )
                raw_target_path = target_root / "target.json"
                if not raw_target_path.is_file():
                    row_errors.append("feedback_raw_target_missing")
                else:
                    raw_target = support.load_json(raw_target_path)
                    if (
                        raw_target.get("outcome_equivalence")
                        != expected_equivalence
                    ):
                        row_errors.append(
                            "feedback_raw_target_equivalence_"
                            "binding_mismatch"
                        )
                    if raw_target.get(
                        "selected_relation_evaluation"
                    ) != expected_relation_evaluation:
                        row_errors.append(
                            "feedback_raw_target_relation_"
                            "capability_mismatch"
                        )
                round_dirs = sorted(
                    path
                    for path in target_root.glob("round_*")
                    if path.is_dir()
                )
                if not round_dirs:
                    row_errors.append("feedback_rounds_missing")
                for round_dir in round_dirs:
                    raw_candidate_path = round_dir / "candidate.json"
                    if not raw_candidate_path.is_file():
                        row_errors.append(
                            "feedback_raw_candidate_missing"
                        )
                    else:
                        raw_candidate = support.load_json(
                            raw_candidate_path
                        )
                        if raw_candidate.get(
                            "outcome_equivalence"
                        ) != expected_equivalence:
                            row_errors.append(
                                "feedback_raw_candidate_equivalence_"
                                "binding_mismatch"
                            )
                        if raw_candidate.get(
                            "selected_relation_evaluation"
                        ) != expected_relation_evaluation:
                            row_errors.append(
                                "feedback_raw_candidate_relation_"
                                "capability_mismatch"
                            )
                    round_result_path = (
                        round_dir / "round_result.json"
                    )
                    if round_result_path.is_file():
                        round_result = support.load_json(
                            round_result_path
                        )
                        round_candidate = round_result.get("candidate")
                        if (
                            round_result.get(
                                "canonical_evidence_role"
                            )
                            != "diagnostic_only"
                            or round_result.get(
                                "selected_relation_evaluation"
                            )
                            != expected_relation_evaluation
                            or not isinstance(round_candidate, dict)
                            or round_candidate.get(
                                "outcome_equivalence"
                            )
                            != expected_equivalence
                        ):
                            row_errors.append(
                                "feedback_round_result_"
                                "diagnostic_binding_mismatch"
                            )
                    diagnostic_path = (
                        round_dir
                        / support.FEEDBACK_DIAGNOSTIC_BINDING_FILENAME
                    )
                    if not diagnostic_path.is_file():
                        row_errors.append(
                            "feedback_round_diagnostic_binding_missing"
                        )
                    elif support.load_json(diagnostic_path) != (
                        support.feedback_round_diagnostic_binding(
                            target,
                            round_dir,
                            expected_equivalence,
                            expected_relation_evaluation,
                        )
                    ):
                        row_errors.append(
                            "feedback_round_diagnostic_binding_stale"
                        )
                target_summary_path = (
                    target_root / "summary.json"
                )
                if not target_summary_path.is_file():
                    row_errors.append("feedback_raw_summary_missing")
                else:
                    target_summary = support.load_json(
                        target_summary_path
                    )
                    target_final = target_summary.get("final")
                    target_final_candidate = (
                        target_final.get("candidate")
                        if isinstance(target_final, dict)
                        else None
                    )
                    if (
                        target_summary.get(
                            "selected_relation_evaluation"
                        )
                        != expected_relation_evaluation
                        or not isinstance(target_final_candidate, dict)
                        or target_final_candidate.get(
                            "outcome_equivalence"
                        )
                        != expected_equivalence
                        or target_final_candidate.get(
                            "selected_relation_evaluation"
                        )
                        != expected_relation_evaluation
                    ):
                        row_errors.append(
                            "feedback_raw_summary_relation_"
                            "capability_mismatch"
                        )
                    for target_history in target_summary.get(
                        "history", []
                    ):
                        target_history_candidate = (
                            target_history.get("candidate")
                            if isinstance(target_history, dict)
                            else None
                        )
                        if (
                            isinstance(target_history_candidate, dict)
                            and (
                                target_history_candidate.get(
                                    "outcome_equivalence"
                                )
                                != expected_equivalence
                                or target_history_candidate.get(
                                    "selected_relation_evaluation"
                                )
                                != expected_relation_evaluation
                            )
                        ):
                            row_errors.append(
                                "feedback_raw_summary_history_"
                                "binding_mismatch"
                            )
                            break
            det_status = str(candidate.get("det_status") or "")
            r0_z3 = str(candidate.get("r0_z3") or "")
            projection_adjudicated = (
                item_id == 26942
                and det_status == "verus_error"
                and projection_adjudication.get("status") == "passed"
                and projection_adjudication.get("adjudication")
                == "unsupported_projection_lowering"
                and projection_adjudication.get("feedback_batch_sha256")
                == support.sha256(support.FEEDBACK_SUMMARY_PATH)
                and projection_adjudication.get("projection_probe_sha256")
                == support.sha256(support.FROM_ITER_PROBE_REPORT_PATH)
            )
            if projection_adjudicated:
                canonical_classification = (
                    "unsupported_projection_lowering"
                )
            elif det_status in fatal_statuses:
                row_errors.append("feedback_fatal_checker_status")
                canonical_classification = det_status
            elif r0_z3 == "sat":
                canonical_classification = "sat"
            elif r0_z3 == "unsat":
                canonical_classification = "unsat"
            elif r0_z3 == "unknown":
                canonical_classification = "unknown"
            elif det_status:
                canonical_classification = "unsupported_or_no_smt"
            else:
                row_errors.append("feedback_determinism_status_missing")
            if expected_equivalence is not None:
                classification = "selected_relation_unsupported"
        taxonomy[classification] += 1
        canonical_taxonomy[canonical_classification] += 1
        for code in row_errors:
            error(errors, code, rustdoc_item_id=item_id, target=target)
        records.append(
            {
                "classification": classification,
                "canonical_checker_classification": (
                    canonical_classification
                ),
                "equivalence_version_id": (
                    equivalence_records.get(target, {}).get(
                        "equivalence_version_id"
                    )
                ),
                "rustdoc_item_id": item_id,
                "status": "passed" if not row_errors else "failed",
                "target": target,
            }
        )

    counts = summary.get("counts")
    if not isinstance(counts, dict):
        error(errors, "feedback_counts_malformed")
        counts = {}
    expected_count = len(expected_targets)
    for field, expected in (
        ("manifest_targets", expected_count),
        ("targets", expected_count),
        ("missing_targets", 0),
        ("extra_targets", 0),
        ("add_spec", expected_count),
        ("typecheck_passed", expected_count),
        ("equivalence_bound_targets", expected_count),
        ("selected_relation_evaluated_targets", 0),
        ("selected_relation_unsupported_targets", expected_count),
    ):
        if counts.get(field) != expected:
            error(
                errors,
                "feedback_count_mismatch",
                actual=counts.get(field),
                expected=expected,
                field=field,
            )
    if (
        counts.get("diagnostic_only_rounds")
        != diagnostic_bindings["binding_count"]
        or diagnostic_bindings["binding_count"] < expected_count
    ):
        error(errors, "feedback_diagnostic_binding_count_mismatch")
    if (
        not isinstance(raw_manifest_targets, list)
        or len(manifest_targets) != len(raw_manifest_targets)
        or set(manifest_targets) != expected_targets
    ):
        error(errors, "feedback_manifest_target_set_mismatch")
    if manifest.get("metadata", {}).get("outcome_equivalence") != (
        common_equivalence_binding
    ):
        error(errors, "feedback_manifest_equivalence_set_mismatch")
    if manifest.get("metadata", {}).get(
        "selected_relation_evaluation"
    ) != common_relation_capability:
        error(errors, "feedback_manifest_relation_capability_mismatch")
    if (
        summary.get("outcome_equivalence")
        != common_equivalence_binding
        or summary.get("metadata", {}).get("outcome_equivalence")
        != common_equivalence_binding
    ):
        error(errors, "feedback_summary_equivalence_set_mismatch")
    if (
        summary.get("selected_relation_evaluation")
        != common_relation_capability
        or summary.get("metadata", {}).get(
            "selected_relation_evaluation"
        )
        != common_relation_capability
    ):
        error(errors, "feedback_summary_relation_capability_mismatch")
    if (
        summary.get("canonical_diagnostic_bindings")
        != diagnostic_bindings
        or summary.get("metadata", {}).get(
            "canonical_diagnostic_bindings"
        )
        != diagnostic_bindings
    ):
        error(errors, "feedback_summary_diagnostic_binding_mismatch")

    if (
        binding.get("status") != "completed"
        or binding.get("summary_sha256")
        != support.sha256(support.FEEDBACK_SUMMARY_PATH)
        or binding.get("outcome_equivalence")
        != common_equivalence_binding
        or binding.get("equivalence_bound_target_count")
        != expected_count
        or binding.get("selected_relation_evaluation")
        != common_relation_capability
        or binding.get("canonical_diagnostic_bindings")
        != diagnostic_bindings
    ):
        error(errors, "feedback_run_binding_stale")
    run_manifest_relative = binding.get("run_manifest_path")
    run_manifest_path = (
        support.ROOT / str(run_manifest_relative)
        if run_manifest_relative
        else Path()
    )
    if (
        not run_manifest_relative
        or not run_manifest_path.is_file()
        or binding.get("run_manifest_sha256")
        != support.sha256(run_manifest_path)
    ):
        error(errors, "feedback_run_manifest_binding_stale")
        run_manifest: dict[str, Any] = {}
    else:
        run_manifest = support.load_json(run_manifest_path)
    feedback_runner = support.ROOT.parent / "run_rust_std_spec_feedback.py"
    verus_bin = (
        support.ROOT.parent
        / "verus"
        / "source"
        / "target-verus"
        / "release"
        / "verus"
    )
    z3_path = support.ROOT.parent / "verus" / "source" / "z3"
    expected_snapshot = {
        "contract_sha256": support.sha256(support.CONTRACT_PATH),
        "feedback_adapter_sha256": support.sha256(
            support.FEEDBACK_ADAPTER_PATH
        ),
        "feedback_manifest_sha256": support.sha256(
            support.FEEDBACK_MANIFEST_PATH
        ),
        "feedback_runner_sha256": support.sha256(feedback_runner),
        "feedback_worker_sha256": support.sha256(
            support.ROOT / "tools" / "run_supervised_feedback.py"
        ),
        "outcome_equivalence_sha256": support.sha256(
            support.OUTCOME_EQUIVALENCE_PATH
        ),
        "outcome_equivalence_version_set_sha256": equivalence[
            "version_set_sha256"
        ],
        "relation_capability_sha256": support.sha256(
            support.FEEDBACK_RELATION_CAPABILITY_PATH
        ),
        "seed_candidates_sha256": support.sha256(
            support.FEEDBACK_SEED_PATH
        ),
        "verus_binary_sha256": support.sha256(verus_bin),
        "vstd_closure_manifest_sha256": support.sha256(
            support.ROOT / "provenance" / "vstd_dependency_closure.json"
        ),
        "vstd_context_sha256": support.sha256(
            support.VSTD_CONTRACTS_PATH
        ),
        "vocabulary_sha256": support.sha256(support.VOCABULARY_PATH),
        "z3_binary_sha256": support.sha256(z3_path),
    }
    if run_manifest.get("source_snapshot") != expected_snapshot:
        error(errors, "feedback_run_inputs_stale")
    run_command = run_manifest.get("command")
    if (
        not isinstance(run_command, list)
        or str(support.FEEDBACK_ADAPTER_PATH) not in run_command
        or command_argument(run_command, "--runner")
        != str(feedback_runner)
        or command_argument(run_command, "--outcome-equivalence")
        != str(support.OUTCOME_EQUIVALENCE_PATH)
        or command_argument(run_command, "--relation-capability")
        != str(support.FEEDBACK_RELATION_CAPABILITY_PATH)
    ):
        error(errors, "feedback_run_command_omits_equivalence")
    return report(
        "feedback_determinism",
        errors,
        len(records),
        {
            "records": records,
            "run_id": binding.get("run_id"),
            "canonical_checker_taxonomy": dict(
                sorted(canonical_taxonomy.items())
            ),
            "taxonomy": dict(sorted(taxonomy.items())),
        },
    )


AUDITS: tuple[tuple[str, Callable[[], dict[str, Any]]], ...] = (
    ("anti_vacuity", anti_vacuity_audit),
    ("direct_ensures", direct_ensures_audit),
    ("source_fidelity", source_fidelity_audit),
    ("signature", signature_audit),
    ("provenance", provenance_audit),
    ("helper_usage", helper_usage_audit),
    ("outcome_equivalence", outcome_equivalence_audit),
    ("artifact_integrity", artifact_integrity_audit),
    ("feedback_determinism", feedback_determinism_audit),
)


def main() -> int:
    support.validate_metadata_coverage()
    outputs: list[dict[str, Any]] = []
    for name, function in AUDITS:
        payload = function()
        path = support.AUDIT_ROOT / f"{name}.json"
        support.write_json(path, payload)
        outputs.append(
            {
                "audit": name,
                "path": str(path.relative_to(support.ROOT)),
                "sha256": support.sha256(path),
                "status": payload["status"],
            }
        )
    counts = Counter(row["status"] for row in outputs)
    summary = {
        "audits": outputs,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "counts": dict(sorted(counts.items())),
        "inputs": base_inputs(),
        "schema_version": 1,
        "status": (
            "passed"
            if all(row["status"] == "passed" for row in outputs)
            else "failed"
        ),
    }
    support.write_json(SUMMARY_PATH, summary)
    print(
        {
            "audits": len(outputs),
            "status": summary["status"],
        }
    )
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
