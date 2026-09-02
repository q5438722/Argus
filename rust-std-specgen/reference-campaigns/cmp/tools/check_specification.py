#!/usr/bin/env python3
"""Fail closed on stale, incomplete, or unreviewed core::cmp specifications."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

CAMPAIGN_ROOT = Path(__file__).resolve().parents[1]
if str(CAMPAIGN_ROOT) not in sys.path:
    sys.path.insert(0, str(CAMPAIGN_ROOT))

from tools import build_specification as builder
from tools.review_schema import artifact_binding_map, question_verdict_map


ROOT = builder.ROOT
CHECK_REPORT = ROOT / "specification" / "cmp_specification_check.json"
NO_VERIFY_LATEST = (
    ROOT / "verification" / "evidence" / "specification-no-verify" / "latest.json"
)
INDEPENDENT_REVIEW = ROOT / "reviews" / "independent_specification_review.json"
CANONICAL_HANDOFF = ROOT / "reviews" / "canonical_specification_handoff.json"
MISSION_PATH = Path(
    "/home/chentianyu/.argus-skill-v011-slice-conditional/projects/"
    "s-506ff1d3/handoffs/39c8ea40fd42/mission.json"
)
MARKER = re.compile(
    r"^// @spec-row (?P<row_id>\S+) family=(?P<family>\S+)$",
    re.MULTILINE,
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact_hash(values: list[str]) -> str:
    data = json.dumps(
        sorted(values), separators=(",", ":"), ensure_ascii=True
    ).encode()
    return hashlib.sha256(data).hexdigest()


def contract_blocks(text: str) -> dict[str, tuple[str, str]]:
    matches = list(MARKER.finditer(text))
    blocks: dict[str, tuple[str, str]] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks[match.group("row_id")] = (
            match.group("family"),
            text[match.start():end],
        )
    return blocks


def required_family_fragments(
    row: dict[str, Any],
    family: str,
) -> tuple[str, ...]:
    method = row["method_name"]
    if family == "array_slice_order_forwarding":
        fragments = [
            "cmp_array_slice_forwarding",
            "cmp_array_order_dispatch",
        ]
        if method == "partial_cmp":
            fragments.extend(
                [
                    "CmpOrderDispatch::AlwaysApplicableOrd",
                    "CmpOrderDispatch::GenericOrdLoop",
                    "cmp_always_applicable_ord_dispatch",
                    "cmp_hidden_ord_lexicographic_prefix",
                ]
            )
        elif method in {"lt", "le", "gt", "ge"}:
            fragments.extend(
                [
                    (
                        "if outcomes.len() > 0 && outcomes.last() "
                        "!= Some(core::cmp::Ordering::Equal)"
                    ),
                    "outcomes.last() is Some && cmp_relation_holds",
                ]
            )
        return tuple(fragments)
    if family == "slice_order_dispatch":
        fragments = [
            "cmp_slice_order_dispatch",
            "CmpOrderDispatch::",
            "cmp_length_order",
        ]
        if method == "partial_cmp":
            fragments.extend(
                [
                    "CmpOrderDispatch::AlwaysApplicableOrd",
                    "CmpOrderDispatch::GenericOrdLoop",
                    "cmp_always_applicable_ord_dispatch",
                    "cmp_hidden_ord_lexicographic_prefix",
                ]
            )
        elif method in {"lt", "le", "gt", "ge"}:
            relation = method.capitalize()
            fragments.extend(
                [
                    "cmp_lexicographic_partial_cmp_prefix",
                    (
                        "if outcomes.len() > 0 && outcomes.last() "
                        "!= Some(core::cmp::Ordering::Equal)"
                    ),
                    "outcomes.last() is Some && cmp_relation_holds",
                    f"cmp_relation_holds(CmpRelation::{relation},",
                ]
            )
        return tuple(fragments)
    requirements = {
        "array_equality_dispatch": (
            "CmpEqDispatch::GenericElementLoop",
            "CmpEqDispatch::Bytewise",
            "cmp_sequence_observation_count",
        ),
        "slice_equality_dispatch": (
            "left@.len() != right@.len()",
            "CmpEqDispatch::GenericElementLoop",
            "CmpEqDispatch::Bytewise",
        ),
        "tuple_short_circuit": (
            "cmp_tuple_observation_count",
            (
                "as PartialOrd>::partial_cmp"
                if method in {"lt", "le", "gt", "ge"}
                and len(row["signature"]["owner_generics"]["type_parameters"]) > 1
                else "call_ensures"
            ),
            (
                "!= Some(core::cmp::Ordering::Equal)"
                if method in {"lt", "le", "gt", "ge"}
                and len(row["signature"]["owner_generics"]["type_parameters"]) > 1
                else "call_ensures"
            ),
            (
                "is Some && cmp_relation_holds"
                if method in {"lt", "le", "gt", "ge"}
                and len(row["signature"]["owner_generics"]["type_parameters"]) > 1
                else "call_ensures"
            ),
            (
                "(result <==> ("
                if method in {"eq", "ne"}
                else (
                    "(result == ("
                    if method in {"partial_cmp", "cmp"}
                    else (
                        "result == if"
                        if len(
                            row["signature"]["owner_generics"][
                                "type_parameters"
                            ]
                        ) > 1
                        else "call_ensures"
                    )
                )
            ),
        ),
        "ordering_value": ("result",),
        "ordering_debug": ("cmp_ordering_debug_effect",),
        "ordering_hash": ("cmp_ordering_hash_effect",),
        "ordering_then_with": (
            "ordering != Ordering::Equal",
            "ordering == Ordering::Equal",
            "callback.ensures((), result)",
            "== 0",
            "== 1",
        ),
        "reverse_forwarding": ("&left.0, &right.0",),
        "reverse_default": ("T::default", "result == Reverse(value)"),
        "reverse_debug": ("cmp_reverse_debug_effect(&value.0",),
        "reverse_hash": ("cmp_reverse_hash_effect(&value.0",),
        "reverse_operand_reversal": ("&right.0, &left.0",),
        "reverse_clone": (
            "source.0",
            "result.0" if method == "clone" else "final(target).0",
        ),
        "free_ord_forwarding": (
            f"<T as Ord>::{method}",
            "(v1, v2)",
        ),
        "comparator_callback": (
            "compare.ensures((&v1, &v2), order)",
            "cmp_comparator_observation_count(compare, &v1, &v2) == 1",
        ),
        "key_callback_order": (
            "callback.ensures((&v2,), key2)",
            "callback_after_v2.ensures((&v1,), key1)",
            "cmp_fn_mut_state_transition(callback, &v2, key2, callback_after_v2)",
            "cmp_fn_mut_state_transition(callback_after_v2, &v1, key1, callback_after_v1)",
            "cmp_key_callback_observation_count(callback, &v2, &v1) == 2",
        ),
        "unit_value": ("result",),
        "char_value": ("cmp_char_",),
        "bool_value": ("result",),
        "primitive_clamp": (
            "CmpCallOutcome::Panicked",
            "CmpCallOutcome::Returned(",
            "== CmpCallOutcome::Returned(result)",
            "{ min } else if",
            "{ max } else",
        ),
        "trait_default_clamp": (
            "pub open spec fn cmp_ord_clamp_contract",
            "Self_::obeys_partial_cmp_spec()",
            "min.partial_cmp_spec(&max) == Some(Ordering::Greater)",
            "CmpCallOutcome::Panicked",
            "CmpCallOutcome::Returned(",
            "value.partial_cmp_spec(&min) == Some(Ordering::Less)",
            "value.partial_cmp_spec(&max) == Some(Ordering::Greater)",
        ),
        "empty_eq_default": (
            "pub open spec fn cmp_eq_assert_receiver_is_total_eq_contract",
            "true",
        ),
    }
    if (
        family == "tuple_short_circuit"
        and method in {"lt", "le", "gt", "ge"}
        and len(row["signature"]["owner_generics"]["type_parameters"]) > 1
    ):
        return (
            *requirements[family],
            "== Some(core::cmp::Ordering::Equal)",
            f"cmp_relation_holds(CmpRelation::{method.capitalize()},",
        )
    if family not in requirements:
        if family == "reference_forwarding":
            if "PartialEq" in row["target"]:
                trait_name = "PartialEq<B>"
            elif "PartialOrd" in row["target"]:
                trait_name = "PartialOrd<B>"
            else:
                trait_name = "Ord"
            left = (
                "cmp_shared_reborrow(left)"
                if row["target"].startswith("<&mut A")
                else "*left"
            )
            right = (
                "cmp_shared_reborrow(right)"
                if (
                    "<&mut B>>" in row["target"]
                    or (
                        trait_name == "Ord"
                        and row["target"].startswith("<&mut A")
                    )
                )
                else "*right"
            )
            return (
                f"call_ensures(<A as {trait_name}>::{method}",
                f"({left}, {right}), result)",
            )
        return ("__unknown_family__",)
    return requirements[family]


def contract_text_errors(
    text: str,
    rows: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    pending = {
        row["row_id"]: row
        for row in builder.generated_candidate_rows(rows)
    }
    exact = {
        row["row_id"]
        for row in rows
        if row["disposition"] == "exact_vstd"
    }
    matches = list(MARKER.finditer(text))
    marker_ids = [match.group("row_id") for match in matches]
    if len(marker_ids) != len(set(marker_ids)):
        errors.append("duplicate_contract_markers")
    if set(marker_ids) != set(pending):
        errors.append("generated_contract_identity_set_mismatch")
    if set(marker_ids) & exact:
        errors.append("exact_vstd_identity_redeclared")
    blocks = contract_blocks(text)
    if len(blocks) != len(pending):
        errors.append("contract_block_count_mismatch")
    for row_id, row in pending.items():
        if row_id not in blocks:
            continue
        family, block = blocks[row_id]
        expected_family = builder.build_contract(row).family
        if family != expected_family:
            errors.append(f"contract_family_mismatch:{row_id}")
        for fragment in required_family_fragments(row, family):
            if fragment not in block:
                errors.append(f"missing_family_fragment:{row_id}:{fragment}")
        if family in {"empty_eq_default", "trait_default_clamp"}:
            if "assume_specification" in block:
                errors.append(f"trait_default_illegal_generic_binding:{row_id}")
            if "pub open spec fn" not in block:
                errors.append(f"missing_trait_default_outcome_contract:{row_id}")
        else:
            if block.count("pub assume_specification") != 1:
                errors.append(f"target_binding_count:{row_id}")
            if "ensures" not in block:
                errors.append(f"missing_direct_ensures:{row_id}")
        if re.search(r"ensures\s+true\s*[,;]", block):
            errors.append(f"vacuous_direct_ensures:{row_id}")
    return sorted(set(errors))


def source_evidence_errors(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for row in rows:
        evidence = row["source_evidence"]
        path = ROOT / evidence["snapshot_path"]
        if not path.is_file():
            errors.append(f"source_missing:{row['row_id']}")
            continue
        if sha256(path) != evidence["snapshot_sha256"]:
            errors.append(f"source_hash_mismatch:{row['row_id']}")
            continue
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        begin = int(row["source_begin_line"])
        end = int(row["source_end_line"])
        excerpt = "".join(lines[begin - 1:end]).encode()
        if hashlib.sha256(excerpt).hexdigest() != evidence["span_sha256"]:
            errors.append(f"source_span_hash_mismatch:{row['row_id']}")
    return errors


def evidence_errors() -> list[str]:
    if not NO_VERIFY_LATEST.is_file():
        return ["no_verify_latest_missing"]
    latest = load(NO_VERIFY_LATEST)
    run_dir = ROOT / str(latest.get("run_dir", ""))
    result_path = run_dir / "result.json"
    if not result_path.is_file():
        return ["no_verify_result_missing"]
    result = load(result_path)
    errors = []
    if result.get("status") != "passed" or result.get("exit_code") != 0:
        errors.append("no_verify_failed")
    expected = {
        "contract_sha256": sha256(builder.GENERATED),
        "inventory_sha256": sha256(builder.INVENTORY),
        "vocabulary_sha256": sha256(builder.VOCABULARY),
    }
    for field, value in expected.items():
        if result.get("inputs", {}).get(field) != value:
            errors.append(f"no_verify_stale:{field}")
    command = result.get("command", [])
    if "--no-verify" not in command:
        errors.append("no_verify_flag_missing")
    if "specs/generated_cmp_specs.rs" not in command:
        errors.append("no_verify_wrong_crate")
    return errors


def review_errors(rows: list[dict[str, Any]]) -> list[str]:
    if not INDEPENDENT_REVIEW.is_file():
        return ["independent_review_missing"]
    review = load(INDEPENDENT_REVIEW)
    errors = []
    if review.get("producer_role") != "reviewer":
        errors.append("independent_reviewer_role_invalid")
    request = load(builder.REVIEW_REQUEST)
    if review.get("schema_version") != 1:
        errors.append("independent_review_schema_invalid")
    if review.get("module") != request.get("module"):
        errors.append("independent_review_module_invalid")
    if review.get("review_type") != request.get("review_type"):
        errors.append("independent_review_type_invalid")
    if review.get("review_request") != {
        "path": str(builder.REVIEW_REQUEST.relative_to(ROOT)),
        "sha256": sha256(builder.REVIEW_REQUEST),
    }:
        errors.append("independent_review_request_stale")
    independence = review.get("independence", {})
    if (
        independence.get("independent") is not True
        or independence.get("artifacts_modified_by_reviewer") != []
    ):
        errors.append("independent_review_not_independent")
    decision = review.get("review", {})
    if decision.get("status") != "done":
        errors.append("independent_review_status_not_done")
    if decision.get("rejected") not in (None, False):
        errors.append("independent_review_contradictory_rejection")
    if decision.get("implementation_proofs_authorized") is not True:
        errors.append("review_does_not_authorize_proofs")
    if decision.get("unresolved_findings") != []:
        errors.append("independent_review_has_findings")
    verdicts = decision.get("question_verdicts", [])
    verdict_by_question = question_verdict_map(verdicts)
    if (
        verdict_by_question is None
        or set(verdict_by_question) != set(request["review_questions"])
    ):
        errors.append("independent_review_question_set_mismatch")
    else:
        for question in request["review_questions"]:
            expected = (
                "no"
                if question.startswith(
                    "Are any whole target outcomes hidden"
                )
                else "satisfied"
            )
            if verdict_by_question[question] != expected:
                errors.append("independent_review_question_not_accepted")
                break
    expected_artifacts = {
        item["path"]: item["sha256"]
        for item in request["artifacts"]
    }
    actual_artifacts = artifact_binding_map(
        review.get("artifact_bindings")
    )
    if actual_artifacts is None:
        errors.append("independent_review_artifact_bindings_schema_invalid")
    elif actual_artifacts != expected_artifacts:
        errors.append("independent_review_artifacts_stale")
    equivalence = decision.get("outcome_equivalence", {})
    row_ids = [row["row_id"] for row in rows]
    if equivalence.get("accepted") is not True:
        errors.append("outcome_equivalence_not_accepted")
    if equivalence.get("reviewed_row_count") != len(row_ids):
        errors.append("outcome_equivalence_review_count_mismatch")
    if equivalence.get("reviewed_row_ids_sha256") != compact_hash(row_ids):
        errors.append("outcome_equivalence_review_ids_stale")
    if equivalence.get("non_exact_equivalence_count") != 0:
        errors.append("unexpected_equivalence_quotient")
    impossible_rows = builder.model_boundary_rows(rows)
    impossible_ids = sorted(row["row_id"] for row in impossible_rows)
    impossible = decision.get("genuinely_impossible", {})
    if impossible.get("accepted") is not True:
        errors.append("genuinely_impossible_rows_not_accepted")
    if impossible.get("approved_row_count") != len(impossible_ids):
        errors.append("genuinely_impossible_review_count_mismatch")
    if impossible.get("approved_row_ids") != impossible_ids:
        errors.append("genuinely_impossible_review_ids_mismatch")
    if impossible.get("approved_row_ids_sha256") != compact_hash(
        impossible_ids
    ):
        errors.append("genuinely_impossible_review_ids_stale")
    if impossible.get("evidence_path") != str(
        builder.FLOAT_MODEL_BOUNDARY.relative_to(ROOT)
    ):
        errors.append("genuinely_impossible_evidence_path_invalid")
    elif impossible.get("evidence_sha256") != sha256(
        builder.FLOAT_MODEL_BOUNDARY
    ):
        errors.append("genuinely_impossible_evidence_stale")
    canonical = review.get("canonical_handoff", {})
    if canonical.get("path") != str(CANONICAL_HANDOFF.relative_to(ROOT)):
        errors.append("canonical_specification_handoff_path_invalid")
    elif not CANONICAL_HANDOFF.is_file():
        errors.append("canonical_specification_handoff_missing")
    elif canonical.get("sha256") != sha256(CANONICAL_HANDOFF):
        errors.append("canonical_specification_handoff_stale")
    else:
        handoff = load(CANONICAL_HANDOFF)
        handoff_review = handoff.get("review", {})
        mission = handoff.get("mission", {})
        mission_path = Path(str(mission.get("path", "")))
        if (
            handoff.get("producer_role") != "reviewer"
            or handoff_review.get("status") != "done"
            or handoff_review.get("next_action") != ""
            or handoff_review.get("implementation_proofs_authorized")
            is not True
            or handoff_review.get(
                "approved_genuinely_impossible_row_count"
            )
            != len(impossible_ids)
            or handoff_review.get(
                "approved_genuinely_impossible_row_ids_sha256"
            )
            != compact_hash(impossible_ids)
            or handoff_review.get("unresolved_findings") != []
        ):
            errors.append("canonical_specification_handoff_verdict_invalid")
        if handoff.get("review_request") != {
            "path": str(builder.REVIEW_REQUEST.relative_to(ROOT)),
            "sha256": sha256(builder.REVIEW_REQUEST),
        }:
            errors.append("canonical_specification_handoff_request_stale")
        if handoff.get("artifact_bindings") != request["artifacts"]:
            errors.append("canonical_specification_handoff_artifacts_stale")
        if (
            mission_path != MISSION_PATH
            or not mission_path.is_file()
            or mission.get("sha256") != sha256(mission_path)
        ):
            errors.append("canonical_specification_handoff_mission_stale")
    return errors


def proof_phase_authorized(rows: list[dict[str, Any]]) -> bool:
    return (
        INDEPENDENT_REVIEW.is_file()
        and not review_errors(rows)
        and load(INDEPENDENT_REVIEW).get("review", {}).get(
            "implementation_proofs_authorized"
        )
        is True
    )


def validate(
    *,
    require_evidence: bool = True,
    require_review: bool = True,
) -> list[str]:
    errors: list[str] = []
    inventory = load(builder.INVENTORY)
    rows = inventory["rows"]
    expected_payloads = builder.build_payloads()
    for path, expected in expected_payloads.items():
        if not path.is_file():
            errors.append(f"package_artifact_missing:{path.relative_to(ROOT)}")
        elif path.read_bytes() != expected:
            errors.append(f"package_artifact_stale:{path.relative_to(ROOT)}")

    if builder.GENERATED.is_file():
        errors.extend(
            contract_text_errors(
                builder.GENERATED.read_text(encoding="utf-8"),
                rows,
            )
        )
    errors.extend(source_evidence_errors(rows))

    catalog = load(builder.CATALOG)
    catalog_rows = catalog.get("rows", [])
    if len(catalog_rows) != len(rows):
        errors.append("catalog_row_count_mismatch")
    if {row.get("row_id") for row in catalog_rows} != {
        row["row_id"] for row in rows
    }:
        errors.append("catalog_identity_set_mismatch")
    dispositions = Counter(row.get("disposition") for row in catalog_rows)
    inventory_dispositions = Counter(row["disposition"] for row in rows)
    generated_rows = builder.generated_candidate_rows(rows)
    impossible_rows = builder.model_boundary_rows(rows)
    if dispositions["generated"] != len(generated_rows):
        errors.append("generated_count_mismatch")
    if dispositions["exact_vstd"] != inventory_dispositions["exact_vstd"]:
        errors.append("exact_vstd_count_mismatch")
    if dispositions["genuinely_impossible"] != len(impossible_rows):
        errors.append("genuinely_impossible_count_mismatch")
    if catalog.get("counts", {}).get("pending") != 0:
        errors.append("catalog_pending_nonzero")
    expected_specified = (
        len(generated_rows) + inventory_dispositions["exact_vstd"]
    )
    counts = catalog.get("counts", {})
    if counts.get("specified_total") != expected_specified:
        errors.append("specified_total_mismatch")
    if counts.get("genuinely_impossible") != len(impossible_rows):
        errors.append("catalog_genuinely_impossible_count_mismatch")
    expected_coverage = expected_specified / len(rows) if rows else 1.0
    if counts.get("strict_specification_coverage") != expected_coverage:
        errors.append("strict_specification_coverage_mismatch")

    float_boundary = load(builder.FLOAT_MODEL_BOUNDARY)
    float_records = float_boundary.get("records", [])
    if (
        float_boundary.get("record_count") != len(impossible_rows)
        or {record.get("row_id") for record in float_records}
        != {row["row_id"] for row in impossible_rows}
    ):
        errors.append("float_model_boundary_identity_mismatch")
    if any(
        record.get("disposition") != "genuinely_impossible"
        or record.get("counts_as_specification_coverage") is not False
        or record.get("missing_model_boundary", {}).get(
            "whole_target_outcome"
        )
        is not True
        or record.get("missing_model_boundary", {}).get(
            "accepted_for_contract_or_proof"
        )
        is not False
        or len(record.get("attempts", [])) < 4
        or len(record.get("semantic_mutations", [])) < 2
        or "not_claimed" not in record.get("mutation_status", "")
        for record in float_records
    ):
        errors.append("float_model_boundary_record_invalid")
    try:
        builder.float_probe_binding()
    except (builder.SpecificationBuildError, OSError, ValueError, KeyError):
        errors.append("float_model_boundary_probe_invalid")

    bindings = load(builder.EXISTING_BINDINGS)
    binding_records = bindings.get("records", [])
    exact_rows = [row for row in rows if row["disposition"] == "exact_vstd"]
    if len(binding_records) != len(exact_rows):
        errors.append("exact_binding_record_count_mismatch")
    canonical = sum(
        row["vstd_provenance_class"] == "tracked_clean_vstd"
        for row in exact_rows
    )
    noncanonical = len(exact_rows) - canonical
    if bindings.get("counts", {}).get("canonical_upstream") != canonical:
        errors.append("canonical_exact_binding_count_mismatch")
    if (
        bindings.get("counts", {}).get("frozen_dirty_or_untracked")
        != noncanonical
    ):
        errors.append("noncanonical_exact_binding_count_mismatch")
    dirty = [
        record
        for record in binding_records
        if not record.get("canonical_upstream_binding")
    ]
    if len(dirty) != noncanonical:
        errors.append("noncanonical_binding_partition_mismatch")
    if any(
        record.get("vstd_provenance_class")
        != "frozen_dirty_or_untracked_current_vstd"
        or not record.get("target", "").startswith("Ordering::")
        for record in dirty
    ):
        errors.append("noncanonical_binding_not_clearly_distinguished")

    equivalence = load(builder.EQUIVALENCE)
    equivalence_rows = equivalence.get("records", [])
    if len(equivalence_rows) != len(rows):
        errors.append("equivalence_row_count_mismatch")
    if {row.get("row_id") for row in equivalence_rows} != {
        row["row_id"] for row in rows
    }:
        errors.append("equivalence_identity_set_mismatch")
    if equivalence.get("non_exact_equivalence_count") != 0:
        errors.append("equivalence_quotient_present")
    if any(
        row.get("kind") != "exact_observable_outcome_equality"
        or row.get("quotient_used") is not False
        or row.get("positive_and_negative_witnesses_required") is not False
        for row in equivalence_rows
    ):
        errors.append("equivalence_record_invalid")

    helper_audit = load(builder.HELPER_AUDIT)
    helper_records = helper_audit.get("records", [])
    helper_names = [record.get("name") for record in helper_records]
    if helper_audit.get("status") != "passed":
        errors.append("helper_audit_not_passed")
    if helper_audit.get("vocabulary_sha256") != sha256(builder.VOCABULARY):
        errors.append("helper_audit_vocabulary_stale")
    if len(helper_names) != len(set(helper_names)):
        errors.append("helper_audit_duplicate_names")
    if helper_audit.get("counts", {}).get("whole_target_outcome") != 0:
        errors.append("helper_audit_whole_target_outcome_nonzero")
    if any(record.get("whole_target_outcome") is not False for record in helper_records):
        errors.append("helper_audit_whole_target_helper")
    if helper_audit.get("prohibited_helpers_absent") is not True:
        errors.append("prohibited_whole_target_helper_present")
    vocabulary_text = builder.VOCABULARY.read_text(encoding="utf-8")
    generated_text = builder.GENERATED.read_text(encoding="utf-8")
    if "cmp_reference_forward_result" in vocabulary_text or (
        "cmp_reference_forward_result" in generated_text
    ):
        errors.append("opaque_reference_forwarding_helper_present")

    manifest = load(builder.MANIFEST)
    if manifest.get("implementation_proofs_authorized") is not False:
        errors.append("manifest_prematurely_authorizes_proofs")
    harnesses = ROOT / "proof_harnesses"
    if (
        not proof_phase_authorized(rows)
        and harnesses.exists()
        and any(harnesses.iterdir())
    ):
        errors.append("proof_harnesses_exist_before_spec_acceptance")

    if require_evidence:
        errors.extend(evidence_errors())
    if require_review:
        errors.extend(review_errors(rows))
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-missing-evidence", action="store_true")
    parser.add_argument("--allow-pending-review", action="store_true")
    args = parser.parse_args()
    errors = validate(
        require_evidence=not args.allow_missing_evidence,
        require_review=not args.allow_pending_review,
    )
    inventory = load(builder.INVENTORY)
    rows = inventory["rows"]
    report = {
        "schema_version": 1,
        "module": "core::cmp",
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "metrics": {
            "stable_inventory_total": len(rows),
            "exact_vstd": sum(
                row["disposition"] == "exact_vstd" for row in rows
            ),
            "generated": len(builder.generated_candidate_rows(rows)),
            "genuinely_impossible": len(
                builder.model_boundary_rows(rows)
            ),
            "specified_total": len(
                builder.selected_specification_rows(rows)
            ),
            "strict_specification_coverage": (
                len(builder.selected_specification_rows(rows)) / len(rows)
                if rows
                else 1.0
            ),
            "pending": 0,
            "independent_review_required": not args.allow_pending_review,
            "no_verify_evidence_required": not args.allow_missing_evidence,
        },
    }
    CHECK_REPORT.parent.mkdir(parents=True, exist_ok=True)
    CHECK_REPORT.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
