#!/usr/bin/env python3
"""Build the complete 64-row core::result specification view."""

from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path
import re
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import specification_support as support


IMPORTS = [
    "core::clone::Clone",
    "core::cmp::{Ord, Ordering, PartialEq, PartialOrd}",
    "core::default::Default",
    "core::fmt::{Debug, Formatter}",
    "core::hash::{Hash, Hasher}",
    (
        "core::iter::{DoubleEndedIterator, FromIterator, IntoIterator, "
        "Iterator, Product, Sum}"
    ),
    "core::ops::{Deref, DerefMut}",
    "core::option::Option",
    "core::result::{IntoIter, Iter, IterMut, Result}",
    "vstd::prelude::*",
    (
        "vstd::std_specs::iter::{into_iter_remaining, "
        "FromIteratorSpec}"
    ),
]


def source_record(row: dict[str, Any]) -> dict[str, Any]:
    frozen = support.frozen_source_for(row)
    if support.sha256(frozen) != row["source_file_sha256"]:
        raise ValueError(f"frozen source hash mismatch for {row['target']}")
    excerpt = support.source_excerpt(frozen, row)
    if support.text_sha256(excerpt) != row["source_excerpt_sha256"]:
        raise ValueError(f"source excerpt hash mismatch for {row['target']}")
    return {
        "canonical_path": row["source_path"],
        "copied_path": str(frozen.relative_to(support.ROOT)),
        "end_column": int(row["source_end_column"]),
        "end_line": int(row["source_end_line"]),
        "excerpt_sha256": row["source_excerpt_sha256"],
        "file_sha256": row["source_file_sha256"],
        "start_column": int(row["source_start_column"]),
        "start_line": int(row["source_start_line"]),
    }


def declaration_text(declaration: dict[str, Any]) -> str:
    path = support.ROOT / str(declaration["source_path"])
    return support.extract_lines(
        path,
        int(declaration["start_line"]),
        int(declaration["end_line"]),
    ).rstrip("\n")


def vocabulary_inner() -> str:
    source = support.VOCABULARY_PATH.read_text(encoding="utf-8")
    start_marker = "verus! {"
    start = source.find(start_marker)
    end = source.rfind("} // verus!")
    if start < 0 or end < 0 or end <= start:
        raise ValueError("shared vocabulary wrapper is malformed")
    return source[start + len(start_marker) : end].strip()


def vstd_source_file(declaration: dict[str, Any]) -> str:
    path = str(declaration["source_path"])
    marker = "source/vstd/"
    if marker not in path:
        raise ValueError(f"vstd declaration path is malformed: {path}")
    return path.split(marker, 1)[1]


def feedback_entry(
    row: dict[str, Any],
    source: dict[str, Any],
    equivalence: dict[str, Any],
    relation_evaluation: dict[str, Any],
) -> dict[str, Any]:
    copied = support.ROOT / source["copied_path"]
    path = str(copied)
    marker = "/library/"
    if marker not in path:
        raise ValueError(f"feedback source is outside Rust library: {path}")
    declaration = {
        "line": int(row["source_start_line"]),
        "observability": support.observability(row),
        "source_context": support.source_context(copied, row),
        "source_file": path.split(marker, 1)[1],
        "target": row["target"],
    }
    return {
        "available_in_verus_rust_1_96": True,
        "canonical_target": row["target"],
        "category": "result",
        "classification": "suitable_now",
        "classification_reasons": [],
        "declaration_count": 1,
        "declarations": [declaration],
        "display_paths": [row["target"]],
        "feedback_safe_name": support.safe_name(str(row["target"])),
        "kinds": [row["impl_kind"]],
        "modules": ["core::result"],
        "outcome_equivalence": equivalence,
        "recommended_contract_form": "assume_specification",
        "selected_relation_evaluation": relation_evaluation,
        "semantic_risks": support.feedback_risks(
            int(row["rustdoc_item_id"]), row
        ),
        "static_reward_eligible": True,
        "target": row["target"],
        "verification_declaration_count": 1,
        "verification_declarations": [declaration],
    }


def helper_usage_payload(
    rows: list[dict[str, Any]],
    blocks: dict[int, support.ContractBlock],
) -> dict[str, Any]:
    inventory = {
        int(row["rustdoc_item_id"]): row
        for row in rows
    }
    users: dict[str, list[int]] = {
        helper: [] for helper in support.helper_names()
    }
    for item_id, block in sorted(blocks.items()):
        for helper in support.used_helpers(block):
            users[helper].append(item_id)
    linked_to = {
        "result_into_iter_value_values": "result_into_iter_values",
        "result_iter_mut_value_identities": "result_iter_mut_identities",
        "result_iter_mut_value_values": "result_iter_mut_values",
        "result_iter_value_identities": "result_iter_identities",
        "result_iter_value_values": "result_iter_values",
    }
    records = []
    for helper in sorted(users):
        classification, boundary = support.helper_classification(helper)
        item_ids = users[helper]
        records.append(
            {
                "boundary": boundary,
                "classification": classification,
                "helper": helper,
                "linked_to": linked_to.get(helper),
                "rustdoc_item_ids": item_ids,
                "target_count": len(item_ids),
                "targets": [inventory[item_id]["target"] for item_id in item_ids],
            }
        )
    return {
        "contracts_sha256": support.sha256(support.CONTRACT_PATH),
        "defined_helper_count": len(records),
        "generated_target_count": len(blocks),
        "records": records,
        "schema_version": 1,
        "unused_helpers": sorted(
            helper for helper, item_ids in users.items() if not item_ids
        ),
        "vocabulary_path": str(
            support.VOCABULARY_PATH.relative_to(support.ROOT)
        ),
        "vocabulary_sha256": support.sha256(support.VOCABULARY_PATH),
        "whole_target_helpers": [],
    }


def outcome_equivalence_payload(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    records = [support.outcome_equivalence_record(row) for row in rows]
    counts = Counter(record["kind"] for record in records)
    return {
        "exact_equality_default": True,
        "exact_equality_count": len(records),
        "exact_observation_schema_equality_count": len(
            support.PROJECTED_EXACT_OBSERVATION_SCHEMAS
        ),
        "inventory_sha256": support.sha256(support.INVENTORY_PATH),
        "kind_counts": dict(sorted(counts.items())),
        "non_exact_equivalence_count": 0,
        "policy": (
            "Completeness uses exact equality. For values with private "
            "representation or returned references, exactness is defined over "
            "the explicitly named source-backed semantic observation schema; "
            "unmodeled representation is outside the theorem domain rather "
            "than quotiented as a non-exact output."
        ),
        "records": records,
        "schema_version": 3,
        "version_set_sha256": (
            support.outcome_equivalence_version_set_sha256(records)
        ),
    }


def package_manifest(counts: Counter[str]) -> dict[str, Any]:
    artifacts = []
    for relative in support.SPEC_PACKAGE_ARTIFACTS:
        path = support.ROOT / relative
        if not path.is_file():
            raise ValueError(f"specification artifact is missing: {relative}")
        artifacts.append(
            {
                "path": relative,
                "sha256": support.sha256(path),
            }
        )
    return {
        "artifacts": artifacts,
        "counts": {
            "exact_vstd": counts["exact_vstd"],
            "generated": counts["generated"],
            "specified": counts["exact_vstd"] + counts["generated"],
        },
        "module": "core::result",
        "proof_harnesses_authorized": False,
        "schema_version": 2,
    }


def panic_record(
    item_id: int, block: support.ContractBlock
) -> dict[str, Any]:
    if item_id == 29300:
        return {
            "classification": "panics_outside_requires",
            "direct_domain": "input is Err",
            "excluded_behavior": "input is Ok calls unwrap_failed",
        }
    if item_id in support.UNSAFE_IDS:
        branch = "Ok" if item_id == 29308 else "Err"
        return {
            "classification": "unsafe_precondition",
            "direct_domain": f"input is {branch}",
            "excluded_behavior": (
                "the opposite Result branch reaches "
                "hint::unreachable_unchecked"
            ),
        }
    if item_id in support.CALLBACK_IDS or item_id in {
        26760,
        26882,
        10004,
        10005,
        10010,
        11011,
        11356,
        11599,
        26942,
        29299,
        29312,
        29315,
        29329,
        29331,
        29343,
        29354,
        29366,
    }:
        return {
            "classification": "dependency_may_unwind",
            "direct_domain": None,
            "excluded_behavior": None,
        }
    unwind = (
        "no_unwind"
        if re.search(r"(?m)^\s*no_unwind\s*$", block.text)
        else None
    )
    return {
        "classification": (
            "source_unconditionally_no_unwind"
            if unwind is not None
            else "no_unwind_claim_not_made"
        ),
        "contract_unwind_clause": unwind,
        "direct_domain": None,
        "excluded_behavior": None,
    }


def derive_record(
    item_id: int, captures: dict[int, dict[str, Any]]
) -> dict[str, Any] | None:
    if item_id not in support.DERIVED_IDS:
        return None
    capture = captures.get(item_id)
    if capture is None:
        raise ValueError(f"missing derive capture for rustdoc-{item_id}")
    expanded = capture["expanded_method"]
    data = support.DERIVE_SOURCE_PATH.read_bytes()
    selected = data[int(expanded["start_byte"]) : int(expanded["end_byte"])]
    digest = hashlib.sha256(selected).hexdigest()
    if digest != expanded["sha256"]:
        raise ValueError(f"derive method hash mismatch for rustdoc-{item_id}")
    return {
        "capture_path": str(support.DERIVE_AUDIT_PATH.relative_to(support.ROOT)),
        "capture_sha256": support.sha256(support.DERIVE_AUDIT_PATH),
        "expanded_impl_header": capture["expanded_impl_header"],
        "expanded_method_end_byte": int(expanded["end_byte"]),
        "expanded_method_end_line": int(expanded["end_line"]),
        "expanded_method_sha256": expanded["sha256"],
        "expanded_method_start_byte": int(expanded["start_byte"]),
        "expanded_method_start_line": int(expanded["start_line"]),
        "expanded_path": str(
            support.DERIVE_SOURCE_PATH.relative_to(support.ROOT)
        ),
        "expanded_source_sha256": support.sha256(
            support.DERIVE_SOURCE_PATH
        ),
        "semantic_markers": capture["semantic_markers"],
    }


def generated_row(
    row: dict[str, Any],
    block: support.ContractBlock,
    captures: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    item_id = int(row["rustdoc_item_id"])
    requires, ensures = support.structured_clauses(block.text)
    semantic_record = {
        "ensures": [support.squash(clause) for clause in ensures],
        "requires": [support.squash(clause) for clause in requires],
    }
    return {
        "contract": {
            "binding": support.binding_text(block),
            "direct_ensures": semantic_record["ensures"],
            "marker": f"rustdoc-{item_id}",
            "path": str(support.CONTRACT_PATH.relative_to(support.ROOT)),
            "required_direct_fragments": list(
                support.DIRECT_FRAGMENTS[item_id]
            ),
            "requires": semantic_record["requires"],
            "segment_end_line": block.end_line,
            "segment_sha256": support.text_sha256(block.text),
            "segment_start_line": block.start_line,
            "semantic_clause_sha256": support.object_sha256(
                semantic_record
            ),
        },
        "dependencies": support.used_helpers(block),
        "derive_expansion": derive_record(item_id, captures),
        "disposition": "generated",
        "group": support.group_for(item_id),
        "mutation_kind": support.mutation_kind(item_id),
        "panic_behavior": panic_record(item_id, block),
        "rustdoc_item_id": item_id,
        "signature": row["signature"],
        "signature_shape_sha256": row["signature_shape_sha256"],
        "source": source_record(row),
        "source_fidelity": {
            "required_source_fragments": list(
                support.SOURCE_FRAGMENTS.get(item_id, ())
            ),
            "source_body_kind": row["source_body_kind"],
        },
        "status": "generated_validation_required",
        "target": row["target"],
    }


def exact_row(
    row: dict[str, Any],
    audit_row: dict[str, Any],
    declaration: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    item_id = int(row["rustdoc_item_id"])
    text = declaration_text(declaration)
    if support.text_sha256(text) != declaration["declaration_sha256"]:
        raise ValueError(f"exact declaration hash mismatch for {row['target']}")
    requires, ensures = support.structured_clauses(text)
    reference = {
        "declaration_id": declaration["declaration_id"],
        "declaration_sha256": declaration["declaration_sha256"],
        "end_line": int(declaration["end_line"]),
        "rustdoc_item_id": item_id,
        "source_path": declaration["source_path"],
        "source_sha256": declaration["source_sha256"],
        "start_line": int(declaration["start_line"]),
        "target": row["target"],
    }
    catalog = {
        "contract": {
            **reference,
            "binding": declaration["target_binding"],
            "direct_ensures": [
                support.squash(clause) for clause in ensures
            ],
            "requires": [
                support.squash(clause) for clause in requires
            ],
        },
        "dependencies": [],
        "derive_expansion": None,
        "disposition": "exact_vstd",
        "group": "exact_vstd",
        "mutation_kind": None,
        "panic_behavior": {
            "classification": "defined_by_loaded_vstd_contract"
        },
        "rustdoc_item_id": item_id,
        "signature": row["signature"],
        "signature_shape_sha256": row["signature_shape_sha256"],
        "source": source_record(row),
        "source_fidelity": {
            "exact_audit_lifetime_match_mode": audit_row[
                "lifetime_match_mode"
            ],
            "source_body_kind": row["source_body_kind"],
        },
        "status": "referenced_exact_vstd",
        "target": row["target"],
    }
    return catalog, reference


def main() -> int:
    support.validate_metadata_coverage()
    rows = support.inventory_rows()
    blocks = support.contract_blocks()
    captures = support.derived_captures()
    exact_audit = support.load_json(support.EXACT_AUDIT_PATH)
    audit_rows_raw = exact_audit.get("rows")
    declarations_raw = exact_audit.get("declarations")
    if not isinstance(audit_rows_raw, list) or not isinstance(
        declarations_raw, list
    ):
        raise ValueError("exact-vstd audit is malformed")
    audit_rows = {
        int(row["rustdoc_item_id"]): row
        for row in audit_rows_raw
        if isinstance(row, dict)
    }
    declarations = {
        str(row["declaration_id"]): row
        for row in declarations_raw
        if isinstance(row, dict)
    }
    helper_usage = helper_usage_payload(rows, blocks)
    equivalence = outcome_equivalence_payload(rows)
    support.write_json(support.HELPER_USAGE_PATH, helper_usage)
    support.write_json(support.OUTCOME_EQUIVALENCE_PATH, equivalence)
    relation_capability = support.feedback_relation_capability_payload(
        equivalence
    )
    support.write_json(
        support.FEEDBACK_RELATION_CAPABILITY_PATH,
        relation_capability,
    )
    common_relation_capability = (
        support.feedback_relation_capability_binding(
            relation_capability
        )
    )
    equivalence_by_id = {
        int(record["rustdoc_item_id"]): record
        for record in equivalence["records"]
    }

    catalog_rows: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    feedback_targets: list[dict[str, Any]] = []
    seed_candidates: dict[str, Any] = {}
    vstd_contexts: list[dict[str, Any]] = []
    vocabulary = vocabulary_inner()
    for row in rows:
        item_id = int(row["rustdoc_item_id"])
        disposition = row["disposition"]
        if disposition == "pending":
            block = blocks[item_id]
            catalog = generated_row(row, block, captures)
            source = catalog["source"]
            dependencies = support.used_helpers(block)
            requires, ensures = support.structured_clauses(block.text)
            equivalence_binding = support.outcome_equivalence_binding(
                equivalence_by_id[item_id], equivalence
            )
            relation_evaluation = (
                support.feedback_relation_target_classification(
                    equivalence_binding,
                    relation_capability,
                )
            )
            feedback_targets.append(
                feedback_entry(
                    row,
                    source,
                    equivalence_binding,
                    relation_evaluation,
                )
            )
            seed_candidates[str(row["target"])] = {
                "assumptions": [
                    helper
                    for helper in dependencies
                    if support.helper_classification(helper)[1]
                ],
                "canonical_target": row["target"],
                "contract_code": vocabulary + "\n\n" + block.text,
                "contract_form": "assume_specification",
                "decision": "add_spec",
                "ensures": ensures,
                "feature_gates": ["sized_hierarchy"],
                "feedback_safe_name": support.safe_name(str(row["target"])),
                "feedback_target": row["target"],
                "imports": IMPORTS,
                "outcome_equivalence": equivalence_binding,
                "rationale": (
                    "Direct ensures derived from frozen Rust 1.96 source "
                    f"excerpt {source['excerpt_sha256']}."
                ),
                "requires": requires,
                "risks": support.feedback_risks(item_id, row),
                "selected_relation_evaluation": relation_evaluation,
                "source_fidelity": (
                    "Bound to the exact frozen source span and the shared "
                    "helper-usage artifact."
                ),
                "source_line": str(row["source_start_line"]),
                "state_models": dependencies,
                "useful": True,
            }
        elif disposition == "exact_vstd":
            audit_row = audit_rows[item_id]
            declaration_id = str(audit_row["exact_declaration_id"])
            catalog, reference = exact_row(
                row, audit_row, declarations[declaration_id]
            )
            references.append(reference)
            declaration = declarations[declaration_id]
            vstd_contexts.append(
                {
                    "api_path": row["target"],
                    "signature": row["signature"],
                    "source_file": vstd_source_file(declaration),
                    "source_line": int(declaration["start_line"]),
                }
            )
        else:
            raise ValueError(
                f"unexpected inventory disposition {disposition!r}"
            )
        equivalence_record = equivalence_by_id[item_id]
        catalog["outcome_equivalence"] = (
            support.outcome_equivalence_binding(
                equivalence_record,
                equivalence,
            )
        )
        catalog_rows.append(catalog)

    counts = Counter(row["disposition"] for row in catalog_rows)
    support.write_json(
        support.FEEDBACK_MANIFEST_PATH,
        {
            "metadata": {
                "outcome_equivalence": (
                    support.outcome_equivalence_artifact_binding(
                        equivalence
                    )
                ),
                "scope": (
                    "core::result generated rows without an exact loaded "
                    "vstd contract"
                ),
                "selected_relation_evaluation": (
                    common_relation_capability
                ),
                "stable_inventory_rows": len(rows),
                "target_count": len(feedback_targets),
                "target_field": "canonical full Rust target",
            },
            "targets": sorted(
                feedback_targets, key=lambda value: value["target"]
            ),
        },
    )
    support.write_json(support.FEEDBACK_SEED_PATH, seed_candidates)
    support.write_json(
        support.VSTD_CONTRACTS_PATH,
        sorted(vstd_contexts, key=lambda value: value["api_path"]),
    )
    payload = {
        "counts": {
            "exact_vstd": counts["exact_vstd"],
            "generated": counts["generated"],
            "genuinely_impossible": 0,
            "pending": 0,
            "specified": counts["exact_vstd"] + counts["generated"],
            "stable_inventory_total": len(rows),
        },
        "inputs": {
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
        },
        "module": "core::result",
        "rows": catalog_rows,
        "schema_version": 1,
        "strict_specification_coverage": (
            (counts["exact_vstd"] + counts["generated"]) / len(rows)
            if rows
            else 0.0
        ),
    }
    references_payload = {
        "exact_reference_count": len(references),
        "references": references,
        "schema_version": 1,
        "source_rule": (
            "Reference only exact full-signature matches from "
            "inventory/exact_vstd_audit.json; do not redeclare them locally."
        ),
    }
    support.write_json(support.CATALOG_PATH, payload)
    support.write_json(support.EXACT_REFERENCES_PATH, references_payload)
    support.write_json(
        support.PACKAGE_MANIFEST_PATH,
        package_manifest(counts),
    )
    print(
        {
            "exact_vstd": counts["exact_vstd"],
            "generated": counts["generated"],
            "total": len(rows),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
