#!/usr/bin/env python3
"""Fail closed on incomplete, stale, or unsound core::cmp proof artifacts."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_specification as specification
from tools import check_specification
from tools.review_schema import artifact_binding_map, question_verdict_map
from tools import run_implementation_proofs as runner
from tools import run_mutation_probes as mutation_runner


TARGETS = ROOT / "proof_inventory" / "targets.json"
TARGETS_CSV = ROOT / "proof_inventory" / "targets.csv"
DEPENDENCY_GRAPH = ROOT / "proof_inventory" / "dependency_graph.json"
DEPENDENCY_GRAPH_DOT = ROOT / "proof_inventory" / "dependency_graph.dot"
FROZEN_INPUTS = ROOT / "frozen_inputs" / "file_manifest.json"
FROZEN_INPUTS_CSV = ROOT / "frozen_inputs" / "file_manifest.csv"
AUTHORIZATION = ROOT / "proof_inventory" / "proof_phase_authorization.json"
AGGREGATE_JSON = ROOT / "proof_inventory" / "aggregate_coverage.json"
AGGREGATE_MD = ROOT / "proof_inventory" / "aggregate_coverage.md"
MUTATION_SUMMARY = ROOT / "verification" / "mutations" / "summary.json"
TRUST_AUDIT = ROOT / "audits" / "implementation_trust_boundary_audit.json"
TRUST_MD = ROOT / "TRUST_BOUNDARY_AUDIT.md"
CHECK_REPORT = ROOT / "proof_inventory" / "implementation_proof_check.json"
REVIEW_REQUEST = ROOT / "reviews" / "implementation_completeness_review_request.json"
REVIEW = ROOT / "reviews" / "implementation_completeness_review.json"
CANONICAL_REVIEW_HANDOFF = (
    ROOT / "reviews" / "canonical_implementation_handoff.json"
)
REQUIRED_FILES = (
    "implementation_proof.rs",
    "completeness_proof.rs",
    "source_excerpt.rs",
    "accepted_contract.rs",
    "contract_equivalence.json",
    "source_body.json",
    "transformation_manifest.json",
    "dependency_assumptions.json",
    "trust_boundaries.json",
    "proof_manifest.json",
)
REQUIRED_MUTATION_CATEGORIES = {
    "forwarding",
    "callback_order_state",
    "branch_reversal",
    "equality_ordering_distinction",
    "specialization_dispatch",
    "panic_domain",
    "chaining_equal_continue",
    "chaining_non_equal_relation",
    "chaining_none_false",
}
EXTERNAL_ATTRIBUTE_RE = re.compile(
    r"#\[\s*verifier\s*::\s*external_body\s*\]"
)
EXTERNAL_FUNCTION_RE = re.compile(
    r"#\[verifier::external_body\]\s*"
    r"(?:#\[[^\n]+\]\s*)*"
    r"(?:pub(?:\([^)]*\))?\s+)?"
    r"(?:unsafe\s+)?(?:broadcast\s+)?(?:(?:open|closed)\s+)?"
    r"(?:(?:spec|proof|exec)\s+)?fn\s+([A-Za-z0-9_]+)"
)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(value)
    temporary.replace(path)


def atomic_json(path: Path, value: Any) -> None:
    atomic_bytes(path, json_bytes(value))


def add(errors: list[dict[str, Any]], code: str, **details: Any) -> None:
    errors.append({"code": code, **details})


def selected_live_rows(
    live_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    selected_ids = {
        row["row_id"]
        for row in load(specification.CATALOG)["rows"]
        if row["disposition"] in {"generated", "exact_vstd"}
    }
    return [
        row for row in live_rows if row["row_id"] in selected_ids
    ]


def target_dir(row: dict[str, Any]) -> Path:
    return runner.target_dir(row)


def function_body(text: str, name: str) -> str | None:
    match = re.search(
        rf"\bpub\s+(?:unsafe\s+)?(?:proof\s+)?fn\s+{re.escape(name)}\b",
        text,
    )
    if match is None:
        return None
    opening = text.find("\n{", match.end())
    if opening < 0:
        return None
    opening += 1
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1:index]
    return None


def function_declaration(text: str, name: str) -> str | None:
    match = re.search(
        rf"\bpub\s+(?:unsafe\s+)?(?:proof\s+)?fn\s+{re.escape(name)}\b",
        text,
    )
    if match is None:
        return None
    opening = text.find("\n{", match.end())
    if opening < 0:
        return None
    opening += 1
    return text[match.start():opening]


def external_functions(text: str) -> list[str]:
    normalized = EXTERNAL_ATTRIBUTE_RE.sub(
        "#[verifier::external_body]",
        text,
    )
    return EXTERNAL_FUNCTION_RE.findall(normalized)


def external_body_count(text: str) -> int:
    return len(EXTERNAL_ATTRIBUTE_RE.findall(text))


def normalized_contract_clauses(text: str, name: str) -> str:
    declaration = function_declaration(text, name)
    if declaration is None:
        return ""
    start_candidates = [
        index
        for keyword in ("\n    requires", "\n    ensures")
        if (index := declaration.find(keyword)) >= 0
    ]
    if not start_candidates:
        return ""
    return re.sub(
        r"\s+",
        " ",
        declaration[min(start_candidates):],
    ).strip()


def expected_source_excerpt(row: dict[str, Any]) -> str:
    path = ROOT / row["source_evidence"]["snapshot_path"]
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    return "".join(
        lines[int(row["source_begin_line"]) - 1:int(row["source_end_line"])]
    )


def proof_hash(
    manifest: dict[str, Any],
    key: str,
) -> str | None:
    value = manifest.get(key)
    if isinstance(value, str):
        return value
    artifacts = manifest.get("artifacts", {})
    if isinstance(artifacts, dict):
        record = artifacts.get(key.removesuffix("_sha256"))
        if isinstance(record, dict):
            candidate = record.get("sha256")
            return candidate if isinstance(candidate, str) else None
    return None


def semantic_boundaries(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("boundaries", "semantic_boundaries", "records"):
            value = payload.get(key)
            if isinstance(value, list):
                return [
                    record
                    for record in value
                    if isinstance(record, dict)
                ]
    return []


def nested_sha256_values(value: Any) -> set[str]:
    hashes: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith("sha256") and isinstance(item, str):
                hashes.add(item)
            hashes.update(nested_sha256_values(item))
    elif isinstance(value, list):
        for item in value:
            hashes.update(nested_sha256_values(item))
    return hashes


def structural_errors(
    live_rows: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    trust_records: list[dict[str, Any]] = []
    selected_live = selected_live_rows(live_rows)
    live_by_id = {row["row_id"]: row for row in selected_live}
    row_ids = [row.get("row_id") for row in rows]
    if len(row_ids) != len(set(row_ids)):
        add(errors, "duplicate_proof_inventory_row_id")
    if set(row_ids) != set(live_by_id):
        add(
            errors,
            "proof_inventory_identity_set_mismatch",
            missing=sorted(set(live_by_id) - set(row_ids)),
            extra=sorted(set(row_ids) - set(live_by_id)),
        )
    if not TARGETS_CSV.is_file():
        add(errors, "proof_inventory_csv_missing")
    else:
        with TARGETS_CSV.open(newline="", encoding="utf-8") as stream:
            csv_rows = list(csv.DictReader(stream))
        csv_ids = [row.get("row_id") for row in csv_rows]
        if (
            len(csv_ids) != len(set(csv_ids))
            or set(csv_ids) != set(live_by_id)
        ):
            add(errors, "proof_inventory_csv_identity_mismatch")
        json_by_id = {row["row_id"]: row for row in rows}
        for csv_row in csv_rows:
            json_row = json_by_id.get(str(csv_row.get("row_id")))
            if json_row is None:
                continue
            for field in (
                "target",
                "target_dir",
                "disposition",
                "proof_family",
            ):
                if str(csv_row.get(field, "")) != str(
                    json_row.get(field, "")
                ):
                    add(
                        errors,
                        "proof_inventory_csv_field_mismatch",
                        row_id=csv_row.get("row_id"),
                        field=field,
                    )
    if not DEPENDENCY_GRAPH.is_file() or not DEPENDENCY_GRAPH_DOT.is_file():
        add(errors, "proof_dependency_graph_missing")
    else:
        graph = load(DEPENDENCY_GRAPH)
        nodes = graph.get("nodes", [])
        node_keys = [
            node.get("id") or node.get("row_id")
            for node in nodes
            if isinstance(node, dict)
        ]
        target_node_ids = [
            node.get("row_id")
            for node in nodes
            if isinstance(node, dict) and node.get("row_id") is not None
        ]
        if (
            len(node_keys) != len(nodes)
            or len(node_keys) != len(set(node_keys))
            or len(target_node_ids) != len(set(target_node_ids))
            or set(target_node_ids) != set(live_by_id)
        ):
            add(errors, "proof_dependency_graph_node_mismatch")
        for edge in graph.get("edges", []):
            if not isinstance(edge, dict):
                add(errors, "proof_dependency_graph_edge_invalid")
                continue
            source = edge.get("from") or edge.get("source")
            target = edge.get("to") or edge.get("target")
            if source not in node_keys or target not in node_keys:
                add(
                    errors,
                    "proof_dependency_graph_endpoint_invalid",
                    source=source,
                    target=target,
                )
        if not DEPENDENCY_GRAPH_DOT.read_text(encoding="utf-8").strip():
            add(errors, "proof_dependency_graph_dot_empty")
    if not FROZEN_INPUTS.is_file() or not FROZEN_INPUTS_CSV.is_file():
        add(errors, "frozen_proof_input_manifest_missing")
    else:
        frozen_hashes = nested_sha256_values(load(FROZEN_INPUTS))
        required_frozen_paths = {
            specification.INVENTORY,
            specification.GENERATED,
            specification.VOCABULARY,
            specification.CATALOG,
            specification.EXISTING_BINDINGS,
            specification.EQUIVALENCE,
            specification.REVIEW_REQUEST,
            check_specification.INDEPENDENT_REVIEW,
            check_specification.CANONICAL_HANDOFF,
            check_specification.MISSION_PATH,
            specification.FLOAT_MODEL_BOUNDARY,
            *(
                ROOT / row["source_evidence"]["snapshot_path"]
                for row in selected_live
            ),
        }
        missing_hashes = sorted(
            sha256(path)
            for path in required_frozen_paths
            if path.is_file() and sha256(path) not in frozen_hashes
        )
        if missing_hashes:
            add(
                errors,
                "frozen_proof_input_hashes_missing",
                hashes=missing_hashes,
            )
        if not FROZEN_INPUTS_CSV.read_text(encoding="utf-8").strip():
            add(errors, "frozen_proof_input_csv_empty")
    directories = [target_dir(row).resolve() for row in rows]
    if len(directories) != len(set(directories)):
        add(errors, "duplicate_proof_target_directory")
    proof_root = ROOT / "proof_harnesses"
    actual_children = (
        {
            path.resolve()
            for path in proof_root.iterdir()
            if path.is_dir() or path.is_symlink()
        }
        if proof_root.is_dir()
        else set()
    )
    if actual_children != set(directories):
        add(
            errors,
            "proof_harness_children_mismatch",
            expected=len(directories),
            actual=len(actual_children),
        )

    generated_blocks = check_specification.contract_blocks(
        specification.GENERATED.read_text(encoding="utf-8")
    )
    exact_bindings = {
        record["row_id"]: record
        for record in load(specification.EXISTING_BINDINGS)["records"]
    }
    for proof_row in rows:
        row_id = proof_row.get("row_id")
        live = live_by_id.get(row_id)
        if live is None:
            continue
        if proof_row.get("target") != live["target"]:
            add(errors, "proof_inventory_target_mismatch", row_id=row_id)
        if proof_row.get("disposition") != live["disposition"]:
            add(errors, "proof_inventory_disposition_mismatch", row_id=row_id)
        if not isinstance(proof_row.get("proof_family"), str) or not proof_row[
            "proof_family"
        ]:
            add(errors, "proof_inventory_family_missing", row_id=row_id)
        directory = target_dir(proof_row)
        slug = proof_row.get("slug")
        if not isinstance(slug, str) or not slug:
            add(errors, "proof_inventory_slug_missing", row_id=row_id)
        else:
            mirror = ROOT / "proof_manifests" / slug
            for name in (
                "source_body.json",
                "transformation_manifest.json",
                "dependency_assumptions.json",
            ):
                target_record = directory / name
                mirror_record = mirror / name
                if (
                    not mirror_record.is_file()
                    or not target_record.is_file()
                    or mirror_record.read_bytes() != target_record.read_bytes()
                ):
                    add(
                        errors,
                        "proof_manifest_mirror_mismatch",
                        row_id=row_id,
                        artifact=name,
                    )
        for name in REQUIRED_FILES:
            if not (directory / name).is_file():
                add(
                    errors,
                    "required_target_artifact_missing",
                    row_id=row_id,
                    path=str((directory / name).relative_to(ROOT)),
                )
        if not (directory / "evidence").is_dir():
            add(errors, "target_evidence_directory_missing", row_id=row_id)
        if any(not (directory / name).is_file() for name in REQUIRED_FILES):
            continue
        manifest = load(directory / "proof_manifest.json")
        if manifest.get("row_id") != row_id:
            add(errors, "manifest_row_id_mismatch", row_id=row_id)
        if manifest.get("target") != live["target"]:
            add(errors, "manifest_target_mismatch", row_id=row_id)
        if manifest.get("inventory_signature_sha256") != runner.compact_hash(
            live["signature"]
        ):
            add(errors, "manifest_signature_hash_mismatch", row_id=row_id)
        if manifest.get("source_span_sha256") != live["source_evidence"][
            "span_sha256"
        ]:
            add(errors, "manifest_source_span_hash_mismatch", row_id=row_id)
        if manifest.get("specification_review_sha256") != sha256(
            check_specification.INDEPENDENT_REVIEW
        ):
            add(errors, "manifest_specification_review_stale", row_id=row_id)
        for file_name, key in (
            ("implementation_proof.rs", "implementation_proof_sha256"),
            ("completeness_proof.rs", "completeness_proof_sha256"),
            ("accepted_contract.rs", "accepted_contract_sha256"),
            ("source_excerpt.rs", "source_excerpt_sha256"),
        ):
            expected = proof_hash(manifest, key)
            if expected != sha256(directory / file_name):
                add(
                    errors,
                    "manifest_artifact_hash_mismatch",
                    row_id=row_id,
                    artifact=file_name,
                )

        source_text = (directory / "source_excerpt.rs").read_text(
            encoding="utf-8"
        )
        expected_excerpt = expected_source_excerpt(live)
        if source_text != expected_excerpt:
            add(errors, "source_excerpt_not_exact_span", row_id=row_id)
        source_body = load(directory / "source_body.json")
        evidence = live["source_evidence"]
        if source_body.get("snapshot_sha256") != evidence["snapshot_sha256"]:
            add(errors, "source_body_snapshot_hash_mismatch", row_id=row_id)
        if source_body.get("span_sha256") != evidence["span_sha256"]:
            add(errors, "source_body_span_hash_mismatch", row_id=row_id)
        if source_body.get("start_line") != live["source_begin_line"]:
            add(errors, "source_body_start_line_mismatch", row_id=row_id)
        if source_body.get("end_line") != live["source_end_line"]:
            add(errors, "source_body_end_line_mismatch", row_id=row_id)

        accepted_text = (directory / "accepted_contract.rs").read_text(
            encoding="utf-8"
        )
        if row_id not in accepted_text:
            add(errors, "accepted_contract_identity_unbound", row_id=row_id)
        if live["disposition"] == "pending":
            block = generated_blocks.get(row_id)
            if block is None or block[1].strip() not in accepted_text:
                add(errors, "generated_contract_excerpt_mismatch", row_id=row_id)
        elif row_id not in exact_bindings:
            add(errors, "exact_vstd_binding_missing", row_id=row_id)

        equivalence = load(directory / "contract_equivalence.json")
        if equivalence.get("row_id") != row_id:
            add(errors, "equivalence_row_id_mismatch", row_id=row_id)
        if (
            equivalence.get("kind")
            != "exact_observable_outcome_equality"
        ):
            add(errors, "non_exact_equivalence_in_proof", row_id=row_id)
        if equivalence.get("quotient_used") is not False:
            add(errors, "proof_equivalence_quotient_present", row_id=row_id)

        implementation = (directory / "implementation_proof.rs").read_text(
            encoding="utf-8"
        )
        completeness = (directory / "completeness_proof.rs").read_text(
            encoding="utf-8"
        )
        implementation_external = external_functions(implementation)
        completeness_external = external_functions(completeness)
        implementation_external_literals = external_body_count(implementation)
        completeness_external_literals = external_body_count(completeness)
        if "implementation_target" in implementation_external:
            add(errors, "implementation_target_external_body", row_id=row_id)
        target_body = function_body(implementation, "implementation_target")
        if target_body is None:
            add(errors, "implementation_target_missing", row_id=row_id)
        else:
            forbidden = (
                "unimplemented!()",
                "todo!()",
                "loop {}",
                "assume(",
                "admit(",
            )
            if any(token in target_body for token in forbidden):
                add(
                    errors,
                    "implementation_target_vacuous_or_assumed",
                    row_id=row_id,
                )
            if not target_body.strip():
                add(errors, "implementation_target_empty", row_id=row_id)
            called_external = [
                name
                for name in implementation_external
                if name != "implementation_target"
                and re.search(rf"\b{re.escape(name)}\s*\(", target_body)
            ]
            compact_target_body = re.sub(r"\s+", " ", target_body).strip()
            target_contract = normalized_contract_clauses(
                implementation,
                "implementation_target",
            )
            for helper in called_external:
                helper_contract = normalized_contract_clauses(
                    implementation,
                    helper,
                )
                single_call = re.fullmatch(
                    rf"(?:return\s+)?{re.escape(helper)}"
                    r"\s*(?:::\s*<[^>]*>\s*)?\([\s\S]*\)\s*;?",
                    compact_target_body,
                )
                if (
                    single_call is not None
                    or (
                        helper_contract
                        and helper_contract == target_contract
                    )
                    or "accepted_contract(" in helper_contract
                ):
                    add(
                        errors,
                        "whole_target_external_passthrough",
                        row_id=row_id,
                        helper=helper,
                    )
        if re.search(r"\b(?:assume|admit)\s*!?\(", implementation):
            add(errors, "implementation_harness_contains_assumption", row_id=row_id)
        if "completeness_theorem" in completeness_external:
            add(errors, "completeness_theorem_external_body", row_id=row_id)
        complete_body = function_body(completeness, "completeness_theorem")
        complete_declaration = function_declaration(
            completeness,
            "completeness_theorem",
        )
        if complete_body is None:
            add(errors, "completeness_theorem_missing", row_id=row_id)
        if re.search(r"\b(?:assume|admit)\s*!?\(", completeness):
            add(errors, "completeness_harness_contains_assumption", row_id=row_id)
        accepted_premises = (
            complete_declaration.count("accepted_contract(")
            if complete_declaration is not None
            else 0
        )
        linked_premises = (
            complete_declaration.count(
                "call_ensures(implementation_contract_link"
            )
            if complete_declaration is not None
            else 0
        )
        if accepted_premises < 1 and linked_premises < 2:
            add(errors, "completeness_does_not_compare_contract", row_id=row_id)
        completeness_fragment = (
            manifest.get("completeness_mutation", {}).get("fragment")
        )
        if (
            complete_declaration is None
            or "ensures" not in complete_declaration
            or not isinstance(completeness_fragment, str)
            or completeness_fragment not in complete_declaration
        ):
            add(errors, "completeness_exact_result_missing", row_id=row_id)

        transformations = load(directory / "transformation_manifest.json")
        if transformations.get("row_id") != row_id:
            add(errors, "transformation_row_id_mismatch", row_id=row_id)
        source_tokens = manifest.get("source_shape_tokens", [])
        if not isinstance(source_tokens, list):
            add(errors, "source_shape_tokens_invalid", row_id=row_id)
        else:
            missing_tokens = [
                token
                for token in source_tokens
                if not isinstance(token, str) or token not in implementation
            ]
            if missing_tokens:
                add(
                    errors,
                    "source_shape_token_missing",
                    row_id=row_id,
                    tokens=missing_tokens,
                )

        dependencies = load(directory / "dependency_assumptions.json")
        trust = load(directory / "trust_boundaries.json")
        boundaries = semantic_boundaries(trust)
        if any(
            boundary.get("whole_target_outcome") is not False
            for boundary in boundaries
        ):
            add(errors, "whole_target_trust_boundary_present", row_id=row_id)
        categories = sorted(
            {
                str(
                    boundary.get("category")
                    or boundary.get("kind")
                    or boundary.get("permitted_role")
                    or "uncategorized"
                )
                for boundary in boundaries
            }
        )
        external_helpers = sorted(
            {
                *(
                    name
                    for name in implementation_external
                    if name != "implementation_target"
                ),
                *(
                    name
                    for name in completeness_external
                    if name != "completeness_theorem"
                ),
            }
        )
        declared_external = {
            str(record.get("function") or record.get("name"))
            for record in semantic_boundaries(dependencies)
            if record.get("function") or record.get("name")
        }
        if set(external_helpers) != declared_external:
            add(
                errors,
                "external_helper_dependency_manifest_mismatch",
                row_id=row_id,
                discovered=external_helpers,
                declared=sorted(declared_external),
            )
        trust_names = {
            str(boundary.get("function") or boundary.get("name"))
            for boundary in boundaries
            if boundary.get("function") or boundary.get("name")
        }
        if not set(external_helpers) <= trust_names:
            add(
                errors,
                "external_helper_trust_manifest_incomplete",
                row_id=row_id,
                helpers=sorted(set(external_helpers) - trust_names),
            )
        declared_boundary_count = trust.get("literal_external_body_count")
        scanned_boundary_count = (
            implementation_external_literals
            + completeness_external_literals
        )
        if (
            declared_boundary_count != scanned_boundary_count
            or sum(
                boundary.get("literal_external_body") is True
                for boundary in boundaries
            )
            != scanned_boundary_count
        ):
            add(
                errors,
                "trust_literal_external_body_count_mismatch",
                row_id=row_id,
            )
        trust_records.append(
            {
                "row_id": row_id,
                "target": live["target"],
                "disposition": live["disposition"],
                "proof_family": proof_row.get("proof_family"),
                "target_external_body": (
                    "implementation_target" in implementation_external
                ),
                "completeness_external_body": (
                    "completeness_theorem" in completeness_external
                ),
                "implementation_literal_external_body_count": len(
                    implementation_external
                ),
                "completeness_literal_external_body_count": len(
                    completeness_external
                ),
                "implementation_raw_external_body_count": (
                    implementation_external_literals
                ),
                "completeness_raw_external_body_count": (
                    completeness_external_literals
                ),
                "helper_dependency_function_external_body_count": len(
                    external_helpers
                ),
                "model_or_type_external_body_count": max(
                    0,
                    implementation_external_literals
                    + completeness_external_literals
                    - len(implementation_external)
                    - len(completeness_external),
                ),
                "harness_wide_literal_external_body_count": (
                    implementation_external_literals
                    + completeness_external_literals
                ),
                "external_helper_functions": external_helpers,
                "semantic_boundary_categories": categories,
                "semantic_boundary_count": len(boundaries),
                "no_additional_implementation_dependency_boundary": (
                    not external_helpers and not boundaries
                ),
                "foundational_end_to_end_trust_free": False,
            }
        )
    return errors, trust_records


def authorization_errors(
    live_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not AUTHORIZATION.is_file():
        return [{"code": "proof_phase_authorization_missing"}]
    authorization = load(AUTHORIZATION)
    review = load(check_specification.INDEPENDENT_REVIEW)
    errors: list[dict[str, Any]] = []
    expected = {
        "module": "core::cmp",
        "status": "authorized",
        "selected_target_count": len(live_rows),
        "inventory_sha256": sha256(specification.INVENTORY),
        "specification_review_path": str(
            check_specification.INDEPENDENT_REVIEW.relative_to(ROOT)
        ),
        "specification_review_sha256": sha256(
            check_specification.INDEPENDENT_REVIEW
        ),
        "canonical_specification_handoff_path": str(
            check_specification.CANONICAL_HANDOFF.relative_to(ROOT)
        ),
        "canonical_specification_handoff_sha256": sha256(
            check_specification.CANONICAL_HANDOFF
        ),
        "mission_path": str(check_specification.MISSION_PATH),
        "mission_sha256": sha256(check_specification.MISSION_PATH),
        "reviewer_producer_role": "reviewer",
        "reviewer_status": "done",
        "implementation_proofs_authorized": True,
        "authorization_errors": [],
    }
    for field, value in expected.items():
        if authorization.get(field) != value:
            add(
                errors,
                "proof_phase_authorization_invalid",
                field=field,
            )
    if (
        review.get("producer_role") != "reviewer"
        or review.get("review", {}).get("status") != "done"
        or review.get("review", {}).get(
            "implementation_proofs_authorized"
        )
        is not True
    ):
        add(errors, "specification_review_no_longer_authorizes_proofs")
    return errors


def evidence_errors(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    latest_path = runner.EVIDENCE_ROOT / "latest.json"
    if not latest_path.is_file():
        return [{"code": "proof_evidence_latest_missing"}]
    latest = load(latest_path)
    try:
        run_dir = runner.checked_descendant(
            ROOT / str(latest.get("run_dir", "")),
            runner.EVIDENCE_BASE,
            "proof evidence run",
        )
    except ValueError:
        return [{"code": "proof_evidence_run_path_invalid"}]
    result_path = run_dir / "result.json"
    manifest_path = run_dir / "manifest.json"
    input_manifest_path = run_dir / "input_manifest.json"
    if not all(
        path.is_file()
        for path in (result_path, manifest_path, input_manifest_path)
    ):
        return [{"code": "proof_evidence_run_incomplete"}]
    if latest.get("result_sha256") != sha256(result_path):
        add(errors, "proof_evidence_latest_hash_stale")
    if latest.get("manifest_sha256") != sha256(manifest_path):
        add(errors, "proof_evidence_manifest_hash_stale")
    if latest.get("input_manifest_sha256") != sha256(input_manifest_path):
        add(errors, "proof_evidence_input_manifest_hash_stale")
    result = load(result_path)
    run_manifest = load(manifest_path)
    input_manifest = load(input_manifest_path)
    versions_path = run_dir / "versions.json"
    verus_value = run_manifest.get("verus_path")
    z3_value = run_manifest.get("z3_path")
    verus = Path(verus_value).resolve() if isinstance(verus_value, str) else None
    z3 = Path(z3_value).resolve() if isinstance(z3_value, str) else None
    if (
        not versions_path.is_file()
        or latest.get("versions_sha256") != sha256(versions_path)
        or run_manifest.get("versions_sha256") != sha256(versions_path)
        or result.get("versions_sha256") != sha256(versions_path)
    ):
        add(errors, "proof_tool_versions_stale")
    elif (
        load(versions_path).get("verus", {}).get("exit_code") != 0
        or load(versions_path).get("z3", {}).get("exit_code") != 0
    ):
        add(errors, "proof_tool_version_command_failed")
    if (
        verus is None
        or z3 is None
        or not verus.is_file()
        or not z3.is_file()
        or run_manifest.get("verus_binary_sha256") != sha256(verus)
        or run_manifest.get("z3_sha256") != sha256(z3)
    ):
        add(errors, "proof_tool_binary_stale")
    if not (
        latest.get("run_id")
        == result.get("run_id")
        == run_manifest.get("run_id")
    ):
        add(errors, "proof_evidence_run_id_mismatch")
    if result.get("status") != "passed":
        add(errors, "proof_evidence_run_failed")
    if (
        result.get("phase") != "all"
        or run_manifest.get("phase") != "all"
        or result.get("complete_campaign_run") is not True
        or run_manifest.get("complete_campaign_run") is not True
    ):
        add(errors, "proof_evidence_not_both_modes")
    if run_manifest.get("inventory_sha256") != sha256(
        specification.INVENTORY
    ):
        add(errors, "proof_evidence_inventory_stale")
    if run_manifest.get("proof_inventory_sha256") != sha256(TARGETS):
        add(errors, "proof_evidence_proof_inventory_stale")
    if run_manifest.get("specification_review_sha256") != sha256(
        check_specification.INDEPENDENT_REVIEW
    ):
        add(errors, "proof_evidence_specification_review_stale")
    if run_manifest.get("input_manifest_sha256") != sha256(
        input_manifest_path
    ):
        add(errors, "proof_evidence_input_manifest_unbound")
    for field, path in (
        ("inventory_sha256", specification.INVENTORY),
        ("proof_inventory_sha256", TARGETS),
        (
            "specification_review_sha256",
            check_specification.INDEPENDENT_REVIEW,
        ),
    ):
        if input_manifest.get(field) != sha256(path):
            add(errors, f"proof_input_manifest_{field}_stale")
    row_ids = {row["row_id"] for row in rows}
    if set(run_manifest.get("target_row_ids", [])) != row_ids:
        add(errors, "proof_evidence_identity_set_mismatch")
    if result.get("target_count") != len(rows):
        add(errors, "proof_evidence_target_count_mismatch")
    if result.get("verified_target_count") != len(rows):
        add(errors, "proof_evidence_verified_count_mismatch")
    run_id = result.get("run_id")
    expected_phases = {
        "implementation_no_verify",
        "implementation_actual",
        "completeness_no_verify",
        "completeness_actual",
    }
    expected_keys = {
        (row["row_id"], phase)
        for row in rows
        for phase in expected_phases
    }
    index = result.get("result_index", [])
    index_keys = [
        (record.get("row_id"), record.get("phase"))
        for record in index
        if isinstance(record, dict)
    ]
    if len(index_keys) != len(set(index_keys)):
        add(errors, "proof_evidence_result_index_duplicate")
    if set(index_keys) != expected_keys:
        add(errors, "proof_evidence_result_index_incomplete")
    if result.get("result_index_sha256") != runner.compact_hash(index):
        add(errors, "proof_evidence_result_index_hash_mismatch")
    closures = input_manifest.get("closures", [])
    closure_map = {
        (record.get("row_id"), record.get("proof_kind")): record
        for record in closures
        if isinstance(record, dict)
    }
    expected_closure_keys = {
        (row["row_id"], proof_kind)
        for row in rows
        for proof_kind in ("implementation", "completeness")
    }
    if (
        len(closures) != len(closure_map)
        or set(closure_map) != expected_closure_keys
    ):
        add(errors, "proof_input_closure_set_incomplete")
    rows_by_id = {row["row_id"]: row for row in rows}
    for key, closure in closure_map.items():
        inputs = closure.get("inputs", [])
        if closure.get("closure_sha256") != runner.compact_hash(inputs):
            add(errors, "proof_input_closure_hash_mismatch")
        row = rows_by_id.get(str(key[0]))
        proof_kind = str(key[1])
        if row is not None and proof_kind in {"implementation", "completeness"}:
            expected_paths = runner.verifier_input_closure(row, proof_kind)
            expected_inputs = [
                {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": sha256(path),
                    "size": path.stat().st_size,
                }
                for path in expected_paths
            ]
            expected_proof = str(
                (
                    target_dir(row) / f"{proof_kind}_proof.rs"
                ).relative_to(ROOT)
            )
            if (
                closure.get("row_id") != row["row_id"]
                or closure.get("target") != row["target"]
                or closure.get("proof_kind") != proof_kind
                or closure.get("proof_path") != expected_proof
                or inputs != expected_inputs
            ):
                add(
                    errors,
                    "proof_input_closure_definition_mismatch",
                    row_id=row["row_id"],
                    proof_kind=proof_kind,
                )
        for input_record in inputs:
            relative = input_record.get("path")
            if not isinstance(relative, str):
                add(errors, "proof_input_path_invalid")
                continue
            source = ROOT / relative
            snapshot = run_dir / "input_snapshot" / relative
            if (
                not source.is_file()
                or not snapshot.is_file()
                or input_record.get("sha256") != sha256(source)
                or input_record.get("sha256") != sha256(snapshot)
            ):
                add(
                    errors,
                    "proof_input_closure_file_stale",
                    path=relative,
                )
    records_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for index_record in index:
        row_id = index_record.get("row_id")
        phase = index_record.get("phase")
        key = (row_id, phase)
        path_value = index_record.get("path")
        if not isinstance(path_value, str):
            add(errors, "proof_command_record_path_invalid", row_id=row_id)
            continue
        try:
            command_record_path = runner.checked_descendant(
                ROOT / path_value,
                run_dir,
                "proof command record",
            )
        except ValueError:
            add(errors, "proof_command_record_path_escape", row_id=row_id)
            continue
        if (
            not command_record_path.is_file()
            or index_record.get("sha256") != sha256(command_record_path)
        ):
            add(errors, "proof_command_record_hash_mismatch", row_id=row_id)
            continue
        item = load(command_record_path)
        records_by_key[key] = item
        row = rows_by_id.get(row_id)
        if row is None:
            continue
        proof_kind = (
            "implementation"
            if str(phase).startswith("implementation_")
            else "completeness"
        )
        mode = (
            "no_verify"
            if str(phase).endswith("_no_verify")
            else "actual"
        )
        source_proof = target_dir(row) / f"{proof_kind}_proof.rs"
        snapshot_proof = (
            run_dir / "input_snapshot" / source_proof.relative_to(ROOT)
        )
        closure = closure_map.get((row_id, proof_kind), {})
        identity_valid = (
            item.get("run_id") == run_id
            and item.get("row_id") == row_id
            and item.get("target") == row["target"]
            and item.get("phase") == phase
            and item.get("proof_kind") == proof_kind
            and item.get("mode") == mode
            and item.get("source_proof_path")
            == str(source_proof.relative_to(ROOT))
            and item.get("proof_sha256") == sha256(source_proof)
            and item.get("expected_proof_sha256") == sha256(source_proof)
            and item.get("input_closure_sha256")
            == closure.get("closure_sha256")
            and item.get("inventory_sha256")
            == sha256(specification.INVENTORY)
            and item.get("proof_inventory_sha256") == sha256(TARGETS)
            and item.get("specification_review_sha256")
            == sha256(check_specification.INDEPENDENT_REVIEW)
            and item.get("verus_binary_sha256")
            == (sha256(verus) if verus is not None and verus.is_file() else None)
            and item.get("z3_sha256")
            == (sha256(z3) if z3 is not None and z3.is_file() else None)
        )
        if not identity_valid:
            add(
                errors,
                "proof_command_record_identity_mismatch",
                row_id=row_id,
                phase=phase,
            )
        if (
            item.get("status") != "passed"
            or item.get("exit_code") != 0
            or item.get("timed_out") is not False
            or item.get("cancelled") is not False
            or item.get("input_unchanged") is not True
        ):
            add(
                errors,
                "target_proof_result_failed",
                row_id=row_id,
                phase=phase,
            )
        command = item.get("command", [])
        expected_command = [
            str(verus),
            str(snapshot_proof.resolve()),
            "--crate-type=lib",
        ]
        if mode == "no_verify":
            expected_command.append("--no-verify")
        if command != expected_command:
            add(
                errors,
                "target_proof_command_mismatch",
                row_id=row_id,
                phase=phase,
            )
        command_artifact = item.get("command_path")
        if (
            isinstance(command_artifact, str)
            and (ROOT / command_artifact).is_file()
            and (ROOT / command_artifact).read_text(encoding="utf-8")
            != runner.command_text(expected_command, z3)
            + "\n"
        ):
            add(
                errors,
                "target_proof_command_capture_mismatch",
                row_id=row_id,
                phase=phase,
            )
        if item.get("working_directory") != str(snapshot_proof.parent):
            add(
                errors,
                "target_proof_working_directory_mismatch",
                row_id=row_id,
                phase=phase,
            )
        for path_field, hash_field in (
            ("command_path", "command_sha256"),
            ("stdout_path", "stdout_sha256"),
            ("stderr_path", "stderr_sha256"),
            ("rc_path", "rc_sha256"),
        ):
            artifact_value = item.get(path_field)
            if not isinstance(artifact_value, str):
                add(errors, "proof_raw_artifact_path_invalid", row_id=row_id)
                continue
            try:
                artifact = runner.checked_descendant(
                    ROOT / artifact_value,
                    run_dir,
                    "proof raw artifact",
                )
            except ValueError:
                add(errors, "proof_raw_artifact_path_escape", row_id=row_id)
                continue
            if (
                not artifact.is_file()
                or item.get(hash_field) != sha256(artifact)
            ):
                add(
                    errors,
                    "proof_raw_artifact_hash_mismatch",
                    row_id=row_id,
                    phase=phase,
                    artifact=path_field,
                )
        rc_value = item.get("rc_path")
        if isinstance(rc_value, str):
            rc_path = ROOT / rc_value
            if rc_path.is_file() and rc_path.read_text().strip() != "0":
                add(errors, "proof_raw_rc_mismatch", row_id=row_id, phase=phase)
        if mode == "actual":
            parsed = item.get("parsed_verification", {})
            if (
                parsed.get("errors") != 0
                or not isinstance(parsed.get("verified"), int)
                or parsed["verified"] < 1
            ):
                add(
                    errors,
                    "actual_verus_result_unparsed",
                    row_id=row_id,
                    phase=phase,
                )
    for row in rows:
        pointer_path = target_dir(row) / "verification_manifest.json"
        colocated_pointer = target_dir(row) / "evidence" / "latest.json"
        if not pointer_path.is_file() or not colocated_pointer.is_file():
            add(
                errors,
                "target_verification_pointer_missing",
                row_id=row["row_id"],
            )
            continue
        pointer = load(pointer_path)
        if colocated_pointer.read_bytes() != pointer_path.read_bytes():
            add(
                errors,
                "target_colocated_evidence_pointer_mismatch",
                row_id=row["row_id"],
            )
        pointer_keys = {
            (
                row["row_id"],
                record.get("phase"),
            )
            for record in pointer.get("command_records", [])
        }
        if (
            pointer.get("authoritative") is not False
            or pointer.get("run_id") != run_id
            or pointer_keys
            != {(row["row_id"], phase) for phase in expected_phases}
        ):
            add(
                errors,
                "target_verification_pointer_stale",
                row_id=row["row_id"],
            )
    return errors


def mutation_errors(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    latest_path = mutation_runner.MUTATION_ROOT / "latest.json"
    if not MUTATION_SUMMARY.is_file() or not latest_path.is_file():
        return ([{"code": "mutation_summary_missing"}], None)
    summary = load(MUTATION_SUMMARY)
    latest = load(latest_path)
    errors: list[dict[str, Any]] = []
    try:
        run_dir = runner.checked_descendant(
            ROOT / str(latest.get("run_dir", "")),
            mutation_runner.MUTATION_ROOT / "runs",
            "mutation evidence run",
        )
    except ValueError:
        return ([{"code": "mutation_run_path_invalid"}], summary)
    result_path = run_dir / "result.json"
    manifest_path = run_dir / "manifest.json"
    input_manifest_path = run_dir / "input_manifest.json"
    if not all(
        path.is_file()
        for path in (result_path, manifest_path, input_manifest_path)
    ):
        return ([{"code": "mutation_run_incomplete"}], summary)
    if (
        latest.get("result_sha256") != sha256(result_path)
        or latest.get("manifest_sha256") != sha256(manifest_path)
        or latest.get("input_manifest_sha256")
        != sha256(input_manifest_path)
    ):
        add(errors, "mutation_latest_hash_stale")
    if MUTATION_SUMMARY.read_bytes() != result_path.read_bytes():
        add(errors, "mutation_summary_not_authoritative_result")
    run_manifest = load(manifest_path)
    input_manifest = load(input_manifest_path)
    versions_path = run_dir / "versions.json"
    verus_value = run_manifest.get("verus_path")
    z3_value = run_manifest.get("z3_path")
    verus = Path(verus_value).resolve() if isinstance(verus_value, str) else None
    z3 = Path(z3_value).resolve() if isinstance(z3_value, str) else None
    if (
        not versions_path.is_file()
        or latest.get("versions_sha256") != sha256(versions_path)
        or run_manifest.get("versions_sha256") != sha256(versions_path)
        or summary.get("versions_sha256") != sha256(versions_path)
    ):
        add(errors, "mutation_tool_versions_stale")
    elif (
        load(versions_path).get("verus", {}).get("exit_code") != 0
        or load(versions_path).get("z3", {}).get("exit_code") != 0
    ):
        add(errors, "mutation_tool_version_command_failed")
    if (
        verus is None
        or z3 is None
        or not verus.is_file()
        or not z3.is_file()
        or run_manifest.get("verus_binary_sha256") != sha256(verus)
        or run_manifest.get("z3_sha256") != sha256(z3)
    ):
        add(errors, "mutation_tool_binary_stale")
    if (
        summary.get("status") != "passed"
        or summary.get("complete_campaign_run") is not True
        or summary.get("representative") is not False
        or run_manifest.get("complete_campaign_run") is not True
        or run_manifest.get("representative") is not False
    ):
        add(errors, "mutation_gate_failed")
    if (
        summary.get("inventory_sha256") != sha256(specification.INVENTORY)
        or run_manifest.get("inventory_sha256")
        != sha256(specification.INVENTORY)
    ):
        add(errors, "mutation_inventory_stale")
    if (
        summary.get("proof_inventory_sha256") != sha256(TARGETS)
        or run_manifest.get("proof_inventory_sha256") != sha256(TARGETS)
    ):
        add(errors, "mutation_proof_inventory_stale")
    if (
        summary.get("manifest_sha256") != sha256(manifest_path)
        or summary.get("input_manifest_sha256")
        != sha256(input_manifest_path)
        or run_manifest.get("input_manifest_sha256")
        != sha256(input_manifest_path)
    ):
        add(errors, "mutation_manifest_binding_stale")
    input_closures = input_manifest.get("closures", [])
    input_closure_map = {
        (record.get("row_id"), record.get("proof_kind")): record
        for record in input_closures
        if isinstance(record, dict)
    }
    expected_closure_keys = {
        (row["row_id"], proof_kind)
        for row in rows
        for proof_kind in ("implementation", "completeness")
    }
    if (
        len(input_closures) != len(input_closure_map)
        or set(input_closure_map) != expected_closure_keys
    ):
        add(errors, "mutation_input_closure_set_incomplete")
    mutation_rows_by_id = {row["row_id"]: row for row in rows}
    for key, closure in input_closure_map.items():
        inputs = closure.get("inputs", [])
        if closure.get("closure_sha256") != runner.compact_hash(inputs):
            add(errors, "mutation_input_closure_hash_mismatch")
        row = mutation_rows_by_id.get(str(key[0]))
        proof_kind = str(key[1])
        if row is not None and proof_kind in {"implementation", "completeness"}:
            expected_paths = runner.verifier_input_closure(row, proof_kind)
            expected_inputs = [
                {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": sha256(path),
                    "size": path.stat().st_size,
                }
                for path in expected_paths
            ]
            if (
                closure.get("target") != row["target"]
                or closure.get("proof_path")
                != str(
                    (
                        target_dir(row) / f"{proof_kind}_proof.rs"
                    ).relative_to(ROOT)
                )
                or inputs != expected_inputs
            ):
                add(
                    errors,
                    "mutation_input_closure_definition_mismatch",
                    row_id=row["row_id"],
                    proof_kind=proof_kind,
                )
        for input_record in inputs:
            relative = input_record.get("path")
            if not isinstance(relative, str):
                add(errors, "mutation_input_path_invalid")
                continue
            source = ROOT / relative
            snapshot = run_dir / "input_snapshot" / relative
            if (
                not source.is_file()
                or not snapshot.is_file()
                or input_record.get("sha256") != sha256(source)
                or input_record.get("sha256") != sha256(snapshot)
            ):
                add(
                    errors,
                    "mutation_input_closure_file_stale",
                    path=relative,
                )
    categories = set(summary.get("covered_categories", []))
    missing = sorted(REQUIRED_MUTATION_CATEGORIES - categories)
    if missing:
        add(errors, "mutation_categories_missing", categories=missing)
    rows_by_id = {row["row_id"]: row for row in rows}
    expected_pairs: set[tuple[str, str]] = set()
    expected_probes: set[tuple[str, str, str]] = set()
    plan_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        manifest = load(target_dir(row) / "proof_manifest.json")
        for proof_kind in ("implementation", "completeness"):
            expected_pairs.add((row["row_id"], proof_kind))
            try:
                plans = mutation_runner.mutation_plans(
                    manifest, proof_kind
                )
                ids = [
                    mutation_runner.mutation_id(plan, index, len(plans))
                    for index, plan in enumerate(plans)
                ]
            except ValueError:
                add(
                    errors,
                    "mutation_plan_schema_invalid",
                    row_id=row["row_id"],
                    proof_kind=proof_kind,
                )
                continue
            if not plans:
                add(
                    errors,
                    "mutation_plan_missing",
                    row_id=row["row_id"],
                    proof_kind=proof_kind,
                )
                continue
            if len(ids) != len(set(ids)):
                add(
                    errors,
                    "mutation_plan_id_duplicate",
                    row_id=row["row_id"],
                    proof_kind=proof_kind,
                )
                continue
            for mutation_id_value, plan in zip(ids, plans):
                key = (row["row_id"], proof_kind, mutation_id_value)
                expected_probes.add(key)
                plan_map[key] = plan
    index = summary.get("result_index", [])
    index_probes = [
        (
            record.get("row_id"),
            record.get("proof_kind"),
            record.get("mutation_id"),
        )
        for record in index
        if isinstance(record, dict)
    ]
    if len(index_probes) != len(set(index_probes)):
        add(errors, "mutation_result_index_duplicate")
    if set(index_probes) != expected_probes:
        add(errors, "mutation_result_index_incomplete")
    if (
        summary.get("probe_count") != len(expected_probes)
        or run_manifest.get("probe_count") != len(expected_probes)
        or summary.get("syntax_valid_count") != len(expected_probes)
        or summary.get("actual_verus_rejected_count")
        != len(expected_probes)
    ):
        add(errors, "mutation_probe_count_mismatch")
    if summary.get("result_index_sha256") != runner.compact_hash(index):
        add(errors, "mutation_result_index_hash_mismatch")
    manifest_probes = {
        (
            record.get("row_id"),
            record.get("proof_kind"),
            record.get("mutation_id"),
        )
        for record in run_manifest.get("expected_probes", [])
        if isinstance(record, dict)
    }
    if manifest_probes != expected_probes:
        add(errors, "mutation_manifest_probe_set_incomplete")
    for expected_record in run_manifest.get("expected_probes", []):
        if not isinstance(expected_record, dict):
            continue
        key = (
            str(expected_record.get("row_id")),
            str(expected_record.get("proof_kind")),
            str(expected_record.get("mutation_id")),
        )
        plan = plan_map.get(key)
        row = rows_by_id.get(key[0])
        if (
            plan is None
            or row is None
            or expected_record.get("plan_sha256")
            != runner.compact_hash(plan)
            or expected_record.get("proof_manifest_sha256")
            != sha256(target_dir(row) / "proof_manifest.json")
        ):
            add(
                errors,
                "mutation_manifest_probe_identity_stale",
                row_id=key[0],
                proof_kind=key[1],
                mutation_id=key[2],
            )
    for row_id, proof_kind in expected_pairs:
        row = rows_by_id[row_id]
        pointer_path = (
            target_dir(row)
            / "evidence"
            / "mutations"
            / f"{proof_kind}.json"
        )
        pair_records = sorted(
            (
                {
                    "mutation_id": record.get("mutation_id"),
                    "record_path": record.get("path"),
                    "record_sha256": record.get("sha256"),
                }
                for record in index
                if isinstance(record, dict)
                and record.get("row_id") == row_id
                and record.get("proof_kind") == proof_kind
            ),
            key=lambda record: str(record["mutation_id"]),
        )
        if not pointer_path.is_file():
            add(
                errors,
                "mutation_colocated_pointer_missing",
                row_id=row_id,
                proof_kind=proof_kind,
            )
        elif load(pointer_path) != {
            "schema_version": 2,
            "authoritative": False,
            "run_id": summary.get("run_id"),
            "row_id": row_id,
            "target": row["target"],
            "proof_kind": proof_kind,
            "records": pair_records,
        }:
            add(
                errors,
                "mutation_colocated_pointer_stale",
                row_id=row_id,
                proof_kind=proof_kind,
            )
    for index_record in index:
        row_id = index_record.get("row_id")
        proof_kind = index_record.get("proof_kind")
        mutation_id_value = index_record.get("mutation_id")
        path_value = index_record.get("path")
        if not isinstance(path_value, str):
            add(errors, "mutation_record_path_invalid", row_id=row_id)
            continue
        try:
            path = runner.checked_descendant(
                ROOT / path_value,
                run_dir,
                "mutation record",
            )
        except ValueError:
            add(errors, "mutation_record_path_escape", row_id=row_id)
            continue
        if (
            not path.is_file()
            or index_record.get("sha256") != sha256(path)
        ):
            add(errors, "mutation_record_hash_mismatch", row_id=row_id)
            continue
        record = load(path)
        row = rows_by_id.get(row_id)
        if row is None:
            continue
        manifest_path_current = target_dir(row) / "proof_manifest.json"
        plan = plan_map.get(
            (str(row_id), str(proof_kind), str(mutation_id_value))
        )
        if plan is None:
            add(
                errors,
                "mutation_plan_missing",
                row_id=row_id,
                proof_kind=proof_kind,
                mutation_id=mutation_id_value,
            )
            continue
        baseline = target_dir(row) / f"{proof_kind}_proof.rs"
        identity_valid = (
            record.get("run_id") == summary.get("run_id")
            and record.get("row_id") == row_id
            and record.get("target") == row["target"]
            and record.get("proof_family") == row.get("proof_family")
            and record.get("proof_kind") == proof_kind
            and record.get("mutation_id") == mutation_id_value
            and record.get("plan_sha256") == runner.compact_hash(plan)
            and record.get("proof_manifest_sha256")
            == sha256(manifest_path_current)
            and record.get("baseline_proof_sha256") == sha256(baseline)
        )
        if not identity_valid:
            add(errors, "mutation_record_identity_stale", row_id=row_id)
        if (
            record.get("baseline_fragment") != plan.get("fragment")
            or record.get("replacement") != plan.get("replacement")
            or record.get("category") != plan.get("category")
            or record.get("omitted_observable")
            != plan.get("omitted_observable")
        ):
            add(errors, "mutation_plan_fields_stale", row_id=row_id)
        if (
            record.get("syntax_valid") is not True
            or record.get("actual_verus_rejected") is not True
        ):
            add(
                errors,
                "mutation_not_decisive",
                row_id=record.get("row_id"),
                category=record.get("category"),
            )
        mutated_path_value = record.get("mutated_path")
        mutated_path: Path | None = None
        if not isinstance(mutated_path_value, str):
            add(errors, "mutation_source_path_invalid", row_id=row_id)
        else:
            try:
                mutated_path = runner.checked_descendant(
                    run_dir / mutated_path_value,
                    run_dir / "input_snapshot",
                    "mutated proof",
                )
            except ValueError:
                add(errors, "mutation_source_path_escape", row_id=row_id)
            else:
                if (
                    not mutated_path.is_file()
                    or record.get("mutated_sha256") != sha256(mutated_path)
                ):
                    add(errors, "mutation_source_hash_mismatch", row_id=row_id)
                    mutated_path = None
                    continue
                baseline_snapshot = (
                    run_dir
                    / "input_snapshot"
                    / baseline.relative_to(ROOT)
                )
                fragment = plan.get("fragment")
                replacement = plan.get("replacement")
                if (
                    not baseline_snapshot.is_file()
                    or not isinstance(fragment, str)
                    or not isinstance(replacement, str)
                ):
                    add(errors, "mutation_baseline_snapshot_invalid", row_id=row_id)
                else:
                    baseline_text = baseline_snapshot.read_text(encoding="utf-8")
                    if baseline_text.count(fragment) != 1:
                        add(
                            errors,
                            "mutation_anchor_count_invalid",
                            row_id=row_id,
                        )
                    elif mutated_path.read_text(encoding="utf-8") != (
                        baseline_text.replace(fragment, replacement, 1)
                    ):
                        add(
                            errors,
                            "mutation_source_not_planned_replacement",
                            row_id=row_id,
                        )
        nested = record.get("results", [])
        modes = {item.get("mode") for item in nested}
        if modes != {"no_verify", "actual"}:
            add(errors, "mutation_modes_incomplete", row_id=row_id)
            continue
        for nested_index in nested:
            nested_path_value = nested_index.get("path")
            if not isinstance(nested_path_value, str):
                add(errors, "mutation_command_path_invalid", row_id=row_id)
                continue
            try:
                nested_path = runner.checked_descendant(
                    ROOT / nested_path_value,
                    run_dir,
                    "mutation command record",
                )
            except ValueError:
                add(errors, "mutation_command_path_escape", row_id=row_id)
                continue
            if (
                not nested_path.is_file()
                or nested_index.get("sha256") != sha256(nested_path)
            ):
                add(errors, "mutation_command_hash_mismatch", row_id=row_id)
                continue
            command = load(nested_path)
            mode = nested_index.get("mode")
            expected_exit = (
                command.get("exit_code") == 0
                if mode == "no_verify"
                else command.get("exit_code") != 0
            )
            if (
                command.get("run_id") != summary.get("run_id")
                or command.get("row_id") != row_id
                or command.get("target") != row["target"]
                or command.get("proof_kind") != proof_kind
                or command.get("mutation_id") != mutation_id_value
                or command.get("mode") != mode
                or command.get("status") != "passed"
                or command.get("expected_result_observed") is not True
                or command.get("timed_out") is not False
                or command.get("cancelled") is not False
                or not expected_exit
            ):
                add(
                    errors,
                    "mutation_command_result_invalid",
                    row_id=row_id,
                    proof_kind=proof_kind,
                    mode=mode,
                )
            command_line = command.get("command", [])
            has_no_verify = "--no-verify" in command_line
            if has_no_verify != (mode == "no_verify"):
                add(
                    errors,
                    "mutation_command_mode_mismatch",
                    row_id=row_id,
                    mode=mode,
                )
            if mutated_path is not None:
                expected_command = [
                    str(verus),
                    str(mutated_path),
                    "--crate-type=lib",
                ]
                if mode == "no_verify":
                    expected_command.append("--no-verify")
                if (
                    command_line != expected_command
                    or command.get("working_directory")
                    != str(mutated_path.parent)
                    or command.get("verus_binary_sha256")
                    != (
                        sha256(verus)
                        if verus is not None and verus.is_file()
                        else None
                    )
                    or command.get("z3_sha256")
                    != (
                        sha256(z3)
                        if z3 is not None and z3.is_file()
                        else None
                    )
                    or command.get("sha256") != sha256(mutated_path)
                ):
                    add(
                        errors,
                        "mutation_command_identity_mismatch",
                        row_id=row_id,
                        mode=mode,
                    )
                command_capture = command.get("command_path")
                if (
                    isinstance(command_capture, str)
                    and (ROOT / command_capture).is_file()
                    and (ROOT / command_capture).read_text(
                        encoding="utf-8"
                    )
                    != f"VERUS_Z3_PATH={z3} "
                    + " ".join(expected_command)
                    + "\n"
                ):
                    add(
                        errors,
                        "mutation_command_capture_mismatch",
                        row_id=row_id,
                        mode=mode,
                    )
            for path_field, hash_field in (
                ("command_path", "command_sha256"),
                ("stdout_path", "stdout_sha256"),
                ("stderr_path", "stderr_sha256"),
                ("rc_path", "rc_sha256"),
            ):
                artifact_value = command.get(path_field)
                if not isinstance(artifact_value, str):
                    add(errors, "mutation_raw_path_invalid", row_id=row_id)
                    continue
                try:
                    artifact = runner.checked_descendant(
                        ROOT / artifact_value,
                        run_dir,
                        "mutation raw artifact",
                    )
                except ValueError:
                    add(errors, "mutation_raw_path_escape", row_id=row_id)
                    continue
                if (
                    not artifact.is_file()
                    or command.get(hash_field) != sha256(artifact)
                ):
                    add(
                        errors,
                        "mutation_raw_hash_mismatch",
                        row_id=row_id,
                        mode=mode,
                    )
            if mode == "actual":
                stdout_value = command.get("stdout_path")
                stderr_value = command.get("stderr_path")
                output = ""
                for value in (stdout_value, stderr_value):
                    if isinstance(value, str) and (ROOT / value).is_file():
                        output += (ROOT / value).read_text(
                            encoding="utf-8",
                            errors="replace",
                        )
                if not any(
                    message in output
                    for message in mutation_runner.EXPECTED_REJECTION
                ):
                    add(
                        errors,
                        "mutation_rejection_not_semantic",
                        row_id=row_id,
                        proof_kind=proof_kind,
                    )
    return errors, summary


def trust_payload(records: list[dict[str, Any]]) -> dict[str, Any]:
    categories = Counter(
        category
        for record in records
        for category in record["semantic_boundary_categories"]
    )
    float_boundary = load(specification.FLOAT_MODEL_BOUNDARY)
    float_records = float_boundary["records"]
    return {
        "schema_version": 1,
        "module": "core::cmp",
        "status": "passed",
        "language": {
            "no_additional_boundary": (
                "No target-local implementation or dependency boundary beyond "
                "the accepted contract, source adaptation, Verus/rustc/Z3, "
                "vstd, and reviewed models."
            ),
            "foundational_trust_free": (
                "Not claimed. Verus, rustc, Z3, vstd, source adaptations, and "
                "all listed semantic models remain foundational trust."
            ),
            "rejected_float_boundary": (
                "The loaded vstd float result predicates are whole-target "
                "semantic boundaries and are rejected, not counted as "
                "implementation or completeness proof trust."
            ),
        },
        "counts": {
            "selected_targets": len(records),
            "target_level_external_body": sum(
                record["target_external_body"] for record in records
            ),
            "completeness_level_external_body": sum(
                record["completeness_external_body"] for record in records
            ),
            "implementation_harness_literal_external_body": sum(
                record["implementation_raw_external_body_count"]
                for record in records
            ),
            "completeness_harness_literal_external_body": sum(
                record["completeness_raw_external_body_count"]
                for record in records
            ),
            "helper_dependency_function_external_body": sum(
                record["helper_dependency_function_external_body_count"]
                for record in records
            ),
            "model_or_type_external_body": sum(
                record["model_or_type_external_body_count"]
                for record in records
            ),
            "harness_wide_literal_external_body": sum(
                record["harness_wide_literal_external_body_count"]
                for record in records
            ),
            "semantic_boundaries": sum(
                record["semantic_boundary_count"] for record in records
            ),
            "no_additional_implementation_dependency_boundary": sum(
                record["no_additional_implementation_dependency_boundary"]
                for record in records
            ),
            "foundational_end_to_end_trust_free": 0,
            "rejected_whole_target_float_boundaries": len(
                float_records
            ),
        },
        "semantic_boundary_categories": dict(sorted(categories.items())),
        "rejected_model_boundaries": [
            {
                "row_id": record["row_id"],
                "target": record["target"],
                "function": record["missing_model_boundary"]["predicate"],
                "whole_target_outcome": True,
                "accepted_for_contract_or_proof": False,
                "evidence_path": str(
                    specification.FLOAT_MODEL_BOUNDARY.relative_to(ROOT)
                ),
                "evidence_sha256": sha256(
                    specification.FLOAT_MODEL_BOUNDARY
                ),
            }
            for record in float_records
        ],
        "records": records,
    }


def aggregate_payload(
    live_rows: list[dict[str, Any]],
    trust: dict[str, Any],
    evidence_required: bool,
    mutation_required: bool,
) -> dict[str, Any]:
    proof_rows = load(TARGETS)["rows"]
    selected_ids = {row["row_id"] for row in proof_rows}
    generated = sum(
        row["disposition"] == "pending"
        and row["row_id"] in selected_ids
        for row in live_rows
    )
    exact = sum(
        row["disposition"] == "exact_vstd"
        and row["row_id"] in selected_ids
        for row in live_rows
    )
    impossible = len(live_rows) - len(proof_rows)
    evidence_passed = (
        runner.EVIDENCE_ROOT.joinpath("latest.json").is_file()
        and not evidence_errors(proof_rows)
    )
    mutations_passed = (
        MUTATION_SUMMARY.is_file()
        and not mutation_errors(proof_rows)[0]
    )
    verified = len(proof_rows) if evidence_passed else 0
    return {
        "schema_version": 1,
        "module": "core::cmp",
        "status": (
            "passed"
            if (
                (evidence_passed or not evidence_required)
                and (mutations_passed or not mutation_required)
            )
            else "pending"
        ),
        "inventory_sha256": sha256(specification.INVENTORY),
        "proof_inventory_sha256": sha256(TARGETS),
        "counts": {
            "stable_inventory_total": len(live_rows),
            "selected": len(proof_rows),
            "generated_contract": generated,
            "exact_vstd_contract": exact,
            "genuinely_impossible": impossible,
            "actual_verus_verified": verified,
            "failed": 0 if evidence_passed else len(proof_rows),
            "pending": 0 if evidence_passed else len(proof_rows),
            **trust["counts"],
        },
        "evidence_required": evidence_required,
        "evidence_passed": evidence_passed,
        "mutations_required": mutation_required,
        "mutations_passed": mutations_passed,
        "trust_audit": str(TRUST_AUDIT.relative_to(ROOT)),
    }


def review_request_payload() -> dict[str, Any]:
    paths = [
        TARGETS,
        TARGETS_CSV,
        DEPENDENCY_GRAPH,
        DEPENDENCY_GRAPH_DOT,
        FROZEN_INPUTS,
        FROZEN_INPUTS_CSV,
        AUTHORIZATION,
        AGGREGATE_JSON,
        TRUST_AUDIT,
        TRUST_MD,
        MUTATION_SUMMARY,
        runner.EVIDENCE_ROOT / "latest.json",
        specification.INVENTORY,
        specification.FLOAT_MODEL_BOUNDARY,
        check_specification.INDEPENDENT_REVIEW,
        check_specification.CANONICAL_HANDOFF,
    ]
    artifacts = [
        {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256(path),
        }
        for path in paths
        if path.is_file()
    ]
    return {
        "schema_version": 1,
        "module": "core::cmp",
        "review_type": "implementation_and_completeness",
        "required_verdict": {
            "producer_role": "reviewer",
            "review_status": "done",
            "implementation_completeness_accepted": True,
            "independent": True,
            "canonical_handoff_required": True,
            "approved_genuinely_impossible_count": len(
                specification.model_boundary_rows(
                    load(specification.INVENTORY)["rows"]
                )
            ),
        },
        "artifacts": artifacts,
        "review_questions": [
            (
                "Does every selected exact-vstd or generated identity have "
                "exactly one source/contract-bound target directory?"
            ),
            (
                "Are the 14 independently approved float model-boundary "
                "exceptions excluded from proof and mutation success counts?"
            ),
            "Is every implementation_target executable, source-shaped, and free of whole-target assumptions?",
            "Does every completeness theorem compare two accepted-contract outcomes under the same full environment?",
            "Do all four fresh Verus modes pass per target with current hashes?",
            "Do semantic mutations independently reject chaining equal/continue, non-equal relation, and None-to-false branches as well as omitted forwarding, callback, reversal, distinction, specialization, and panic behavior?",
            "Are literal external_body and semantic trust boundaries complete and accurately categorized?",
        ],
    }


def review_errors() -> list[dict[str, Any]]:
    if not REVIEW.is_file():
        return [{"code": "implementation_review_missing"}]
    review = load(REVIEW)
    errors: list[dict[str, Any]] = []
    request = load(REVIEW_REQUEST)
    if review.get("schema_version") != 1:
        add(errors, "implementation_review_schema_invalid")
    if review.get("module") != "core::cmp":
        add(errors, "implementation_review_module_invalid")
    if review.get("review_type") != "implementation_and_completeness":
        add(errors, "implementation_review_type_invalid")
    if review.get("producer_role") != "reviewer":
        add(errors, "implementation_reviewer_role_invalid")
    independence = review.get("independence", {})
    if (
        independence.get("independent") is not True
        or independence.get("artifacts_modified_by_reviewer") != []
    ):
        add(errors, "implementation_review_not_independent")
    decision = review.get("review", {})
    if decision.get("status") != "done":
        add(errors, "implementation_review_status_not_done")
    if decision.get("implementation_completeness_accepted") is not True:
        add(errors, "implementation_completeness_not_accepted")
    if decision.get("rejected") not in (None, False):
        add(errors, "implementation_review_contradictory_rejection")
    if decision.get("unresolved_findings") != []:
        add(errors, "implementation_review_has_findings")
    questions = request.get("review_questions")
    if not isinstance(questions, list) or not all(
        isinstance(question, str) for question in questions
    ):
        add(errors, "implementation_review_request_questions_invalid")
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
        add(errors, "implementation_review_question_set_invalid")
    request_binding = review.get("review_request", {})
    if request_binding != {
        "path": str(REVIEW_REQUEST.relative_to(ROOT)),
        "sha256": sha256(REVIEW_REQUEST),
    }:
        add(errors, "implementation_review_request_stale")
    expected = {
        item["path"]: item["sha256"] for item in request["artifacts"]
    }
    actual = artifact_binding_map(review.get("artifact_bindings"))
    if actual is None:
        add(errors, "implementation_review_artifact_bindings_schema_invalid")
    elif actual != expected:
        add(errors, "implementation_review_artifacts_stale")
    live_rows = load(specification.INVENTORY)["rows"]
    selected_count = len(selected_live_rows(live_rows))
    if decision.get("accepted_target_count") != selected_count:
        add(errors, "implementation_review_target_count_mismatch")
    if decision.get("approved_genuinely_impossible_count") != (
        len(live_rows) - selected_count
    ):
        add(errors, "implementation_review_impossible_count_mismatch")
    canonical = review.get("canonical_handoff", {})
    if canonical.get("path") != str(
        CANONICAL_REVIEW_HANDOFF.relative_to(ROOT)
    ):
        add(errors, "canonical_implementation_handoff_path_invalid")
    elif not CANONICAL_REVIEW_HANDOFF.is_file():
        add(errors, "canonical_implementation_handoff_missing")
    elif canonical.get("sha256") != sha256(CANONICAL_REVIEW_HANDOFF):
        add(errors, "canonical_implementation_handoff_stale")
    else:
        handoff = load(CANONICAL_REVIEW_HANDOFF)
        handoff_review = handoff.get("review", {})
        mission = handoff.get("mission", {})
        mission_path = Path(str(mission.get("path", "")))
        if (
            handoff.get("producer_role") != "reviewer"
            or handoff_review.get("status") != "done"
            or handoff_review.get("next_action") != ""
            or handoff_review.get(
                "implementation_completeness_accepted"
            )
            is not True
            or handoff_review.get(
                "approved_genuinely_impossible_count"
            )
            != len(live_rows) - selected_count
            or handoff_review.get("unresolved_findings") != []
        ):
            add(errors, "canonical_implementation_handoff_verdict_invalid")
        if handoff.get("review_request") != {
            "path": str(REVIEW_REQUEST.relative_to(ROOT)),
            "sha256": sha256(REVIEW_REQUEST),
        }:
            add(errors, "canonical_implementation_handoff_request_stale")
        if handoff.get("artifact_bindings") != request["artifacts"]:
            add(errors, "canonical_implementation_handoff_artifacts_stale")
        if (
            mission_path != check_specification.MISSION_PATH
            or not mission_path.is_file()
            or mission.get("sha256") != sha256(mission_path)
        ):
            add(errors, "canonical_implementation_handoff_mission_stale")
    return errors


def validate(
    *,
    require_results: bool,
    require_mutations: bool,
    require_review: bool,
    write_artifacts: bool = True,
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    spec_errors = check_specification.validate(
        require_evidence=True,
        require_review=True,
    )
    for error in spec_errors:
        add(errors, "specification_gate_failed", detail=error)
    if not TARGETS.is_file():
        return [*errors, {"code": "proof_inventory_missing"}]
    live_rows = load(specification.INVENTORY)["rows"]
    selected_rows = selected_live_rows(live_rows)
    errors.extend(authorization_errors(selected_rows))
    proof_rows = load(TARGETS).get("rows", [])
    structural, trust_records = structural_errors(live_rows, proof_rows)
    errors.extend(structural)
    trust = trust_payload(trust_records)
    if trust["counts"]["target_level_external_body"] != 0:
        add(errors, "target_external_body_nonzero")
    if trust["counts"]["completeness_level_external_body"] != 0:
        add(errors, "completeness_external_body_nonzero")
    if write_artifacts:
        atomic_json(TRUST_AUDIT, trust)
    trust_markdown = (
        "# core::cmp trust-boundary audit\n\n"
        f"- Selected targets: {len(trust_records)}\n"
        f"- Target-level `external_body`: {trust['counts']['target_level_external_body']}\n"
        f"- Completeness-level `external_body`: {trust['counts']['completeness_level_external_body']}\n"
        f"- Harness-wide implementation `external_body`: {trust['counts']['implementation_harness_literal_external_body']}\n"
        f"- Harness-wide completeness `external_body`: {trust['counts']['completeness_harness_literal_external_body']}\n"
        f"- Helper/dependency function `external_body`: {trust['counts']['helper_dependency_function_external_body']}\n"
        f"- Model/type `external_body`: {trust['counts']['model_or_type_external_body']}\n"
        f"- Combined harness-level `external_body`: {trust['counts']['harness_wide_literal_external_body']}\n"
        f"- No-additional-boundary targets: {trust['counts']['no_additional_implementation_dependency_boundary']}\n"
        f"- Rejected whole-target float model boundaries: {trust['counts']['rejected_whole_target_float_boundaries']}\n"
        "- Foundational end-to-end trust-free targets: 0 (not claimed)\n\n"
        "No-additional-boundary is campaign-local language; Verus, rustc, Z3, "
        "vstd, reviewed models, and source adaptations remain foundational trust.\n"
    )
    if write_artifacts:
        atomic_bytes(TRUST_MD, trust_markdown.encode())
    if require_results:
        errors.extend(evidence_errors(proof_rows))
    mutation_summary = None
    if require_mutations:
        mutation_gate_errors, mutation_summary = mutation_errors(proof_rows)
        errors.extend(mutation_gate_errors)
    aggregate = aggregate_payload(
        live_rows,
        trust,
        require_results,
        require_mutations,
    )
    if write_artifacts:
        atomic_json(AGGREGATE_JSON, aggregate)
    aggregate_markdown = (
        "# core::cmp implementation/completeness aggregate\n\n"
        f"- Selected: {aggregate['counts']['selected']}\n"
        f"- Generated-contract: {aggregate['counts']['generated_contract']}\n"
        f"- Exact-vstd: {aggregate['counts']['exact_vstd_contract']}\n"
        f"- Genuinely impossible: {aggregate['counts']['genuinely_impossible']}\n"
        f"- Actual-Verus verified: {aggregate['counts']['actual_verus_verified']}\n"
        f"- Failed: {aggregate['counts']['failed']}\n"
        f"- Pending: {aggregate['counts']['pending']}\n"
    )
    if write_artifacts:
        atomic_bytes(AGGREGATE_MD, aggregate_markdown.encode())
        atomic_json(REVIEW_REQUEST, review_request_payload())
    if require_review:
        errors.extend(review_errors())
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-results", action="store_true")
    parser.add_argument("--require-mutations", action="store_true")
    parser.add_argument("--require-review", action="store_true")
    args = parser.parse_args()
    errors = validate(
        require_results=args.require_results,
        require_mutations=args.require_mutations,
        require_review=args.require_review,
    )
    report = {
        "schema_version": 1,
        "module": "core::cmp",
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "requirements": {
            "results": args.require_results,
            "mutations": args.require_mutations,
            "review": args.require_review,
        },
    }
    atomic_json(CHECK_REPORT, report)
    print(json.dumps(report, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
